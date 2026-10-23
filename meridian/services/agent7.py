"""Application boundary for the verified Agent 7 bundle (inference only).

Set MERIDIAN_AGENT7_PYTHON to the interpreter with Agent 7's pinned packages
when Reflex runs in a different environment. No shell, network, or training.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys

SCORE_FIELDS = ("leadership_score", "research_score", "competition_score", "volunteering_score")
COUNT_FIELDS = ("publication_count", "patent_count")
PROFILE_KEYS = SCORE_FIELDS + COUNT_FIELDS + ("agent7_degree_level", "agent7_field")
MODEL_DIR = Path(__file__).resolve().parents[2] / "backend/app/agents/extracurricular_agent/trained_models"
NOTICE = ('P(Strong) is the probability of Agent 7\'s synthetic "Strong" class, '
          'NOT admission probability. Training uses synthetic rubric labels; '
          'real-world admissions accuracy is unknown / not validated.')


class Agent7Unavailable(RuntimeError):
    """The verified scoring environment could not return a valid result."""


def candidate_from_profile(profile: dict) -> dict:
    """Require explicit values; never infer scores from text or defaults."""
    missing = [k for k in PROFILE_KEYS if not str(profile.get(k, "")).strip() or profile.get(k) is None]
    if missing:
        raise ValueError("Complete Agent 7 fields in Experience: " + ", ".join(missing) +
                         ". Unknown values must stay blank; enter 0 only when you know the value is zero.")
    candidate = {}
    for key in SCORE_FIELDS + COUNT_FIELDS:
        try:
            value = float(profile[key])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{key} must be a number.") from exc
        if isinstance(profile[key], bool) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{key} must be a finite, nonnegative number.")
        if key in SCORE_FIELDS and value > 10:
            raise ValueError(f"{key} must be between 0 and 10.")
        if key in COUNT_FIELDS and (not value.is_integer() or value >= 2**31):
            raise ValueError(f"{key} must be a whole number from 0 to {2**31 - 1}.")
        candidate[key] = int(value) if key in COUNT_FIELDS else value
    for key, choices in {"degree_level": ("Bachelors", "Masters", "PhD-applicant"),
                         "field": ("STEM", "Business", "SocialSci", "Arts", "Other")}.items():
        value = profile[f"agent7_{key}"]
        if value not in choices:
            raise ValueError(f"Agent 7 {key} must be one of: {', '.join(choices)}.")
        candidate[key] = value
    return candidate


class Agent7Service:
    def score_profile(self, profile: dict) -> dict:
        candidate = candidate_from_profile(profile)
        local = Path(__file__).resolve().parents[2] / '.venv-agent7' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        executable = os.environ.get("MERIDIAN_AGENT7_PYTHON") or (str(local) if local.is_file() else sys.executable)
        worker = Path(__file__).with_name("agent7_worker.py")
        try:
            completed = subprocess.run(
                [executable, "-B", str(worker)], input=json.dumps(candidate),
                text=True, encoding="utf-8", capture_output=True, timeout=60,
                cwd=worker.parent, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=True,
            )
            result = json.loads(completed.stdout)
            expected = {"strength_tier", "profile_strength_score", "P(Strong)",
                        "achievement_archetype", "has_research_evidence"}
            if set(result) != expected or result["strength_tier"] not in ("Weak", "Moderate", "Strong"):
                raise ValueError("Unexpected Agent 7 result schema")
            for key, maximum in (("profile_strength_score", 100), ("P(Strong)", 1)):
                value = result[key]
                if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= maximum:
                    raise ValueError("Invalid Agent 7 result value")
            if not isinstance(result["achievement_archetype"], str) or type(result["has_research_evidence"]) is not int or result["has_research_evidence"] not in (0, 1):
                raise ValueError("Invalid Agent 7 evidence/archetype")
            return result
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError) as exc:
            raise Agent7Unavailable(
                "Agent 7 could not load or score with its verified bundle. Check MERIDIAN_AGENT7_PYTHON "
                "and Agent 7's pinned requirements; no substitute score was generated."
            ) from exc
