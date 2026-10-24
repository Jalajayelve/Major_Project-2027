"""Pinned-environment worker for Agent 6 artifact inference."""
import json
import sys

from career import analyze_career


if __name__ == "__main__":
    profile = json.loads(sys.stdin.read())
    print(json.dumps(analyze_career(profile), separators=(",", ":")))
