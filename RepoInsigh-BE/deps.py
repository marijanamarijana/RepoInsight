from __future__ import annotations
from typing import Annotated, Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(
    auto_error=False,
    description=(
        "Optional GitHub personal access token. "
        "If omitted, the server GITHUB_TOKEN is used."
    ),
)


def get_github_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Read a GitHub PAT from `Authorization: Bearer <token>`."""
    if credentials is None:
        return None
    token = credentials.credentials.strip()
    return token or None


TokenDep = Annotated[Optional[str], Depends(get_github_token)]
