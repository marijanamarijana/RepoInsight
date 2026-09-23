import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.analysis import (
    CodeFrequencyAnalysis,
    CommitActivityAnalysis,
    ContributorAnalysis,
)
from services.graphQL.analyzer import (
    _parse_dt,
    _median,
    _gini,
    _sparkline,
    parse_repository_overview,
    parse_languages,
    parse_recent_commits,
    parse_issues,
    parse_pull_requests,
    parse_releases,
    fetch_contributors,
    fetch_commit_activity,
    fetch_code_frequency,
    build_summary,
    run_full_analysis,
    fetch_rate_limit,
)

def test_parse_dt():
    result = _parse_dt("2026-09-22T12:30:00Z")

    assert result.year == 2026
    assert result.month == 9
    assert result.day == 22
    assert result.hour == 12
    assert result.tzinfo is not None


def test_median_empty():
    assert _median([]) is None


def test_median_odd():
    assert _median([1, 3, 2]) == 2


def test_median_even():
    assert _median([1, 2, 3, 4]) == 2.5


def test_gini_empty():
    assert _gini([]) == 0.0


def test_gini_equal_values():
    assert _gini([10, 10, 10]) == 0.0


def test_gini_single_contributor():
    assert _gini([100]) == 0.0


def test_gini_unequal_values():
    result = _gini([0, 100])

    assert result == 0.5


def test_sparkline_empty():
    assert _sparkline([]) == ""


def test_sparkline():
    result = _sparkline([0, 5, 10])

    assert len(result) == 3
    assert result[0] == " "
    assert result[-1] == "█"

def test_parse_repository_overview():
    data = {
        "repository": {
            "name": "test",
            "nameWithOwner": "owner/test",
            "description": "Test repository",
            "stargazerCount": 100,
            "forkCount": 20,
            "watchers": {
                "totalCount": 50,
            },
            "issues": {
                "totalCount": 10,
            },
            "isArchived": False,
            "isFork": False,
            "createdAt": "2025-01-01T00:00:00Z",
            "pushedAt": "2026-09-20T00:00:00Z",
            "primaryLanguage": {
                "name": "Python",
            },
            "licenseInfo": {
                "name": "MIT",
            },
            "repositoryTopics": {
                "nodes": [
                    {"topic": {"name": "python"}},
                    {"topic": {"name": "github"}},
                ],
            },
            "defaultBranchRef": {
                "name": "main",
            },
        }
    }

    result = parse_repository_overview(data)

    assert result.full_name == "owner/test"
    assert result.description == "Test repository"
    assert result.stars == 100
    assert result.forks == 20
    assert result.open_issues == 10
    assert result.watchers == 50
    assert result.default_branch == "main"
    assert result.primary_language == "Python"
    assert result.license == "MIT"
    assert result.is_archived is False
    assert result.is_fork is False
    assert result.topics == ["python", "github"]


def test_parse_repository_overview_without_optional_fields():
    data = {
        "repository": {
            "nameWithOwner": "owner/test",
            "description": None,
            "stargazerCount": 0,
            "forkCount": 0,
            "watchers": {"totalCount": 0},
            "issues": {"totalCount": 0},
            "isArchived": False,
            "isFork": False,
            "createdAt": "2025-01-01T00:00:00Z",
            "pushedAt": "2026-09-20T00:00:00Z",
            "primaryLanguage": None,
            "licenseInfo": None,
            "repositoryTopics": {"nodes": []},
            "defaultBranchRef": {"name": "main"},
        }
    }

    result = parse_repository_overview(data)

    assert result.primary_language is None
    assert result.license is None
    assert result.default_branch == "main"
    assert result.topics == []


def test_parse_languages():
    data = {
        "repository": {
            "languages": {
                "edges": [
                    {
                        "size": 600,
                        "node": {"name": "Python"},
                    },
                    {
                        "size": 400,
                        "node": {"name": "JavaScript"},
                    },
                ]
            }
        }
    }

    result = parse_languages(data)

    assert result.total_bytes == 1000
    assert len(result.languages) == 2

    assert result.languages[0].language == "Python"
    assert result.languages[0].bytes == 600
    assert result.languages[0].percentage == 60.0

    assert result.languages[1].language == "JavaScript"
    assert result.languages[1].percentage == 40.0


def test_parse_recent_commits():
    data = {
        "repository": {
            "defaultBranchRef": {
                "target": {
                    "history": {
                        "nodes": [
                            {
                                "committedDate": "2026-09-22T10:00:00Z",
                                "message": "Fix bug",
                            },
                            {
                                "committedDate": "2026-09-22T10:00:00Z",
                                "message": "Add feature",
                            },
                            {
                                "committedDate": "2026-09-22T12:00:00Z",
                                "message": "Update documentation",
                            },
                        ]
                    }
                }
            }
        }
    }

    result = parse_recent_commits(data)

    assert result.total_sampled == 3
    assert result.min_message_length == len("Fix bug")
    assert result.max_message_length == len("Update documentation")

    assert len(result.commits_by_hour) == 24
    assert result.commits_by_hour[10].count == 2
    assert result.commits_by_hour[12].count == 1

    assert result.peak_hour_utc == 10


