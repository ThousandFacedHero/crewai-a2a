from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Global LLM defaults — every agent inherits these unless overridden.
    llm_base_url: str
    llm_api_key: str
    llm_model: str = "gpt-4o"

    # Per-agent overrides. When set, the agent gets its own LiteLLM key/model/url
    # instead of the global default. Useful for routing agents through different
    # LiteLLM virtual keys with separate rate limits or model access.
    coordinator_llm_api_key: str | None = None
    coordinator_llm_model: str | None = None
    coordinator_llm_base_url: str | None = None
    researcher_llm_api_key: str | None = None
    researcher_llm_model: str | None = None
    researcher_llm_base_url: str | None = None
    writer_llm_api_key: str | None = None
    writer_llm_model: str | None = None
    writer_llm_base_url: str | None = None

    ssl_verify: bool = True

    a2a_port: int = 5000
    a2a_peer_url: str | None = None
    log_level: str = "INFO"
    otel_exporter_endpoint: str | None = None
    graphiti_uri: str | None = None
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = None

    def llm_for(self, agent_name: str) -> dict:
        """Return {"model", "api_key", "base_url"} for an agent, with fallback to globals."""
        prefix = agent_name.lower()
        return {
            "model": getattr(self, f"{prefix}_llm_model", None) or self.llm_model,
            "api_key": getattr(self, f"{prefix}_llm_api_key", None) or self.llm_api_key,
            "base_url": getattr(self, f"{prefix}_llm_base_url", None) or self.llm_base_url,
        }

    @property
    def graphiti_enabled(self) -> bool:
        return self.graphiti_uri is not None
