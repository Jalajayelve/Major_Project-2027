"""Agent 7 inference independent of notebook state and working directory."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import importlib.metadata
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .schema import CLUSTER_COLUMNS, feature_frame, validate_candidate
from .sop import combine_scores, score_sop

MODEL_DIR = Path(__file__).resolve().parent / "trained_models"
ARTIFACT_TYPES = {
    "agent7_xgb_tier_model.joblib": XGBClassifier,
    "agent7_gbr_score_model.joblib": GradientBoostingRegressor,
    "agent7_feature_columns.joblib": list,
    "agent7_archetype_kmeans.joblib": KMeans,
    "agent7_archetype_scaler.joblib": StandardScaler,
}


class ArtifactError(RuntimeError):
    """Missing, incompatible or unverified Agent 7 artifacts."""


@dataclass(frozen=True)
class Bundle:
    classifier: XGBClassifier
    regressor: GradientBoostingRegressor
    columns: list[str]
    archetype: KMeans
    scaler: StandardScaler


@lru_cache(maxsize=4)
def _load_verified(directory: str) -> Bundle:
    directory = Path(directory)
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema_version"] != 1 or manifest["training_source"] != "synthetic_notebook_rubric":
            raise ArtifactError("Unsupported Agent 7 artifact manifest.")
        for package, expected in manifest["dependencies"].items():
            actual = importlib.metadata.version(package)
            if actual != expected:
                raise ArtifactError(f"{package} version mismatch: expected {expected}, found {actual}. Use Agent 7 requirements.txt.")
        loaded = {}
        for name, expected_type in ARTIFACT_TYPES.items():
            path = directory / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["artifact_sha256"][name]:
                raise ArtifactError(f"Artifact hash mismatch: {name}.")
            obj = joblib.load(path)
            if not isinstance(obj, expected_type):
                raise ArtifactError(f"{name} expected {expected_type.__name__}, got {type(obj).__name__}.")
            loaded[name] = obj
        columns = loaded["agent7_feature_columns.joblib"]
        if not columns or not all(isinstance(c, str) for c in columns) or len(columns) != len(set(columns)):
            raise ArtifactError("Invalid feature-column artifact.")
        if columns != manifest["feature_columns"]:
            raise ArtifactError("Manifest and feature-column artifact disagree.")
        classifier = loaded["agent7_xgb_tier_model.joblib"]
        regressor = loaded["agent7_gbr_score_model.joblib"]
        if set(classifier.classes_.tolist()) != {0, 1, 2}:
            raise ArtifactError("Classifier must encode Weak=0, Moderate=1, Strong=2.")
        for model in (classifier, regressor):
            if model.n_features_in_ != len(columns) or list(model.feature_names_in_) != columns:
                raise ArtifactError("Model input schema does not match its saved feature columns.")
        scaler = loaded["agent7_archetype_scaler.joblib"]
        archetype = loaded["agent7_archetype_kmeans.joblib"]
        if list(scaler.feature_names_in_) != CLUSTER_COLUMNS or archetype.n_features_in_ != len(CLUSTER_COLUMNS):
            raise ArtifactError("Archetype input schema is incompatible.")
        return Bundle(classifier, regressor, columns, archetype, scaler)
    except ArtifactError:
        raise
    except Exception as exc:
        raise ArtifactError(f"Cannot load verified Agent 7 bundle from {directory}: {exc}") from exc


def score_extracurricular(candidate: dict, *, model_dir: str | Path | None = None) -> dict:
    clean = validate_candidate(candidate)
    directory = MODEL_DIR if model_dir is None else Path(model_dir).expanduser().resolve()
    bundle = _load_verified(str(directory))
    raw = pd.DataFrame([clean])
    encoded = feature_frame(raw)
    if list(encoded.columns) != bundle.columns:
        raise ArtifactError("Inference feature construction differs from training; refusing silent zero filling.")
    probabilities = bundle.classifier.predict_proba(encoded)[0]
    predicted = int(bundle.classifier.predict(encoded)[0])
    score = float(bundle.regressor.predict(encoded)[0])
    if not np.isfinite(probabilities).all() or not np.isfinite(score) or not np.isclose(probabilities.sum(), 1, atol=1e-5):
        raise ArtifactError("Model returned invalid predictions.")
    cluster = int(bundle.archetype.predict(bundle.scaler.transform(raw[CLUSTER_COLUMNS]))[0])
    return {
        "strength_tier": {0: "Weak", 1: "Moderate", 2: "Strong"}[predicted],
        "profile_strength_score": round(float(np.clip(score, 0, 100)), 1),
        "P(Strong)": round(float(probabilities[list(bundle.classifier.classes_).index(2)]), 6),
        "achievement_archetype": str(cluster),
        "has_research_evidence": int(clean["publication_count"] > 0 or clean["patent_count"] > 0),
    }


def agent7_output_to_state(candidate: dict, sop_text: str | None = None,
                           target_university: str | None = None, target_program: str | None = None,
                           program_description: str | None = None, *, model_dir=None,
                           embed_model=None, groq_llm=None, sop_weight=.20) -> dict:
    """Return independent output; never writes into another agent's state."""
    base = score_extracurricular(candidate, model_dir=model_dir)
    context = (sop_text, target_university, target_program, program_description)
    if all(v is None for v in context):
        return {**base, "sop_score": None}
    if any(v is None for v in context):
        raise ValueError("SOP evaluation requires text, university, program and description together.")
    result = score_sop(sop_text, target_university, target_program, program_description,
                       embed_model=embed_model, groq_llm=groq_llm)
    return {**combine_scores(base, result, sop_weight), "sop_evaluation": result}


def agent7_full_pipeline(*args, **kwargs):
    raise ArtifactError(
        "Full resume processing is unavailable: the original complete NER bundle, resume corpus, "
        "keyword thresholds and verified patent data are missing/unverified. "
        "Use score_extracurricular with documented structured evidence; do not invent missing scores."
    )


def main():
    parser = argparse.ArgumentParser(description="Score documented Agent 7 inputs from a JSON file.")
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    value = json.loads(args.input_json.read_text(encoding="utf-8"))
    candidates = value if isinstance(value, list) else [value]
    print(json.dumps([score_extracurricular(c, model_dir=args.model_dir) for c in candidates], indent=2))


if __name__ == "__main__":
    main()
