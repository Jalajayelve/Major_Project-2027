"""Real exported-bundle checks. Requires the isolated Agent 2 and Agent 7 runtimes."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from meridian.data import mock
from meridian.services.agent2 import Agent2Service, Agent2Unavailable, require_bundle, ROOT
from meridian.services.agent7 import Agent7Service
from meridian.services.report_pdf import render_report_pdf
from meridian.state import State

INPUTS = {"leadership_score": "6", "research_score": "9", "competition_score": "5",
          "volunteering_score": "4", "publication_count": "3", "patent_count": "0",
          "agent7_degree_level": "Masters", "agent7_field": "STEM"}


class RealBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = {**mock.STUDENT_PROFILE, **INPUTS, "full_name": "TEST PROFILE - Agent 2 and Agent 7",
                       "gpa": "8.4", "gpa_scale": "10", "gre_quant": "165", "degree_goal": "MS", "field": "Computer Science"}
        cls.agent7 = Agent7Service().score_profile(cls.profile)
        cls.first = Agent2Service().match_profile(cls.profile, cls.agent7)
        cls.second = Agent2Service().match_profile({**cls.profile, "gpa": "9.8"}, cls.agent7)

    def test_real_predictions_respond_to_gpa(self):
        self.assertEqual(len(self.first["universities"]), 10)
        self.assertEqual(len(self.second["universities"]), 10)
        first = {u["id"]: u["probability"] for u in self.first["universities"]}
        second = {u["id"]: u["probability"] for u in self.second["universities"]}
        shared = first.keys() & second.keys()
        self.assertTrue(shared)
        self.assertTrue(any(abs(first[k] - second[k]) > .001 for k in shared))
        for result in (self.first, self.second):
            self.assertTrue(all(len(u["factors"]) == 3 for u in result["universities"]))
        evidence = {"agent7_inputs": INPUTS, "agent7_result": self.agent7,
                    "first": self.first, "second": self.second, "profiles": {"first_gpa": "8.4/10", "second_gpa": "9.8/10"}}
        (ROOT / "reports/agent2-local/live-inference.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    def test_manifest_detects_catalog_change_before_inference(self):
        manifest = require_bundle()
        self.assertEqual(len(manifest["artifacts"]), 14)
        with patch("meridian.services.agent2.CATALOG", Path(__file__)):
            with self.assertRaises(Agent2Unavailable):
                require_bundle()

    def test_missing_and_outside_training_gre_keep_matches_without_scores(self):
        for gre in ("", "150", "170"):
            with self.subTest(gre=gre):
                result = Agent2Service().match_profile({**self.profile, "gre_quant": gre}, self.agent7)
                self.assertEqual(len(result["universities"]), 10)
                for row in result["universities"]:
                    self.assertIsNone(row["probability"])
                    self.assertEqual(row["tier"], "Insufficient evidence")
                    self.assertEqual(row["prob_str"], "Insufficient evidence")
                    self.assertEqual(row["factors"], [])
                    self.assertTrue(row["evidence_reason"])
                    self.assertGreater(row["match_score"], 0)
                (ROOT / f"reports/agent2-local/unsupported-gre-{gre or 'missing'}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    def test_actual_results_are_exported_to_pdf(self):
        state = State(_reflex_internal_init=True)
        state.profile = dict(self.profile)
        state.agent7_result = dict(self.agent7)
        state.agent2_result = copy.deepcopy(self.first)
        captured = {}
        class Capture:
            def get_report(self, profile):
                return mock.build_report(profile)
            def render_pdf(self, report):
                captured.update(report)
                return render_report_pdf(report)
        with patch("meridian.state.get_report_service", return_value=Capture()):
            state.download_report()
        self.assertEqual(captured["universities"], self.first["universities"])
        self.assertEqual(len(captured["key_factors"]), 30)
        self.assertEqual(captured["profile_strength"]["score"], "55.4")


if __name__ == "__main__":
    unittest.main()
