"""Custom A2A delegation tool for CrewAI agents.

Bypasses CrewAI's built-in A2A client (which forces structured output via
response_model, breaking models that wrap JSON in markdown fences). Instead,
makes A2A JSON-RPC calls directly via httpx through CrewAI's standard tool
calling mechanism — which works reliably with any LLM.

A2A spec compliance:
- JSON-RPC 2.0 binding with method "SendMessage"
- A2A-Version: 1.0 header
- ROLE_USER message with TextPart
- UUID-based messageId
- Extracts artifacts from completed task response
"""

from __future__ import annotations

import logging
import uuid

import httpx

from crewai.tools import tool

from crewai_a2a.config import Settings

logger = logging.getLogger(__name__)


def make_a2a_delegate_tool(settings: Settings):
    """Factory: returns a CrewAI tool bound to the configured A2A peer."""

    @tool("Delegate to A2A Agent")
    def delegate_to_a2a_agent(query: str) -> str:
        """Send a research query to an external agent service via the A2A protocol.
        Use this when the task would benefit from an external specialist's analysis.
        The external agent will process the query and return its findings."""
        if not settings.a2a_peer_url:
            return "No A2A peer service configured — proceed with your own analysis."

        msg_id = str(uuid.uuid4())
        request_body = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "SendMessage",
            "params": {
                "message": {
                    "role": "ROLE_USER",
                    "parts": [{"text": query}],
                    "messageId": msg_id,
                },
            },
        }
        headers = {
            "Content-Type": "application/json",
            "A2A-Version": "1.0",
        }

        try:
            with httpx.Client(verify=settings.ssl_verify, timeout=300) as client:
                resp = client.post(
                    f"{settings.a2a_peer_url}/",
                    json=request_body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            logger.warning("A2A delegation HTTP error: %s", exc)
            return f"A2A delegation failed (network error) — proceed with your own analysis."

        if resp.status_code != 200:
            return f"A2A peer returned HTTP {resp.status_code} — proceed with your own analysis."

        body = resp.json()

        error = body.get("error")
        if error:
            return f"A2A peer error: {error.get('message', error)}"

        task = body.get("result", {}).get("task", {})
        artifacts = task.get("artifacts", [])
        for artifact in artifacts:
            parts = artifact.get("parts", [])
            text_parts = [p["text"] for p in parts if p.get("text")]
            if text_parts:
                return "\n".join(text_parts)

        return f"A2A peer completed but returned no text artifacts."

    return delegate_to_a2a_agent
