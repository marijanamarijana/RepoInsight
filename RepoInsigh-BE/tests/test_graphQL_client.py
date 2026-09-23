import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.graphQL.github_client import GitHubClient, _build_headers
from services.graphQL.query_for_graphQL_full_analysis import REPOSITORY_ANALYSIS_QUERY
from config import settings


class TestBuildHeaders:
    def test_rest_headers_without_token(self):
        with patch("config.settings.github_token", None):
            headers = _build_headers()

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert "Authorization" not in headers

    def test_rest_headers_with_token(self):
        headers = _build_headers("test-token")

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert headers["Authorization"] == "Bearer test-token"

    def test_graphql_headers_without_token(self):
        with patch("config.settings.github_token", None):
            headers = _build_headers(graphql=True)

        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers
        assert "X-GitHub-Api-Version" not in headers

    def test_graphql_headers_with_token(self):
        headers = _build_headers("test-token", graphql=True)

        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-token"


class TestGraphQLClient:
    @pytest.mark.asyncio
    async def test_graphql_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "repository": {
                    "name": "test-repo"
                }
            }
        }
        response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        result = await client.graphql(
            "query { repository { name } }",
            {"owner": "test", "repo": "test-repo"},
        )

        assert result == {
            "repository": {
                "name": "test-repo"
            }
        }

        mock_client.post.assert_awaited_once_with(
            "https://api.github.com/graphql",
            json={
                "query": "query { repository { name } }",
                "variables": {
                    "owner": "test",
                    "repo": "test-repo",
                },
            },
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer test-token",
            },
        )

    @pytest.mark.asyncio
    async def test_graphql_without_variables_uses_empty_dict(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "rateLimit": {
                    "remaining": 4999
                }
            }
        }
        response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        result = await client.graphql(
            "query { rateLimit { remaining } }"
        )

        assert result["rateLimit"]["remaining"] == 4999

        mock_client.post.assert_awaited_once_with(
            "https://api.github.com/graphql",
            json={
                "query": "query { rateLimit { remaining } }",
                "variables": {},
            },
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer test-token",
            },
        )

    @pytest.mark.asyncio
    async def test_graphql_http_error(self):
        response = MagicMock()
        response.status_code = 401
        response.raise_for_status.side_effect = Exception("401 Unauthorized")

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="bad-token")
        client._client = mock_client

        with pytest.raises(Exception, match="401 Unauthorized"):
            await client.graphql("query { viewer { login } }")

    @pytest.mark.asyncio
    async def test_graphql_api_error(self):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "errors": [
                {
                    "message": "Could not resolve to a Repository"
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        with pytest.raises(RuntimeError, match="GitHub GraphQL error"):
            await client.graphql(
                "query { repository { name } }"
            )

    @pytest.mark.asyncio
    async def test_graphql_calls_raise_for_status(self):
        response = MagicMock()
        response.status_code = 500
        response.raise_for_status.side_effect = RuntimeError("Server error")

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        with pytest.raises(RuntimeError, match="Server error"):
            await client.graphql("query { viewer { login } }")

        response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        client = GitHubClient(token="test-token")
        client._client = AsyncMock()

        async with client as result:
            assert result is client

        client._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "rateLimit": {
                    "limit": 5000,
                    "cost": 1,
                    "remaining": 4999,
                    "resetAt": "2026-09-22T18:00:00Z",
                    "used": 1,
                }
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        result = await client.rate_limit()

        assert result == {
            "limit": 5000,
            "cost": 1,
            "remaining": 4999,
            "resetAt": "2026-09-22T18:00:00Z",
            "used": 1,
        }

    @pytest.mark.asyncio
    async def test_rest_get_success(self):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "name": "test-repo"
        }
        response.headers = {
            "X-RateLimit-Remaining": "4999"
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        result = await client.get("/repos/test/test-repo")

        assert result == {
            "name": "test-repo"
        }

        mock_client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_202_retries(self):
        response_202 = MagicMock()
        response_202.status_code = 202
        response_202.headers = {}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.headers = {}
        response_200.raise_for_status.return_value = None
        response_200.json.return_value = {"result": "done"}

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            response_202,
            response_200,
        ]

        client = GitHubClient(token="test-token")
        client._client = mock_client

        with patch("services.graphQL.github_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.get(
                "/some/stats/endpoint",
                retry_delay=0,
            )

        assert result == {"result": "done"}
        assert mock_client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_get_returns_empty_list_after_max_202_retries(self):
        response = MagicMock()
        response.status_code = 202
        response.headers = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        with patch(
            "services.graphQL.github_client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await client.get(
                "/some/stats/endpoint",
                max_retries=3,
                retry_delay=0,
            )

        assert result == []
        assert mock_client.get.await_count == 3

    @pytest.mark.asyncio
    async def test_get_without_retry_on_202(self):
        response = MagicMock()
        response.status_code = 202
        response.headers = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = response

        client = GitHubClient(token="test-token")
        client._client = mock_client

        result = await client.get(
            "/some/stats/endpoint",
            retry_on_202=False,
        )

        assert result == response.json()
        mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_analysis_query_response():
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": {
            "repository": {
                "name": "vue",
                "nameWithOwner": "vuejs/vue",
                "description": "Vue.js",
                "stargazerCount": 200000,
                "forkCount": 30000,
                "watchers": {
                    "totalCount": 5000
                },
                "issues": {
                    "totalCount": 1000
                },
                "isArchived": False,
                "isFork": False,
                "createdAt": "2013-07-28T00:00:00Z",
                "pushedAt": "2026-09-22T00:00:00Z",
                "primaryLanguage": {
                    "name": "JavaScript"
                },
                "licenseInfo": {
                    "name": "MIT"
                },
                "repositoryTopics": {
                    "nodes": [
                        {
                            "topic": {
                                "name": "javascript"
                            }
                        }
                    ]
                },
                "defaultBranchRef": {
                    "name": "main",
                    "target": {
                        "history": {
                            "nodes": []
                        }
                    }
                },
                "languages": {
                    "edges": [
                        {
                            "size": 100000,
                            "node": {
                                "name": "JavaScript"
                            }
                        }
                    ]
                },
                "releases": {
                    "nodes": []
                },
                "openIssues": {
                    "nodes": []
                },
                "closedIssues": {
                    "nodes": []
                },
                "openPullRequests": {
                    "nodes": []
                },
                "closedPullRequests": {
                    "nodes": []
                },
            }
        }
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = response

    client = GitHubClient(token="test-token")
    client._client = mock_client

    result = await client.graphql(
        REPOSITORY_ANALYSIS_QUERY,
        {
            "owner": "vuejs",
            "repo": "vue",
        },
    )

    repository = result["repository"]

    assert repository["name"] == "vue"
    assert repository["nameWithOwner"] == "vuejs/vue"
    assert repository["stargazerCount"] == 200000
    assert repository["primaryLanguage"]["name"] == "JavaScript"
    assert repository["languages"]["edges"][0]["node"]["name"] == "JavaScript"