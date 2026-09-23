from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone

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
from services.analysis_sampling import (
    CLOSED_ISSUES,
    CLOSED_PR_FIRST_COMMENT_SAMPLE,
    CLOSED_PULL_REQUESTS,
    CONTRIBUTORS,
    OPEN_ISSUES,
    OPEN_PULL_REQUESTS,
    RECENT_COMMITS,
    RELEASES,
    max_pages_for,
)
from services.github_client import GitHubClient

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
    vals = sorted(values)
    n = len(vals)
    if n == 0 or sum(vals) == 0:
        return 0.0
    csum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(vals))
    return round(csum / (n * sum(vals)), 4)


def _sparkline(totals: list[int]) -> str:
    peak = max(totals) if totals else 1
    return "".join(SPARKLINE_BLOCKS[int(t / peak * 8)] for t in totals)


async def fetch_overview(client: GitHubClient, owner: str, repo: str) -> RepoOverview:
    data = await client.get(f"/repos/{owner}/{repo}")
    last_push = _parse_dt(data["pushed_at"])
    days_idle = (_now() - last_push).days
    return RepoOverview(
        full_name=data["full_name"],
        description=data.get("description"),
        stars=data["stargazers_count"],
        forks=data["forks_count"],
        open_issues=data["open_issues_count"],
        watchers=data["watchers_count"],
        default_branch=data["default_branch"],
        primary_language=data.get("language"),
        license=data.get("license", {}).get("name") if data.get("license") else None,
        created_at=data["created_at"],
        last_pushed_at=data["pushed_at"],
        days_since_last_push=days_idle,
        is_archived=data.get("archived", False),
        is_fork=data.get("fork", False),
        topics=data.get("topics", []),
    )


async def fetch_languages(client: GitHubClient, owner: str, repo: str) -> LanguageBreakdown:
    data: dict[str, int] = await client.get(f"/repos/{owner}/{repo}/languages")
    total = sum(data.values())
    entries = [
        LanguageEntry(language=lang, bytes=b, percentage=round(b / total * 100, 2))
        for lang, b in sorted(data.items(), key=lambda x: -x[1])
    ]
    return LanguageBreakdown(total_bytes=total, languages=entries)


