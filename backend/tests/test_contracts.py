from fastapi.testclient import TestClient
from app import create_app

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
    assert client.post('/predict/ms', json=ms).status_code == 503
    assert client.post('/predict/mba', json=mba).status_code == 503
    assert client.post('/predict/ms', json={}).status_code == 400
