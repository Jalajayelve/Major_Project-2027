"""Integration checks: inference only, no training or artifact writes.

Run: python -B -m unittest discover -s tests -p test_agent7_integration.py -v
MERIDIAN_AGENT7_PYTHON must select the verified model runtime if different.
"""
import asyncio
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from meridian.data import mock
from meridian.services.agent7 import Agent7Service, Agent7Unavailable, candidate_from_profile
from meridian.services.report_pdf import render_report_pdf
from meridian.state import State

TEST_PROFILE = {
    **mock.STUDENT_PROFILE, "full_name": "TEST PROFILE - Agent 7 integration",
    "leadership_score": "6", "research_score": "9", "competition_score": "5",
    "volunteering_score": "4", "publication_count": "3", "patent_count": "0",
    "agent7_degree_level": "Masters", "agent7_field": "STEM",
}


class IntegrationTests(unittest.TestCase):
    def test_failed_submission_stays_put_and_can_retry_from_experience(self):
        state = State(_reflex_internal_init=True)
        state.profile = {**TEST_PROFILE, "research_score": ""}
        final_tab = len(mock.FORM_SCHEMA) - 1
        state.profile_tab = final_tab
        async def submit():
            return [event async for event in state.next_tab()]
        with patch("meridian.state.Agent7Service.score_profile") as score:
            asyncio.run(submit())
            score.assert_not_called()
        self.assertEqual(state.profile_tab, final_tab)
        self.assertTrue(state.profile_submission_attempted)
        self.assertIn("research_score", state.agent7_error)
        self.assertFalse(state.agent7_busy)
        experience = next(i for i,s in enumerate(mock.FORM_SCHEMA) if s['id']=='experience')
        state.set_tab(experience)
        state.set_field("research_score", "9")
        with patch("meridian.state.Agent7Service.score_profile", side_effect=Agent7Unavailable("Runtime unavailable")):
            asyncio.run(submit())
        self.assertEqual(state.profile_tab, experience)
        self.assertEqual(state.agent7_error, "Runtime unavailable")
        with patch("meridian.state.Agent7Service.score_profile", return_value={"profile_strength_score":55.4}):
            events = asyncio.run(submit())
        self.assertEqual(state.agent7_error, "")
        self.assertIn("/documents", str(events[-1]))

    def test_missing_unknown_invalid_inputs(self):
        variants = [(key, "") for key in candidate_from_profile(TEST_PROFILE) if key not in ("field", "degree_level")]
        variants += [("agent7_field", ""), ("agent7_degree_level", ""), ("leadership_score", "11"),
                     ("research_score", "nan"), ("competition_score", "-1"), ("patent_count", "1.5"),
                     ("publication_count", True), ("agent7_field", "Computer Science")]
        for key, value in variants:
            with self.subTest(key=key, value=value), patch("meridian.services.agent7.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    Agent7Service().score_profile({**TEST_PROFILE, key: value})
                run.assert_not_called()

    def test_no_dataset_score_or_free_text_inference(self):
        value = candidate_from_profile({**TEST_PROFILE, "profile_strength_score": 99.99, "research": "invented free text"})
        self.assertNotIn("profile_strength_score", value)
        self.assertEqual(value["field"], "STEM")
        self.assertEqual(value["publication_count"], 3)

    def test_missing_runtime_fails_without_fallback(self):
        with patch.dict(os.environ, {"MERIDIAN_AGENT7_PYTHON": str(Path(tempfile.gettempdir()) / "missing-agent7-python.exe")}):
            with self.assertRaises(Agent7Unavailable):
                Agent7Service().score_profile(TEST_PROFILE)

    def test_real_submission_fresh_worker_foreign_cwd_and_pdf(self):
        state = State(_reflex_internal_init=True)
        state.profile = dict(TEST_PROFILE)
        state.profile_tab = len(mock.FORM_SCHEMA) - 1
        async def submit():
            return [event async for event in state.next_tab()]
        previous = Path.cwd()
        try:
            os.chdir(tempfile.gettempdir())
            events = asyncio.run(submit())
        finally:
            os.chdir(previous)
        self.assertTrue(events)
        self.assertEqual(state.agent7_error, "")
        self.assertFalse(state.agent7_busy)
        self.assertEqual(state.agent7_result, {
            "strength_tier": "Moderate", "profile_strength_score": 55.4, "P(Strong)": 0.156443,
            "achievement_archetype": "1", "has_research_evidence": 1,
        })
        before = copy.deepcopy(mock.PROFILE_STRENGTH)
        captured = {}
        class ReportCapture:
            def get_report(self, profile):
                return mock.build_report(profile)
            def render_pdf(self, report):
                captured.update(report)
                pdf = render_report_pdf(report)
                self_test.assertTrue(pdf.startswith(b"%PDF"))
                return pdf
        self_test = self
        with patch("meridian.state.get_report_service", return_value=ReportCapture()):
            state.download_report()
        self.assertEqual(captured["profile_strength"]["score"], "55.4")
        self.assertIn("NOT admission probability", captured["agent7_notice"])
        self.assertEqual(mock.PROFILE_STRENGTH, before)
        state.set_field("research_score", "8")
        self.assertEqual(state.agent7_result, {})
        self.assertEqual(state.agent7_score, "Not scored")

    def test_second_profile_has_different_real_result(self):
        result = Agent7Service().score_profile({**TEST_PROFILE, "agent7_degree_level": "Bachelors",
            "leadership_score": "1", "research_score": "1", "competition_score": "0",
            "volunteering_score": "1", "publication_count": "0"})
        self.assertEqual(result["strength_tier"], "Weak")
        self.assertEqual(result["profile_strength_score"], 3.5)
        self.assertEqual(result["has_research_evidence"], 0)


if __name__ == "__main__":
    unittest.main()
