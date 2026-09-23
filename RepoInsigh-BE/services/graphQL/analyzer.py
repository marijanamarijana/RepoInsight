from __future__ import annotations
import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from models.analysis import (
    CodeFrequencyAnalysis,
    CodeFrequencyWeek,
    CommitActivityAnalysis,
    CommitHourBucket,
    ContributorAnalysis,
    ContributorEntry,
    FullAnalysis,
    IssuesAnalysis,
    LabelEntry,
    LanguageBreakdown,
    LanguageEntry,
    PullRequestsAnalysis,
    RateLimitStatus,
    ReleaseEntry,
    ReleasesAnalysis,
    RecentCommitsAnalysis,
    RepoOverview,
    RepoSummary,
    WeeklyActivity,
)
from services.graphQL.github_client import GitHubClient
from services.graphQL.query_for_graphQL_full_analysis import REPOSITORY_ANALYSIS_QUERY

logger = logging.getLogger(__name__)

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SPARKLINE_BLOCKS = " ▁▂▃▄▅▆▇█"
TEST_PATTERNS = ["-test.", ".test.", ".spec.", "__tests__", "/test/", "/tests/", "_test."]


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _gini(values: list[int]) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    n = len(vals)
    if n == 0 or sum(vals) == 0:
        return 0.0
    csum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(vals))
    return round(csum / (n * sum(vals)), 4)


def _sparkline(totals: list[int]) -> str:
    peak = max(totals) if totals else 1
    return "".join(SPARKLINE_BLOCKS[int(t / peak * 8)] for t in totals)

async def fetch_rate_limit(client: GitHubClient) -> RateLimitStatus:
    data = await client.rate_limit()
    reset_at = data["resetAt"]

    return RateLimitStatus(
        limit=data["limit"],
        remaining=data["remaining"],
        used=data["used"],
        reset_at=reset_at,
    )

async def run_full_analysis(client: GitHubClient, owner: str, repo: str) -> FullAnalysis:
    graphql_data = await client.graphql(
        REPOSITORY_ANALYSIS_QUERY,
        {
            "owner": owner,
            "repo": repo,
        },
    )

    overview = parse_repository_overview(graphql_data)
    languages = parse_languages(graphql_data)
    recent_commits = parse_recent_commits(graphql_data)
    issues = parse_issues(graphql_data, overview,)
    pull_requests = parse_pull_requests(graphql_data)
    releases = parse_releases(graphql_data)

    (contributors, commit_activity, code_frequency,) = await asyncio.gather(fetch_contributors(client, owner, repo,),
                                                                            fetch_commit_activity(client, owner, repo,),
                                                                            fetch_code_frequency(client, owner, repo,),
                                                                            return_exceptions=False)


    summary = build_summary(overview, contributors, pull_requests, issues, releases)

    return FullAnalysis(
        overview=overview,
        languages=languages,
        contributors=contributors,
        commit_activity=commit_activity,
        recent_commits=recent_commits,
        issues=issues,
        pull_requests=pull_requests,
        releases=releases,
        code_frequency=code_frequency,
        summary=summary,
    )

def parse_repository_overview(data: dict[str, Any]) -> RepoOverview:
    repo = data["repository"]
    pushed_at = repo["pushedAt"]
    last_push = _parse_dt(pushed_at)
    days_idle = (_now() - last_push).days

    topics = [
        node["topic"]["name"]
        for node in repo["repositoryTopics"]["nodes"]
    ]

    return RepoOverview(
        full_name=repo["nameWithOwner"],
        description=repo.get("description"),
        stars=repo["stargazerCount"],
        forks=repo["forkCount"],
        open_issues=repo["issues"]["totalCount"],
        watchers=repo["watchers"]["totalCount"],
        default_branch=(
            repo["defaultBranchRef"]["name"]
            if repo.get("defaultBranchRef") and repo["defaultBranchRef"]["name"] is not None
            else None
        ),
        primary_language=(
            repo["primaryLanguage"]["name"]
            if repo.get("primaryLanguage")
            else None
        ),
        license=(
            repo["licenseInfo"]["name"]
            if repo.get("licenseInfo")
            else None
        ),
        created_at=repo["createdAt"],
        last_pushed_at=pushed_at,
        days_since_last_push=days_idle,
        is_archived=repo["isArchived"],
        is_fork=repo["isFork"],
        topics=topics,
    )


