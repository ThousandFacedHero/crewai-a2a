from pathlib import Path
import yaml
from crewai import Agent, LLM
from crewai_a2a.a2a_tool import make_a2a_delegate_tool
from crewai_a2a.config import Settings

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

def _load_agent_config() -> dict:
    with open(CONFIG_DIR / "agents.yaml") as f:
        return yaml.safe_load(f)

def _build_llm(settings: Settings, agent_name: str) -> LLM:
    cfg = settings.llm_for(agent_name)
    return LLM(model=cfg["model"], api_key=cfg["api_key"], base_url=cfg["base_url"])

def create_agents(settings: Settings) -> list[Agent]:
    cfg = _load_agent_config()

    # Build A2A delegation tool for the Researcher. Uses standard tool calling
    # instead of CrewAI's built-in A2A client (which forces structured output
    # via response_model, breaking models that wrap JSON in markdown fences).
    researcher_tools = []
    if settings.a2a_peer_url:
        researcher_tools.append(make_a2a_delegate_tool(settings))

    coordinator = Agent(
        role=cfg["coordinator"]["role"],
        goal=cfg["coordinator"]["goal"],
        backstory=cfg["coordinator"]["backstory"],
        llm=_build_llm(settings, "coordinator"),
        verbose=True,
        allow_delegation=True,
    )
    researcher = Agent(
        role=cfg["researcher"]["role"],
        goal=cfg["researcher"]["goal"],
        backstory=cfg["researcher"]["backstory"],
        llm=_build_llm(settings, "researcher"),
        verbose=True,
        allow_delegation=True,
        tools=researcher_tools,
    )
    writer = Agent(
        role=cfg["writer"]["role"],
        goal=cfg["writer"]["goal"],
        backstory=cfg["writer"]["backstory"],
        llm=_build_llm(settings, "writer"),
        verbose=True,
        allow_delegation=False,
    )
    return [coordinator, researcher, writer]
