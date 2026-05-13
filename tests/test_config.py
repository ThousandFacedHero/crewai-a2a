import os
import pytest
from crewai_a2a.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    s = Settings(_env_file=None)
    assert s.llm_base_url == "http://localhost:4000/v1"
    assert s.llm_api_key == "test-key"
    assert s.llm_model == "gpt-4o"
    assert s.a2a_port == 5000


def test_settings_requires_llm_base_url():
    clean = {k: v for k, v in os.environ.items() if not k.startswith("LLM_")}
    with pytest.raises(Exception):
        Settings(_env_file=None, **{})


def test_graphiti_disabled_by_default(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://x")
    monkeypatch.setenv("LLM_API_KEY", "k")
    s = Settings()
    assert s.graphiti_enabled is False


def test_graphiti_enabled_when_uri_set(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://x")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("GRAPHITI_URI", "bolt://localhost:7687")
    s = Settings()
    assert s.graphiti_enabled is True


def test_llm_for_returns_global_defaults(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://proxy:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "global-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    s = Settings()
    cfg = s.llm_for("researcher")
    assert cfg["api_key"] == "global-key"
    assert cfg["model"] == "gpt-4o"
    assert cfg["base_url"] == "http://proxy:4000/v1"


def test_llm_for_per_agent_override(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://proxy:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "global-key")
    monkeypatch.setenv("RESEARCHER_LLM_API_KEY", "researcher-key")
    monkeypatch.setenv("RESEARCHER_LLM_MODEL", "gpt-4o-mini")
    s = Settings()
    researcher_cfg = s.llm_for("researcher")
    assert researcher_cfg["api_key"] == "researcher-key"
    assert researcher_cfg["model"] == "gpt-4o-mini"
    assert researcher_cfg["base_url"] == "http://proxy:4000/v1"  # falls back
    coordinator_cfg = s.llm_for("coordinator")
    assert coordinator_cfg["api_key"] == "global-key"  # not overridden
