from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app

RATE = {
    "limit": 5000,
    "remaining": 4999,
    "used": 1,
    "reset_at": "2026-01-01T00:00:00Z",
}


def _client_cm():
    instance = MagicMock()
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    return instance


@patch("routers.analysis.fetch_rate_limit", new_callable=AsyncMock)
@patch("routers.analysis.GitHubClient")
def test_bearer_token_is_passed_to_github_client(mock_client_cls, mock_fetch):
    mock_fetch.return_value = RATE
    mock_client_cls.return_value = _client_cm()

    response = TestClient(app).get(
        "/analyze/rate-limit",
        headers={"Authorization": "Bearer ghp_user"},
    )

    assert response.status_code == 200
    mock_client_cls.assert_called_once_with(token="ghp_user")


@patch("routers.analysis.fetch_rate_limit", new_callable=AsyncMock)
@patch("routers.analysis.GitHubClient")
def test_query_token_is_not_used(mock_client_cls, mock_fetch):
    mock_fetch.return_value = RATE
    mock_client_cls.return_value = _client_cm()

    response = TestClient(app).get(
        "/analyze/rate-limit",
        params={"token": "ghp_query"},
    )

    assert response.status_code == 200
    mock_client_cls.assert_called_once_with(token=None)


@patch("routers.analysis.fetch_rate_limit", new_callable=AsyncMock)
@patch("routers.analysis.GitHubClient")
def test_missing_authorization_uses_server_token_fallback(mock_client_cls, mock_fetch):
    mock_fetch.return_value = RATE
    mock_client_cls.return_value = _client_cm()

    response = TestClient(app).get("/analyze/rate-limit")

    assert response.status_code == 200
    mock_client_cls.assert_called_once_with(token=None)
