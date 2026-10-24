import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path("backend/app/agents/career_agent/career.py")
SPEC = importlib.util.spec_from_file_location("agent6_career", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
analyze_career = MODULE.analyze_career
validate_profile = MODULE.validate_profile


PROFILE = {
    "degree_goal": "MS",
    "field": "Computer Science",
    "career_goal": "machine learning engineer",
    "work_years": "2",
    "role": "Software Engineer",
    "projects": "python machine learning sql",
}


def test_agent6_returns_model_and_rule_based_outputs():
    result = analyze_career(PROFILE)
    assert result["agent"] == "career"
    assert result["career_paths"]
    assert result["top_path"] in [row["career_path"] for row in result["career_paths"]]
    assert isinstance(result["model_estimated_annual_earnings_usd"], float)
    assert all(0 <= row["alignment_score"] <= 100 for row in result["career_paths"])
    assert all(isinstance(row["skill_gaps"], list) for row in result["career_paths"])
    assert "model estimate" in result["notice"]


@pytest.mark.parametrize("field", ["degree_goal", "field", "career_goal"])
def test_agent6_rejects_missing_required_fields(field):
    profile = dict(PROFILE)
    profile[field] = ""
    with pytest.raises(ValueError, match=field):
        validate_profile(profile)


def test_corrupted_lookup_bundle_is_not_used_as_a_success_signal():
    bundle = Path("backend/app/agents/career_agent/trained_models_A6/agent6_lookup_bundle.joblib")
    assert bundle.exists()
    with pytest.raises(Exception):
        import joblib
        joblib.load(bundle)
