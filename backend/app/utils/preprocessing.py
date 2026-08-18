def normalize_gpa(record):
    """Normalize GPA from 0-10 scale into a 0-4 scale if needed."""
    if not isinstance(record, dict):
        raise ValueError("Profile payload must be a dictionary.")

    gpa = record.get("gpa")
    if gpa is None:
        raise ValueError("GPA is required.")

    gpa = float(gpa)
    if gpa > 4.0:
        gpa = gpa / 10.0
    record["gpa"] = round(max(0.0, min(4.0, gpa)), 3)
    return record


def validate_profile_input(payload, program_type):
    """Validate the required fields for MS or MBA prediction."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object for the profile payload.")

    required = ["gpa", "gre_score", "toefl_score", "research_experience", "work_experience"]
    if program_type == "mba":
        required = ["gpa", "gmat_score", "work_experience", "essay_score"]

    missing = [key for key in required if key not in payload or payload[key] in (None, "")]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    for key in required:
        if key in payload:
            try:
                payload[key] = float(payload[key])
            except (TypeError, ValueError):
                raise ValueError(f"Field '{key}' must be numeric.")

    return payload
