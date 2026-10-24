"""Real Agent 7 inference through the authenticated Meridian workflow."""
import asyncio
import io
import json
import subprocess
import pytest
from pypdf import PdfReader
from meridian.data.profile import empty_profile
from meridian.services import api, storage, validation
from meridian.services.agent7 import Agent7Service, candidate_from_profile
from meridian.services.agent2 import Agent2Service, NOTICE as AGENT2_NOTICE
from meridian.services.agent2 import candidate_from_profile as agent2_candidate
from meridian.state import State, agent7_report_text
from test_meridian_integration import BackgroundHarness

INPUTS = dict(leadership_score='6', research_score='9', competition_score='5',
              volunteering_score='4', publication_count='3', patent_count='0',
              agent7_degree_level='Masters', agent7_field='STEM')
PROFILE = {**empty_profile(), **INPUTS, 'full_name': 'Agent 7 test', 'gpa': '3.4',
           'gpa_scale': '4', 'degree_goal': 'MS', 'field': 'Computer Science',
           'match_country': 'USA', 'match_tier': 'medium'}

@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv('MERIDIAN_DATA_DIR', str(tmp_path))
    token = storage.authenticate('agent7@example.com', 'test password long enough', True, 'Test')
    storage.save(token, 'profile', PROFILE)
    value = State(_reflex_internal_init=True)
    value.session = token
    value._load()
    return value

def run(state):
    async def consume():
        return [event async for event in State.run_agents.fn(BackgroundHarness(state))]
    asyncio.run(consume())

@pytest.fixture
def other_agents(monkeypatch):
    # Contract fixtures for other services only; Agent 7 uses real models.
    calls = []
    async def response(path, payload):
        calls.append((path, payload))
        if path == '/agent1/profile':
            return {'prediction': 'Contract fixture'}
        if path == '/match':
            return {'matched_universities': [{'name': 'Fixture University', 'country': 'USA', 'tier': 'medium', 'gpa': 3.4}]}
        return {'programs': []}
    monkeypatch.setattr(api, 'request', response)
    return calls

@pytest.mark.parametrize('key,value', [('leadership_score', ''), ('research_score', 'nan'),
    ('competition_score', '-1'), ('volunteering_score', '11'), ('publication_count', '1.5'),
    ('patent_count', True), ('agent7_field', 'Computer Science'), ('agent7_degree_level', '')])
def test_invalid_inputs_never_start_worker(key, value, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid input reached subprocess')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    with pytest.raises(ValueError):
        Agent7Service().score_profile({**PROFILE, key: value})

def test_form_validation_and_no_free_text_scores():
    assert not validation.profile_errors(PROFILE)
    assert 'publication_count' in validation.profile_errors({**PROFILE, 'publication_count': '1.5'})
    assert 'profile_strength_score' not in candidate_from_profile({**PROFILE, 'profile_strength_score': 100, 'research': 'Invented'})

def test_real_worker_foreign_cwd_determinism_and_agent2_mapping(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    first = Agent7Service().score_profile(PROFILE)
    assert first == Agent7Service().score_profile(PROFILE)
    assert first['strength_tier'] in ('Weak', 'Moderate', 'Strong')
    assert 0 <= first['profile_strength_score'] <= 100
    assert 0 <= first['P(Strong)'] <= 1
    low = Agent7Service().score_profile({**PROFILE, **{k: '0' for k in INPUTS if not k.startswith('agent7_')}})
    assert low['profile_strength_score'] < first['profile_strength_score']
    assert low['has_research_evidence'] == 0
    mapped = agent2_candidate(PROFILE, first)
    assert mapped['profile_strength_score'] == first['profile_strength_score']
    assert 'tier_score' not in mapped

def test_analysis_persistence_reload_pdf_invalidation(state, other_agents, monkeypatch):
    run(state)
    result = state.results['extracurricular']
    assert state.agents[6]['status'] == 'completed'
    assert state.agents[1]['status'] == state.agents[2]['status'] == 'completed'
    assert [path for path, _ in other_agents] == ['/agent1/profile', '/match', '/agent3/program', '/agent4/financial', '/agent6/career']
    assert set(other_agents[1][1]) == {'gpa', 'country', 'tier'}
    assert json.loads(storage.user(state.session)['results'])['extracurricular'] == result
    completed = next(row for row in storage.analysis_history(state.session) if row['agent'] == 'extracurricular' and row['status'] == 'completed')
    assert json.loads(completed['result']) == result
    restored = State(_reflex_internal_init=True)
    restored.session = state.session
    restored._load()
    assert restored.agent7_summary == state.agent7_summary
    assert restored.agents[6]['status'] == 'completed'
    assert restored.agents_done
    captured = {}
    def download(**kwargs):
        captured.update(kwargs)
    monkeypatch.setattr('meridian.state.rx.download', download)
    restored.download_report()
    text = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(captured['data'])).pages)
    assert str(result['profile_strength_score']) in text
    assert 'NOT admission probability' in text
    assert result['strength_tier'] in text
    restored.set_field('research_score', '8')
    restored._save_profile()
    assert restored.results == {}
    assert json.loads(storage.user(state.session)['results']) == {}


