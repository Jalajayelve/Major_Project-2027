"""Private JSON stdin/stdout inference worker; run by Agent7Service only."""
from pathlib import Path
import json
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from backend.app.agents.extracurricular_agent.predict import score_extracurricular

    candidate = json.load(sys.stdin)
    result = score_extracurricular(
        candidate, model_dir=root / "backend/app/agents/extracurricular_agent/trained_models"
    )
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
