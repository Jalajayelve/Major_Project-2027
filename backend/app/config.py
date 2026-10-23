import os
from pathlib import Path


class Config:
    MODEL_DIR = os.environ.get("MERIDIAN_MODEL_DIR", str(Path(__file__).parent / "agents/profile_agent/trained_models_A1"))
