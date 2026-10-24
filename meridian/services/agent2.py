"""Agent 2 application boundary; only the updated bundle may be used."""
from __future__ import annotations

import json
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "backend/app/agents/university_matching_agent/trained_models_local"
CATALOG = ROOT / "data/raw/agent2/agent2_enhanced_program_catalog.csv"
ARTIFACT_NAMES = (
    "agent2_admission_model.joblib", "agent2_feature_columns.joblib",
    "agent2_agent1_tier_features.joblib", "agent2_agent1_tier_representation.joblib",
    "agent2_decision_threshold.joblib", "agent2_shap_explainer.joblib",
    "applicant_cluster_model.joblib", "applicant_cluster_scaler.joblib",
    "applicant_cluster_medians.joblib", "applicant_cluster_features.joblib",
    "university_cluster_model.joblib", "university_cluster_scaler.joblib",
    "university_cluster_medians.joblib", "university_cluster_features.joblib",
)
NOTICE = (
    "Experimental results: percentages are unvalidated model scores, not admission chances. "
    "Higher (65% and above), middle (35% to below 65%) and lower (below 35%) are score bands, "
    "not safety or admission categories. Insufficient evidence means no model score is shown. "
    "Match scores describe catalog fit, not admission likelihood. Program tier scores come "
    "from the saved catalog; Agent 1's live candidate-tier classification is retained "
    "as orchestration context but is not a feature in this bundle. Offline retrieval uses TF-IDF "
    "text similarity, not the notebook's embedding/reranker services. Agent 7 affects "
    "the matching score, not this admission model. SHAP factors explain the uncalibrated "
    "classifier, while model scores use the calibrated classifier. Catalog tuition "
    "and program requirements may be outdated; verify them with the university."
)


def score_band(score: float) -> str:
    return "Higher" if score >= .65 else "Middle" if score >= .35 else "Lower"


class Agent2Unavailable(RuntimeError):
    """No verified university result can be produced."""


