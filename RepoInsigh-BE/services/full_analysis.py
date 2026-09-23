from __future__ import annotations

import logging

from models.analysis import FullAnalysis
from services.analyzer import run_full_analysis as run_rest_full_analysis
from services.github_client import GitHubClient as RestGitHubClient
from services.graphQL.analyzer import run_full_analysis as run_graphql_full_analysis
from services.graphQL.github_client import GitHubClient as GraphQLGitHubClient

logger = logging.getLogger(__name__)


async def run_full_analysis(
    owner: str,
    repo: str,
    *,
    token: str | None = None,
    prefer_graphql: bool = True,
) -> FullAnalysis:
    if prefer_graphql:
        try:
            async with GraphQLGitHubClient(token=token) as client:
                return await run_graphql_full_analysis(client, owner, repo)
        except Exception as exc:
            logger.warning(
                "GraphQL full analysis failed for %s/%s, falling back to REST: %s",
                owner,
                repo,
                exc,
            )

    async with RestGitHubClient(token=token) as client:
        return await run_rest_full_analysis(client, owner, repo)
