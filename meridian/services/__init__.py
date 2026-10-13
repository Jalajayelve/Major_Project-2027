"""Service factories; keep UI/PDF dependencies out of isolated ML workers."""
from .interfaces import AgentEvent, AgentEventSource, ProfileService, ReportService


def get_event_source() -> AgentEventSource:
    from .mock import MockEventSource
    return MockEventSource()


def get_report_service() -> ReportService:
    from .mock import MockReportService
    return MockReportService()


__all__ = ["AgentEvent", "AgentEventSource", "ProfileService", "ReportService", "get_event_source", "get_report_service"]
