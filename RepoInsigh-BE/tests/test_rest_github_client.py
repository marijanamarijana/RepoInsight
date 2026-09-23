import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.github_client import GitHubClient, _build_headers


class TestBuildHeaders:
    def test_headers_without_token(self):
        headers = _build_headers()

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_headers_with_token(self):
        headers = _build_headers("test-token")

        assert headers["Authorization"] == "Bearer test-token"

    def test_explicit_token_overrides_settings_token(self):
        with patch(
            "config.settings.github_token",
            "settings-token",
        ):
            headers = _build_headers("explicit-token")

        assert headers["Authorization"] == "Bearer explicit-token"


class TestGitHubClient:
    @pytest.mark.asyncio
    async def test_get_success(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {
            "X-RateLimit-Remaining": "4999"
        }
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": 1},
            {"id": 2},
        ]

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.get("/repos/test/test")

        assert result == [
            {"id": 1},
            {"id": 2},
        ]

        client._client.get.assert_awaited_once_with(
            "/repos/test/test",
            params=None,
        )

    @pytest.mark.asyncio
    async def test_get_passes_params(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        params = {
            "state": "open",
            "per_page": 100,
        }

        result = await client.get(
            "/repos/test/test/issues",
            params,
        )

        assert result == {"ok": True}

        client._client.get.assert_awaited_once_with(
            "/repos/test/test/issues",
            params=params,
        )

    @pytest.mark.asyncio
    async def test_get_raises_for_http_error(self):
        response = MagicMock()
        response.status_code = 404
        response.headers = {}
        response.raise_for_status.side_effect = RuntimeError(
            "404 Not Found"
        )

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        with pytest.raises(RuntimeError, match="404 Not Found"):
            await client.get("/repos/does/not-exist")

    @pytest.mark.asyncio
    async def test_get_retries_202(self):
        response_202 = MagicMock()
        response_202.status_code = 202
        response_202.headers = {}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}
        response_200.raise_for_status.return_value = None
        response_200.json.return_value = {
            "ready": True
        }

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()

        client._client.get.side_effect = [
            response_202,
            response_200,
        ]

        with patch(
            "services.github_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            result = await client.get(
                "/repos/test/stats",
                retry_delay=1,
            )

        assert result == {"ready": True}
        assert client._client.get.await_count == 2
        mock_sleep.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_returns_empty_list_after_202_retries(self):
        response = MagicMock()
        response.status_code = 202
        response.headers = {}

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        with patch(
            "services.github_client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await client.get(
                "/repos/test/stats",
                max_retries=3,
            )

        assert result == []
        assert client._client.get.await_count == 3

    @pytest.mark.asyncio
    async def test_get_does_not_retry_202_when_disabled(self):
        response = MagicMock()
        response.status_code = 202
        response.headers = {}

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.get(
            "/repos/test/stats",
            retry_on_202=False,
        )

        assert result == response.json()
        assert client._client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_get_paginated_single_page(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ]

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.get_paginated(
            "/repos/test/test/issues",
            max_pages=5,
        )

        assert result == [
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ]

        client._client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_paginated_multiple_pages(self):
        page1 = MagicMock()
        page1.status_code = 200
        page1.headers = {}
        page1.raise_for_status.return_value = None
        page1.json.return_value = [
            {"id": i}
            for i in range(100)
        ]

        page2 = MagicMock()
        page2.status_code = 200
        page2.headers = {}
        page2.raise_for_status.return_value = None
        page2.json.return_value = [
            {"id": 100},
            {"id": 101},
        ]

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()

        client._client.get.side_effect = [
            page1,
            page2,
        ]

        result = await client.get_paginated(
            "/repos/test/test/issues",
            max_pages=5,
        )

        assert len(result) == 102
        assert result[0] == {"id": 0}
        assert result[-1] == {"id": 101}
        assert client._client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_get_paginated_stops_on_empty_page(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = []

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.get_paginated(
            "/repos/test/test/issues",
            max_pages=10,
        )

        assert result == []
        assert client._client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_get_paginated_stops_when_response_is_not_list(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "message": "something unexpected"
        }

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.get_paginated(
            "/repos/test/test/issues",
            max_pages=10,
        )

        assert result == []
        assert client._client.get.await_count == 1

    @pytest.mark.asyncio
    async def test_get_paginated_sets_per_page_to_100(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = [{"id": 1}]

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        await client.get_paginated(
            "/repos/test/test/issues",
            params={"state": "open"},
            max_pages=5,
        )

        client._client.get.assert_awaited_once_with(
            "/repos/test/test/issues",
            params={
                "state": "open",
                "per_page": 100,
                "page": 1,
            },
        )

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                }
            }
        }

        client = GitHubClient(token="test-token")
        client._client = AsyncMock()
        client._client.get.return_value = response

        result = await client.rate_limit()

        assert result == {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                }
            }
        }

        client._client.get.assert_awaited_once_with(
            "/rate_limit",
            params=None,
        )

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        client = GitHubClient(token="test-token")
        client._client = AsyncMock()

        async with client as result:
            assert result is client

        client._client.aclose.assert_awaited_once()