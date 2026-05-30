from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from stock_agent.config import get_settings


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenRouterClientError(RuntimeError):
    pass


def _chat_completions_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped


def openrouter_chat_json(
    messages: list[ChatMessage],
    *,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise OpenRouterClientError("OPENROUTER_API_KEY is not configured")

    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        _chat_completions_url(settings.openrouter_base_url),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Pocat-1-team/stock-agent",
            "X-Title": "stock-agent Competitor Analysis",
        },
        json=payload,
        timeout=settings.openrouter_timeout_seconds,
    )
    if response.status_code >= 400:
        raise OpenRouterClientError(
            f"OpenRouter request failed ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterClientError("OpenRouter response missing chat message") from exc

    try:
        parsed = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise OpenRouterClientError(f"OpenRouter response is not valid JSON: {content[:300]}") from exc

    if not isinstance(parsed, dict):
        raise OpenRouterClientError("OpenRouter JSON response must be an object")
    return parsed
