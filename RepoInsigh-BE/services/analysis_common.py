from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from models.analysis import (
    CodeFrequencyAnalysis,
    CodeFrequencyWeek,
    CommitActivityAnalysis,
    ContributorAnalysis,
    ContributorEntry,
    IssuesAnalysis,
    PullRequestsAnalysis,
    ReleasesAnalysis,
    RepoOverview,
    RepoSummary,
    WeeklyActivity,
)

logger = logging.getLogger(__name__)

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SPARKLINE_BLOCKS = " ▁▂▃▄▅▆▇█"
STALE_ISSUE_DAYS = 90


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def gini(values: list[int]) -> float:
    vals = sorted(values)
    n = len(vals)
    if n == 0 or sum(vals) == 0:
        return 0.0
    csum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(vals))
    return round(csum / (n * sum(vals)), 4)


def sparkline(totals: list[int]) -> str:
    peak = max(totals, default=0) or 1
    return "".join(SPARKLINE_BLOCKS[int(t / peak * 8)] for t in totals)


def contributor_analysis_from_raw(raw: list[dict[str, Any]]) -> ContributorAnalysis:
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
        gini_coefficient=gini([c["contributions"] for c in raw]),
        top_contributors=entries[:15],
        ownership=ownership,
    )


def commit_activity_from_raw(raw: list[dict[str, Any]] | None) -> CommitActivityAnalysis:
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
            week_start=datetime.utcfromtimestamp(w["week"]).strftime("%Y-%m-%d"),
            total=w["total"],
            days=w["days"],
        )
        for w in raw
    ]
    return CommitActivityAnalysis(
        sparkline=sparkline(totals),
        peak_week_commits=max(totals),
        avg_commits_per_week=round(sum(totals) / len(totals), 2),
        weeks=weeks,
        commits_by_day={name: count for name, count in zip(DAY_NAMES, day_totals)},
    )


def empty_code_frequency() -> CodeFrequencyAnalysis:
    return CodeFrequencyAnalysis(
        total_additions=0, total_deletions=0, net_lines=0, recent_weeks=[]
    )


def code_frequency_from_raw(raw: list[list[int]] | None) -> CodeFrequencyAnalysis:
    if not raw:
        return empty_code_frequency()

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


async def fetch_commit_activity(client: Any, owner: str, repo: str) -> CommitActivityAnalysis:
    raw = await client.get(f"/repos/{owner}/{repo}/stats/commit_activity")
    return commit_activity_from_raw(raw)


async def fetch_code_frequency(client: Any, owner: str, repo: str) -> CodeFrequencyAnalysis:
    try:
        raw = await client.get(f"/repos/{owner}/{repo}/stats/code_frequency")
    except Exception as exc:
        logger.warning("fetch_code_frequency failed for %s/%s: %s", owner, repo, exc)
        return empty_code_frequency()
    return code_frequency_from_raw(raw)


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
