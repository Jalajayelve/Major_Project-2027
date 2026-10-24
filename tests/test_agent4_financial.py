import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path("backend/app/agents/financial_agent/financial.py")
SPEC = importlib.util.spec_from_file_location("agent4_financial", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _features():
    _, columns = MODULE.load_artifacts()
    return {column: 0 for column in columns} | {"living_cost_annual": 15000}


def test_agent4_loads_existing_pickle_and_predicts():
    result = MODULE.analyze_financial({
        "degree_goal": "MS",
        "programs": [{
            "university": "Test University",
            "program_name": "MS Computer Science",
            "financial_features": _features(),
        }],
    })
    row = result["finance"][0]
    assert result["agent"] == "financial"
    assert row["cost_data_quality"] == "MODEL_PREDICTED"
    assert row["tuition_annual"] >= 0
    assert row["total_cost"] == row["tuition_annual"] + row["living_cost_annual"]


def test_agent4_rejects_missing_verified_features():
    with pytest.raises(MODULE.FinancialUnavailable, match="no eligible"):
        MODULE.analyze_financial({"degree_goal": "MS", "programs": [{"university": "Test", "program_name": "MS CS"}]})


def test_agent4_rejects_incomplete_feature_row():
    with pytest.raises(MODULE.FinancialUnavailable, match="missing"):
        MODULE.analyze_financial({
            "degree_goal": "MS",
            "programs": [{
                "university": "Test",
                "program_name": "MS CS",
                "financial_features": {"living_cost_annual": 1000},
            }],
        })


def test_agent4_uses_published_cost_comparison_source():
    result = MODULE.analyze_financial({
        "degree_goal": "MS",
        "programs": [{
            "university": "Massachusetts Institute of Technology",
            "program_name": "MS Computer Science",
        }],
    })
    row = result["finance"][0]
    assert row["cost_data_quality"] == "PUBLISHED_SOURCE"
    assert row["total_cost"] == row["tuition_annual"] + row["living_cost_annual"]


def test_agent4_skips_unmatched_programs_without_failing_eligible_rows():
    result = MODULE.analyze_financial({
        "degree_goal": "MS",
        "programs": [
            {"university": "Massachusetts Institute of Technology", "program_name": "MS Computer Science"},
            {"university": "Massachusetts Institute of Technology", "program_name": "MS Missing Program"},
        ],
    })
    assert len(result["finance"]) == 1
    assert result["finance_skipped"][0]["program_name"] == "MS Missing Program"
