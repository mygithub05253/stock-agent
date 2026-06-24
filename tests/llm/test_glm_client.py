from unittest.mock import MagicMock, patch

import pytest

from stock_agent.llm.glm_client import (
    ChatMessage,
    GLMClientError,
    _strip_json_fence,
    chat_completion_json,
)


def _mock_settings(api_key: str | None = "glm:test-key"):
    s = MagicMock()
    s.glm_api_key = api_key
    s.glm_model = "glm-4.5-flash"
    s.glm_base_url = "https://api.z.ai/api/paas/v4"
    s.glm_timeout_seconds = 30
    return s


def test_strip_json_fence_removes_json_prefix():
    raw = '```json\n{"key": "value"}\n```'
    assert _strip_json_fence(raw) == '{"key": "value"}'


def test_raises_when_no_api_key():
    with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings(None)):
        with pytest.raises(GLMClientError, match="GLM_API_KEY"):
            chat_completion_json([ChatMessage(role="user", content="test")])


def test_parses_valid_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": '{"intent": "ok"}'}}]}
    with patch("stock_agent.llm.glm_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            result = chat_completion_json([ChatMessage(role="user", content="test")])
    assert result == {"intent": "ok"}


def test_raises_on_http_error_after_retries_exhausted():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limit exceeded"
    with patch("stock_agent.llm.glm_client.requests.post", return_value=mock_resp) as mock_post:
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.glm_client.time.sleep"):
                with pytest.raises(GLMClientError, match="429"):
                    chat_completion_json([ChatMessage(role="user", content="test")])
    assert mock_post.call_count == 3


def test_does_not_retry_on_client_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "unauthorized"
    with patch("stock_agent.llm.glm_client.requests.post", return_value=mock_resp) as mock_post:
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(GLMClientError, match="401"):
                chat_completion_json([ChatMessage(role="user", content="test")])
    assert mock_post.call_count == 1


def test_retries_then_succeeds_on_transient_error():
    fail_resp = MagicMock()
    fail_resp.status_code = 503
    fail_resp.text = "temporarily unavailable"
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"choices": [{"message": {"content": '{"intent": "recovered"}'}}]}
    with patch(
        "stock_agent.llm.glm_client.requests.post",
        side_effect=[fail_resp, ok_resp],
    ) as mock_post:
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.glm_client.time.sleep"):
                result = chat_completion_json([ChatMessage(role="user", content="test")])
    assert result == {"intent": "recovered"}
    assert mock_post.call_count == 2


def test_retries_on_network_exception_then_succeeds():
    import requests as requests_module

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"choices": [{"message": {"content": '{"intent": "ok"}'}}]}
    with patch(
        "stock_agent.llm.glm_client.requests.post",
        side_effect=[requests_module.ConnectionError("boom"), ok_resp],
    ) as mock_post:
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            with patch("stock_agent.llm.glm_client.time.sleep"):
                result = chat_completion_json([ChatMessage(role="user", content="test")])
    assert result == {"intent": "ok"}
    assert mock_post.call_count == 2


def test_raises_on_invalid_json():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "not json"}}]}
    with patch("stock_agent.llm.glm_client.requests.post", return_value=mock_resp):
        with patch("stock_agent.llm.glm_client.get_settings", return_value=_mock_settings()):
            with pytest.raises(GLMClientError, match="not valid JSON"):
                chat_completion_json([ChatMessage(role="user", content="test")])
