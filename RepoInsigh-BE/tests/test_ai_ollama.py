from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from services.ai.llm import (
    SYSTEM_PROMPT,
    _extract_json,
    _ollama,
    _ollama_chat,
    complete_json,
)


VALID_INSIGHT = {
    "health_summary": "Healthy repo with steady commits.",
    "strengths": ["Active maintainers"],
    "risks": ["Low bus factor"],
    "recommendations": ["Add tests"],
    "readme_assessment": "Clear setup steps.",
    "community_signals": "Issues are answered quickly.",
}


def test_extract_json_from_plain_object():
    parsed = _extract_json('{"health_summary": "ok", "strengths": []}')
    assert parsed["health_summary"] == "ok"
    assert parsed["strengths"] == []


def test_extract_json_from_markdown_fence():
    text = "```json\n" + '{"health_summary": "ok"}' + "\n```"
    assert _extract_json(text)["health_summary"] == "ok"


def test_extract_json_repairs_truncated_object():
    parsed = _extract_json('{"health_summary": "partial", "strengths": ["a"')
    assert parsed["health_summary"] == "partial"
    assert parsed["strengths"] == ["a"]


def test_extract_json_ignores_leading_prose():
    text = 'Here you go:\n{"health_summary": "ok", "risks": []}'
    assert _extract_json(text)["health_summary"] == "ok"


@pytest.mark.asyncio
async def test_complete_json_uses_ollama_when_configured(monkeypatch):
    async def fake_ollama(user_content: str):
        assert user_content == "repo context"
        return VALID_INSIGHT, "ollama", "llama3.2:3b"

    monkeypatch.setattr("services.ai.llm.settings.ai_provider", "ollama")
    monkeypatch.setattr("services.ai.llm._ollama", fake_ollama)

    parsed, provider, model = await complete_json(user_content="repo context")
    assert parsed == VALID_INSIGHT
    assert provider == "ollama"
    assert model == "llama3.2:3b"


@pytest.mark.asyncio
async def test_complete_json_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_provider", "openai")
    with pytest.raises(RuntimeError, match="not configured"):
        await complete_json(user_content="x")


@pytest.mark.asyncio
async def test_ollama_chat_sends_json_schema_when_requested(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_max_tokens", 111)

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"content": "{}"}}
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)

    body = await _ollama_chat(
        client,
        base="http://127.0.0.1:11434",
        model="llama3.2:3b",
        user_content="analyze this",
        json_mode=True,
    )

    assert body == {"message": {"content": "{}"}}
    client.post.assert_awaited_once()
    url, kwargs = client.post.await_args.args[0], client.post.await_args.kwargs
    assert url == "http://127.0.0.1:11434/api/chat"
    payload = kwargs["json"]
    assert payload["model"] == "llama3.2:3b"
    assert payload["stream"] is False
    assert payload["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert payload["messages"][1]["content"] == "analyze this"
    assert payload["options"]["num_predict"] == 111
    assert payload["format"]["type"] == "object"
    assert "health_summary" in payload["format"]["properties"]


@pytest.mark.asyncio
async def test_ollama_chat_omits_format_without_json_mode(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_max_tokens", 50)
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"ok": True}
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)

    await _ollama_chat(
        client,
        base="http://localhost:11434",
        model="qwen2.5:1.5b",
        user_content="x",
        json_mode=False,
    )
    assert "format" not in client.post.await_args.kwargs["json"]


@pytest.mark.asyncio
async def test_ollama_chat_missing_model_raises():
    response = MagicMock()
    response.status_code = 404
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)

    with pytest.raises(RuntimeError, match="ollama pull llama3.2:3b"):
        await _ollama_chat(
            client,
            base="http://127.0.0.1:11434",
            model="llama3.2:3b",
            user_content="x",
            json_mode=True,
        )


