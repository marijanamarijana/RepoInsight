import pytest
from unittest.mock import AsyncMock, patch

from services.full_analysis import run_full_analysis


@pytest.mark.asyncio
async def test_full_analysis_uses_graphql_when_successful():
    expected = object()

    with patch(
        "services.full_analysis.run_graphql_full_analysis",
        new_callable=AsyncMock,
        return_value=expected,
    ) as gql_run, patch(
        "services.full_analysis.run_rest_full_analysis",
        new_callable=AsyncMock,
    ) as rest_run:
        result = await run_full_analysis("owner", "repo", token="tok")

    assert result is expected
    gql_run.assert_awaited_once()
    rest_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_analysis_falls_back_to_rest_on_graphql_error():
    expected = object()

    with patch(
        "services.full_analysis.run_graphql_full_analysis",
        new_callable=AsyncMock,
        side_effect=RuntimeError("GraphQL down"),
    ), patch(
        "services.full_analysis.run_rest_full_analysis",
        new_callable=AsyncMock,
        return_value=expected,
    ) as rest_run:
        result = await run_full_analysis("owner", "repo", token="tok")

    assert result is expected
    rest_run.assert_awaited_once()
