# Agent 7

The authenticated application integration and reproducible verification are documented in [the integration report](../../../../docs/Agent7-Application-Integration.md).

- `trained_models_A7/`: supplied artifacts, preserved unchanged despite incorrect filenames.
- `trained_models/`: verified operational bundle; four byte-for-byte recoveries and one rebuilt missing classifier, with manifest/provenance.
- `schema.py` / `predict.py`: strict structured inputs and inference.
- `repair.py`: explicit maintenance entry point for `scripts/prepare_agent7_bundle.py`; never called by the app.
- `verify_repair.py`: fresh-process, corruption, validation and SOP checks.

Use Python 3.11 with the pinned `requirements.txt` in an isolated environment. The application selects `.venv-agent7` or `MERIDIAN_AGENT7_PYTHON`. See the integration report for commands and limitations. Predictions reflect synthetic rubric labels, not validated admission probabilities.
