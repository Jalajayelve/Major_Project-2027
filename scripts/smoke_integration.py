"""Run against the local API. Uses disposable test data, never a real account."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meridian.services import api, storage
from meridian.state import State


class Harness:
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


async def main():
    base = os.getenv('MERIDIAN_API_URL', 'http://127.0.0.1:8001')
    async with httpx.AsyncClient(trust_env=False) as client:
        health = await client.get(base+'/health')
        assert health.json()['status'] == 'ok'
        for path, payload in [('/predict/ms', {'gpa':3.4,'gre_score':310,'toefl_score':100,'research_experience':0,'work_experience':1}),
                              ('/predict/mba', {'gpa':3.4,'gmat_score':700,'essay_score':5,'work_experience':1})]:
            response = await client.post(base+path, json=payload)
            assert response.status_code == 503, response.text
            print(path, '503 (missing original model export)')
    with tempfile.TemporaryDirectory() as directory:
        os.environ['MERIDIAN_DATA_DIR'] = directory
        state = State(_reflex_internal_init=True)
        state.session = storage.authenticate('smoke@example.com', 'disposable smoke test password', True, 'Smoke Test')
        storage.save(state.session, 'profile', {'gpa':'3.4','gpa_scale':'4','degree_goal':'MS','work_years':'1',
            'gre_verbal':'150','gre_quant':'160','toefl':'100','research_experience':'0','match_country':'USA','match_tier':'medium'})
        async for _ in State.run_agents.fn(Harness(state)):
            pass
        assert state.agents[0]['status'] == 'failed'
        assert state.agents[1]['status'] == 'completed'
        assert not state.agents_running
        assert state.recommendations[0]['name'] == 'Northeastern University'
        assert json.loads(storage.user(state.session)['results'])['university']['count'] == 1
        state.download_report()
        state.logout()
        assert not state.authenticated
        print('PASS: real Reflex analysis handler -> HTTP API -> persisted match -> report -> logout')


asyncio.run(main())
