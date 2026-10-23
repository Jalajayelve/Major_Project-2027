"""Meridian state: authenticated persistence and real request-level analysis."""
from __future__ import annotations
import asyncio
import io
import json
import os
import logging
import time
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
import reflex as rx
from .data import mock
from .data.profile import FORM_SCHEMA, US_STATES, empty_profile
from .services import storage, api, validation, documents
from .services.agent7 import Agent7Service, Agent7Unavailable, NOTICE as AGENT7_NOTICE

logger = logging.getLogger(__name__)


def agent7_report_text(results):
    result = results.get('extracurricular')
    if not result:
        return 'Agent 7: Not scored. Complete the eight structured Experience fields and run analysis. Unknown values should remain blank; zero means known absence.'
    return (f"Agent 7 extracurricular strength: {result['profile_strength_score']} / 100; "
            f"tier: {result['strength_tier']}; P(Strong): {result['P(Strong)']}; "
            f"achievement archetype: Cluster {result['achievement_archetype']}; "
            f"research evidence reported: {'Yes' if result['has_research_evidence'] else 'No'}. "
            + AGENT7_NOTICE)


def initial_agents():
    return [{**a, 'status': 'waiting' if a['id'] in ('profile', 'university', 'program', 'extracurricular') else 'unavailable', 'pct': '', 'progress': 0} for a in mock.AGENTS]


