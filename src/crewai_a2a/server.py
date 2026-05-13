import logging
import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers.default_request_handler_v2 import (
    DefaultRequestHandlerV2,
)
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Artifact,
    Part,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from crewai_a2a.config import Settings
from crewai_a2a.crew import build_crew

logger = logging.getLogger(__name__)


class CrewAgentExecutor(AgentExecutor):
    """Runs the CrewAI research crew in response to A2A SendMessage requests."""

    def __init__(self, settings: Settings):
        self._settings = settings

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task_id = context.task_id
        context_id = context.context_id

        # Extract text from the incoming message parts.
        topic = ""
        if context.message:
            for part in context.message.parts:
                if part.text:
                    topic += part.text

        # The SDK requires a Task object as the first event to create it in
        # the store. Subsequent TaskStatusUpdateEvents update its state.
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
            )
        )

        if not topic:
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_FAILED),
                )
            )
            return

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
            )
        )

        try:
            crew = build_crew(self._settings)
            result = crew.kickoff(inputs={"topic": topic})

            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    artifact=Artifact(
                        artifact_id="result",
                        parts=[Part(text=str(result))],
                    ),
                    last_chunk=True,
                )
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                )
            )
        except Exception:
            logger.exception("Crew execution failed")
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_FAILED),
                )
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_CANCELED),
            )
        )


def _build_agent_card(settings: Settings) -> AgentCard:
    port = settings.a2a_port
    base_url = os.getenv("A2A_PUBLIC_URL", f"http://localhost:{port}")
    return AgentCard(
        name="CrewAI Research Crew",
        description=(
            "Multi-agent research crew that decomposes topics, researches "
            "sub-questions, and produces structured reports."
        ),
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        skills=[
            AgentSkill(
                id="research-report",
                name="Research and Report",
                description="Research a topic and produce a structured report",
                tags=["research", "report", "analysis"],
            )
        ],
        supported_interfaces=[
            AgentInterface(
                url=base_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
    )


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _make_agent_card_route(agent_card: AgentCard, base_url: str):
    from a2a.server.routes.agent_card_routes import agent_card_to_dict

    async def _get_agent_card(request: Request) -> JSONResponse:
        card_dict = agent_card_to_dict(agent_card)
        card_dict.setdefault("url", f"{base_url}/")
        return JSONResponse(card_dict)

    return Route("/.well-known/agent-card.json", _get_agent_card, methods=["GET"])


def create_app(settings: Settings | None = None) -> Starlette:
    if settings is None:
        settings = Settings()

    agent_card = _build_agent_card(settings)
    base_url = os.getenv("A2A_PUBLIC_URL", f"http://localhost:{settings.a2a_port}")
    executor = CrewAgentExecutor(settings)
    task_store = InMemoryTaskStore()

    handler = DefaultRequestHandlerV2(
        agent_executor=executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    routes = [
        Route("/healthz", health, methods=["GET"]),
        _make_agent_card_route(agent_card, base_url),
        *create_jsonrpc_routes(handler, rpc_url="/"),
    ]

    return Starlette(routes=routes)


def _disable_ssl_verification():
    """Monkey-patch httpx to skip SSL verification for internal CA environments."""
    import httpx

    _orig_sync = httpx.Client.__init__
    _orig_async = httpx.AsyncClient.__init__

    def _sync_no_verify(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _orig_sync(self, *args, **kwargs)

    def _async_no_verify(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _orig_async(self, *args, **kwargs)

    httpx.Client.__init__ = _sync_no_verify
    httpx.AsyncClient.__init__ = _async_no_verify


def main():
    import uvicorn

    settings = Settings()
    logging.basicConfig(level=getattr(logging, settings.log_level))
    if not settings.ssl_verify:
        _disable_ssl_verification()
    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=settings.a2a_port)


if __name__ == "__main__":
    main()
