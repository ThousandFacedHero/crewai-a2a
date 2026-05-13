from crewai import Crew, Process
from crewai_a2a.agents import create_agents
from crewai_a2a.config import Settings
from crewai_a2a.tasks import create_tasks

def build_crew(settings: Settings) -> Crew:
    agents = create_agents(settings)
    tasks = create_tasks(agents)
    coordinator = next(a for a in agents if a.role == "Coordinator")
    # CrewAI requires manager_agent to be excluded from the agents (worker) list
    worker_agents = [a for a in agents if a.role != "Coordinator"]
    crew = Crew(
        agents=worker_agents,
        tasks=tasks,
        process=Process.hierarchical,
        manager_agent=coordinator,
        verbose=True,
    )
    return crew
