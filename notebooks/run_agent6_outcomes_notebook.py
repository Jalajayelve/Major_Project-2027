"""Execute the canonical Agent 6 notebook in order, preserving all source cells."""
from pathlib import Path

from execute_notebook import execute_notebook


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    execute_notebook(root / "backend/app/agents/career_agent/Agent6_Career_agent.ipynb")