class State(rx.State):
    session: str = rx.Cookie('', name='meridian_session', max_age=86400, same_site='strict', secure=os.getenv('MERIDIAN_SECURE_COOKIE') == '1')
    authenticated: bool = False
    opening: bool = False
    profile: dict[str, str] = empty_profile()
    profile_tab: int = 0
    docs: dict[str, str] = {}
    uploaded_slots: list[str] = []
    agents: list[dict[str, Any]] = initial_agents()
    event_log: list[str] = []
    agents_running: bool = False
    analysis_error: str = ''
    results: dict[str, Any] = {}
    recommendations: list[dict[str, str]] = []
    selected_uni: str = ''
    message: str = ''
    field_errors: dict[str, str] = {}
    auth_busy: bool = False
    show_password: bool = False
    region_query: str = ''
    saving: bool = False
    _saved_profile: dict[str, str] = {}
    _loaded_session: str = ''
    upload_states: dict[str, str] = {}
    upload_errors: dict[str, str] = {}

    def _error(self, exc):
        if isinstance(exc, (ValueError, Agent7Unavailable)):
            return str(exc)
        logger.exception('Meridian operation failed')
        return 'The operation could not be completed. Please retry; your saved information is retained.'

    @rx.event
    def toggle_password(self):
        self.show_password = not self.show_password

    @rx.event
    async def login(self, form: dict):
        async for event in self._authenticate(form, False):
            yield event

    @rx.event
    async def register(self, form: dict):
        async for event in self._authenticate(form, True):
            yield event

    async def _authenticate(self, form, register):
        self.auth_busy = True
        self.message = ''
        yield
        try:
            token = await asyncio.to_thread(storage.authenticate, form.get('email', ''), form.get('password', ''), register, form.get('name', ''))
            if self.session:
                storage.logout(self.session)
            self.session = token
            self._load()
            yield rx.redirect('/dashboard')
        except Exception as exc:
            self.message = self._error(exc)
        finally:
            self.auth_busy = False

    def _load(self):
        account = storage.user(self.session)
        self.profile = {**empty_profile(), **json.loads(account['profile'])}
        if self.profile.get('regions', '').strip().casefold() in {state.casefold() for state in US_STATES if ',' in state}:
            self.profile['regions'] = self.profile['regions'].strip() + ';'
        self._saved_profile = dict(self.profile)
        self._loaded_session = self.session
        self.field_errors = {}
        self.docs = json.loads(account['documents'])
        self.uploaded_slots = [s['slot'] for s in mock.DOC_SLOTS if self.docs.get(s['slot']+'_name')]
        self.results = json.loads(account['results'])
        errors = self.results.get('_errors', [])
        self.agents = initial_agents()
        for row in self.agents:
            if row['id'] in self.results:
                row['status'] = 'completed'
            elif any(error.startswith(row['id'] + ':') for error in errors):
                row['status'] = 'failed'
        self.event_log = [f"{row['id']}: completed" for row in self.agents if row['status'] == 'completed'] + errors
        self._recommendations()
        self.authenticated = True

    @rx.event
    def require_auth(self):
        try:
            draft = dict(self.profile)
            dirty = self.profile_dirty and self.session == self._loaded_session
            self._load()
            if dirty:
                self.profile = draft
                self.field_errors = validation.profile_errors(draft)
                self.message = 'You have unsaved profile changes. Save or cancel them in Edit profile.'
        except ValueError:
            self._clear()
            return rx.redirect('/login')
        except Exception as exc:
            self.authenticated = False
            self.message = self._error(exc)

    def _clear(self):
        self.session = ''
        self.authenticated = False
        self.profile = empty_profile()
        self.docs = {}
        self.uploaded_slots = []
        self.results = {}
        self.recommendations = []
        self.agents = initial_agents()
        self.agents_running = False
        self.analysis_error = ''
        self.event_log = []
        self.message = ''
        self.field_errors = {}
        self._saved_profile = {}
        self._loaded_session = ''
        self.upload_states = {}
        self.upload_errors = {}
        self.region_query = ''
        self.show_password = False

    @rx.event
    def logout(self):
        try:
            storage.logout(self.session)
        except Exception as exc:
            self.message = self._error(exc)
            return
        self._clear()
        return rx.redirect('/')

    @rx.event
    async def start_journey(self):
        if self.opening:
            return
        self.opening = True
        yield
        await asyncio.sleep(1.55)
        self.opening = False
        yield rx.redirect('/dashboard' if self.authenticated else '/login')

    @rx.event
    def set_field(self, key: str, value: str):
        if key not in validation.FIELDS:
            return
        self.profile[key] = '' if value is None else str(value)
        self.field_errors = validation.profile_errors(self.profile)

    @rx.event
    def set_region_query(self, value: str):
        self.region_query = value

    @rx.var
    def regions(self) -> list[str]:
        raw = self.profile.get('regions', '')
        normalized = raw.strip().rstrip(';').strip()
        if normalized.casefold() in {state.casefold() for state in US_STATES}:
            return [normalized]
        separator = ';' if ';' in raw else ','
        return [v.strip() for v in raw.split(separator) if v.strip()]

    @rx.event
    def add_region(self):
        value = ' '.join(self.region_query.strip().split())
        if value and value.casefold() not in [r.casefold() for r in self.regions]:
            regions = self.regions + [value]
            self.profile['regions'] = '; '.join(regions)
            if len(regions) == 1 and ',' in value:
                self.profile['regions'] += ';'
        self.region_query = ''

    @rx.event
    def remove_region(self, value: str):
        self.profile['regions'] = '; '.join(r for r in self.regions if r != value)

    @rx.event
    def clear_regions(self):
        self.profile['regions'] = ''
        self.region_query = ''

    @rx.var
    def profile_dirty(self) -> bool:
        return bool(self._saved_profile) and self.profile != self._saved_profile

    def _save_profile(self):
        storage.user(self.session)
        self.field_errors = validation.profile_errors(self.profile)
        if self.field_errors:
            raise ValueError('Please correct the highlighted fields before saving.')
        storage.save_profile(self.session, self.profile, self._saved_profile)
        if self._saved_profile != self.profile:
            self.results = {}
            self.recommendations = []
            self.event_log = []
        self._saved_profile = dict(self.profile)
        self.message = 'Profile saved.'

    @rx.event
    async def save_profile(self):
        self.saving = True
        yield
        try:
            self._save_profile()
        except Exception as exc:
            self.message = self._error(exc)
        finally:
            self.saving = False

    @rx.event
    def cancel_profile(self):
        try:
            self._load()
            self.field_errors = {}
            self.message = 'Unsaved changes discarded.'
            return rx.redirect('/dashboard')
        except ValueError:
            self._clear()
            return rx.redirect('/login')
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def set_tab(self, index: int):
        self.profile_tab = max(0, min(index, len(FORM_SCHEMA)-1))

    @rx.event
    def next_tab(self):
        try:
            self._save_profile()
            if self.profile_tab == len(FORM_SCHEMA)-1:
                return rx.redirect('/documents')
            self.profile_tab += 1
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def prev_tab(self):
        self.profile_tab = max(0, self.profile_tab-1)

    @rx.var
    def profile_completion(self) -> int:
        keys = ['full_name', 'email', 'degree_goal', 'field', 'gpa', 'gpa_scale', 'regions']
        return round(100*sum(bool(self.profile.get(k, '').strip()) for k in keys)/len(keys))

    @rx.var
    def completion_str(self) -> str:
        return f'{self.profile_completion}%'

    @rx.var
    def student_name(self) -> str:
        return self.profile.get('full_name') or 'Your dossier'

    @rx.var
    def target_program(self) -> str:
        return ' '.join(filter(None, [self.profile.get('degree_goal'), self.profile.get('field')])) or 'Choose your study goals'

    async def _save(self, slot, files):
        token = self.session
        self.upload_states[slot] = 'Uploading'
        self.upload_errors.pop(slot, None)
        yield
        try:
            storage.user(token)
            if len(files) != 1:
                raise ValueError('Choose one file per document slot.')
            data = await files[0].read(documents.MAX_BYTES + 1)
            self.upload_states[slot] = 'Processing'
            yield
            docs = await asyncio.to_thread(documents.store, token, slot, files[0].filename or 'document', data)
            if token == self.session:
                self.docs = docs
                self.uploaded_slots = [s for s in documents.SLOTS if docs.get(s+'_name')]
                self.upload_states[slot] = 'Stored'
                self.message = 'File stored privately and processed for a text preview.'
        except Exception as exc:
            if token == self.session:
                self.upload_states[slot] = 'Failed'
                self.upload_errors[slot] = self._error(exc)
        finally:
            for file in files:
                await file.close()

    @rx.event
    async def upload_resume(self, files: list[rx.UploadFile]):
        async for event in self._save('resume', files):
            yield event

    @rx.event
    async def upload_transcript(self, files: list[rx.UploadFile]):
        async for event in self._save('transcript', files):
            yield event

    @rx.event
    async def upload_sop(self, files: list[rx.UploadFile]):
        async for event in self._save('sop', files):
            yield event

    @rx.event
    async def upload_lor(self, files: list[rx.UploadFile]):
        async for event in self._save('lor', files):
            yield event

    @rx.event
    async def upload_other(self, files: list[rx.UploadFile]):
        async for event in self._save('other', files):
            yield event

    @rx.event
    def remove_document(self, slot: str):
        try:
            self.docs = documents.remove(self.session, slot)
            self.uploaded_slots = [s for s in self.uploaded_slots if s != slot]
            self.upload_states.pop(slot, None)
            self.message = 'Document removed.'
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def download_document(self, slot: str):
        try:
            name, data = documents.download(self.session, slot)
            return rx.download(data=data, filename=name)
        except Exception as exc:
            self.message = self._error(exc)

    @rx.var
    def docs_count(self) -> int:
        return len(self.uploaded_slots)

    def _recommendations(self):
        self.recommendations = [{k: str(v) for k, v in row.items()} for row in self.results.get('university', {}).get('matched_universities', [])]

    @rx.var
    def program_results(self) -> list[dict[str, Any]]:
        result = self.results.get('program', {})
        return result.get('programs', []) if isinstance(result, dict) else []

    @rx.event(background=True)
    async def run_agents(self):
        async with self:
            if self.agents_running:
                return
            try:
                if self.profile_dirty:
                    self.message = 'Save or cancel your profile changes before running analysis.'
                    return
                self._load()
            except ValueError:
                self._clear()
                yield rx.redirect('/login')
                return
            self.agents_running = True
            self.analysis_error = ''
            self.agents = initial_agents()
            self.results = {}
            self.recommendations = []
            self.event_log = []
            profile = dict(self.profile)
            token = self.session
        try:
            for agent in ('profile', 'extracurricular', 'university', 'program'):
                index = next(i for i, row in enumerate(self.agents) if row['id'] == agent)
                started_at = time.time()
                storage.record_analysis_event(token, agent, 'running', started_at)
                async with self:
                    if token != self.session:
                        return
                    self.agents[index]['status'] = 'processing'
                try:
                    if agent == 'profile':
                        payload = api.agent1_payload(profile)
                        result = await asyncio.wait_for(api.request('/agent1/profile', payload), timeout=50)
                        if 'prediction' not in result:
                            raise ValueError('Agent 1 returned an invalid response.')
                    elif agent == 'extracurricular':
                        result = await asyncio.to_thread(Agent7Service().score_profile, profile)
                    elif agent == 'university':
                        if not profile.get('match_country') or not profile.get('match_tier'):
                            raise ValueError('Choose matching country and catalog tier in Study goals.')
                        result = await asyncio.wait_for(api.request('/match', {'gpa': api.gpa(profile), 'country': profile['match_country'], 'tier': profile['match_tier']}), timeout=50)
                        if not isinstance(result.get('matched_universities'), list):
                            raise ValueError('Matching API returned an invalid response.')
                    else:
                        university_result = self.results.get('university', {})
                        matches = university_result.get('matched_universities', []) if isinstance(university_result, dict) else []
                        if not matches:
                            raise ValueError('Agent 3 requires a successful university shortlist.')
                        result = await asyncio.wait_for(
                            api.request('/agent3/program', {
                                'profile': {
                                    'degree_goal': profile.get('degree_goal', ''),
                                    'field': profile.get('field', ''),
                                    'programs': profile.get('programs', ''),
                                },
                                'matched_universities': matches,
                            }),
                            timeout=50,
                        )
                        if not isinstance(result.get('programs'), list):
                            raise ValueError('Program API returned an invalid response.')
                    async with self:
                        account = storage.user(token)
                        if token != self.session:
                            return
                        if {**empty_profile(), **json.loads(account['profile'])} != profile:
                            self.results = {}
                            self.recommendations = []
                            self.event_log.append('Profile changed. Run analysis again for the saved profile.')
                            self.agents[index]['status'] = 'cancelled'
                            return
                        self.results[agent] = result
                        self.agents[index]['status'] = 'completed'
                        self.event_log.append(f'{agent}: completed')
                        storage.record_analysis_event(token, agent, 'completed', started_at, time.time(), result=result)
                except Exception as exc:
                    async with self:
                        if token != self.session:
                            return
                        self.agents[index]['status'] = 'failed'
                        detail = self._error(exc) if not isinstance(exc, asyncio.TimeoutError) else "Request timed out; retry."
                        self.analysis_error = detail
                        self.event_log.append(f'{agent}: {detail}')
                        storage.record_analysis_event(token, agent, 'failed', started_at, time.time(), error=detail)
            async with self:
                if token == self.session:
                    self._recommendations()
                    self.results['_errors'] = [e for e in self.event_log if not e.endswith(': completed')]
                    storage.save_results(token, profile, self.results)
        except Exception as exc:
            async with self:
                if token == self.session:
                    self.results = {}
                    self.recommendations = []
                    self.message = self._error(exc)
                    self.analysis_error = self.message
                    self.event_log.append(self.message)
        finally:
            async with self:
                self.agents_running = False

    @rx.var
    def agent7_summary(self) -> str:
        return agent7_report_text(self.results)

    @rx.var
    def agent7_available(self) -> bool:
        return isinstance(self.results.get("extracurricular"), dict)

    @rx.var
    def agent7_score(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("profile_strength_score", "Not scored")) if isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_tier(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("strength_tier", "Not scored")) if isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_probability(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("P(Strong)", "Not scored")) if isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_archetype(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("achievement_archetype", "Not scored")) if isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_research_evidence(self) -> str:
        result = self.results.get("extracurricular", {})
        return "Yes" if isinstance(result, dict) and result.get("has_research_evidence") else "No"

    @rx.var
    def agents_done(self) -> bool:
        return not self.agents_running and bool(self.event_log)

    @rx.var
    def agents_completed_count(self) -> int:
        return sum(a['status'] == 'completed' for a in self.agents)

    @rx.var
    def overall_pct(self) -> str:
        if self.agents_running:
            return 'Running'
        return 'Complete' if self.event_log else 'Pending'

    @rx.var
    def profile_analysis_available(self) -> bool:
        return isinstance(self.results.get("profile"), dict) and bool(self.results.get("profile", {}).get("prediction"))

    @rx.var
    def profile_analysis_summary(self) -> str:
        result = self.results.get("profile", {})
        if not isinstance(result, dict):
            return "No Agent 1 result available."
        probability = result.get("probability")
        confidence = f" · Tier 1 probability {probability:.1%}" if isinstance(probability, (float, int)) else ""
        return f"{result.get('prediction', 'No result')}{confidence}"

    @rx.var
    def matching_ready(self) -> bool:
        return bool(self.profile.get('match_country')) and bool(self.profile.get('match_tier'))

    @rx.var
    def prediction_unavailable(self) -> bool:
        return bool(self.agents) and self.agents[0]['status'] == 'failed' and 'profile' not in self.results

    @rx.var
    def prediction_text(self) -> str:
        result = self.results.get('profile', {})
        return str(result.get('prediction', 'No profile prediction available. The backend requires its original MS/MBA model exports.'))

    @rx.var
    def prediction_confidence(self) -> str:
        probability = self.results.get('profile', {}).get('probability')
        return f'Model class confidence: {probability:.1%} (not admission probability)' if isinstance(probability, (float, int)) else ''

    @rx.var
    def result_json(self) -> str:
        return json.dumps(self.results, indent=2, ensure_ascii=False) if self.results else 'No saved analysis yet.'

    @rx.event
    def select_uni(self, uni_id: str):
        self.selected_uni = uni_id

    @rx.event
    def download_report(self):
        try:
            account = storage.user(self.session)
        except Exception as exc:
            self.message = self._error(exc)
            return
        profile = json.loads(account['profile'])
        results = json.loads(account['results'])
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        lines = [profile.get('full_name', 'Your dossier'), ' '.join(filter(None, [profile.get('degree_goal'), profile.get('field')])),
                 'Rule-based catalog matches; no admission probabilities are supplied.',
                 str(results.get('profile', {}).get('prediction', 'No profile prediction available.'))]
        lines += [f"{r['name']} | {r['country']} | catalog tier: {r['tier']}" for r in results.get('university', {}).get('matched_universities', [])]
        lines += [
            f"{p.get('university')} | {p.get('program_name')} | fit {float(p.get('match_score', 0)):.3f} | {p.get('duration', 'Not specified')}"
            for p in results.get('program', {}).get('programs', [])
        ]
        lines += [agent7_report_text(results)]
        lines += results.get('_errors', [])
        story = []
        for line in lines:
            story.extend([Paragraph(escape(line), styles['BodyText']), Spacer(1, 12)])
        SimpleDocTemplate(buffer).build(story)
        return rx.download(data=buffer.getvalue(), filename='Meridian-Dossier.pdf')
