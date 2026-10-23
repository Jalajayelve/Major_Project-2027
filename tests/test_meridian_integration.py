import asyncio
import json
import sqlite3
import pytest
import httpx
from meridian.services import storage, api


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv('MERIDIAN_DATA_DIR', str(tmp_path))
    return tmp_path


def test_registration_persistence_isolation_logout(isolated_store):
    first = storage.authenticate('student@example.com', 'long secure test password', True, 'Student')
    second = storage.authenticate('other@example.com', 'another secure test password', True, 'Other')
    storage.save(first, 'profile', {'full_name': 'Updated', 'regions': 'Canada'})
    assert json.loads(storage.user(first)['profile'])['regions'] == 'Canada'
    assert 'regions' not in json.loads(storage.user(second)['profile'])
    again = storage.authenticate('student@example.com', 'long secure test password')
    assert json.loads(storage.user(again)['profile'])['full_name'] == 'Updated'
    with storage.connect() as db:
        row = db.execute('SELECT password FROM users LIMIT 1').fetchone()
        assert row['password'].startswith('$argon2id$')
        assert db.execute('SELECT token FROM sessions WHERE token=?', (first,)).fetchone() is None
    storage.logout(first)
    with pytest.raises(ValueError):
        storage.user(first)
    assert storage.user(second)


def test_validation_and_rate_limit(isolated_store):
    with pytest.raises(ValueError):
        storage.authenticate('invalid', '123', True, 'Name')
    token = storage.authenticate('student@example.com', 'long secure test password', True, 'Student')
    for _ in range(8):
        with pytest.raises(ValueError, match='Invalid email or password'):
            storage.authenticate('student@example.com', 'wrong')
    with pytest.raises(ValueError, match='Too many'):
        storage.authenticate('student@example.com', 'long secure test password')
    with storage.connect() as db:
        db.execute('UPDATE sessions SET expires=0')
    with pytest.raises(ValueError, match='expired'):
        storage.user(token)


def test_explicit_gpa_mapping_and_missing_inputs():
    assert api.gpa({'gpa':'8.4', 'gpa_scale':'10'}) == pytest.approx(3.36)
    assert api.gpa({'gpa':'80', 'gpa_scale':'100'}) == 3.2
    with pytest.raises(ValueError):
        api.gpa({'gpa':'nan','gpa_scale':'4'})
    with pytest.raises(ValueError):
        api.prediction_payload({'gpa':'3.5','gpa_scale':'4','degree_goal':'MBA','work_years':'2'})


def test_http_timeout_is_retryable(monkeypatch):
    async def timeout(*args, **kwargs):
        raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(httpx.AsyncClient, 'post', timeout)
    with pytest.raises(ValueError, match='timed out'):
        asyncio.run(api.request('/match', {}))


def test_empty_profile_no_demo_identity():
    from meridian.data.profile import empty_profile
    assert all(value == '' for value in empty_profile().values())


class BackgroundHarness:
    def __init__(self, state):
        object.__setattr__(self, 'state', state)

    def __getattr__(self, key):
        return getattr(self.state, key)

    def __setattr__(self, key, value):
        setattr(self.state, key, value)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def test_analysis_failure_finishes_and_matching_survives(isolated_store, monkeypatch):
    from meridian.state import State
    token = storage.authenticate('test@example.com', 'long test password', True, 'Test')
    profile = {'gpa':'3.4', 'gpa_scale':'4', 'degree_goal':'MS', 'work_years':'1',
               'gre_verbal':'150','gre_quant':'160','toefl':'100','research_experience':'0',
               'match_country':'USA','match_tier':'medium'}
    storage.save(token, 'profile', profile)
    state = State(_reflex_internal_init=True)
    state.session = token
    calls = []
    async def response(path, payload):
        calls.append((path, payload))
        if path.startswith('/predict'):
            raise ValueError('Model unavailable')
        return {'matched_universities':[{'name':'Test catalog row','country':'USA','tier':'medium','gpa':3.4}]}
    monkeypatch.setattr(api, 'request', response)
    async def run():
        return [event async for event in State.run_agents.fn(BackgroundHarness(state))]
    asyncio.run(run())
    assert not state.agents_running
    assert state.agents[0]['status'] == 'failed'
    assert state.agents[1]['status'] == 'completed'
    assert all(a['status']=='unavailable' for a in state.agents[2:])
    assert state.recommendations[0]['name'] == 'Test catalog row'
    assert calls[0][1]['gre_score'] == 310
    assert json.loads(storage.user(token)['results'])['university']
    state.set_field('gpa', '3.8')
    async def save():
        return [event async for event in state.save_profile()]
    asyncio.run(save())
    assert not state.results
    assert not json.loads(storage.user(token)['results'])


def test_analysis_page_renders_partial_matching_results():
    from meridian.pages.analysis import analysis_page

    rendered = str(analysis_page())
    assert 'University matching results' in rendered
    assert 'These are the universities returned by the backend catalog matcher.' in rendered
    assert 'Profile prediction unavailable' in rendered
    assert 'Run / retry analysis' in rendered
    assert 'Unavailable' in rendered
    assert 'No verified backend service is configured' in rendered


def test_matching_fields_are_explained_as_required_for_matching():
    from meridian.pages.profile import _field
    from meridian.data.profile import FORM_SCHEMA

    fields = {field['key']: field for section in FORM_SCHEMA for field in section['fields']}
    assert fields['match_country']['kind'] == 'select'
    assert fields['match_tier']['kind'] == 'select'
    assert 'Required for university matching' in str(_field(fields['match_country']))
    assert 'Required for university matching' in str(_field(fields['match_tier']))


def test_protected_event_without_session():
    from meridian.state import State
    state = State(_reflex_internal_init=True)
    assert state.require_auth() is not None
    assert not state.authenticated
    assert state.download_report() is None
    assert 'sign in' in state.message
