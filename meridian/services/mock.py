"""Local stand-ins that satisfy the service Protocols.

This is NOT a WebSocket. It is a development event source that emits the same
event shape the backend will, so the UI can be built and demoed offline.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from ..data import mock
from .interfaces import AgentEvent
from .report_pdf import render_report_pdf


class MockEventSource:
    def __init__(self, ticks: int = 4, tick_seconds: float = 0.55):
        self.ticks, self.tick_seconds = ticks, tick_seconds

    async def stream(self, profile: dict[str, str]) -> AsyncIterator[AgentEvent]:
        for agent in mock.AGENT_IDS:
            for i in range(self.ticks):
                yield {"type": f"{agent}_processing", "agent": agent, "progress": (i + 1) / (self.ticks + 1)}
                await asyncio.sleep(self.tick_seconds)
            yield {"type": f"{agent}_completed", "agent": agent, "progress": 1.0}
            await asyncio.sleep(0.35)


class MockReportService:
    def get_report(self, profile):
        return mock.build_report(profile)

    def render_pdf(self, report):
        return render_report_pdf(report)
