from __future__ import annotations

import asyncio
import logging
from typing import Any
import httpx
from config import settings

logger = logging.getLogger(__name__)

_REST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

_GRAPHQL_HEADERS = {
    "Accept": "application/json",
}


def _build_headers(
    token: str | None = None,
    *,
    graphql: bool = False,
) -> dict[str, str]:
    t = token or settings.github_token

    headers = dict(
        _GRAPHQL_HEADERS if graphql else _REST_HEADERS
    )

    if t:
        headers["Authorization"] = f"Bearer {t}"

    return headers


class GitHubClient:
    def __init__(self, token: str | None = None):
        self._token = token or settings.github_token

        self._client = httpx.AsyncClient(
            timeout=settings.request_timeout,
        )

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._client.aclose()

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        retry_on_202: bool = True,
        max_retries: int = 3,
        retry_delay: float = 3.0,
    ) -> Any:

        headers = _build_headers(self._token)

        for attempt in range(max_retries):

            r = await self._client.get(
                f"https://api.github.com{path}",
                params=params,
                headers=headers,
            )

            remaining = r.headers.get(
                "X-RateLimit-Remaining",
                "?",
            )

            logger.debug(
                "REST GET %s status=%s rate_remaining=%s",
                path,
                r.status_code,
                remaining,
            )

            if r.status_code == 202 and retry_on_202:
                if attempt < max_retries - 1:
                    logger.info(
                        "202 on %s — retrying in %.0fs",
                        path,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                return []

            r.raise_for_status()
            return r.json()

        return []

    async def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        headers = _build_headers(
            self._token,
            graphql=True,
        )

        response = await self._client.post(
            "https://api.github.com/graphql",
            json={
                "query": query,
                "variables": variables or {},
            },
            headers=headers,
        )

        logger.debug(
            "GraphQL status=%s",
            response.status_code,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("errors"):
            logger.error(
                "GraphQL errors: %s",
                payload["errors"],
            )

            raise RuntimeError(
                f"GitHub GraphQL error: {payload['errors']}"
            )

        return payload["data"]

    async def rate_limit(self) -> dict[str, Any]:
        query = """
        query {
          rateLimit {
            limit
            cost
            remaining
            resetAt
            used
          }
        }
        """

        data = await self.graphql(query)
        return data["rateLimit"]