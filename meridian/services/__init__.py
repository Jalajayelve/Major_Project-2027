"""Swap these factories for real FastAPI / WebSocket clients later."""
from .interfaces import AgentEvent, AgentEventSource, ProfileService, ReportService
from .mock import MockEventSource, MockReportService


def get_event_source() -> AgentEventSource:
    return MockEventSource()


def get_report_service() -> ReportService:
    return MockReportService()


__all__ = ["AgentEvent", "AgentEventSource", "ProfileService", "ReportService", "get_event_source", "get_report_service"]
