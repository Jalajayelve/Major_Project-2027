"""Compatibility entry point for the minimal, audited Agent 7 bundle recovery."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[4] / 'scripts/prepare_agent7_bundle.py'), run_name='__main__')
