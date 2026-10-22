"""Meridian state: authenticated persistence and real request-level analysis."""
from __future__ import annotations
import asyncio
import io
import json
import os
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape
import reflex as rx
from .data import mock
from .data.profile import FORM_SCHEMA, empty_profile
from .services import storage, api


def initial_agents():
    return [{**a, 'status': 'waiting' if a['id'] in ('profile', 'university') else 'unavailable', 'pct': '', 'progress': 0} for a in mock.AGENTS]


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
    results: dict[str, Any] = {}
    recommendations: list[dict[str, str]] = []
    selected_uni: str = ''
    message: str = ''
    field_errors: dict[str, str] = {}
    auth_busy: bool = False
    show_password: bool = False
    region_query: str = ''

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
        except ValueError as exc:
            self.message = str(exc)
        finally:
            self.auth_busy = False

    def _load(self):
        account = storage.user(self.session)
        self.profile = {**empty_profile(), **json.loads(account['profile'])}
        self.docs = json.loads(account['documents'])
        self.uploaded_slots = [s['slot'] for s in mock.DOC_SLOTS if self.docs.get(s['slot']+'_name')]
        self.results = json.loads(account['results'])
        self._recommendations()
        self.authenticated = True

    @rx.event
    def require_auth(self):
        try:
            self._load()
        except ValueError:
            self._clear()
            return rx.redirect('/login')

    def _clear(self):
        self.session = ''
        self.authenticated = False
        self.profile = empty_profile()
        self.docs = {}
        self.uploaded_slots = []
        self.results = {}
        self.recommendations = []
        self.agents = initial_agents()
        self.event_log = []
        self.message = ''
        self.field_errors = {}

    @rx.event
    def logout(self):
        storage.logout(self.session)
        self._clear()
        return rx.redirect('/')

    @rx.event
    async def start_journey(self):
        self.opening = True
        yield
        await asyncio.sleep(1.55)
        yield rx.redirect('/dashboard' if self.authenticated else '/login')
        await asyncio.sleep(.4)
        self.opening = False

    @rx.event
    def set_field(self, key: str, value: str):
        self.profile[key] = value
        self.field_errors.pop(key, None)
        if key == 'email' and value and not storage.valid_email(value):
            self.field_errors[key] = 'Enter a valid email address.'
        if key in ('gpa', 'gpa_scale', 'budget', 'work_years', 'internships', 'commute_minutes') and value:
            try:
                api.number(self.profile, key, 0, 100000000)
            except ValueError as exc:
                self.field_errors[key] = str(exc)

    @rx.event
    def set_region_query(self, value: str):
        self.region_query = value

    @rx.var
    def regions(self) -> list[str]:
        return [v.strip() for v in self.profile.get('regions', '').split(',') if v.strip()]

    @rx.event
    def add_region(self):
        value = self.region_query.strip().replace(',', '')[:80]
        if value and value not in self.regions:
            self.profile['regions'] = ', '.join(self.regions + [value])
        self.region_query = ''

    @rx.event
    def remove_region(self, value: str):
        self.profile['regions'] = ', '.join(r for r in self.regions if r != value)

    def _save_profile(self):
        account = storage.user(self.session)
        if self.field_errors:
            raise ValueError('Please correct the highlighted fields before saving.')
        storage.save(self.session, 'profile', self.profile)
        if json.loads(account['profile']) != self.profile:
            storage.save(self.session, 'results', {})
            self.results = {}
            self.recommendations = []
        self.message = 'Profile saved.'

    @rx.event
    def save_profile(self):
        try:
            self._save_profile()
        except ValueError as exc:
            self.message = str(exc)

    @rx.event
    def cancel_profile(self):
        try:
            self._load()
            self.field_errors = {}
            self.message = 'Unsaved changes discarded.'
            return rx.redirect('/dashboard')
        except ValueError:
            return rx.redirect('/login')

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
        except ValueError as exc:
            self.message = str(exc)

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
        # No document ingestion API exists: do not retain sensitive files or imply processing.
        self.message = 'Document processing is unavailable: no upload or extraction API is connected. Your file was not stored.'

    @rx.event
    async def upload_resume(self, files: list[rx.UploadFile]):
        await self._save('resume', files)

    @rx.event
    async def upload_transcript(self, files: list[rx.UploadFile]):
        await self._save('transcript', files)

    @rx.event
    async def upload_sop(self, files: list[rx.UploadFile]):
        await self._save('sop', files)

    @rx.event
    async def upload_lor(self, files: list[rx.UploadFile]):
        await self._save('lor', files)

    @rx.event
    async def upload_other(self, files: list[rx.UploadFile]):
        await self._save('other', files)

    @rx.event
    def remove_document(self, slot: str):
        storage.user(self.session)
        self.docs = {k: v for k, v in self.docs.items() if not k.startswith(slot+'_')}
        self.uploaded_slots = [s for s in self.uploaded_slots if s != slot]
        storage.save(self.session, 'documents', self.docs)

    @rx.var
    def docs_count(self) -> int:
        return len(self.uploaded_slots)

    def _recommendations(self):
        self.recommendations = [{k: str(v) for k, v in row.items()} for row in self.results.get('university', {}).get('matched_universities', [])]

    @rx.event(background=True)
    async def run_agents(self):
        async with self:
            if self.agents_running:
                return
            try:
                self._load()
            except ValueError:
                yield rx.redirect('/login')
                return
            self.agents_running = True
            self.agents = initial_agents()
            self.results = {}
            self.recommendations = []
            self.event_log = []
            profile = dict(self.profile)
            token = self.session
        try:
            for index, agent in enumerate(('profile', 'university')):
                async with self:
                    if token != self.session:
                        return
                    self.agents[index]['status'] = 'processing'
                try:
                    if agent == 'profile':
                        payload = api.prediction_payload(profile)
                        result = await asyncio.wait_for(api.request('/predict/'+profile['degree_goal'].lower(), payload), timeout=50)
                        if 'prediction' not in result:
                            raise ValueError('Prediction API returned an invalid response.')
                    else:
                        if not profile.get('match_country') or not profile.get('match_tier'):
                            raise ValueError('Choose matching country and catalog tier in Study goals.')
                        result = await asyncio.wait_for(api.request('/match', {'gpa': api.gpa(profile), 'country': profile['match_country'], 'tier': profile['match_tier']}), timeout=50)
                        if not isinstance(result.get('matched_universities'), list):
                            raise ValueError('Matching API returned an invalid response.')
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
                except Exception as exc:
                    async with self:
                        if token != self.session:
                            return
                        self.agents[index]['status'] = 'failed'
                        self.event_log.append(f'{agent}: {str(exc) or "Request timed out; retry."}')
            async with self:
                if token == self.session:
                    self._recommendations()
                    storage.save(token, 'results', self.results)
        finally:
            async with self:
                self.agents_running = False

    @rx.var
    def agents_done(self) -> bool:
        return not self.agents_running and bool(self.event_log)

    @rx.var
    def agents_completed_count(self) -> int:
        return sum(a['status'] == 'completed' for a in self.agents)

    @rx.var
    def overall_pct(self) -> str:
        return 'Request running' if self.agents_running else 'Ready'

    @rx.var
    def prediction_text(self) -> str:
        result = self.results.get('profile', {})
        return str(result.get('prediction', 'No profile prediction available. The backend requires its original MS/MBA model exports.'))

    @rx.var
    def result_json(self) -> str:
        return json.dumps(self.results, indent=2, ensure_ascii=False) if self.results else 'No saved analysis yet.'

    @rx.event
    def select_uni(self, uni_id: str):
        self.selected_uni = uni_id

    @rx.event
    def download_report(self):
        storage.user(self.session)
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        lines = [self.student_name, self.target_program, 'Rule-based catalog matches; no admission probabilities are supplied.', self.prediction_text]
        lines += [f"{r['name']} | {r['country']} | catalog tier: {r['tier']}" for r in self.recommendations]
        story = []
        for line in lines:
            story.extend([Paragraph(escape(line), styles['BodyText']), Spacer(1, 12)])
        SimpleDocTemplate(buffer).build(story)
        return rx.download(data=buffer.getvalue(), filename='Meridian-Dossier.pdf')
