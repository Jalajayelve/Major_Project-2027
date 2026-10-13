"""Shared Agent 7 input validation and feature construction."""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

SCORES = ["leadership_score", "research_score", "competition_score", "volunteering_score"]
COUNTS = ["publication_count", "patent_count"]
CLUSTER_COLUMNS = SCORES + COUNTS
CATEGORIES = {
    "degree_level": ["Bachelors", "Masters", "PhD-applicant"],
    "field": ["STEM", "Business", "SocialSci", "Arts", "Other"],
}
REQUIRED_INPUTS = CLUSTER_COLUMNS + list(CATEGORIES)


def validate_candidate(candidate: Mapping) -> dict:
    if not isinstance(candidate, Mapping):
        raise ValueError("Candidate must be a mapping of the eight documented input fields.")
    missing = set(REQUIRED_INPUTS) - set(candidate)
    extra = set(candidate) - set(REQUIRED_INPUTS)
    if missing or extra:
        raise ValueError(f"Missing fields: {sorted(missing)}; unsupported fields: {sorted(extra)}")
    clean = {}
    for key in CLUSTER_COLUMNS:
        if isinstance(candidate[key], (bool, np.bool_)):
            raise ValueError(f"{key} must be numeric, not boolean.")
        try:
            value = float(candidate[key])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{key} must be a finite number.") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{key} must be finite and nonnegative.")
        if key in SCORES and value > 10:
            raise ValueError(f"{key} must be between 0 and 10.")
        if key in COUNTS and (not value.is_integer() or value > 2**31-1):
            raise ValueError(f"{key} must be a nonnegative integer below 2**31.")
        clean[key] = int(value) if key in COUNTS else value
    for key, allowed in CATEGORIES.items():
        if candidate[key] not in allowed:
            raise ValueError(f"{key} must be one of {allowed}.")
        clean[key] = candidate[key]
    return clean


def feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Same numeric, categorical and interaction features in training/inference.

    Archetypes are output-only, matching the notebook's training decision.
    Neither a supplied profile-strength score nor an outcome is accepted.
    """
    raw = frame[REQUIRED_INPUTS].copy()
    raw["has_research_evidence"] = ((raw["publication_count"] > 0) | (raw["patent_count"] > 0)).astype(int)
    for key, values in CATEGORIES.items():
        raw[key] = pd.Categorical(raw[key], categories=values)
    encoded = pd.get_dummies(raw, columns=list(CATEGORIES), dtype=float)
    encoded["publication_log"] = np.log1p(encoded["publication_count"])
    encoded["patent_log"] = np.log1p(encoded["patent_count"])
    encoded["total_activity"] = encoded[SCORES].sum(axis=1)
    encoded["achievement_mean"] = encoded[SCORES].mean(axis=1)
    encoded["research_publication_interaction"] = encoded["research_score"] * encoded["publication_log"]
    encoded["research_patent_interaction"] = encoded["research_score"] * encoded["patent_log"]
    encoded["leadership_volunteering_interaction"] = encoded["leadership_score"] * encoded["volunteering_score"]
    return encoded.astype(float)
