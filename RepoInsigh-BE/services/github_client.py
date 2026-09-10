from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _build_headers(token: str | None = None) -> dict[str, str]:
    t = token or settings.github_token
    headers = dict(_HEADERS)
    if t:
        headers["Authorization"] = f"Bearer {t}"
    return headers


class GitHubClient:

    def __init__(self, token: str | None = None):
        self._headers = _build_headers(token)
        self._client = httpx.AsyncClient(
            base_url=settings.github_api_base,
            headers=self._headers,
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
        for attempt in range(max_retries):
            r = await self._client.get(path, params=params)
            remaining = r.headers.get("X-RateLimit-Remaining", "?")
            logger.debug("GET %s  status=%s  rate_remaining=%s", path, r.status_code, remaining)

            if r.status_code == 202 and retry_on_202:
                if attempt < max_retries - 1:
                    logger.info("202 on %s — retrying in %.0fs", path, retry_delay)
                    await asyncio.sleep(retry_delay)
                    continue
                return []

            r.raise_for_status()
            return r.json()

        return []  # should not reach

    async def get_paginated(
            self,
            path: str,
            params: dict[str, Any] | None = None,
            *,
            max_pages: int | None = None,
    ) -> list[Any]:
        params = dict(params or {})
        params["per_page"] = 100
        max_pages = max_pages or settings.max_pages_default
        results: list[Any] = []

        for page in range(1, max_pages + 1):
            params["page"] = page
            data = await self.get(path, params)
            if not isinstance(data, list) or not data:
                break
            results.extend(data)
            if len(data) < 100:
                break

        return results

    async def rate_limit(self) -> dict[str, Any]:
        return await self.get("/rate_limit")
