from crewai_a2a.tasks import create_tasks
from crewai_a2a.agents import create_agents
from crewai_a2a.crew import build_crew

def test_create_tasks_returns_two(mock_settings):
    agents = create_agents(mock_settings)
    tasks = create_tasks(agents)
    assert len(tasks) == 2

def test_research_task_assigned_to_researcher(mock_settings):
    agents = create_agents(mock_settings)
    tasks = create_tasks(agents)
    research_task = tasks[0]
    assert research_task.agent.role == "Researcher"

def test_write_task_assigned_to_writer(mock_settings):
    agents = create_agents(mock_settings)
    tasks = create_tasks(agents)
    write_task = tasks[1]
    assert write_task.agent.role == "Writer"

def test_build_crew_has_all_agents(mock_settings):
    crew = build_crew(mock_settings)
    # Coordinator is the manager_agent and excluded from crew.agents per CrewAI rules.
    # Worker agents are Researcher and Writer only.
    assert len(crew.agents) == 2
    roles = {a.role for a in crew.agents}
    assert "Researcher" in roles
    assert "Writer" in roles
    assert crew.manager_agent.role == "Coordinator"

def test_build_crew_has_all_tasks(mock_settings):
    crew = build_crew(mock_settings)
    assert len(crew.tasks) == 2