def test_parse_recent_commits_without_branch():
    data = {
        "repository": {
            "defaultBranchRef": None
        }
    }

    result = parse_recent_commits(data)

    assert result.total_sampled == 0
    assert result.avg_message_length == 0
    assert result.min_message_length == 0
    assert result.max_message_length == 0
    assert result.commits_by_hour == []
    assert result.peak_hour_utc == 0


def test_parse_issues():
    data = {
        "repository": {
            "openIssues": {
                "nodes": [
                    {
                        "number": 1,
                        "updatedAt": "2026-09-21T00:00:00Z",
                        "labels": {
                            "nodes": [
                                {"name": "bug"},
                            ]
                        },
                    }
                ]
            },
            "closedIssues": {
                "nodes": [
                    {
                        "number": 2,
                        "createdAt": "2026-09-01T00:00:00Z",
                        "closedAt": "2026-09-03T00:00:00Z",
                        "updatedAt": "2026-09-03T00:00:00Z",
                        "labels": {
                            "nodes": [
                                {"name": "bug"},
                                {"name": "feature"},
                            ]
                        },
                    }
                ]
            }
        }
    }

    overview = MagicMock()
    overview.open_issues = 1

    result = parse_issues(data, overview)

    assert result.open_count == 1
    assert result.open_sampled == 1
    assert result.closed_sampled == 1

    assert result.avg_close_time_days == 2.0
    assert result.median_close_time_days == 2.0

    assert result.stale_threshold_days == 90

    labels = {
        label.name: label.count
        for label in result.top_labels
    }

    assert labels["bug"] == 2
    assert labels["feature"] == 1


def test_parse_pull_requests():
    data = {
        "repository": {
            "openPullRequests": {
                "nodes": [
                    {
                        "number": 1,
                        "createdAt": "2026-09-20T00:00:00Z",
                        "updatedAt": "2026-09-21T00:00:00Z",
                        "mergedAt": None,
                    }
                ]
            },
            "closedPullRequests": {
                "nodes": [
                    {
                        "number": 2,
                        "createdAt": "2026-09-01T00:00:00Z",
                        "updatedAt": "2026-09-04T00:00:00Z",
                        "mergedAt": "2026-09-03T00:00:00Z",
                        "comments": {
                            "nodes": [
                                {
                                    "createdAt": "2026-09-01T12:00:00Z"
                                }
                            ]
                        },
                    },
                    {
                        "number": 3,
                        "createdAt": "2026-09-01T00:00:00Z",
                        "updatedAt": "2026-09-05T00:00:00Z",
                        "mergedAt": None,
                        "comments": {
                            "nodes": []
                        },
                    },
                ]
            }
        }
    }

    result = parse_pull_requests(data)

    assert result.open_count == 1
    assert result.closed_sampled == 2
    assert result.merged_count == 1
    assert result.rejected_count == 1

    assert result.merge_rate_pct == 50.0

    assert result.avg_time_to_merge_days == 2.0
    assert result.median_time_to_merge_days == 2.0

    assert result.avg_first_response_hours == 12.0


def test_parse_releases():
    data = {
        "repository": {
            "releases": {
                "nodes": [
                    {
                        "tagName": "v3",
                        "name": "Version 3",
                        "publishedAt": "2026-09-20T00:00:00Z",
                        "isPrerelease": False,
                    },
                    {
                        "tagName": "v2",
                        "name": "Version 2",
                        "publishedAt": "2026-09-10T00:00:00Z",
                        "isPrerelease": False,
                    },
                    {
                        "tagName": "v1",
                        "name": "Version 1",
                        "publishedAt": "2026-09-01T00:00:00Z",
                        "isPrerelease": True,
                    },
                ]
            }
        }
    }

    result = parse_releases(data)

    assert result.total_fetched == 3
    assert result.last_releases[0].tag == "v3"

    assert result.avg_days_between_releases == 9.5
    assert result.fastest_gap_days == 9
    assert result.slowest_gap_days == 10


@pytest.mark.asyncio
async def test_fetch_code_frequency():
    client = MagicMock()

    client.get = AsyncMock(
        return_value=[
            [1000, 10, -5],
            [2000, 20, -10],
            [3000, 5, -2],
        ]
    )

    result = await fetch_code_frequency(
        client,
        "owner",
        "repo",
    )

    assert result.total_additions == 35
    assert result.total_deletions == 17
    assert result.net_lines == 18

    assert len(result.recent_weeks) == 3

    client.get.assert_awaited_once_with(
        "/repos/owner/repo/stats/code_frequency"
    )

