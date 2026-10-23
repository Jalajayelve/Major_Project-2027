import math


def normalize_gpa(record):
    """Accept explicit scales; never guess or silently clamp an academic score."""
    if not isinstance(record, dict):
        raise ValueError("Profile payload must be a dictionary.")

    gpa = record.get("gpa")
    if gpa is None:
        raise ValueError("GPA is required.")

    gpa = float(gpa)
    scale = float(record.pop('gpa_scale', 4))
    if scale not in (4, 10, 100) or not math.isfinite(gpa) or not 0 <= gpa <= scale:
        raise ValueError('GPA must be within its explicit scale (4, 10 or 100); the default scale is 4.')
    record["gpa"] = round(gpa / scale * 4, 3)
    return record


def validate_profile_input(payload, program_type):
    """Validate the required fields for MS or MBA prediction."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object for the profile payload.")
    payload = dict(payload)

    required = ["gpa", "gre_score", "toefl_score", "research_experience", "work_experience"]
    if program_type == "mba":
        required = ["gpa", "gmat_score", "work_experience", "essay_score"]

    missing = [key for key in required if key not in payload or payload[key] in (None, "")]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    for key in required:
        if key in payload:
            try:
                if isinstance(payload[key], bool):
                    raise ValueError()
                payload[key] = float(payload[key])
                if not math.isfinite(payload[key]):
                    raise ValueError()
            except (TypeError, ValueError):
                raise ValueError(f"Field '{key}' must be numeric.")

    limits = {'gre_score': (260, 340), 'toefl_score': (0, 120), 'gmat_score': (200, 800),
              'research_experience': (0, math.inf), 'work_experience': (0, math.inf)}
    for key, (low, high) in limits.items():
        if key in required and not low <= payload[key] <= high:
            raise ValueError(f"Field '{key}' is outside its supported range.")

    return payload
