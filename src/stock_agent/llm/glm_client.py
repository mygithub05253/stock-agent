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


class GLMClientError(RuntimeError):
    pass


def _chat_completions_url(base_url: str) -> str:
    clean_base_url = base_url.rstrip("/")
    if clean_base_url.endswith("/chat/completions"):
        return clean_base_url
    return f"{clean_base_url}/chat/completions"


def _api_key_for_header(api_key: str) -> str:
    if api_key.startswith("glm:"):
        return api_key.removeprefix("glm:")
    return api_key


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped


def chat_completion_json(
    messages: list[ChatMessage],
    *,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.glm_api_key:
        raise GLMClientError("GLM_API_KEY is not configured")

    payload = {
        "model": settings.glm_model,
        "messages": [message.__dict__ for message in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }
    response = requests.post(
        _chat_completions_url(settings.glm_base_url),
        headers={
            "Authorization": f"Bearer {_api_key_for_header(settings.glm_api_key)}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=settings.glm_timeout_seconds,
    )
    if response.status_code >= 400:
        raise GLMClientError(f"GLM request failed with status {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GLMClientError("GLM response did not include a chat message") from exc

    try:
        parsed = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise GLMClientError(f"GLM response was not valid JSON: {content[:300]}") from exc

    if not isinstance(parsed, dict):
        raise GLMClientError("GLM JSON response must be an object")
    return parsed