def parse_languages(data: dict[str, Any]) -> LanguageBreakdown:
    edges = data["repository"]["languages"]["edges"]
    total = sum(
        edge["size"]
        for edge in edges
    )
    entries = [
        LanguageEntry(
            language=edge["node"]["name"],
            bytes=edge["size"],
            percentage=round(
                edge["size"] / total * 100,
                2,
            ),
        )
        for edge in edges
    ]

    return LanguageBreakdown(
        total_bytes=total,
        languages=entries,
    )

def parse_recent_commits(data: dict[str, Any]) -> RecentCommitsAnalysis:
    repo = data["repository"]
    branch = repo.get("defaultBranchRef")

    if not branch or not branch.get("target"):
        return RecentCommitsAnalysis(
            total_sampled=0,
            avg_message_length=0,
            min_message_length=0,
            max_message_length=0,
            commits_by_hour=[],
            peak_hour_utc=0,
        )

    history = branch["target"]["history"]["nodes"]

    if not history:
        return RecentCommitsAnalysis(
            total_sampled=0,
            avg_message_length=0,
            min_message_length=0,
            max_message_length=0,
            commits_by_hour=[],
            peak_hour_utc=0,
        )

    lengths = [
        len(commit["message"])
        for commit in history
    ]

    hour_counter: Counter[int] = Counter()

    for commit in history:
        date_str = commit.get("committedDate")

        if not date_str:
            continue

        try:
            dt = _parse_dt(date_str)
            hour_counter[dt.hour] += 1
        except Exception:
            pass

    by_hour = [
        CommitHourBucket(
            hour=h,
            count=hour_counter.get(h, 0),
        )
        for h in range(24)
    ]

    peak_hour = (
        hour_counter.most_common(1)[0][0]
        if hour_counter
        else 0
    )

    return RecentCommitsAnalysis(
        total_sampled=len(history),
        avg_message_length=round(sum(lengths) / len(lengths), 1),
        min_message_length=min(lengths),
        max_message_length=max(lengths),
        commits_by_hour=by_hour,
        peak_hour_utc=peak_hour,
    )

def parse_issues(data: dict[str, Any], overview: RepoOverview) -> IssuesAnalysis:
    repo = data["repository"]
    open_issues = repo["openIssues"]["nodes"]
    closed_issues = repo["closedIssues"]["nodes"]
    close_times: list[float] = []

    for issue in closed_issues:
        if issue.get("closedAt") and issue.get("createdAt"):
            diff = (
                _parse_dt(issue["closedAt"])
                - _parse_dt(issue["createdAt"])
            ).total_seconds()

            close_times.append(diff / 3600)

    avg_close = (
        round(sum(close_times) / len(close_times) / 24, 2)
        if close_times
        else None
    )

    med_close = (
        round((_median(close_times) or 0) / 24, 2)
        if close_times
        else None
    )

    stale = [
        issue
        for issue in open_issues
        if (
            _now()
            - _parse_dt(issue["updatedAt"])
        ).days > 90
    ]

    label_counter: Counter[str] = Counter()

    for issue in open_issues + closed_issues:
        for label in issue["labels"]["nodes"]:
            label_counter[label["name"]] += 1

    return IssuesAnalysis(
        open_count=overview.open_issues,
        closed_sampled=len(closed_issues),
        open_sampled=len(open_issues),
        avg_close_time_days=avg_close,
        median_close_time_days=med_close,
        stale_issues_count=len(stale),
        stale_threshold_days=90,
        top_labels=[
            LabelEntry(name=name, count=count)
            for name, count
            in label_counter.most_common(10)
        ],
    )


