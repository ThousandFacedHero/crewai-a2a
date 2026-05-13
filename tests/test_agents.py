from crewai_a2a.agents import create_agents

def test_create_agents_returns_three(mock_settings):
    agents = create_agents(mock_settings)
    assert len(agents) == 3
    roles = {a.role for a in agents}
    assert "Coordinator" in roles
    assert "Researcher" in roles
    assert "Writer" in roles

def test_researcher_has_delegation_enabled(mock_settings):
    agents = create_agents(mock_settings)
    researcher = next(a for a in agents if a.role == "Researcher")
    assert researcher.allow_delegation is True

def test_researcher_has_a2a_tool_when_peer_url_set(monkeypatch, mock_settings):
    monkeypatch.setenv("A2A_PEER_URL", "http://maf:5000")
    from crewai_a2a.config import Settings
    settings = Settings()

    agents = create_agents(settings)
    researcher = next(a for a in agents if a.role == "Researcher")

    tool_names = [t.name for t in researcher.tools]
    assert "Delegate to A2A Agent" in tool_names


def test_researcher_no_a2a_tool_when_peer_url_unset(mock_settings):
    agents = create_agents(mock_settings)
    researcher = next(a for a in agents if a.role == "Researcher")

    tool_names = [t.name for t in researcher.tools]
    assert "Delegate to A2A Agent" not in tool_names


def test_per_agent_llm_keys(monkeypatch, mock_settings):
    monkeypatch.setenv("RESEARCHER_LLM_API_KEY", "researcher-key-123")
    monkeypatch.setenv("RESEARCHER_LLM_MODEL", "gpt-4o-mini")
    from crewai_a2a.config import Settings
    settings = Settings()
    agents = create_agents(settings)
    researcher = next(a for a in agents if a.role == "Researcher")
    coordinator = next(a for a in agents if a.role == "Coordinator")
    assert researcher.llm.api_key == "researcher-key-123"
    assert researcher.llm.model == "gpt-4o-mini"
    assert coordinator.llm.api_key == "test-key"
