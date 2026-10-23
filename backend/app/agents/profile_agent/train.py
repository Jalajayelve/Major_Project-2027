import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier


def train_sample_model(csv_path: str, model_path: str, target_column: str = "admission_status"):
    """Placeholder training script for demo use. Replace with your real model pipeline."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training data not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")

    features = [col for col in df.columns if col != target_column]
    X = df[features]
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    return {"accuracy": float(model.score(X_test, y_test)), "model_path": model_path}


if __name__ == "__main__":
    train_sample_model(
        csv_path="data/raw/student_data.csv",
        model_path="backend/app/agents/profile_agent/trained_models/ms_model.pkl",
    )
