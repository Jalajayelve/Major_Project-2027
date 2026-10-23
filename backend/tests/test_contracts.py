from fastapi.testclient import TestClient
from app import create_app
import pytest

client = TestClient(create_app())


def test_matching_actual_contract():
    result = client.post('/match', json={'gpa':3.4,'country':'USA','tier':'medium'})
    assert result.status_code == 200
    rows = result.json()['matched_universities']
    assert rows == [{'name':'Northeastern University','country':'USA','tier':'medium','gpa':3.4}]
    assert 'probability' not in rows[0]


def test_prediction_missing_models(monkeypatch, tmp_path):
    from app.config import Config
    monkeypatch.setattr(Config, 'MODEL_DIR', str(tmp_path))
    ms = {'gpa':3.5,'gre_score':320,'toefl_score':100,'research_experience':1,'work_experience':2}
    mba = {'gpa':3.5,'gmat_score':700,'work_experience':2,'essay_score':5}
    ms_response = client.post('/predict/ms', json=ms)
    mba_response = client.post('/predict/mba', json=mba)
    assert ms_response.status_code == 503
    assert 'candidate-tier artifacts' in ms_response.json()['detail']
    assert mba_response.status_code == 503
    assert 'candidate-tier artifacts' in mba_response.json()['detail']
    assert client.post('/predict/ms', json={}).status_code == 400


def test_agent1_profile_uses_bundled_candidate_tier_model():
    response = client.post('/agent1/profile', json={
        'track': 'MS', 'gpa_normalized_4': 3.4, 'gre_score': 310,
        'toefl_score': 100, 'has_research': 0, 'work_experience_months': 12,
        'major': 'STEM',
    })
    assert response.status_code == 200
    body = response.json()
    assert body['agent'] == 'profile'
    assert body['analysis'] == 'candidate_tier'
    assert body['prediction'] in ('Tier1', 'Tier2')
    assert 'not an admission probability' in body['notice']


def test_agent3_program_ranks_agent2_shortlist():
    response = client.post('/agent3/program', json={
        'profile': {'degree_goal': 'MS', 'field': 'Computer Science'},
        'matched_universities': [{
            'name': 'Northeastern University',
            'country': 'USA',
            'tier': 'medium',
            'gpa': 3.4,
        }],
    })
    assert response.status_code == 200
    body = response.json()
    assert body['agent'] == 'program'
    assert body['programs']
    assert all(item['university'] == 'Northeastern University' for item in body['programs'])
    assert all(item['score_type'] == 'relevance_not_probability' for item in body['programs'])
    assert all(item['admit_probability'] is None for item in body['programs'])


@pytest.mark.parametrize('payload', [{}, {'gpa': 'nan'}, {'gpa': 10}, {'gpa': True}, {'gpa':3, 'tier':[]}, {'gpa':3, 'country':None}])
def test_matching_rejects_bad_input(payload):
    assert client.post('/match', json=payload).status_code == 400


def test_explicit_scale_conversion_and_input_not_mutated():
    from app.utils.preprocessing import normalize_gpa, validate_profile_input
    assert normalize_gpa({'gpa':8.4,'gpa_scale':10})['gpa'] == 3.36
    with pytest.raises(ValueError):
        normalize_gpa({'gpa':8.4})
    payload = {'gpa':3.4,'gmat_score':'700','work_experience':2,'essay_score':5}
    validate_profile_input(payload, 'mba')
    assert payload['gmat_score'] == '700'
    payload['work_experience'] = float('nan')
    with pytest.raises(ValueError):
        validate_profile_input(payload, 'mba')
