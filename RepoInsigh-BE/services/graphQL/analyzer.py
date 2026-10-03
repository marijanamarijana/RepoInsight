from __future__ import annotations
import asyncio
from collections import Counter
from typing import Any
from models.analysis import (
    CommitHourBucket,
    ContributorAnalysis,
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
)
from services.analysis_common import (
    STALE_ISSUE_DAYS,
    build_summary,
    contributor_analysis_from_raw,
    fetch_code_frequency,
    fetch_commit_activity,
    gini,
    median,
    parse_dt,
    sparkline,
    utc_now,
)
from services.analysis_sampling import CLOSED_PR_FIRST_COMMENT_SAMPLE, CONTRIBUTORS
from services.graphQL.github_client import GitHubClient
from services.graphQL.query_for_graphQL_full_analysis import REPOSITORY_ANALYSIS_QUERY

_parse_dt = parse_dt
_now = utc_now
_median = median
_gini = gini
_sparkline = sparkline


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
    issues = parse_issues(graphql_data, overview)
    pull_requests = parse_pull_requests(graphql_data)
    releases = parse_releases(graphql_data)

    contributors, commit_activity, code_frequency = await asyncio.gather(
        fetch_contributors(client, owner, repo),
        fetch_commit_activity(client, owner, repo),
        fetch_code_frequency(client, owner, repo),
        return_exceptions=False,
    )

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
    last_push = parse_dt(pushed_at)
    days_idle = (utc_now() - last_push).days

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
            dt = parse_dt(date_str)
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
                parse_dt(issue["closedAt"])
                - parse_dt(issue["createdAt"])
            ).total_seconds()

            close_times.append(diff / 3600)

    avg_close = (
        round(sum(close_times) / len(close_times) / 24, 2)
        if close_times
        else None
    )

    med_close = (
        round((median(close_times) or 0) / 24, 2)
        if close_times
        else None
    )

    stale = [
        issue
        for issue in open_issues
        if (
            utc_now()
            - parse_dt(issue["updatedAt"])
        ).days > STALE_ISSUE_DAYS
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
        stale_threshold_days=STALE_ISSUE_DAYS,
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
            parse_dt(pr["mergedAt"])
            - parse_dt(pr["createdAt"])
        ).total_seconds()

        merge_times.append(diff / 3600)

    avg_merge = (
        round(sum(merge_times) / len(merge_times) / 24, 2)
        if merge_times
        else None
    )

    med_merge = (
        round((median(merge_times) or 0) / 24, 2)
        if merge_times
        else None
    )

    response_times: list[float] = []

    for pr in closed_prs[:CLOSED_PR_FIRST_COMMENT_SAMPLE]:
        comments = pr["comments"]["nodes"]
        if not comments:
            continue

        first_comment = comments[0]
        diff = (
            parse_dt(first_comment["createdAt"])
            - parse_dt(pr["createdAt"])
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
            parse_dt(e.published_at)
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
    raw = await client.get(
        f"/repos/{owner}/{repo}/contributors",
        params={"per_page": CONTRIBUTORS},
    )
    return contributor_analysis_from_raw(raw[:CONTRIBUTORS])
