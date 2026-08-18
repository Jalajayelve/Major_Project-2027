import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///study_abroad_ai.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODEL_DIR = os.path.join(BASE_DIR, "agents", "profile_agent", "trained_models")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")


Config = Config()
