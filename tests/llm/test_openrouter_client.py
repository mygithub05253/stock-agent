from unittest.mock import MagicMock, patch

import pytest

from stock_agent.llm.openrouter_client import (
    ChatMessage,
    OpenRouterClientError,
    _strip_json_fence,
    openrouter_chat_json,
)


def test_strip_json_fence_removes_json_prefix():
    raw = '```json\n{"key": "value"}\n```'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def test_strip_json_fence_removes_plain_prefix():
    raw = '```\n{"key": "value"}\n```'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def test_strip_json_fence_leaves_clean_json():
    raw = '{"key": "value"}'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def _mock_settings(api_key: str | None = "test-key"):
    s = MagicMock()
    s.openrouter_api_key = api_key
    s.openrouter_model = "google/gemini-flash-1.5"
    s.openrouter_base_url = "https://openrouter.ai/api/v1"
    s.openrouter_timeout_seconds = 30
    return s


def test_raises_when_no_api_key():
    with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings(None)):
        with pytest.raises(OpenRouterClientError, match="OPENROUTER_API_KEY"):
            openrouter_chat_json([ChatMessage(role="user", content="test")])


def test_parses_valid_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"peer_summary": "좋은 요약"}'}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result == {"peer_summary": "좋은 요약"}


def test_parses_fenced_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '```json\n{"peer_summary": "good"}\n```'}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result["peer_summary"] == "good"


def test_raises_on_http_error_after_retries_exhausted():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limit exceeded"
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp) as mock_post:
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.openrouter_client.time.sleep"):
                with pytest.raises(OpenRouterClientError, match="429"):
                    openrouter_chat_json([ChatMessage(role="user", content="test")])
    # 일시적 장애(429)는 최초 1회 + 재시도 2회 = 총 3회 시도 후 실패해야 한다
    assert mock_post.call_count == 3


def test_does_not_retry_on_client_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "unauthorized"
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp) as mock_post:
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(OpenRouterClientError, match="401"):
                openrouter_chat_json([ChatMessage(role="user", content="test")])
    # 잘못된 요청(4xx, 429 제외)은 재시도 없이 즉시 실패해 크레딧을 보호한다
    assert mock_post.call_count == 1


def test_retries_then_succeeds_on_transient_error():
    fail_resp = MagicMock()
    fail_resp.status_code = 503
    fail_resp.text = "temporarily unavailable"
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "choices": [{"message": {"content": '{"peer_summary": "복구됨"}'}}]
    }
    with patch(
        "stock_agent.llm.openrouter_client.requests.post",
        side_effect=[fail_resp, ok_resp],
    ) as mock_post:
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.openrouter_client.time.sleep"):
                result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result == {"peer_summary": "복구됨"}
    assert mock_post.call_count == 2


def test_retries_on_network_exception_then_succeeds():
    import requests as requests_module

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "choices": [{"message": {"content": '{"peer_summary": "ok"}'}}]
    }
    with patch(
        "stock_agent.llm.openrouter_client.requests.post",
        side_effect=[requests_module.ConnectionError("boom"), ok_resp],
    ) as mock_post:
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.openrouter_client.time.sleep"):
                result = openrouter_chat_json([ChatMessage(role="user", content="test")])
    assert result == {"peer_summary": "ok"}
    assert mock_post.call_count == 2


def test_raises_on_invalid_json():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "이것은 JSON이 아닙니다"}}]
    }
    with patch("stock_agent.llm.openrouter_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.openrouter_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(OpenRouterClientError, match="not valid JSON"):
                openrouter_chat_json([ChatMessage(role="user", content="test")])
