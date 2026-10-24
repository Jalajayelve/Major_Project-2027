"""Pinned-environment worker for Agent 5 artifact deserialization."""
import json
import os
import sys

from .scholarship import analyze_scholarships


def main() -> int:
    os.environ["AGENT5_WORKER"] = "1"
    payload = json.load(sys.stdin)
    json.dump(analyze_scholarships(payload), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
