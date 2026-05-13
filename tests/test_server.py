"""A2A protocol compliance tests for the crewai-a2a server.

Tests validate against the A2A spec requirements:
- Agent card at /.well-known/agent-card.json with required fields
- JSON-RPC 2.0 envelope format
- Proper error responses for malformed requests
- Method names are PascalCase (SendMessage, not tasks/send)
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    from crewai_a2a.server import create_app
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Health check (not A2A spec, our custom endpoint) ---

async def test_health_check(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# --- Agent Card: /.well-known/agent-card.json ---

async def test_agent_card_served_at_spec_path(client):
    resp = await client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200

async def test_agent_card_has_required_fields(client):
    resp = await client.get("/.well-known/agent-card.json")
    card = resp.json()
    assert "name" in card
    assert "description" in card
    assert "version" in card
    assert "supportedInterfaces" in card
    assert "defaultInputModes" in card
    assert "defaultOutputModes" in card
    assert "skills" in card
    assert "capabilities" in card

async def test_agent_card_interfaces_have_required_fields(client):
    resp = await client.get("/.well-known/agent-card.json")
    card = resp.json()
    assert len(card["supportedInterfaces"]) >= 1
    iface = card["supportedInterfaces"][0]
    assert "url" in iface
    assert "protocolBinding" in iface
    assert "protocolVersion" in iface

async def test_agent_card_skills_have_required_fields(client):
    resp = await client.get("/.well-known/agent-card.json")
    card = resp.json()
    assert len(card["skills"]) >= 1
    skill = card["skills"][0]
    assert "id" in skill
    assert "name" in skill
    assert "description" in skill
    assert "tags" in skill


# --- JSON-RPC 2.0 envelope compliance ---

async def test_jsonrpc_parse_error_on_invalid_json(client):
    resp = await client.post("/", content=b"not json", headers={"content-type": "application/json"})
    body = resp.json()
    assert body.get("jsonrpc") == "2.0"
    assert "error" in body
    assert body["error"]["code"] in (-32700, -32600)

async def test_jsonrpc_method_not_found(client):
    resp = await client.post("/", json={
        "jsonrpc": "2.0",
        "method": "NoSuchMethod",
        "id": str(uuid.uuid4()),
    })
    body = resp.json()
    assert body.get("jsonrpc") == "2.0"
    assert "error" in body
    assert body["error"]["code"] == -32601

async def test_jsonrpc_invalid_request_missing_method(client):
    resp = await client.post("/", json={
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
    })
    body = resp.json()
    assert body.get("jsonrpc") == "2.0"
    assert "error" in body