async def fetch_contributors(client: GitHubClient, owner: str, repo: str) -> ContributorAnalysis:
    raw = await client.get_paginated(
        f"/repos/{owner}/{repo}/contributors",
        max_pages=max_pages_for(CONTRIBUTORS),
    )
    raw = raw[:CONTRIBUTORS]
    total_commits = sum(c["contributions"] for c in raw) or 1

    entries = [
        ContributorEntry(
            login=c["login"],
            avatar_url=c["avatar_url"],
            contributions=c["contributions"],
            percentage=round(c["contributions"] / total_commits * 100, 2),
        )
        for c in raw
    ]

    cumulative, bus_factor = 0, 0
    for c in raw:
        cumulative += c["contributions"]
        bus_factor += 1
        if cumulative / total_commits >= 0.8:
            break

    ownership: dict[str, int] = {}
    for pct in (50, 80, 95):
        cum, count = 0, 0
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
            sparkline="", peak_week_commits=0, avg_commits_per_week=0,
            weeks=[], commits_by_day={},
        )

    totals = [w["total"] for w in raw]
    day_totals = [sum(w["days"][i] for w in raw) for i in range(7)]

    weeks = [
        WeeklyActivity(
            week_start=datetime.utcfromtimestamp(w["week"]).strftime("%Y-%m-%d"),
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
        commits_by_day={name: count for name, count in zip(DAY_NAMES, day_totals)},
    )


async def fetch_recent_commits(client: GitHubClient, owner: str, repo: str) -> RecentCommitsAnalysis:
    raw = await client.get_paginated(
        f"/repos/{owner}/{repo}/commits",
        max_pages=max_pages_for(RECENT_COMMITS),
    )
    raw = raw[:RECENT_COMMITS]
    if not raw:
        return RecentCommitsAnalysis(
            total_sampled=0, avg_message_length=0,
            min_message_length=0, max_message_length=0,
            commits_by_hour=[], peak_hour_utc=0,
        )

    msg_lengths = [len(c["commit"]["message"]) for c in raw]
    hour_counter: Counter[int] = Counter()
    for c in raw:
        date_str = c["commit"]["author"]["date"]
        try:
            dt = _parse_dt(date_str)
            hour_counter[dt.hour] += 1
        except Exception:
            pass

    by_hour = [CommitHourBucket(hour=h, count=hour_counter.get(h, 0)) for h in range(24)]
    peak_hour = hour_counter.most_common(1)[0][0] if hour_counter else 0

    return RecentCommitsAnalysis(
        total_sampled=len(raw),
        avg_message_length=round(sum(msg_lengths) / len(msg_lengths), 1),
        min_message_length=min(msg_lengths),
        max_message_length=max(msg_lengths),
        commits_by_hour=by_hour,
        peak_hour_utc=peak_hour,
    )


async def fetch_issues(
    client: GitHubClient, owner: str, repo: str, overview: RepoOverview
) -> IssuesAnalysis:
    closed_raw, open_raw = await asyncio.gather(
        client.get_paginated(
            f"/repos/{owner}/{repo}/issues",
            params={"state": "closed", "sort": "updated"},
            max_pages=max_pages_for(CLOSED_ISSUES),
        ),
        client.get_paginated(
            f"/repos/{owner}/{repo}/issues",
            params={"state": "open", "sort": "updated"},
            max_pages=max_pages_for(OPEN_ISSUES),
        ),
    )

    closed_issues = [i for i in closed_raw if "pull_request" not in i][:CLOSED_ISSUES]
    open_issues = [i for i in open_raw if "pull_request" not in i][:OPEN_ISSUES]

    close_times: list[float] = []
    for issue in closed_issues:
        if issue.get("closed_at") and issue.get("created_at"):
            diff = (_parse_dt(issue["closed_at"]) - _parse_dt(issue["created_at"])).total_seconds()
            close_times.append(diff / 3600)

    avg_close = round(sum(close_times) / len(close_times) / 24, 2) if close_times else None
    med_close = round((_median(close_times) or 0) / 24, 2) if close_times else None

    stale = [
        i for i in open_issues
        if (_now() - _parse_dt(i["updated_at"])).days > 90
    ]

    label_counter: Counter[str] = Counter()
    for issue in open_issues + closed_issues:
        for label in issue.get("labels", []):
            label_counter[label["name"]] += 1

    return IssuesAnalysis(
        open_count=overview.open_issues,
        closed_sampled=len(closed_issues),
        open_sampled=len(open_issues),
        avg_close_time_days=avg_close,
        median_close_time_days=med_close,
        stale_issues_count=len(stale),
        stale_threshold_days=90,
        top_labels=[LabelEntry(name=n, count=c) for n, c in label_counter.most_common(10)],
    )


async def fetch_pull_requests(client: GitHubClient, owner: str, repo: str) -> PullRequestsAnalysis:
    closed_raw, open_raw = await asyncio.gather(
        client.get_paginated(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "closed", "sort": "updated"},
            max_pages=max_pages_for(CLOSED_PULL_REQUESTS),
        ),
        client.get_paginated(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "open", "sort": "updated"},
            max_pages=max_pages_for(OPEN_PULL_REQUESTS),
        ),
    )

    closed_raw = closed_raw[:CLOSED_PULL_REQUESTS]
    open_raw = open_raw[:OPEN_PULL_REQUESTS]

    merged   = [pr for pr in closed_raw if pr.get("merged_at")]
    rejected = [pr for pr in closed_raw if not pr.get("merged_at")]
    total_closed = len(closed_raw)
    merge_rate = round(len(merged) / total_closed * 100, 1) if total_closed else 0.0

    merge_times: list[float] = []
    for pr in merged:
        diff = (_parse_dt(pr["merged_at"]) - _parse_dt(pr["created_at"])).total_seconds()
        merge_times.append(diff / 3600)

    avg_merge = round(sum(merge_times) / len(merge_times) / 24, 2) if merge_times else None
    med_merge = round((_median(merge_times) or 0) / 24, 2) if merge_times else None

    response_times: list[float] = []
    sample_prs = closed_raw[:CLOSED_PR_FIRST_COMMENT_SAMPLE]
    comment_tasks = [
        client.get(
            f"/repos/{owner}/{repo}/issues/{pr['number']}/comments",
            params={"per_page": 1},
        )
        for pr in sample_prs
    ]
    comment_results = await asyncio.gather(*comment_tasks, return_exceptions=True)
    for pr, comments in zip(sample_prs, comment_results):
        if isinstance(comments, list) and comments:
            diff = (_parse_dt(comments[0]["created_at"]) - _parse_dt(pr["created_at"])).total_seconds()
            response_times.append(diff / 3600)

    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else None

    return PullRequestsAnalysis(
        open_count=len(open_raw),
        closed_sampled=total_closed,
        merged_count=len(merged),
        rejected_count=len(rejected),
        merge_rate_pct=merge_rate,
        avg_time_to_merge_days=avg_merge,
        median_time_to_merge_days=med_merge,
        avg_first_response_hours=avg_response,
    )