@pytest.mark.asyncio
async def test_fetch_code_frequency():
    client = MagicMock()

    client.get = AsyncMock(
        return_value=[
            [1000, 10, -5],
            [2000, 20, -10],
            [3000, 5, -2],
        ]
    )

    result = await fetch_code_frequency(
        client,
        "owner",
        "repo",
    )

    assert result.total_additions == 35
    assert result.total_deletions == 17
    assert result.net_lines == 18

    assert len(result.recent_weeks) == 3

    client.get.assert_awaited_once_with(
        "/repos/owner/repo/stats/code_frequency"
    )


@pytest.mark.asyncio
async def test_fetch_commit_activity():
    client = MagicMock()

    client.get = AsyncMock(
        return_value=[
            {
                "week": 1758499200,
                "total": 10,
                "days": [1, 2, 3, 1, 2, 1, 0],
            },
            {
                "week": 1759104000,
                "total": 20,
                "days": [2, 4, 5, 3, 3, 2, 1],
            },
        ]
    )

    result = await fetch_commit_activity(
        client,
        "owner",
        "repo",
    )

    assert result.peak_week_commits == 20
    assert result.avg_commits_per_week == 15

    assert len(result.weeks) == 2

    assert result.commits_by_day["Sun"] == 3
    assert result.commits_by_day["Mon"] == 6
    assert result.commits_by_day["Tue"] == 8


@pytest.mark.asyncio
async def test_fetch_commit_activity_empty():
    client = MagicMock()
    client.get = AsyncMock(return_value=[])

    result = await fetch_commit_activity(
        client,
        "owner",
        "repo",
    )

    assert result.sparkline == ""
    assert result.peak_week_commits == 0
    assert result.avg_commits_per_week == 0
    assert result.weeks == []
    assert result.commits_by_day == {}


@pytest.mark.asyncio
async def test_fetch_commit_activity_empty():
    client = MagicMock()
    client.get = AsyncMock(return_value=[])

    result = await fetch_commit_activity(
        client,
        "owner",
        "repo",
    )

    assert result.sparkline == ""
    assert result.peak_week_commits == 0
    assert result.avg_commits_per_week == 0
    assert result.weeks == []
    assert result.commits_by_day == {}


@pytest.mark.asyncio
async def test_run_full_analysis():
    client = MagicMock()

    client.graphql = AsyncMock(
        return_value={
            "repository": {
                "nameWithOwner": "owner/repo",
                "description": "Test repo",
                "stargazerCount": 100,
                "forkCount": 10,
                "watchers": {"totalCount": 20},
                "issues": {"totalCount": 5},
                "isArchived": False,
                "isFork": False,
                "createdAt": "2025-01-01T00:00:00Z",
                "pushedAt": "2026-09-20T00:00:00Z",
                "primaryLanguage": {"name": "Python"},
                "licenseInfo": {"name": "MIT"},
                "repositoryTopics": {"nodes": []},
                "defaultBranchRef": {"name": "main"},
                "languages": {"edges": []},
                "releases": {"nodes": []},
                "openIssues": {"nodes": []},
                "closedIssues": {"nodes": []},
                "openPullRequests": {"nodes": []},
                "closedPullRequests": {"nodes": []},
            }
        }
    )

    with patch(
        "services.graphQL.analyzer.fetch_contributors",
        new_callable=AsyncMock,
    ) as contributors_mock, patch(
        "services.graphQL.analyzer.fetch_commit_activity",
        new_callable=AsyncMock,
    ) as activity_mock, patch(
        "services.graphQL.analyzer.fetch_code_frequency",
        new_callable=AsyncMock,
    ) as frequency_mock:

        contributors_mock.return_value = ContributorAnalysis(
            total_contributors_fetched=0,
            total_commits_sampled=0,
            bus_factor=1,
            gini_coefficient=0.0,
            top_contributors=[],
            ownership={"50%": 0, "80%": 0, "95%": 0},
        )

        activity_mock.return_value = CommitActivityAnalysis(
            peak_week_commits=0,
            avg_commits_per_week=0,
            weeks=[],
            commits_by_day={},
            sparkline="",
        )

        frequency_mock.return_value = CodeFrequencyAnalysis(
            total_additions=0,
            total_deletions=0,
            net_lines=0,
            recent_weeks=[],
        )

        result = await run_full_analysis(
            client,
            "owner",
            "repo",
        )

    client.graphql.assert_awaited_once()

    assert result.overview.full_name == "owner/repo"
    assert result.overview.primary_language == "Python"

    contributors_mock.assert_awaited_once_with(
        client,
        "owner",
        "repo",
    )

    activity_mock.assert_awaited_once_with(
        client,
        "owner",
        "repo",
    )

    frequency_mock.assert_awaited_once_with(
        client,
        "owner",
        "repo",
    )


