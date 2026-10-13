"""Application contracts and current-bundle failure tests; no model training."""
import asyncio
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from meridian.data import mock
from meridian.services.agent2 import (
    Agent2Service, Agent2Unavailable, ARTIFACT_NAMES, NOTICE, MODEL_DIR,
    candidate_from_profile, require_bundle, validate_result,
)
from meridian.services.agent7 import candidate_from_profile as agent7_candidate
from meridian.services.report_pdf import render_report_pdf
from meridian.state import State

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


class BackgroundHarness:
    """Exercise the real event body with an in-memory state and no server locks."""
    def __init__(self, state):
        object.__setattr__(self, "state", state)

    def __getattr__(self, key):
        return getattr(self.state, key)

    def __setattr__(self, key, value):
        setattr(self.state, key, value)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FastEvents:
    def __init__(self, mutate=None):
        self.mutate = mutate

    async def stream(self, profile):
        for agent in mock.AGENT_IDS:
            # Even a mock completion for university must be ignored.
            yield {"type": agent + "_completed", "agent": agent}
        if self.mutate:
            self.mutate()


def fresh_state():
    state = State(_reflex_internal_init=True)
    state.profile = dict(PROFILE)
    state.agent7_result = dict(AGENT7)
    state.agent7_inputs = agent7_candidate(PROFILE)
    return state


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

    def test_missing_agent2_preserves_agent7_and_allows_dossier(self):
        state = fresh_state()
        with patch("meridian.state.get_event_source", return_value=FastEvents()), patch(
            "meridian.state.Agent2Service.match_profile", side_effect=Agent2Unavailable("Missing updated exports")
        ):
            asyncio.run(State.run_agents.fn(BackgroundHarness(state)))
        self.assertEqual(state.agent7_result, AGENT7)
        self.assertEqual(state.agent2_result, {})
        self.assertIn("Missing updated exports", state.agent2_error)
        self.assertTrue(state.agents_done)
        self.assertEqual(next(a for a in state.agents if a["id"] == "university")["status"], "unavailable")
        self.assertEqual(state.university_count, "Unavailable")
        captured = self.capture_report(state)
        self.assertEqual(captured["universities"], [])
        self.assertEqual(captured["key_factors"], [])
        self.assertIn("Missing updated exports", captured["agent2_notice"])

    def test_unsupported_scores_and_old_results_cannot_leak_into_reports(self):
        result = copy.deepcopy(RESULT)
        row = result["universities"][0]
        row.update(probability=None, prob_str="Insufficient evidence", tier="Insufficient evidence",
                   evidence_reason="GRE Quant is missing", factors=[])
        validate_result(result)
        state = fresh_state()
        state.agent2_result = result
        report = self.capture_report(state)
        self.assertIsNone(report["universities"][0]["probability"])
        self.assertEqual(report["key_factors"], [])
        row["probability"] = .98
        with self.assertRaises(ValueError):
            validate_result(result)
        old = copy.deepcopy(RESULT)
        old["universities"][0]["tier"] = "Target"
        state.agent2_result = old
        self.assertFalse(state.agent2_ready)
        self.assertEqual(self.capture_report(state)["universities"], [])

    def test_result_rendering_pdf_and_invalidation_share_session_data(self):
        state = fresh_state()
        with patch("meridian.state.get_event_source", return_value=FastEvents()), patch(
            "meridian.state.Agent2Service.match_profile", return_value=copy.deepcopy(RESULT)
        ) as service:
            asyncio.run(State.run_agents.fn(BackgroundHarness(state)))
            service.assert_called_once_with(PROFILE, AGENT7)
        self.assertEqual(state.university_matches, RESULT["universities"])
        self.assertEqual(state.university_count, "1")
        captured = self.capture_report(state)
        self.assertEqual(captured["universities"], state.university_matches)
        self.assertIn("gpa_numeric", captured["key_factors"][0]["name"])
        state.set_field("gpa", "8")
        self.assertFalse(state.agent2_ready)
        self.assertEqual(state.agent2_profile, {})
        self.assertEqual(state.agent7_result, {})

    def test_profile_edit_during_analysis_cannot_publish_old_results(self):
        state = fresh_state()
        with patch("meridian.state.get_event_source", return_value=FastEvents(lambda: state.set_field("gpa", "8"))), patch(
            "meridian.state.Agent2Service.match_profile", return_value=copy.deepcopy(RESULT)
        ):
            asyncio.run(State.run_agents.fn(BackgroundHarness(state)))
        self.assertFalse(state.agent2_ready)
        self.assertFalse(state.agent7_ready)
        self.assertFalse(state.agents_done)
        self.assertIn("Profile changed", state.agent7_error)

    def capture_report(self, state):
        captured = {}
        test = self
        class Capture:
            def get_report(self, profile):
                return mock.build_report(profile)
            def render_pdf(self, report):
                captured.update(report)
                pdf = render_report_pdf(report)
                test.assertTrue(pdf.startswith(b"%PDF"))
                return pdf
        before = copy.deepcopy(mock.UNIVERSITIES)
        with patch("meridian.state.get_report_service", return_value=Capture()):
            state.download_report()
        self.assertEqual(mock.UNIVERSITIES, before)
        return captured


if __name__ == "__main__":
    unittest.main()