@pytest.mark.asyncio
async def test_ollama_returns_parsed_json(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_model", "llama3.2:3b")
    monkeypatch.setattr("services.ai.llm.settings.ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr("services.ai.llm.settings.ollama_request_timeout", 30)

    async def fake_chat(*_args, **kwargs):
        assert kwargs["json_mode"] is True
        return {"message": {"content": '{"health_summary": "ok", "strengths": []}'}}

    monkeypatch.setattr("services.ai.llm._ollama_chat", fake_chat)

    parsed, provider, model = await _ollama("prompt")
    assert parsed["health_summary"] == "ok"
    assert provider == "ollama"
    assert model == "llama3.2:3b"


@pytest.mark.asyncio
async def test_ollama_retries_without_json_mode_on_empty_content(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_model", "")
    monkeypatch.setattr("services.ai.llm.settings.ollama_base_url", "http://127.0.0.1:11434/")
    monkeypatch.setattr("services.ai.llm.settings.ollama_request_timeout", 10)

    calls: list[bool] = []

    async def fake_chat(*_args, **kwargs):
        calls.append(kwargs["json_mode"])
        if kwargs["json_mode"]:
            return {"message": {"content": "  "}}
        return {"message": {"content": '{"health_summary": "retried"}'}}

    monkeypatch.setattr("services.ai.llm._ollama_chat", fake_chat)

    parsed, provider, model = await _ollama("prompt")
    assert calls == [True, False]
    assert parsed["health_summary"] == "retried"
    assert provider == "ollama"
    assert model == "llama3.2:3b"


@pytest.mark.asyncio
async def test_ollama_empty_content_raises(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_model", "tiny")
    monkeypatch.setattr("services.ai.llm.settings.ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr("services.ai.llm.settings.ollama_request_timeout", 10)

    async def fake_chat(*_args, **_kwargs):
        return {"message": {"content": ""}, "done_reason": "length"}

    monkeypatch.setattr("services.ai.llm._ollama_chat", fake_chat)

    with pytest.raises(RuntimeError, match="empty content"):
        await _ollama("prompt")


@pytest.mark.asyncio
async def test_ollama_timeout_message(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_model", "slow")
    monkeypatch.setattr("services.ai.llm.settings.ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr("services.ai.llm.settings.ollama_request_timeout", 7)

    async def fake_chat(*_args, **_kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("services.ai.llm._ollama_chat", fake_chat)

    with pytest.raises(RuntimeError, match="timed out after 7s"):
        await _ollama("prompt")


@pytest.mark.asyncio
async def test_ollama_connect_error_message(monkeypatch):
    monkeypatch.setattr("services.ai.llm.settings.ai_model", "m")
    monkeypatch.setattr("services.ai.llm.settings.ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr("services.ai.llm.settings.ollama_request_timeout", 5)

    async def fake_chat(*_args, **_kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("services.ai.llm._ollama_chat", fake_chat)

    with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
        await _ollama("prompt")


@pytest.mark.asyncio
async def test_generate_ai_insights_maps_ollama_json():
    from models.analysis import (
        CodeFrequencyAnalysis,
        CommitActivityAnalysis,
        ContributorAnalysis,
        FullAnalysis,
        IssuesAnalysis,
        LanguageBreakdown,
        PullRequestsAnalysis,
        RecentCommitsAnalysis,
        ReleasesAnalysis,
        RepoOverview,
        RepoSummary,
    )
    from services.ai.insights import generate_ai_insights

    overview = RepoOverview(
        full_name="owner/repo",
        description=None,
        stars=1,
        forks=0,
        open_issues=0,
        watchers=0,
        default_branch="main",
        primary_language="Python",
        license=None,
        created_at="2025-01-01T00:00:00Z",
        last_pushed_at="2026-01-01T00:00:00Z",
        days_since_last_push=1,
        is_archived=False,
        is_fork=False,
        topics=[],
    )
    empty_contributors = ContributorAnalysis(
        total_contributors_fetched=0,
        total_commits_sampled=0,
        bus_factor=1,
        gini_coefficient=0.0,
        top_contributors=[],
        ownership={"50%": 0, "80%": 0, "95%": 0},
    )
    empty_prs = PullRequestsAnalysis(
        open_count=0,
        closed_sampled=0,
        merged_count=0,
        rejected_count=0,
        merge_rate_pct=0.0,
        avg_time_to_merge_days=None,
        median_time_to_merge_days=None,
        avg_first_response_hours=None,
    )
    empty_issues = IssuesAnalysis(
        open_count=0,
        closed_sampled=0,
        open_sampled=0,
        avg_close_time_days=None,
        median_close_time_days=None,
        stale_issues_count=0,
        stale_threshold_days=90,
        top_labels=[],
    )
    empty_releases = ReleasesAnalysis(
        total_fetched=0,
        last_releases=[],
        avg_days_between_releases=None,
        fastest_gap_days=None,
        slowest_gap_days=None,
    )
    full = FullAnalysis(
        overview=overview,
        languages=LanguageBreakdown(total_bytes=0, languages=[]),
        contributors=empty_contributors,
        commit_activity=CommitActivityAnalysis(
            sparkline="",
            peak_week_commits=0,
            avg_commits_per_week=0,
            weeks=[],
            commits_by_day={},
        ),
        recent_commits=RecentCommitsAnalysis(
            total_sampled=0,
            avg_message_length=0,
            min_message_length=0,
            max_message_length=0,
            commits_by_hour=[],
            peak_hour_utc=0,
        ),
        issues=empty_issues,
        pull_requests=empty_prs,
        releases=empty_releases,
        code_frequency=CodeFrequencyAnalysis(
            total_additions=0, total_deletions=0, net_lines=0, recent_weeks=[]
        ),
        summary=RepoSummary(
            repo="owner/repo",
            stars=1,
            forks=0,
            open_issues=0,
            days_since_last_push=1,
            primary_language="Python",
            bus_factor=1,
            gini_coefficient=0.0,
            pr_merge_rate_pct=0.0,
            avg_pr_merge_days=None,
            avg_issue_close_days=None,
            total_releases=0,
            top_contributors=[],
        ),
    )

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "services.ai.insights.run_full_analysis",
        new_callable=AsyncMock,
        return_value=full,
    ), patch(
        "services.ai.insights.GitHubClient",
        return_value=client,
    ), patch(
        "services.ai.insights._gather_text",
        new_callable=AsyncMock,
        return_value=("# Readme", []),
    ), patch(
        "services.ai.insights.complete_json",
        new_callable=AsyncMock,
        return_value=(VALID_INSIGHT, "ollama", "llama3.2:3b"),
    ) as complete:
        result = await generate_ai_insights("owner", "repo", github_token="tok")

    complete.assert_awaited_once()
    assert result.repo == "owner/repo"
    assert result.provider == "ollama"
    assert result.model == "llama3.2:3b"
    assert result.health_summary == VALID_INSIGHT["health_summary"]
    assert result.strengths == VALID_INSIGHT["strengths"]
    assert result.risks == VALID_INSIGHT["risks"]
    assert result.recommendations == VALID_INSIGHT["recommendations"]
    assert result.readme_assessment == VALID_INSIGHT["readme_assessment"]
    assert result.community_signals == VALID_INSIGHT["community_signals"]
