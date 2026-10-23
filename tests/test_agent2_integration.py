"""Application contracts and current-bundle failure tests; no model training."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from meridian.data import mock
from meridian.services.agent2 import (
    Agent2Service, Agent2Unavailable, ARTIFACT_NAMES, NOTICE,
    candidate_from_profile, require_bundle, validate_result,
)

PROFILE = {**mock.STUDENT_PROFILE, "leadership_score": "6", "research_score": "9",
           "competition_score": "5", "volunteering_score": "4", "publication_count": "3",
           "patent_count": "0", "agent7_degree_level": "Masters", "agent7_field": "STEM"}
AGENT7 = {"profile_strength_score": 55.4, "strength_tier": "Moderate", "P(Strong)": .156443,
          "achievement_archetype": "1", "has_research_evidence": 1}
# Contract fixture only. These values are never presented as real inference.
RESULT = {"notice": NOTICE, "retrieval": "TF-IDF", "universities": [{
    "id": "contract-fixture", "name": "Fixture University & Institute", "program": "MS <Test>",
    "country": "USA", "region": "CA", "institution_type": "Public", "note": "Contract fixture",
    "probability": .5, "prob_str": "50.0%", "match_score": .6, "match_str": "60.0%",
    "tier_score": 70., "tier": "Middle", "evidence_reason": "", "tuition": None, "tuition_str": "Not listed",
    "factors": [{"feature": "gpa_numeric", "impact": .05}],
}]}


class Agent2Tests(unittest.TestCase):
    def test_missing_exports_never_start_worker_or_use_older_models(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(Agent2Unavailable) as error:
                require_bundle(Path(directory))
            for name in ARTIFACT_NAMES:
                self.assertIn(name, str(error.exception))
            # Simulate an absent installation even after the local bundle exists.
            with patch("meridian.services.agent2.MODEL_DIR", Path(directory)), patch("meridian.services.agent2.subprocess.run") as run:
                with self.assertRaises(Agent2Unavailable) as error:
                    Agent2Service().match_profile(PROFILE, AGENT7)
                self.assertIn("agent2_admission_model.joblib", str(error.exception))
                run.assert_not_called()

    def test_gpa_gre_and_upstream_score_contract(self):
        candidate = candidate_from_profile({**PROFILE, "tier_score": 99, "admit_probability": .99}, AGENT7)
        self.assertAlmostEqual(candidate["gpa_numeric"], 3.36)
        self.assertNotIn("tier_score", candidate)
        self.assertNotIn("admit_probability", candidate)
        self.assertEqual(candidate["profile_strength_score"], 55.4)
        absent = candidate_from_profile({**PROFILE, "gre_quant": ""}, AGENT7)
        self.assertIsNone(absent["gre_numeric"])
        self.assertEqual(absent["gre_missing"], 1)
        for key, value in (("gpa", "11"), ("gpa", "nan"), ("gpa_scale", "0"),
                           ("gre_quant", "0"), ("gre_quant", "165.5"), ("field", ""), ("degree_goal", "PhD")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                candidate_from_profile({**PROFILE, key: value}, AGENT7)
        with self.assertRaises(ValueError):
            candidate_from_profile(PROFILE, {})

    def test_unavailable_runtime_and_invalid_worker_outputs(self):
        with patch("meridian.services.agent2.require_bundle"), patch.dict(os.environ, {"MERIDIAN_AGENT2_PYTHON": "missing-agent2-runtime.exe"}):
            with self.assertRaises(Agent2Unavailable):
                Agent2Service().match_profile(PROFILE, AGENT7)
        validate_result(copy.deepcopy(RESULT))
        for key, value in (("probability", float("nan")), ("prob_str", "99%"),
                           ("tier", "Safe"), ("tuition", -1), ("match_score", 2)):
            result = copy.deepcopy(RESULT)
            result["universities"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_result(result)

    def test_insufficient_evidence_cannot_carry_probability(self):
        result = copy.deepcopy(RESULT)
        row = result['universities'][0]
        row.update(probability=None, prob_str='Insufficient evidence', tier='Insufficient evidence',
                   evidence_reason='GRE Quant is missing', factors=[])
        validate_result(result)
        row['probability'] = .98
        with self.assertRaises(ValueError):
            validate_result(result)


# Current authenticated workflow regressions replace the retired demo-state API.
from test_agent7_integration import state, other_agents, run
from meridian.services import api, storage
import json


def test_matching_failure_keeps_real_agent7_result(state, monkeypatch):
    async def response(path, payload):
        if path == '/agent1/profile':
            return {'prediction': 'Contract fixture'}
        raise ValueError('Matcher unavailable')
    monkeypatch.setattr(api, 'request', response)
    run(state)
    assert 'extracurricular' in state.results
    assert state.agents[1]['status'] == 'failed'
    assert state.agents[2]['status'] == 'failed'
    assert json.loads(storage.user(state.session)['results'])['extracurricular'] == state.results['extracurricular']


def test_matching_payload_and_agent3_shortlist_unchanged(state, other_agents):
    run(state)
    assert other_agents[1] == ('/match', {'gpa': 3.4, 'country': 'USA', 'tier': 'medium'})
    assert other_agents[2][1]['matched_universities'] == state.results['university']['matched_universities']
    state.set_field('gpa', '3.8')
    state._save_profile()
    assert state.results == {}
    assert json.loads(storage.user(state.session)['results']) == {}
