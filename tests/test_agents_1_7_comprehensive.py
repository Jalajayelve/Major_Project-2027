"""Evidence-based coverage for the seven-agent Meridian surface."""
from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest

from meridian.data.profile import empty_profile
from meridian.services import api
from meridian.services.agent7 import Agent7Service
from meridian.state import State


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "backend" / "app" / "agents"

AGENT7_PROFILE = {
    **empty_profile(),
    "leadership_score": "6",
    "research_score": "9",
    "competition_score": "5",
    "volunteering_score": "4",
    "publication_count": "3",
    "patent_count": "0",
    "agent7_degree_level": "Masters",
    "agent7_field": "STEM",
}


def test_agent7_real_artifact_output_contract():
    result = Agent7Service().score_profile(AGENT7_PROFILE)
    assert set(result) == {
        "strength_tier",
        "profile_strength_score",
        "P(Strong)",
        "achievement_archetype",
        "has_research_evidence",
    }
    assert result["strength_tier"] in {"Weak", "Moderate", "Strong"}
    assert 0 <= result["profile_strength_score"] <= 100
    assert 0 <= result["P(Strong)"] <= 1
    assert isinstance(result["achievement_archetype"], str)
    assert result["has_research_evidence"] in (0, 1)


def test_agent1_to_agent3_live_api_contracts():
    async def exercise():
        profile_result = await api.request("/agent1/profile", {
            "track": "MS",
            "gpa_normalized_4": 3.4,
            "gre_score": 310,
            "toefl_score": 100,
            "has_research": 1,
            "work_experience_months": 12,
            "major": "STEM",
        })
        university_result = await api.request("/match", {
            "gpa": 3.4,
            "country": "USA",
            "tier": "medium",
        })
        program_result = await api.request("/agent3/program", {
            "profile": {"degree_goal": "MS", "field": "Computer Science"},
            "matched_universities": university_result["matched_universities"],
        })
        return profile_result, university_result, program_result

    profile_result, university_result, program_result = asyncio.run(exercise())
    assert profile_result["agent"] == "profile"
    assert profile_result["prediction"] in {"Tier1", "Tier2"}
    assert 0 <= profile_result["probability"] <= 1
    assert university_result["matched_universities"]
    assert all(
        isinstance(row["name"], str)
        and isinstance(row["country"], str)
        and isinstance(row["tier"], str)
        and isinstance(row["gpa"], (int, float))
        for row in university_result["matched_universities"]
    )

    assert program_result["programs"]
    assert all(
        row["score_type"] == "relevance_not_probability"
        and row["admit_probability"] is None
        and 0 <= row["match_score"] <= 1
        for row in program_result["programs"]
    )


def test_frontend_exposes_real_and_unavailable_agent_states():
    from meridian.pages.analysis import analysis_page
    from meridian.pages.results import results_page

    analysis = str(analysis_page())
    results = str(results_page())
    assert "agent-progress" in analysis
    assert "Strength tier" in results
    assert "P(Strong)" in results
    assert "Achievement archetype" in results
    assert "No verified backend service is configured" in analysis or "unavailable" in analysis.lower()


@pytest.mark.parametrize(
    ("agent_id", "agent_directory"),
    [
        ("financial", "financial_agent"),
        ("scholarship", "scholarship_agent"),
        ("career", "career_agent"),
    ],
)
def test_agents_4_to_6_report_missing_implementation_evidence(agent_id, agent_directory):
    """Financial remains artifact-limited; Agent 5 and Agent 6 have explicit artifacts."""
    assert agent_id in {"financial", "scholarship", "career"}
    directory = AGENTS_DIR / agent_directory
    if agent_id == "financial":
        notebook = directory / "Agent4_Financial_agent.ipynb"
        assert notebook.exists()
        content = json.loads(notebook.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in content["cells"])
        assert "agent4_master_financial_dataset.csv" in source
        assert not list(notebook.parent.glob("*.joblib"))
    else:
        if agent_id == "career":
            assert (AGENTS_DIR / directory / "trained_models_A6" / "agent6_earnings_model.joblib").exists()
            assert (AGENTS_DIR / directory / "trained_models_A6" / "agent6_lookup_bundle.joblib").exists()
        else:
            assert (directory / "trained_models_A5" / "agent5_scholarship_catalog.joblib").exists()
            assert (directory / "trained_models_A5" / "agent5_tfidf_vectorizer.joblib").exists()
