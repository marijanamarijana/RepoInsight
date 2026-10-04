from __future__ import annotations
import json
import logging
import re
from typing import Any
import httpx
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior open-source maintainer reviewing a GitHub repository.
You receive structured metrics (commits, contributors, issues, PRs, releases) plus README text
and a sample of open issues.

Respond with a single JSON object only (no markdown fences), matching this schema:
{
  "health_summary": "2-4 sentences",
  "strengths": ["...", "..."],
  "risks": ["...", "..."],
  "recommendations": ["actionable item", "..."],
  "readme_assessment": "1-3 sentences or null",
  "community_signals": "1-3 sentences on issues/PR/activity or null"
}

Be specific to the data provided. Do not invent statistics not present in the input.
If README is missing, say so in readme_assessment. Keep lists to at most 5 items each."""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return _repair_truncated_json(text[start:] if start != -1 else text)


def _repair_truncated_json(text: str) -> dict[str, Any]:
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack:
                stack.pop()

    repaired = text
    if in_string:
        repaired += '"'
    repaired = re.sub(r",\s*$", "", repaired)
    repaired += "".join(reversed(stack))
    return json.loads(repaired)

async def complete_json(*, user_content: str) -> tuple[dict[str, Any], str, str]:
    """
    Call configured LLM provider. Returns (parsed_json, provider, model).
    Raises RuntimeError when no provider is configured or the API fails.
    """
    provider = settings.ai_provider.lower().strip()
    if provider == "ollama":
        return await _ollama(user_content)
    raise RuntimeError(
        "AI analysis is not configured. Set AI_PROVIDER to one of: "
        "ollama (free/local), gemini (free API key), groq (free tier), "
        "anthropic, openai."
    )

async def _ollama_chat(
    client: httpx.AsyncClient,
    *,
    base: str,
    model: str,
    user_content: str,
    json_mode: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "options": {
            "num_ctx": 8192,
            "num_predict": settings.ai_max_tokens,
            "temperature": 0.2,
        },
    }
    if json_mode:
        payload["format"] = {
            "type": "object",
            "properties": {
                "health_summary": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "risks": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "recommendations": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "readme_assessment": {"type": ["string", "null"]},
                "community_signals": {"type": ["string", "null"]},
            },
            "required": ["health_summary", "strengths", "risks", "recommendations"],
        }

    response = await client.post(f"{base}/api/chat", json=payload)
    if response.status_code == 404:
        raise RuntimeError(
            f"Ollama model '{model}' not found. Run: ollama pull {model}"
        )
    response.raise_for_status()
    return response.json()


async def _ollama(user_content: str) -> tuple[dict[str, Any], str, str]:
    model = settings.ai_model or "llama3.2:3b"
    base = settings.ollama_base_url.rstrip("/")
    timeout = httpx.Timeout(
        connect=15.0,
        read=float(settings.ollama_request_timeout),
        write=15.0,
        pool=15.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            body = await _ollama_chat(
                client,
                base=base,
                model=model,
                user_content=user_content,
                json_mode=True,
            )
            text = (body.get("message") or {}).get("content") or ""
            if not text.strip():
                logger.warning("Ollama JSON mode returned empty; retrying without format=json")
                body = await _ollama_chat(
                    client,
                    base=base,
                    model=model,
                    user_content=user_content,
                    json_mode=False,
                )
                text = (body.get("message") or {}).get("content") or ""

            if not text.strip():
                done = body.get("done_reason") or "unknown"
                raise RuntimeError(
                    f"Ollama returned empty content (done_reason={done}). "
                    "Try a smaller/faster model: ollama pull llama3.2:1b or qwen2.5:1.5b"
                )
            return _extract_json(text), "ollama", model
    except httpx.ReadTimeout as exc:
        raise RuntimeError(
            f"Ollama timed out after {settings.ollama_request_timeout}s. "
            "Use a smaller model (llama3.2:1b, qwen2.5:1.5b) or increase OLLAMA_REQUEST_TIMEOUT."
        ) from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Cannot reach Ollama at "
            f"{base}. Start the Ollama app or run `ollama serve`."
        ) from exc
