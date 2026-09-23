import pytest
from unittest.mock import AsyncMock, MagicMock

from services.analyzer import (
    fetch_overview,
    fetch_languages,
    fetch_contributors,
    fetch_commit_activity,
    fetch_recent_commits,
    fetch_code_frequency,
)

@pytest.mark.asyncio
async def test_fetch_overview():
    client = MagicMock()

    client.get = AsyncMock(
        return_value={
            "full_name": "owner/repo",
            "description": "Test repository",
            "stargazers_count": 100,
            "forks_count": 20,
            "open_issues_count": 5,
            "watchers_count": 30,
            "default_branch": "main",
            "language": "Python",
            "license": {
                "name": "MIT"
            },
            "created_at": "2025-01-01T00:00:00Z",
            "pushed_at": "2026-09-20T00:00:00Z",
            "archived": False,
            "fork": False,
            "topics": ["python"],
        }
    )

    result = await fetch_overview(
        client,
        "owner",
        "repo",
    )

    assert result.full_name == "owner/repo"
    assert result.stars == 100
    assert result.forks == 20
    assert result.open_issues == 5
    assert result.primary_language == "Python"
    assert result.license == "MIT"
    assert result.topics == ["python"]

    client.get.assert_awaited_once_with(
        "/repos/owner/repo"
    )

@pytest.mark.asyncio
async def test_fetch_languages():
    client = MagicMock()

    client.get = AsyncMock(
        return_value={
            "Python": 600,
            "JavaScript": 400,
        }
    )

    result = await fetch_languages(
        client,
        "owner",
        "repo",
    )

    assert result.total_bytes == 1000

    assert result.languages[0].language == "Python"
    assert result.languages[0].percentage == 60.0

    assert result.languages[1].language == "JavaScript"
    assert result.languages[1].percentage == 40.0


@pytest.mark.asyncio
async def test_fetch_languages():
    client = MagicMock()

    client.get = AsyncMock(
        return_value={
            "Python": 600,
            "JavaScript": 400,
        }
    )

    result = await fetch_languages(
        client,
        "owner",
        "repo",
    )

    assert result.total_bytes == 1000

    assert result.languages[0].language == "Python"
    assert result.languages[0].percentage == 60.0

    assert result.languages[1].language == "JavaScript"
    assert result.languages[1].percentage == 40.0


@pytest.mark.asyncio
async def test_rest_code_frequency_error_fallback():
    client = MagicMock()

    client.get = AsyncMock(
        side_effect=RuntimeError("GitHub API error: 422")
    )

    result = await fetch_code_frequency(
        client,
        "owner",
        "repo",
    )

    assert result.total_additions == 0
    assert result.total_deletions == 0
    assert result.net_lines == 0
    assert result.recent_weeks == []