async def fetch_releases(client: GitHubClient, owner: str, repo: str) -> ReleasesAnalysis:
    raw = await client.get_paginated(
        f"/repos/{owner}/{repo}/releases",
        max_pages=max_pages_for(RELEASES),
    )
    raw = raw[:RELEASES]

    entries = [
        ReleaseEntry(
            tag=r["tag_name"],
            name=r.get("name") or r["tag_name"],
            published_at=r["published_at"],
            is_prerelease=r["prerelease"],
        )
        for r in raw if r.get("published_at")
    ]

    gaps: list[int] = []
    if len(entries) >= 2:
        dates = [_parse_dt(e.published_at) for e in entries]
        gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]

    return ReleasesAnalysis(
        total_fetched=len(entries),
        last_releases=entries[:10],
        avg_days_between_releases=round(sum(gaps) / len(gaps), 1) if gaps else None,
        fastest_gap_days=min(gaps) if gaps else None,
        slowest_gap_days=max(gaps) if gaps else None,
    )


async def fetch_code_frequency(client: GitHubClient, owner: str, repo: str) -> CodeFrequencyAnalysis:
    try:
        raw = await client.get(f"/repos/{owner}/{repo}/stats/code_frequency")
    except Exception as exc:
        logger.warning("fetch_code_frequency failed for %s/%s: %s", owner, repo, exc)
        return CodeFrequencyAnalysis(
            total_additions=0, total_deletions=0, net_lines=0, recent_weeks=[]
        )

    if not raw:
        return CodeFrequencyAnalysis(
            total_additions=0, total_deletions=0, net_lines=0, recent_weeks=[]
        )

    total_add = sum(w[1] for w in raw if w[1] > 0)
    total_del = sum(abs(w[2]) for w in raw if w[2] < 0)

    recent = [
        CodeFrequencyWeek(
            week_start=datetime.utcfromtimestamp(w[0]).strftime("%Y-%m-%d"),
            additions=w[1],
            deletions=abs(w[2]),
        )
        for w in raw[-12:]
    ]

    return CodeFrequencyAnalysis(
        total_additions=total_add,
        total_deletions=total_del,
        net_lines=total_add - total_del,
        recent_weeks=recent,
    )


def build_summary(
    overview: RepoOverview,
    contributors: ContributorAnalysis,
    pull_requests: PullRequestsAnalysis,
    issues: IssuesAnalysis,
    releases: ReleasesAnalysis,
) -> RepoSummary:
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


async def run_full_analysis(client: GitHubClient, owner: str, repo: str) -> FullAnalysis:
    overview = await fetch_overview(client, owner, repo)

    results = await asyncio.gather(
        fetch_languages(client, owner, repo),
        fetch_contributors(client, owner, repo),
        fetch_commit_activity(client, owner, repo),
        fetch_recent_commits(client, owner, repo),
        fetch_issues(client, owner, repo, overview),
        fetch_pull_requests(client, owner, repo),
        fetch_releases(client, owner, repo),
        fetch_code_frequency(client, owner, repo),
        return_exceptions=True,
    )

    (   languages,
        contributors,
        commit_activity,
        recent_commits,
        issues,
        pull_requests,
        releases,
        code_frequency,
    ) = results

    if isinstance(code_frequency, Exception):
        logger.warning("code_frequency failed, using empty fallback: %s", code_frequency)
        code_frequency = CodeFrequencyAnalysis(
            total_additions=0, total_deletions=0, net_lines=0, recent_weeks=[])

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


async def fetch_rate_limit(client: GitHubClient) -> RateLimitStatus:
    data = await client.rate_limit()
    core = data["resources"]["core"]
    reset_at = datetime.utcfromtimestamp(core["reset"]).strftime("%Y-%m-%dT%H:%M:%SZ")
    return RateLimitStatus(
        limit=core["limit"],
        remaining=core["remaining"],
        used=core["limit"] - core["remaining"],
        reset_at=reset_at,
    )
