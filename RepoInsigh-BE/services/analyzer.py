from __future__ import annotations
import asyncio
import logging
from collections import Counter
from datetime import datetime
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
    empty_code_frequency,
    fetch_code_frequency,
    fetch_commit_activity,
    median,
    parse_dt,
    utc_now,
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


async def fetch_overview(client: GitHubClient, owner: str, repo: str) -> RepoOverview:
    data = await client.get(f"/repos/{owner}/{repo}")
    last_push = parse_dt(data["pushed_at"])
    days_idle = (utc_now() - last_push).days
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
    return contributor_analysis_from_raw(raw[:CONTRIBUTORS])


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
            dt = parse_dt(date_str)
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
            diff = (parse_dt(issue["closed_at"]) - parse_dt(issue["created_at"])).total_seconds()
            close_times.append(diff / 3600)

    avg_close = round(sum(close_times) / len(close_times) / 24, 2) if close_times else None
    med_close = round((median(close_times) or 0) / 24, 2) if close_times else None

    stale = [
        i for i in open_issues
        if (utc_now() - parse_dt(i["updated_at"])).days > STALE_ISSUE_DAYS
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
        stale_threshold_days=STALE_ISSUE_DAYS,
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
        diff = (parse_dt(pr["merged_at"]) - parse_dt(pr["created_at"])).total_seconds()
        merge_times.append(diff / 3600)

    avg_merge = round(sum(merge_times) / len(merge_times) / 24, 2) if merge_times else None
    med_merge = round((median(merge_times) or 0) / 24, 2) if merge_times else None

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
            diff = (parse_dt(comments[0]["created_at"]) - parse_dt(pr["created_at"])).total_seconds()
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
        dates = [parse_dt(e.published_at) for e in entries]
        gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]

    return ReleasesAnalysis(
        total_fetched=len(entries),
        last_releases=entries[:10],
        avg_days_between_releases=round(sum(gaps) / len(gaps), 1) if gaps else None,
        fastest_gap_days=min(gaps) if gaps else None,
        slowest_gap_days=max(gaps) if gaps else None,
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
        code_frequency = empty_code_frequency()

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
