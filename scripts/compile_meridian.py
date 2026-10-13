"""Compile using the already installed frontend packages for a local preview."""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if not (ROOT / ".web/node_modules/@react-router/dev/bin.cjs").is_file():
    raise SystemExit("Frontend packages are missing. Run the normal Reflex setup first.")

from meridian.meridian import app

# Only dependency installation is skipped; Reflex still compiles the actual app.
with patch("reflex.utils.js_runtimes.install_frontend_packages"):
    app._compile()
print("Compiled Meridian with existing frontend packages.")
