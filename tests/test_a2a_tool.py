import json
from unittest.mock import patch, MagicMock

import pytest
import httpx

from crewai_a2a.a2a_tool import make_a2a_delegate_tool


@pytest.fixture
def peer_settings(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("A2A_PEER_URL", "http://maf:5000")
    from crewai_a2a.config import Settings
    return Settings()


@pytest.fixture
def no_peer_settings(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    from crewai_a2a.config import Settings
    return Settings()


def _mock_a2a_response(text: str, task_state: str = "TASK_STATE_COMPLETED"):
    return {
        "jsonrpc": "2.0",
        "id": "test-id",
        "result": {
            "task": {
                "id": "task-1",
                "contextId": "ctx-1",
                "status": {"state": task_state},
                "artifacts": [
                    {
                        "artifactId": "result",
                        "parts": [{"text": text}],
                    }
                ],
            }
        },
    }


def test_no_peer_returns_fallback(no_peer_settings):
    tool = make_a2a_delegate_tool(no_peer_settings)
    result = tool.run(query="test query")
    assert "No A2A peer" in result


def test_successful_delegation(peer_settings):
    tool = make_a2a_delegate_tool(peer_settings)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _mock_a2a_response("Analysis results here")

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = tool.run(query="analyze this topic")

    assert result == "Analysis results here"

    call_args = mock_client.post.call_args
    assert call_args[0][0] == "http://maf:5000/"

    body = call_args[1]["json"]
    assert body["jsonrpc"] == "2.0"
    assert body["method"] == "SendMessage"
    assert body["params"]["message"]["role"] == "ROLE_USER"
    assert body["params"]["message"]["parts"][0]["text"] == "analyze this topic"

    headers = call_args[1]["headers"]
    assert headers["A2A-Version"] == "1.0"
    assert headers["Content-Type"] == "application/json"


def test_http_error_returns_fallback(peer_settings):
    tool = make_a2a_delegate_tool(peer_settings)

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = tool.run(query="test")

    assert "HTTP 500" in result


def test_jsonrpc_error_returned(peer_settings):
    tool = make_a2a_delegate_tool(peer_settings)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test-id",
        "error": {"code": -32600, "message": "Invalid request"},
    }

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = tool.run(query="test")

    assert "Invalid request" in result


def test_no_artifacts_handled(peer_settings):
    tool = make_a2a_delegate_tool(peer_settings)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test-id",
        "result": {
            "task": {
                "id": "task-1",
                "contextId": "ctx-1",
                "status": {"state": "TASK_STATE_COMPLETED"},
                "artifacts": [],
            }
        },
    }

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = tool.run(query="test")

    assert "no text artifacts" in result


def test_network_error_returns_fallback(peer_settings):
    tool = make_a2a_delegate_tool(peer_settings)

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value = mock_client

        result = tool.run(query="test")

    assert "failed" in result.lower()


def test_message_id_is_uuid(peer_settings):
    """Verify each call generates a unique UUID messageId per A2A spec."""
    tool = make_a2a_delegate_tool(peer_settings)

    captured_ids = []

    def capture_post(url, **kwargs):
        body = kwargs["json"]
        captured_ids.append(body["params"]["message"]["messageId"])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _mock_a2a_response("ok")
        return resp

    with patch("crewai_a2a.a2a_tool.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = capture_post
        mock_client_cls.return_value = mock_client

        tool.run(query="first")
        tool.run(query="second")

    assert len(captured_ids) == 2
    assert captured_ids[0] != captured_ids[1]
    import uuid
    for mid in captured_ids:
        uuid.UUID(mid)  # raises if not valid UUID
