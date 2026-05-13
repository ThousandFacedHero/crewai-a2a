import pytest


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    from crewai_a2a.config import Settings
    return Settings()
