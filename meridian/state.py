"""App state. Talks only to `data` and `services`, never to UI code."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import reflex as rx

from .data import mock
from .services import get_event_source, get_report_service
from .services.agent7 import Agent7Service, Agent7Unavailable, candidate_from_profile, NOTICE
from .services.agent2 import Agent2Service, Agent2Unavailable, NOTICE as AGENT2_NOTICE, validate_result as validate_agent2_result

_SECTION_COUNT = len(mock.FORM_SCHEMA)


class State(rx.State):
    # journey transition
    opening: bool = False

    # profile
    profile: dict[str, str] = dict(mock.STUDENT_PROFILE)
    profile_tab: int = 0
    profile_submission_attempted: bool = False
    agent7_result: dict[str, Any] = {}
    agent7_inputs: dict[str, Any] = {}
    agent7_error: str = ""
    agent7_busy: bool = False
    agent2_result: dict[str, Any] = {}
    agent2_error: str = ""
    agent2_profile: dict[str, str] = {}

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
        if self.profile.get(key) == value:
            return
        self.profile[key] = value
        self.agent7_result = {}
        self.agent7_inputs = {}
        self.agent7_error = ""
        self.agent2_result = {}
        self.agent2_error = ""
        self.agent2_profile = {}
        self.agents = [dict(a) for a in mock.AGENTS]

    @rx.event
    def set_tab(self, index: int):
        self.profile_tab = max(0, min(index, _SECTION_COUNT - 1))

    @rx.event
    async def next_tab(self):
        if self.profile_tab >= _SECTION_COUNT - 1 or self.profile_submission_attempted:
            if self.agent7_busy:
                return
            self.agent7_busy = True
            self.profile_submission_attempted = True
            self.agent7_error = ""
            self.agent7_result = {}
            self.agent2_result = {}
            self.agent2_profile = {}
            self.agent2_error = ""
            yield
            try:
                profile = dict(self.profile)
                candidate = candidate_from_profile(profile)
                result = await asyncio.to_thread(Agent7Service().score_profile, profile)
                if dict(self.profile) != profile:
                    raise ValueError("Profile changed during scoring. Submit your updated profile again.")
                self.agent7_result = result
                self.agent7_inputs = candidate
                yield rx.redirect("/documents")
            except (ValueError, Agent7Unavailable) as exc:
                self.agent7_error = str(exc)
                logging.getLogger(__name__).warning("Agent 7 submission failed", exc_info=True)
            finally:
                self.agent7_busy = False
        else:
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
            self.agent7_error = ""
            result = dict(self.agent7_result)
            saved_inputs = dict(self.agent7_inputs)
            university_result = dict(self.agent2_result) if self.agent2_ready and self.agent2_profile == profile else {}
            self.agent2_error = ""
            self.agent2_result = {}
            self.agent2_profile = {}
        try:
            candidate = candidate_from_profile(profile)
            if not result or candidate != saved_inputs:
                result = await asyncio.to_thread(Agent7Service().score_profile, profile)
            university_error = ""
            async with self:
                self._apply_event({"type": "university_processing", "agent": "university", "progress": 0})
            try:
                if not university_result:
                    university_result = await asyncio.to_thread(Agent2Service().match_profile, profile, result)
            except (ValueError, Agent2Unavailable) as exc:
                university_error = str(exc)
                logging.getLogger(__name__).warning("Agent 2 analysis unavailable: %s", exc)
            # Only Agents 1, 3, 4, 5 and 6 retain demonstration events.
            async for event in get_event_source().stream(profile):
                if event["agent"] in ("extracurricular", "university"):
                    continue
                async with self:
                    self._apply_event(event)
            async with self:
                if dict(self.profile) != profile:
                    raise ValueError("Profile changed during analysis. Return to the profile and submit again.")
                self.agent7_result = result
                self.agent7_inputs = candidate
                self._apply_event({"type": "extracurricular_completed", "agent": "extracurricular", "payload": result})
                self.agent2_error = university_error
                if university_error:
                    self._apply_event({"type": "university_unavailable", "agent": "university"})
                else:
                    self.agent2_result = university_result
                    self.agent2_profile = profile
                    self._apply_event({"type": "university_completed", "agent": "university", "payload": university_result})
        except (ValueError, Agent7Unavailable) as exc:
            async with self:
                self.agent7_error = str(exc)
                self.agent7_result = {}
                self.agent7_inputs = {}
                self.agent2_result = {}
                self.agent2_profile = {}
                self.agent2_error = "Agent 2 waits for a valid Agent 7 result and an unchanged profile."
                self.event_log = ["Agent 7 unavailable — no result generated"]
            logging.getLogger(__name__).warning("Agent 7 analysis failed", exc_info=True)
        finally:
            async with self:
                self.agents_running = False

    def _apply_event(self, event: dict[str, Any]):
        agents = [dict(a) for a in self.agents]
        i = mock.AGENT_IDS.index(event["agent"])
        if event["type"].endswith("_unavailable"):
            agents[i]["status"], agents[i]["progress"] = "unavailable", 0
        elif event["type"].endswith("_completed"):
            agents[i]["status"], agents[i]["progress"] = "completed", 100
        else:
            agents[i]["status"] = "processing"
            agents[i]["progress"] = int(event.get("progress", 0) * 100)
        agents[i]["pct"] = f"{agents[i]['progress']}%"
        self.agents = agents
        self.event_log = (self.event_log + [event["type"]])[-4:]

    @rx.var
    def agents_done(self) -> bool:
        return bool(self.agent7_result) and not self.agents_running and all(a["status"] in ("completed", "unavailable") for a in self.agents)

    @rx.var
    def agent2_ready(self) -> bool:
        try:
            validate_agent2_result(self.agent2_result)
            return True
        except (ValueError, TypeError, KeyError):
            return False

    @rx.var
    def university_matches(self) -> list[dict[str, Any]]:
        return self.agent2_result.get("universities", []) if self.agent2_ready else []

    @rx.var
    def university_factor_rows(self) -> list[dict[str, str]]:
        return [{"program": u["name"] + " / " + u["program"], "feature": f["feature"],
                 "impact": f"{f['impact']:+.4f}"}
                for u in self.university_matches for f in u["factors"]]

    @rx.var
    def university_count(self) -> str:
        return str(len({u["name"] for u in self.university_matches})) if self.agent2_ready else "Unavailable"

    @rx.var
    def university_scored_count(self) -> str:
        return str(len({u["name"] for u in self.university_matches if not u["evidence_reason"]})) if self.agent2_ready else "Unavailable"

    @rx.var
    def agent2_status(self) -> str:
        return self.agent2_error or "Agent 2 has not evaluated this profile. Run analysis to check its model bundle."

    @rx.var
    def analysis_scope(self) -> str:
        return "Agent 7 uses real model inference. Agent 2 uses its updated bundle when available. Agents 1, 3, 4, 5 and 6 still show demonstration content."

    @rx.var
    def agent7_ready(self) -> bool:
        return bool(self.agent7_result)

    @rx.var
    def agent7_score(self) -> str:
        return str(self.agent7_result["profile_strength_score"]) if self.agent7_result else "Not scored"

    @rx.var
    def agent7_count(self) -> str:
        return str(int(self.agent7_result["profile_strength_score"])) if self.agent7_result else ""

    @rx.var
    def agent7_count_suffix(self) -> str:
        return "." + f"{self.agent7_result['profile_strength_score']:.1f}".split(".")[1] if self.agent7_result else ""

    @rx.var
    def agent7_tier(self) -> str:
        return self.agent7_result.get("strength_tier", "Not scored")

    @rx.var
    def agent7_probability(self) -> str:
        return f"{self.agent7_result['P(Strong)']:.6f}" if self.agent7_result else "Not scored"

    @rx.var
    def agent7_archetype(self) -> str:
        return "Cluster " + self.agent7_result["achievement_archetype"] if self.agent7_result else "Not scored"

    @rx.var
    def agent7_research(self) -> str:
        if not self.agent7_result:
            return "Not scored"
        return "Yes — reported publication or patent" if self.agent7_result["has_research_evidence"] else "No — no reported publication or patent"

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
        report = service.get_report(dict(self.profile))
        # Copy before replacing demonstration values; never mutate shared mock data.
        report["profile_strength"] = {"score": self.agent7_score, "label": self.agent7_tier, "dimensions": []}
        report["extracurricular"] = {"items": [
            {"name": "Profile Strength", "score": self.agent7_score},
            {"name": "Strength Tier", "score": self.agent7_tier},
            {"name": "Achievement Archetype", "score": self.agent7_archetype},
            {"name": "Research Evidence", "score": self.agent7_research},
            {"name": "P(Strong)", "score": self.agent7_probability},
        ]}
        report["agent7_notice"] = NOTICE
        report["universities"] = list(self.university_matches)
        report["agent2_notice"] = AGENT2_NOTICE if self.agent2_ready else self.agent2_status
        report["key_factors"] = [{"name": f["program"] + " / " + f["feature"], "impact": f["impact"]}
                                 for f in self.university_factor_rows]
        pdf = service.render_pdf(report)
        return rx.download(data=pdf, filename="Meridian-Study-Abroad-Report.pdf")
