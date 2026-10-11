from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query
from deps import TokenDep
from models.ai_analysis import AiHealthInsight
from routers.graphQL_analysis_router import _owner_repo
from services.ai.insights import generate_ai_insights

router = APIRouter(
    prefix="/analyze",
    tags=["ai-analysis"],
)

@router.get(
    "/ai-insights",
    response_model=AiHealthInsight,
    summary="AI deep analysis (README, issues, health narrative)",
)
async def ai_insights(
    repo: Annotated[str, Query(description="owner/repo or full GitHub URL")],
    token: TokenDep,
):
    owner, repo_name = _owner_repo(repo)
    try:
        return await generate_ai_insights(owner, repo_name, github_token=token)
    except HTTPException:
        raise
    except RuntimeError as exc:
        message = str(exc)
        if "not configured" in message.lower() or "api_key" in message.lower():
            raise HTTPException(status_code=503, detail=message) from exc
        raise HTTPException(status_code=502, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
