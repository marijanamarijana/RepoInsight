from __future__ import annotations
import base64
import json
import logging
from typing import Any
from models.analysis import FullAnalysis
from services.analysis_sampling import OPEN_ISSUES
from services.github_client import GitHubClient

logger = logging.getLogger(__name__)

README_MAX_CHARS = 12_000
README_COMPACT_MAX_CHARS = 3_500
ISSUE_BODY_MAX_CHARS = 400
ISSUE_BODY_COMPACT_MAX_CHARS = 180
ISSUE_SAMPLE = min(15, OPEN_ISSUES)
ISSUE_SAMPLE_COMPACT = 8


async def fetch_readme_text(client: GitHubClient, owner: str, repo: str) -> str | None:
    try:
        data = await client.get(f"/repos/{owner}/{repo}/readme")
    except Exception as exc:
        logger.info("No README for %s/%s: %s", owner, repo, exc)
        return None

    raw = data.get("content")
    if not raw:
        return None

    try:
        decoded = base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("README decode failed for %s/%s: %s", owner, repo, exc)
        return None

    if len(decoded) > README_MAX_CHARS:
        return decoded[:README_MAX_CHARS] + "\n\n[README truncated for analysis]"
    return decoded


async def fetch_open_issue_snippets(client: GitHubClient, owner: str, repo: str) -> list[dict[str, Any]]:
    try:
        raw = await client.get(
            f"/repos/{owner}/{repo}/issues",
            params={
                "state": "open",
                "sort": "updated",
                "direction": "desc",
                "per_page": ISSUE_SAMPLE,
            },
        )
    except Exception as exc:
        logger.warning("Open issues fetch failed for %s/%s: %s", owner, repo, exc)
        return []

    snippets: list[dict[str, Any]] = []
    for item in raw:
        if "pull_request" in item:
            continue
        body = (item.get("body") or "").strip()
        if len(body) > ISSUE_BODY_MAX_CHARS:
            body = body[:ISSUE_BODY_MAX_CHARS] + "…"
        snippets.append(
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "labels": [lb["name"] for lb in item.get("labels", [])],
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "comments": item.get("comments", 0),
                "body_excerpt": body or None,
            }
        )
    return snippets


def _trim_readme(text: str | None, limit: int) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[README truncated for analysis]"


def build_compact_analysis_context(full: FullAnalysis, *, readme: str | None, open_issues: list[dict[str, Any]]) -> str:
    issues_trimmed = open_issues[:ISSUE_SAMPLE_COMPACT]
    payload = {
        "overview": full.overview.model_dump(mode="json"),
        "summary": full.summary.model_dump(mode="json"),
        "issues": full.issues.model_dump(mode="json"),
        "pull_requests": full.pull_requests.model_dump(mode="json"),
        "contributors": {
            "bus_factor": full.contributors.bus_factor,
            "gini_coefficient": full.contributors.gini_coefficient,
            "total_contributors_fetched": full.contributors.total_contributors_fetched,
            "top_contributors": [
                c.model_dump(mode="json")
                for c in full.contributors.top_contributors[:8]
            ],
        },
        "languages": [
            lang.model_dump(mode="json") for lang in full.languages.languages[:10]
        ],
        "commit_activity": {
            "sparkline": full.commit_activity.sparkline,
            "peak_week_commits": full.commit_activity.peak_week_commits,
            "avg_commits_per_week": full.commit_activity.avg_commits_per_week,
            "commits_by_day": full.commit_activity.commits_by_day,
        },
        "recent_commits": {
            "total_sampled": full.recent_commits.total_sampled,
            "peak_hour_utc": full.recent_commits.peak_hour_utc,
            "avg_message_length": full.recent_commits.avg_message_length,
        },
        "releases": {
            "total_fetched": full.releases.total_fetched,
            "last_releases": [
                r.model_dump(mode="json") for r in full.releases.last_releases[:5]
            ],
            "avg_days_between_releases": full.releases.avg_days_between_releases,
        },
        "code_frequency": {
            "net_lines": full.code_frequency.net_lines,
            "total_additions": full.code_frequency.total_additions,
            "total_deletions": full.code_frequency.total_deletions,
        },
        "readme_markdown": _trim_readme(readme, README_COMPACT_MAX_CHARS),
        "open_issues_sample": issues_trimmed,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_analysis_context(full: FullAnalysis, *, readme: str | None, open_issues: list[dict[str, Any]], compact: bool = False) -> str:
    if compact:
        return build_compact_analysis_context(full, readme=readme, open_issues=open_issues)

    payload = {
        "quantitative_analysis": full.model_dump(mode="json"),
        "readme_markdown": readme,
        "open_issues_sample": open_issues,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
