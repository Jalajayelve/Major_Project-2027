"""Service boundaries for the future FastAPI / WebSocket / LangGraph backend.

The UI only depends on these Protocols and on the event shape below. To connect
the real backend, write classes that satisfy them (REST client, WebSocket
consumer) and return them from `services.__init__`. Nothing else changes.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Literal, Protocol, TypedDict

AgentId = Literal[
    "profile", "university", "program", "financial",
    "scholarship", "career", "extracurricular",
]


class AgentEvent(TypedDict, total=False):
    """One message on the agent-progress channel.

    type      "<agent>_processing" | "<agent>_completed"
    agent     the agent id, e.g. "university"
    progress  0.0-1.0 while processing (optional)
    payload   agent result on completion (LangGraph state slice), optional
    """
    type: str
    agent: AgentId
    progress: float
    payload: dict[str, Any]


class ProfileService(Protocol):
    """REST: POST /profile, POST /documents (multipart)."""

    async def submit_profile(self, profile: dict[str, str]) -> str: ...
    async def submit_document(self, slot: str, filename: str, data: bytes) -> None: ...


class AgentEventSource(Protocol):
    """WebSocket: /ws/journey/{session_id} -> stream of AgentEvent."""

    def stream(self, profile: dict[str, str]) -> AsyncIterator[AgentEvent]: ...


class ReportService(Protocol):
    """REST: GET /report/{id}, GET /report/{id}/pdf."""

    def get_report(self, profile: dict[str, str]) -> dict[str, Any]: ...
    def render_pdf(self, report: dict[str, Any]) -> bytes: ...
