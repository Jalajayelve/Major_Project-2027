import os
import joblib
import pandas as pd

from app.config import Config
from app.utils.preprocessing import validate_profile_input, normalize_gpa


def _get_model_path(program_type: str):
    if program_type not in {"ms", "mba"}:
        raise ValueError(f"Unsupported program type: {program_type}")
    model_name = "ms_model.pkl" if program_type == "ms" else "mba_model.pkl"
    path = os.path.join(Config.MODEL_DIR, model_name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{model_name} is unavailable in {Config.MODEL_DIR}. "
            "The bundled *_tier_model.joblib artifacts are candidate-tier models "
            "with a different feature contract and cannot be used as MS/MBA outcome models."
        )
    return path


def predict_profile_outcome(payload, program_type: str):
    """Load trained model and return a prediction payload."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    validated = validate_profile_input(payload, program_type)
    cleaned = normalize_gpa(validated)

    model_path = _get_model_path(program_type)
    model = joblib.load(model_path)

    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None:
        dataframe = pd.DataFrame([cleaned], columns=feature_names)
        prediction = model.predict(dataframe)[0]
        probability = None
        if hasattr(model, "predict_proba"):
            probability = model.predict_proba(dataframe)[0].max()
        return {
            "program_type": program_type,
            "prediction": str(prediction),
            "probability": float(probability) if probability is not None else None,
            "input": cleaned,
        }

    dataframe = pd.DataFrame([cleaned])
    prediction = model.predict(dataframe)[0]
    return {
        "program_type": program_type,
        "prediction": str(prediction),
        "input": cleaned,
    }
