"""
Analysis router.

All endpoints accept an optional `Authorization: Bearer <token>` header so
users can supply their own GitHub token per-request. Falls back to the
server's GITHUB_TOKEN.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from deps import TokenDep

from models.analysis import (
    CodeFrequencyAnalysis,
    CommitActivityAnalysis,
    ContributorAnalysis,
    FullAnalysis,
    IssuesAnalysis,
    LanguageBreakdown,
    PullRequestsAnalysis,
    RateLimitStatus,
    ReleasesAnalysis,
    RecentCommitsAnalysis,
    RepoOverview,
    RepoSummary,
)
from services.analyzer import (
    build_summary,
    fetch_code_frequency,
    fetch_commit_activity,
    fetch_contributors,
    fetch_issues,
    fetch_languages,
    fetch_overview,
    fetch_pull_requests,
    fetch_rate_limit,
    fetch_recent_commits,
    fetch_releases,
    run_full_analysis,
)
from services.github_client import GitHubClient

router = APIRouter(prefix="/analyze", tags=["analysis"])


def _owner_repo(repo_url_or_slug: str) -> tuple[str, str]:
    """
    Accepts:
      - 'facebook/react'
      - 'https://github.com/facebook/react'
      - 'https://github.com/facebook/react.git'
    Returns (owner, repo).
    """
    slug = repo_url_or_slug.strip().rstrip("/").removesuffix(".git")
    if "github.com/" in slug:
        slug = slug.split("github.com/")[-1]
    parts = slug.split("/")
    if len(parts) != 2 or not all(parts):
        raise HTTPException(
            status_code=422,
            detail="repo must be 'owner/repo' or a full GitHub URL",
        )
    return parts[0], parts[1]


async def _client_ctx(token: str | None):
    return GitHubClient(token=token)


@router.get("/full", response_model=FullAnalysis, summary="Full repo analysis")
async def full_analysis(
    repo: Annotated[str, Query(description="owner/repo or full GitHub URL")],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await run_full_analysis(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/overview", response_model=RepoOverview)
async def overview(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_overview(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/languages", response_model=LanguageBreakdown)
async def languages(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_languages(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/contributors", response_model=ContributorAnalysis)
async def contributors(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_contributors(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/commit-activity", response_model=CommitActivityAnalysis)
async def commit_activity(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_commit_activity(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/recent-commits", response_model=RecentCommitsAnalysis)
async def recent_commits(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_recent_commits(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/issues", response_model=IssuesAnalysis)
async def issues(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            ov = await fetch_overview(client, owner, repo_name)
            return await fetch_issues(client, owner, repo_name, ov)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/pull-requests", response_model=PullRequestsAnalysis)
async def pull_requests(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_pull_requests(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/releases", response_model=ReleasesAnalysis)
async def releases(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_releases(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/code-frequency", response_model=CodeFrequencyAnalysis)
async def code_frequency(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_code_frequency(client, owner, repo_name)
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/summary", response_model=RepoSummary)
async def summary(
    repo: Annotated[str, Query()],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    async with GitHubClient(token=token) as client:
        try:
            full = await run_full_analysis(client, owner, repo_name)
            return full.summary
        except Exception as exc:
            _handle_github_error(exc)


@router.get("/rate-limit", response_model=RateLimitStatus, tags=["meta"])
async def rate_limit(token: TokenDep):
    async with GitHubClient(token=token) as client:
        return await fetch_rate_limit(client)


def _handle_github_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if hasattr(exc, "response") and exc.response is not None:
        status = exc.response.status_code
        if status == 404:
            raise HTTPException(status_code=404, detail="Repository not found")
        if status == 403:
            raise HTTPException(status_code=429, detail="GitHub rate limit exceeded")
        if status == 401:
            raise HTTPException(status_code=401, detail="Invalid GitHub token")
        raise HTTPException(status_code=502, detail=f"GitHub API error: {status}")
    raise HTTPException(status_code=500, detail=str(exc))
