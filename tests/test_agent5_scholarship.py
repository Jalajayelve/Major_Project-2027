import sys

import pytest

sys.path.insert(0, "backend")

from app.agents.scholarship_agent.scholarship import analyze_scholarships


FINANCE = [{
    "university": "Northeastern University",
    "program_name": "MS Computer Science",
    "tuition_annual": 66162.0,
    "living_cost_annual": 18849.11,
    "total_cost": 85011.11,
    "currency": "USD",
}]


def test_agent5_loads_artifacts_and_returns_structured_result():
    result = analyze_scholarships({
        "profile": {
            "nationality": "India",
            "field": "Computer Science",
            "degree_goal": "MS",
            "gpa": "3.4",
            "gpa_scale": "4",
            "budget": "30000",
            "budget_currency": "USD",
        },
        "finance": FINANCE,
    })
    item = result["scholarships"][0]
    assert result["agent"] == "scholarship"
    assert item["catalog_counts"]["examined"] == 9673
    assert isinstance(item["recommendations"], list)
    assert isinstance(item["eligibility_review"], list)
    assert item["funding_gap"] == pytest.approx(55011.11)


def test_agent5_rejects_missing_financial_handoff():
    with pytest.raises(ValueError, match="financial results"):
        analyze_scholarships({"profile": {}, "finance": []})


def test_agent5_preserves_explicit_unavailable_eligibility():
    result = analyze_scholarships({
        "profile": {"degree_goal": "MS", "field": "Computer Science"},
        "finance": FINANCE,
    })
    assert result["scholarships"][0]["recommendations"] == []
    assert result["scholarships"][0]["eligibility_review"]
