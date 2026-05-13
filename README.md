# crewai-a2a

A multi-agent research crew built with [CrewAI](https://github.com/crewai/crewai), exposed as an [A2A](https://google.github.io/A2A/) service. Send it a topic via A2A's `SendMessage` and it returns a structured research report.

## Architecture

Three agents collaborate in a hierarchical crew:

```
Coordinator (manager)
  |-- Researcher  -->  [optional A2A peer delegation]
  |-- Writer
```

- **Coordinator** decomposes the request into sub-tasks and delegates to the team.
- **Researcher** investigates each sub-topic. When a peer A2A service is configured, can delegate analysis to it via the `delegate_to_a2a_agent` tool.
- **Writer** transforms research findings into a structured markdown report.

Agent roles, goals, and backstories are defined in `config/agents.yaml`. Task descriptions live in `config/tasks.yaml`.

### A2A Protocol

The server implements the [A2A protocol](https://google.github.io/A2A/specification/) (JSON-RPC 2.0 binding, protocol version 1.0):

- Agent card at `/.well-known/agent-card.json`
- `SendMessage` accepts a text topic, returns a completed task with the report as an artifact
- Task lifecycle: `SUBMITTED` -> `WORKING` -> `COMPLETED` / `FAILED`
- Health check at `/healthz`

### A2A Peer Delegation

When `A2A_PEER_URL` is set, the Researcher agent gets a `delegate_to_a2a_agent` tool that makes A2A JSON-RPC calls to the configured peer. This uses CrewAI's standard tool calling mechanism rather than CrewAI's built-in A2A client, which has a [known issue](https://github.com/crewai/crewai/issues) with models that wrap JSON output in markdown fences.

### a2a-sdk Compatibility

CrewAI 1.14.x targets a2a-sdk 0.3.x. This project uses a2a-sdk 1.0.x for the protobuf-based server stack. The `_a2a_compat.py` module bridges CrewAI's 0.3.x type imports to 1.0.x at runtime. The `[tool.uv]` section in `pyproject.toml` overrides CrewAI's transitive 0.3.x pin. When CrewAI natively supports a2a-sdk 1.0.x, the compat layer and override can be removed.

## Quickstart

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and enter the repo
git clone <repo-url> crewai-a2a && cd crewai-a2a

# Create your environment file
cp .env.example .env
# Edit .env — set LLM_BASE_URL and LLM_API_KEY at minimum

# Install dependencies
uv sync

# Run the server
uv run python -m crewai_a2a.server
```

The server starts on port 5000 (configurable via `A2A_PORT`).

### Test it

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "SendMessage",
    "params": {
      "message": {
        "role": "ROLE_USER",
        "parts": [{"text": "Research the current state of quantum computing"}],
        "messageId": "msg-1"
      }
    }
  }'
```

### Docker

```bash
docker compose up --build
```

## Configuration

All configuration is via environment variables. See `.env.example` for the full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_BASE_URL` | Yes | | OpenAI-compatible API base URL |
| `LLM_API_KEY` | Yes | | API key for the LLM endpoint |
| `LLM_MODEL` | No | `gpt-4o` | Model name |
| `A2A_PORT` | No | `5000` | Server listen port |
| `A2A_PEER_URL` | No | | A2A peer for delegation (e.g. `http://localhost:5001`) |
| `SSL_VERIFY` | No | `true` | Set `false` for self-signed certificate environments |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

### Per-Agent LLM Overrides

Each agent can use a different LLM endpoint, key, or model. Set `{AGENT}_LLM_API_KEY`, `{AGENT}_LLM_MODEL`, or `{AGENT}_LLM_BASE_URL` where `{AGENT}` is `COORDINATOR`, `RESEARCHER`, or `WRITER`. Unset variables fall back to the global defaults.

## Customization

- **Agents**: Edit `config/agents.yaml` to change roles, goals, and backstories.
- **Tasks**: Edit `config/tasks.yaml` to change task descriptions and expected outputs.
- **Tools**: Add tools to agents in `src/crewai_a2a/agents.py`.
- **Crew process**: Change from hierarchical to sequential in `src/crewai_a2a/crew.py`.

## Tests

```bash
uv run pytest
```

## Project Structure

```
config/
  agents.yaml          # Agent role definitions
  tasks.yaml           # Task descriptions
src/crewai_a2a/
  server.py            # A2A server (Starlette + a2a-sdk)
  crew.py              # Crew assembly
  agents.py            # Agent creation with LLM and tool wiring
  tasks.py             # Task creation
  a2a_tool.py          # Custom A2A delegation tool
  config.py            # Pydantic settings
  _a2a_compat.py       # a2a-sdk 0.3.x -> 1.0.x bridge for CrewAI
tests/
  test_server.py       # A2A server + agent card tests
  test_a2a_tool.py     # A2A delegation tool tests
  test_agents.py       # Agent wiring tests
  test_crew.py         # Crew assembly tests
  test_config.py       # Settings tests
```

## License

MIT