def parse_pull_requests(data: dict[str, Any]) -> PullRequestsAnalysis:
    repo = data["repository"]
    open_prs = repo["openPullRequests"]["nodes"]
    closed_prs = repo["closedPullRequests"]["nodes"]

    merged = [
        pr
        for pr in closed_prs
        if pr.get("mergedAt")
    ]

    rejected = [
        pr
        for pr in closed_prs
        if not pr.get("mergedAt")
    ]

    total_closed = len(closed_prs)

    merge_rate = (
        round(len(merged) / total_closed * 100, 1)
        if total_closed
        else 0.0
    )

    merge_times: list[float] = []

    for pr in merged:
        if not pr.get("createdAt") or not pr.get("mergedAt"):
            continue

        diff = (
            _parse_dt(pr["mergedAt"])
            - _parse_dt(pr["createdAt"])
        ).total_seconds()

        merge_times.append(diff / 3600)

    avg_merge = (
        round(sum(merge_times) / len(merge_times) / 24, 2)
        if merge_times
        else None
    )

    med_merge = (
        round((_median(merge_times) or 0) / 24, 2)
        if merge_times
        else None
    )

    response_times: list[float] = []

    for pr in closed_prs[:10]:
        comments = pr["comments"]["nodes"]
        if not comments:
            continue

        first_comment = comments[0]
        diff = (
            _parse_dt(first_comment["createdAt"])
            - _parse_dt(pr["createdAt"])
        ).total_seconds()

        response_times.append(diff / 3600)

    avg_response = (
        round(sum(response_times) / len(response_times), 2)
        if response_times
        else None
    )

    return PullRequestsAnalysis(
        open_count=len(open_prs),
        closed_sampled=total_closed,
        merged_count=len(merged),
        rejected_count=len(rejected),
        merge_rate_pct=merge_rate,
        avg_time_to_merge_days=avg_merge,
        median_time_to_merge_days=med_merge,
        avg_first_response_hours=avg_response,
    )

def parse_releases(data: dict[str, Any]) -> ReleasesAnalysis:
    raw = data["repository"]["releases"]["nodes"]

    entries = [
        ReleaseEntry(
            tag=r["tagName"],
            name=r.get("name") or r["tagName"],
            published_at=r["publishedAt"],
            is_prerelease=r["isPrerelease"],
        )
        for r in raw
        if r.get("publishedAt")
    ]
    gaps: list[int] = []

    if len(entries) >= 2:
        dates = [
            _parse_dt(e.published_at)
            for e in entries
        ]

        gaps = [
            (dates[i] - dates[i + 1]).days
            for i in range(len(dates) - 1)
        ]

    return ReleasesAnalysis(
        total_fetched=len(entries),
        last_releases=entries[:10],
        avg_days_between_releases=(
            round(sum(gaps) / len(gaps), 1)
            if gaps
            else None
        ),
        fastest_gap_days=min(gaps) if gaps else None,
        slowest_gap_days=max(gaps) if gaps else None,
    )

async def fetch_contributors(client: GitHubClient, owner: str, repo: str) -> ContributorAnalysis:
    raw = await client.get(f"/repos/{owner}/{repo}/contributors",
        params={
            "per_page": 100,
        },
    )
    total_commits = (sum(c["contributions"] for c in raw) or 1)

    entries = [
        ContributorEntry(
            login=c["login"],
            avatar_url=c["avatar_url"],
            contributions=c["contributions"],
            percentage=round(c["contributions"]/ total_commits * 100, 2),
        )
        for c in raw
    ]

    cumulative = 0
    bus_factor = 0

    for c in raw:
        cumulative += c["contributions"]
        bus_factor += 1

        if cumulative / total_commits >= 0.8:
            break

    ownership: dict[str, int] = {}

    for pct in (50, 80, 95):
        cum = 0
        count = 0
        for c in raw:
            cum += c["contributions"]
            count += 1
            if cum / total_commits >= pct / 100:
                break
        ownership[f"{pct}%"] = count

    return ContributorAnalysis(
        total_contributors_fetched=len(raw),
        total_commits_sampled=total_commits,
        bus_factor=bus_factor,
        gini_coefficient=_gini([c["contributions"] for c in raw]),
        top_contributors=entries[:15],
        ownership=ownership,
    )