def test_verified_agent2_receives_agent1_and_agent7_outputs(state, other_agents, monkeypatch):
    captured = {}

    def match_profile(service, profile, agent7_result, agent1_result=None):
        captured['profile'] = profile
        captured['agent7'] = agent7_result
        captured['agent1'] = agent1_result
        return {
            'universities': [{
                'id': 'fixture-1', 'name': 'Verified University', 'program': 'MS Computer Science',
                'country': 'USA', 'region': 'Northeast', 'institution_type': 'Research',
                'tier': 'Middle', 'evidence_reason': '', 'probability': .5, 'prob_str': '50.0%',
                'match_score': .8, 'match_str': '80.0%', 'tier_score': 60,
                'tuition': None, 'tuition_str': 'Not listed', 'factors': [], 'note': 'Verified',
            }],
            'notice': AGENT2_NOTICE,
            'retrieval': 'TF-IDF',
        }

    monkeypatch.setattr(Agent2Service, 'match_profile', match_profile)
    run(state)

    assert captured['agent1']['prediction'] == 'Contract fixture'
    assert captured['agent7']['profile_strength_score'] == state.results['extracurricular']['profile_strength_score']
    assert state.results['university']['source'] == 'verified_agent2_bundle'
    assert state.results['university']['matched_universities'][0]['agent2_id'] == 'fixture-1'

def test_missing_runtime_preserves_other_results_and_retry(state, other_agents, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setenv('MERIDIAN_AGENT7_PYTHON', 'missing-agent7-python.exe')
        run(state)
    assert 'extracurricular' not in state.results
    assert state.agents[6]['status'] == 'failed'
    assert state.agents[1]['status'] == state.agents[2]['status'] == 'completed'
    assert 'no substitute score' in state.analysis_error
    run(state)
    assert state.agents[6]['status'] == 'completed'

def test_concurrent_saved_profile_change_cannot_publish(state, other_agents, monkeypatch):
    original = Agent7Service.score_profile
    def changed(service, profile):
        result = original(service, profile)
        storage.save_profile(state.session, {**PROFILE, 'research_score': '7'}, PROFILE)
        return result
    monkeypatch.setattr(Agent7Service, 'score_profile', changed)
    run(state)
    assert not state.results
    assert not json.loads(storage.user(state.session)['results'])
    assert state.agents[6]['status'] == 'cancelled'

def test_results_and_printable_route_include_live_summary():
    from meridian.pages.results import results_page
    rendered = str(results_page())
    assert 'Beyond grades and scores' in rendered
    assert 'agent7_summary' in rendered
    assert 'Strength tier' in rendered
    assert 'P(Strong)' in rendered
    assert 'Achievement archetype' in rendered
    assert 'Not scored' in agent7_report_text({})


def test_incomplete_persisted_agent7_result_is_not_available(state):
    state.results = {
        "extracurricular": {"profile_strength_score": 72},
        "_errors": ["extracurricular: Complete Agent 7 fields in Experience."],
    }
    assert not state.agent7_available
    assert state.agent7_score == "Not scored"
    assert "could not complete" in state.agent7_summary
