from __future__ import annotations
import logging
from models.ai_analysis import AiHealthInsight
from models.analysis import FullAnalysis
from services.ai.context import (
    build_analysis_context,
    fetch_open_issue_snippets,
    fetch_readme_text,
)
from config import settings
from services.ai.llm import complete_json
from services.full_analysis import run_full_analysis
from services.github_client import GitHubClient

logger = logging.getLogger(__name__)


async def generate_ai_insights(owner: str, repo: str, *, token: str | None = None, github_token: str | None = None) -> AiHealthInsight:

    gh_token = github_token or token
    full: FullAnalysis = await run_full_analysis(owner, repo, token=gh_token)

    async with GitHubClient(token=gh_token) as client:
        readme, open_issues = await _gather_text(client, owner, repo)

    use_compact = settings.ai_compact_context or settings.ai_provider.lower() == "ollama"
    context = build_analysis_context(full, readme=readme, open_issues=open_issues, compact=use_compact)
    logger.info("AI context for %s/%s: compact=%s, chars=%s",owner, repo, use_compact, len(context))
    user_prompt = (
        f"Repository: {owner}/{repo}\n\n"
        "Analyze the following JSON context and produce the required JSON response.\n\n"
        f"{context}"
    )

    parsed, provider, model = await complete_json(user_content=user_prompt)

    return AiHealthInsight(
        repo=full.overview.full_name,
        provider=provider,
        model=model,
        health_summary=parsed.get("health_summary") or "",
        strengths=list(parsed.get("strengths") or []),
        risks=list(parsed.get("risks") or []),
        recommendations=list(parsed.get("recommendations") or []),
        readme_assessment=parsed.get("readme_assessment"),
        community_signals=parsed.get("community_signals"),
    )


async def _gather_text(client: GitHubClient, owner: str, repo: str):
    import asyncio

    return await asyncio.gather(
        fetch_readme_text(client, owner, repo),
        fetch_open_issue_snippets(client, owner, repo),
    )