async def fetch_commit_activity(client: GitHubClient, owner: str, repo: str) -> CommitActivityAnalysis:
    raw = await client.get(f"/repos/{owner}/{repo}/stats/commit_activity")

    if not raw:
        return CommitActivityAnalysis(
            sparkline="",
            peak_week_commits=0,
            avg_commits_per_week=0,
            weeks=[],
            commits_by_day={},
        )

    totals = [w["total"] for w in raw]
    day_totals = [sum(w["days"][i] for w in raw) for i in range(7)]

    weeks = [
        WeeklyActivity(
            week_start=datetime.utcfromtimestamp(
                w["week"]
            ).strftime("%Y-%m-%d"),

            total=w["total"],
            days=w["days"],
        )
        for w in raw
    ]

    return CommitActivityAnalysis(
        sparkline=_sparkline(totals),
        peak_week_commits=max(totals),
        avg_commits_per_week=round(sum(totals) / len(totals), 2),
        weeks=weeks,
        commits_by_day={
            name: count
            for name, count
            in zip(DAY_NAMES, day_totals)
        },
    )

async def fetch_code_frequency(client: GitHubClient,  owner: str, repo: str) -> CodeFrequencyAnalysis:
    try:
        raw = await client.get(f"/repos/{owner}/{repo}/stats/code_frequency")
    except Exception as exc:
        logger.warning(
            "fetch_code_frequency failed for %s/%s: %s",
            owner,
            repo,
            exc,
        )

        return CodeFrequencyAnalysis(
            total_additions=0,
            total_deletions=0,
            net_lines=0,
            recent_weeks=[],
        )

    if not raw:
        return CodeFrequencyAnalysis(
            total_additions=0,
            total_deletions=0,
            net_lines=0,
            recent_weeks=[],
        )

    total_add = sum(w[1] for w in raw if w[1] > 0)
    total_del = sum(abs(w[2]) for w in raw if w[2] < 0)

    recent = [
        CodeFrequencyWeek(
            week_start=datetime.utcfromtimestamp(
                w[0]
            ).strftime("%Y-%m-%d"),
            additions=w[1],
            deletions=abs(w[2]),)
        for w in raw[-12:]
    ]

    return CodeFrequencyAnalysis(
        total_additions=total_add,
        total_deletions=total_del,
        net_lines=total_add - total_del,
        recent_weeks=recent,
    )

def build_summary(overview: RepoOverview,
                contributors: ContributorAnalysis,
                pull_requests: PullRequestsAnalysis,
                issues: IssuesAnalysis,
                releases: ReleasesAnalysis ) -> RepoSummary:
    return RepoSummary(
        repo=overview.full_name,
        stars=overview.stars,
        forks=overview.forks,
        open_issues=overview.open_issues,
        days_since_last_push=overview.days_since_last_push,
        primary_language=overview.primary_language,
        bus_factor=contributors.bus_factor,
        gini_coefficient=contributors.gini_coefficient,
        pr_merge_rate_pct=pull_requests.merge_rate_pct,
        avg_pr_merge_days=pull_requests.avg_time_to_merge_days,
        avg_issue_close_days=issues.avg_close_time_days,
        total_releases=releases.total_fetched,
        top_contributors=[c.login for c in contributors.top_contributors[:5]],
    )