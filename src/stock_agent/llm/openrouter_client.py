from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from stock_agent.config import get_settings

# 일시적 장애(rate limit·서버 오류)만 재시도한다. 그 외 4xx는 요청 자체가 잘못된 것이라
# 재시도해도 같은 실패를 반복하며 크레딧·시간만 소모하므로 즉시 실패시킨다.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = (0.5, 1.5)


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


def _post_with_retry(payload: dict[str, Any], settings: Any) -> requests.Response:
    """일시적 장애(429·5xx·네트워크 오류)에 한해 최대 _MAX_RETRIES회 재시도한다."""
    last_error: Exception | None = None
    response: requests.Response | None = None

    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            time.sleep(_RETRY_BACKOFF_SECONDS[attempt - 1])
        try:
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
        except requests.RequestException as exc:
            last_error = exc
            continue

        if response.status_code not in _RETRYABLE_STATUS_CODES:
            return response

    if response is not None:
        return response
    raise OpenRouterClientError(
        f"OpenRouter request failed after {_MAX_RETRIES + 1} attempts: {last_error}"
    ) from last_error


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
    response = _post_with_retry(payload, settings)
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
