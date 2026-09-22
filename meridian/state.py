"""App state. Talks only to `data` and `services`, never to UI code."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import reflex as rx

from .data import mock
from .services import get_event_source, get_report_service

_SECTION_COUNT = len(mock.FORM_SCHEMA)


class State(rx.State):
    # journey transition
    opening: bool = False

    # profile
    profile: dict[str, str] = dict(mock.STUDENT_PROFILE)
    profile_tab: int = 0

    # documents  (keys: "<slot>_name", "<slot>_type", "<slot>_size")
    docs: dict[str, str] = {}
    uploaded_slots: list[str] = []

    # agents
    agents: list[dict[str, Any]] = [dict(a) for a in mock.AGENTS]
    event_log: list[str] = []
    agents_running: bool = False

    # results
    selected_uni: str = mock.UNIVERSITIES[0]["id"]

    # ── journey ────────────────────────────────────────────────────────────
    @rx.event
    async def start_journey(self):
        """Open the dossier (page-turn overlay), then move to the profile."""
        self.opening = True
        yield
        await asyncio.sleep(1.55)
        yield rx.redirect("/profile")
        await asyncio.sleep(0.4)
        self.opening = False

    # ── profile ────────────────────────────────────────────────────────────
    @rx.event
    def set_field(self, key: str, value: str):
        self.profile[key] = value

    @rx.event
    def set_tab(self, index: int):
        self.profile_tab = max(0, min(index, _SECTION_COUNT - 1))

    @rx.event
    def next_tab(self):
        if self.profile_tab >= _SECTION_COUNT - 1:
            return rx.redirect("/documents")
        self.profile_tab += 1

    @rx.event
    def prev_tab(self):
        self.profile_tab = max(0, self.profile_tab - 1)

    @rx.var
    def profile_completion(self) -> int:
        keys = [f["key"] for s in mock.FORM_SCHEMA for f in s["fields"]]
        optional = {"ielts", "gmat"}
        req = [k for k in keys if k not in optional]
        filled = sum(1 for k in req if self.profile.get(k, "").strip())
        return round(100 * filled / len(req))

    @rx.var
    def completion_str(self) -> str:
        return f"{self.profile_completion}%"

    @rx.var
    def student_name(self) -> str:
        return self.profile.get("full_name", "").strip() or "Your name"

    @rx.var
    def target_program(self) -> str:
        return f"{self.profile.get('degree_goal', 'MS')} {self.profile.get('field', '')}".strip()

    # ── documents ──────────────────────────────────────────────────────────
    async def _save(self, slot: str, files: list[rx.UploadFile]):
        if not files:
            return
        f = files[0]
        name = Path(getattr(f, "filename", None) or getattr(f, "name", "document")).name
        data = await f.read()
        (rx.get_upload_dir() / name).write_bytes(data)
        kb = max(1, round(len(data) / 1024))
        self.docs[f"{slot}_name"] = name
        self.docs[f"{slot}_type"] = (Path(name).suffix.lstrip(".").upper() or "FILE")[:4]
        self.docs[f"{slot}_size"] = f"{kb} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"
        if slot not in self.uploaded_slots:
            self.uploaded_slots.append(slot)

    @rx.event
    async def upload_resume(self, files: list[rx.UploadFile]):
        await self._save("resume", files)

    @rx.event
    async def upload_transcript(self, files: list[rx.UploadFile]):
        await self._save("transcript", files)

    @rx.event
    async def upload_sop(self, files: list[rx.UploadFile]):
        await self._save("sop", files)

    @rx.event
    async def upload_lor(self, files: list[rx.UploadFile]):
        await self._save("lor", files)

    @rx.event
    async def upload_other(self, files: list[rx.UploadFile]):
        await self._save("other", files)

    @rx.event
    def load_sample_documents(self):
        for slot, d in mock.SAMPLE_DOCS.items():
            self.docs[f"{slot}_name"] = d["name"]
            self.docs[f"{slot}_type"] = d["name"].rsplit(".", 1)[-1].upper()
            self.docs[f"{slot}_size"] = d["size"]
            if slot not in self.uploaded_slots:
                self.uploaded_slots.append(slot)

    @rx.event
    def remove_document(self, slot: str):
        self.uploaded_slots = [s for s in self.uploaded_slots if s != slot]

    @rx.var
    def docs_count(self) -> int:
        return len(self.uploaded_slots)

    # ── agents ─────────────────────────────────────────────────────────────
    @rx.event(background=True)
    async def run_agents(self):
        async with self:
            if self.agents_running:
                return
            self.agents_running = True
            self.agents = [dict(a) for a in mock.AGENTS]
            self.event_log = []
            profile = dict(self.profile)
        # Replace get_event_source() with the WebSocket client to go live.
        async for event in get_event_source().stream(profile):
            async with self:
                self._apply_event(event)
        async with self:
            self.agents_running = False

    def _apply_event(self, event: dict[str, Any]):
        agents = [dict(a) for a in self.agents]
        i = mock.AGENT_IDS.index(event["agent"])
        if event["type"].endswith("_completed"):
            agents[i]["status"], agents[i]["progress"] = "completed", 100
        else:
            agents[i]["status"] = "processing"
            agents[i]["progress"] = int(event.get("progress", 0) * 100)
        agents[i]["pct"] = f"{agents[i]['progress']}%"
        self.agents = agents
        self.event_log = (self.event_log + [event["type"]])[-4:]

    @rx.var
    def agents_done(self) -> bool:
        return all(a["status"] == "completed" for a in self.agents)

    @rx.var
    def agents_completed_count(self) -> int:
        return sum(1 for a in self.agents if a["status"] == "completed")

    @rx.var
    def overall_pct(self) -> str:
        total = sum(int(a["progress"]) for a in self.agents) / len(self.agents)
        return f"{round(total)}%"

    # ── results ────────────────────────────────────────────────────────────
    @rx.event
    def select_uni(self, uni_id: str):
        self.selected_uni = uni_id

    @rx.event
    def download_report(self):
        service = get_report_service()
        pdf = service.render_pdf(service.get_report(dict(self.profile)))
        return rx.download(data=pdf, filename="Meridian-Study-Abroad-Report.pdf")
