from pathlib import Path
import yaml
from crewai import Agent, Task

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

def _load_task_config() -> dict:
    with open(CONFIG_DIR / "tasks.yaml") as f:
        return yaml.safe_load(f)

def create_tasks(agents: list[Agent]) -> list[Task]:
    cfg = _load_task_config()
    researcher = next(a for a in agents if a.role == "Researcher")
    writer = next(a for a in agents if a.role == "Writer")
    research_task = Task(
        description=cfg["research"]["description"],
        expected_output=cfg["research"]["expected_output"],
        agent=researcher,
    )
    write_task = Task(
        description=cfg["write_report"]["description"],
        expected_output=cfg["write_report"]["expected_output"],
        agent=writer,
    )
    return [research_task, write_task]
