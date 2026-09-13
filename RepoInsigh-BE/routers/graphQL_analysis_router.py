from __future__ import annotations
from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Query
from models.analysis import FullAnalysis, RateLimitStatus
from services.graphQL.analyzer import fetch_rate_limit, run_full_analysis
from services.graphQL.github_client import GitHubClient

router = APIRouter(
    prefix="/graphQL/analyze",
    tags=["analysis"],
)

TokenDep = Annotated[
    Optional[str],
    Query(description="GitHub personal access token"),
]

def _owner_repo(repo_url_or_slug: str) -> tuple[str, str]:
    """
    Accepts:

    - facebook/react
    - https://github.com/facebook/react
    - https://github.com/facebook/react.git

    Returns:
        (owner, repo)
    """
    slug = (
        repo_url_or_slug
        .strip()
        .rstrip("/")
        .removesuffix(".git")
    )

    if "github.com/" in slug:
        slug = slug.split("github.com/", 1)[1]

    parts = slug.split("/")

    if len(parts) != 2 or not all(parts):
        raise HTTPException(
            status_code=422,
            detail=(
                "repo must be 'owner/repo' "
                "or a full GitHub URL"
            ),
        )

    return parts[0], parts[1]


@router.get(
    "/full",
    response_model=FullAnalysis,
    summary="Full repo analysis",
)
async def full_analysis(
    repo: Annotated[
        str,
        Query(
            description="owner/repo or full GitHub URL"
        ),
    ],
    token: TokenDep = None,
):
    owner, repo_name = _owner_repo(repo)

    async with GitHubClient(token=token) as client:
        try:
            return await run_full_analysis(
                client,
                owner,
                repo_name,
            )

        except Exception as exc:
            _handle_github_error(exc)


@router.get(
    "/rate-limit",
    response_model=RateLimitStatus,
    tags=["meta"],
)
async def rate_limit(token: TokenDep = None):
    async with GitHubClient(token=token) as client:
        try:
            return await fetch_rate_limit(client)

        except Exception as exc:
            _handle_github_error(exc)


def _handle_github_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    if hasattr(exc, "response") and exc.response is not None:
        status = exc.response.status_code
        if status == 404:
            raise HTTPException(
                status_code=404,
                detail="Repository not found",
            )

        if status == 403:
            raise HTTPException(
                status_code=429,
                detail="GitHub rate limit exceeded",
            )

        if status == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid GitHub token",
            )

        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {status}",
        )

    raise HTTPException(
        status_code=500,
        detail=str(exc),
    )