def require_bundle(model_dir: Path | None = None) -> dict:
    model_dir = MODEL_DIR if model_dir is None else model_dir
    missing = [name for name in ARTIFACT_NAMES if not (model_dir / name).is_file()]
    if missing:
        raise Agent2Unavailable(
            "Agent 2 unavailable: the updated training bundle is missing " + ", ".join(missing)
            + ". Generate the complete local bundle with scripts/run_agent2_notebook.py."
        )
    try:
        manifest = json.loads((model_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema_version"] != 1 or set(manifest["artifacts"]) != set(ARTIFACT_NAMES):
            raise ValueError("Invalid artifact manifest")
        for name in ARTIFACT_NAMES:
            if hashlib.sha256((model_dir / name).read_bytes()).hexdigest() != manifest["artifacts"][name]:
                raise ValueError(f"Artifact checksum mismatch: {name}")
        if hashlib.sha256(CATALOG.read_bytes()).hexdigest() != manifest["catalog_sha256"]:
            raise ValueError("Catalog checksum mismatch")
        return manifest
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Agent2Unavailable("Agent 2's bundle or catalog failed its manifest check. Regenerate or restore one complete bundle.") from exc


def model_python() -> str:
    configured = os.environ.get("MERIDIAN_AGENT2_PYTHON")
    if configured:
        return configured
    local = ROOT / ".venv-agent2" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(local) if local.is_file() else sys.executable


def _number(value, label: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if isinstance(value, bool) or not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{label} must be between {low:g} and {high:g}.")
    return number


def candidate_from_profile(profile: dict, agent7_result: dict) -> dict:
    scale = _number(profile.get("gpa_scale"), "GPA scale", 1, 100)
    if scale not in (4, 10, 100):
        raise ValueError("Choose an explicit GPA scale: 4, 10, or 100.")
    gpa = _number(profile.get("gpa"), "GPA", 0, scale)
    gre = profile.get("gre_quant")
    gre_missing = gre is None or (isinstance(gre, str) and not gre.strip())
    quant = None if gre_missing else _number(gre, "GRE Quant", 130, 170)
    if quant is not None and not quant.is_integer():
        raise ValueError("GRE Quant must be a whole number.")
    degree = profile.get("degree_goal")
    if degree not in ("MS", "MBA", "MEng"):
        raise ValueError("Agent 2 supports MS, MBA, or MEng in this catalog.")
    field = str(profile.get("field") or "").strip()
    if not field:
        raise ValueError("Enter your field of study for Agent 2 matching.")
    score = _number(agent7_result.get("profile_strength_score"), "Agent 7 profile strength", 0, 100)
    # Only structured model inputs cross the worker boundary. No admission/tier
    # values supplied in the student's dictionary are accepted.
    return {"gpa_numeric": gpa / scale * 4, "gre_numeric": quant,
            "gre_missing": int(gre_missing), "degree": degree, "field": field,
            "profile_strength_score": score}


def validate_result(result: dict) -> dict:
    if not isinstance(result, dict) or set(result) != {"universities", "notice", "retrieval"}:
        raise ValueError("Unexpected Agent 2 result schema.")
    if result["notice"] != NOTICE or result["retrieval"] != "TF-IDF":
        raise ValueError("Unexpected Agent 2 provenance.")
    rows = result["universities"]
    if not isinstance(rows, list) or len(rows) > 10:
        raise ValueError("Unexpected Agent 2 shortlist.")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid Agent 2 program result.")
        for key in ("id", "name", "program", "country", "region", "institution_type", "note"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Invalid Agent 2 {key}.")
        if row["id"] in seen:
            raise ValueError("Duplicate Agent 2 program.")
        seen.add(row["id"])
        for key, low, high in (("match_score", 0, 1), ("tier_score", 0, 100)):
            if type(row.get(key)) not in (float, int):
                raise ValueError(f"Invalid Agent 2 {key} type.")
            _number(row.get(key), key, low, high)
        reason = row.get("evidence_reason")
        if not isinstance(reason, str):
            raise ValueError("Missing Agent 2 evidence status.")
        if reason:
            if row.get("probability") is not None or row.get("tier") != "Insufficient evidence" or row.get("prob_str") != "Insufficient evidence" or row.get("factors") != []:
                raise ValueError("Unsupported Agent 2 inputs must not display a model score or explanation.")
        else:
            if type(row.get("probability")) not in (float, int):
                raise ValueError("Invalid Agent 2 model score.")
            _number(row["probability"], "model score", 0, 1)
            if row.get("tier") != score_band(row["probability"]) or row.get("prob_str") != f"{row['probability']:.1%}":
                raise ValueError("Invalid Agent 2 experimental band or score.")
        if row.get("match_str") != f"{row['match_score']:.1%}":
            raise ValueError("Invalid Agent 2 display value.")
        tuition = row.get("tuition")
        if tuition is not None:
            if type(tuition) not in (float, int):
                raise ValueError("Invalid Agent 2 tuition type.")
            _number(tuition, "Catalog tuition", 0, 1e9)
        if row.get("tuition_str") != (f"${tuition:,.0f}" if tuition is not None else "Not listed"):
            raise ValueError("Invalid Agent 2 tuition display value.")
        factors = row.get("factors")
        if not isinstance(factors, list) or len(factors) > 3:
            raise ValueError("Invalid Agent 2 explanation.")
        for factor in factors:
            if not isinstance(factor, dict) or type(factor.get("impact")) not in (float, int):
                raise ValueError("Invalid Agent 2 factor.")
            if not isinstance(factor.get("feature"), str):
                raise ValueError("Invalid Agent 2 factor name.")
            _number(factor.get("impact"), "SHAP impact", -1e6, 1e6)
    return result


class Agent2Service:
    def match_profile(self, profile: dict, agent7_result: dict, agent1_result: dict | None = None) -> dict:
        # Check before importing ML libraries or starting a process. Incomplete
        # exports must never resolve to legacy, experimental, or sample models.
        require_bundle()
        if agent1_result is not None:
            if not isinstance(agent1_result, dict) or not isinstance(agent1_result.get("prediction"), str):
                raise ValueError("Agent 1 returned an invalid classification.")
            # The verified Agent 2 bundle has no Agent 1 feature column. Keep the
            # classification as validated orchestration context, but do not
            # invent a feature mapping or admission-weight adjustment.
        candidate = candidate_from_profile(profile, agent7_result)
        executable = model_python()
        worker = Path(__file__).with_name("agent2_worker.py")
        try:
            completed = subprocess.run(
                [executable, "-B", str(worker)], input=json.dumps(candidate, allow_nan=False),
                text=True, encoding="utf-8", capture_output=True, timeout=90,
                cwd=worker.parent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "NUMBA_NUM_THREADS": "4",
                    "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, check=True,
            )
            return validate_result(json.loads(completed.stdout))
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise Agent2Unavailable(
                "Agent 2 could not validate or score its updated bundle. Check its exports and "
                "MERIDIAN_AGENT2_PYTHON against the original training environment. No substitute "
                "university recommendations were generated."
            ) from exc
