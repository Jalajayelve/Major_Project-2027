# Agent 2 application integration

**Status: real Agent 2 and Agent 7 inference is running locally.**

As of 2026-10-13, Agent 2 percentages are presented as **unvalidated model scores**,
with Higher/Middle/Lower experimental bands. They are not admission odds or safety
categories. Missing GRE or GRE outside the verified training range displays
**Insufficient evidence**, retaining catalog matches without model scores or SHAP
factors. Results, printable reports and PDFs share this behavior. Previously saved
results require fresh analysis. See [quality review](Agent2-Quality-Review.md).

Open http://localhost:3000/profile. Results belong to each browser session;
complete and submit your profile, then start analysis. A new browser session
will not inherit the software test profile used for verification.

## What was activated

The user clarified that there were no additional uploads and authorized running
the notebook and completing the frontend integration. The original uploaded
five-feature bundle has ten of fourteen files, while the older model expects
nineteen features. To complete the integration, the notebook's production stages
were executed in an isolated environment and all fourteen artifacts were
exported together into a new directory:

`backend/app/agents/university_matching_agent/trained_models_local/`

The original notebook, uploaded artifacts and datasets were preserved. No Git
operations were performed. The app now defaults to the complete local bundle
and the project-local `.venv-agent2` interpreter. `MERIDIAN_AGENT2_PYTHON` can
override the interpreter; its versions must match the bundle manifest.

## Notebook execution and reproducibility

- Runner: `scripts/run_agent2_notebook.py`.
- Executed notebook: `reports/agent2-local/Agent2-Local-Execution.ipynb`.
- Eleven code cells executed successfully, including dataset loading, clustering,
  classifier fitting/calibration, evaluation, SHAP and export.
- Local adaptations are stated in the executed notebook. This is the local
  production path, not an execution of every Colab/cloud cell in the original.
- Reused the original notebook's selected five features, two applicant clusters,
  ten program clusters and recorded GradientBoosting settings: 300 trees,
  maximum depth 3, learning rate 0.1, random seed 42. Historical model comparison
  and hyperparameter searches were not repeated.
- Corrected the training/validation overlap in the original notebook. There are
  10,232 fitting rows, 2,558 validation rows and 3,198 test rows. Applicant
  preprocessing, classifier fitting and calibration use fitting rows only.
- SHAP explains the uncalibrated classifier's class-1 probability. Admission
  estimates come from the separately calibrated ensemble.
- `manifest.json` records all fourteen artifact hashes, dependency versions,
  feature order, model settings, source notebook/data hashes and evaluation.
- Exact installed packages: `backend/app/agents/university_matching_agent/requirements-local.txt`.
  Key versions are scikit-learn 1.6.1, numpy 2.2.6, pandas 2.2.3 and SHAP 0.48.0.

The local row-holdout accuracy was 0.8727, F1 0.7988, ROC-AUC 0.9339 and Brier
score 0.08445 at the validation-selected threshold 0.42. These describe the
supplied dataset only. Conflicting repeated applicant identities and unverified
provenance remain unresolved; these numbers do not establish real admissions
accuracy or generalization to completely unseen students.

Full metrics and split indices are in `reports/agent2-local/`. The runner refuses
to overwrite a completed local bundle. Inference never executes the notebook
or retrains a model.

## Application behavior

Agent 7 is scored during profile submission. Agent 2 receives the same profile
snapshot and the actual Agent 7 result during analysis. Its isolated worker
loads the complete local bundle and verifies hashes, runtime versions, feature
order, model types/classes, clustering and SHAP metadata before inference.

The input contract is:

- GPA with an explicit scale of 4, 10 or 100, normalized proportionally to 4.0.
- GRE Quant as an integer from 130 to 170, or blank for the notebook's missing
  GRE path. Clustering uses the saved training median when GRE is missing.
- Degree and field of study. Degree is a hard catalog filter; field text ranks
  candidates using offline TF-IDF cosine similarity.
- The actual Agent 7 profile strength from the session. A student-supplied
  admission probability, tier or replacement profile score is ignored.

The feature order is `tier_score`, `gpa_numeric`, `gre_numeric`, `gre_missing`,
`applicant_cluster`. Program tier is taken from the saved catalog; this does not
run Agent 1 live. Matching score combines text similarity, program tier, GPA
fit and Agent 7 strength. Agent 7 affects matching score, not the five-feature
admission estimate or its SHAP factors. The UI's Safe/Target/Reach categories
use the notebook's 0.65/0.35 cutoffs, independently of its binary evaluation
threshold. Catalog requirements and tuition are historical, not current-source
verification.

Results, printable reports and PDFs read the same session result. Profile edits
invalidate both agent results; edits during analysis reject stale snapshots.
Failures produce an explicit unavailable state without sample university
recommendations. Agent 7 remains usable if Agent 2 fails.

Agents 1, 3, 4, 5 and 6, including program, cost, scholarship and career sections,
remain demonstration content. Document extraction, cloud embeddings/reranking,
Groq explanations and Postgres persistence are not connected by this local run.
The legacy FastAPI matching route remains a separate heuristic and is not used
by Meridian's model-backed flow.

## Verification and evidence

- Six application contract/failure tests.
- Five Agent 7 regression tests, including real inference.
- Two actual catalog retrieval tests.
- Three new real-bundle tests: real Agent 7-to-Agent 2 inference for two GPAs,
  changed predictions, manifest failure handling and PDF result consistency.
- The successful real-inference results are saved in
  `reports/agent2-local/live-inference.json`; the original contract fixtures
  remain confined to unit tests.
- Browser verification uses `tests/agent2_browser_check.cjs` with real form
  events and compares displayed recommendations against actual worker results.
  Evidence is saved in `reports/agent2-local/browser-check.json`, desktop/mobile
  screenshots and the downloaded PDF.
- Compilation skips only the frontend package-install step because dependencies
  are already installed. No inference or browser results are mocked.
- Original uploaded updated-artifact/catalog hashes are checked against
  `reports/agent2-existing-inputs.sha256.json`.

## Start the app again

From the repository root in PowerShell, with no other app using ports 3000/8000:

```powershell
./scripts/start_meridian.ps1
```

This compiles the actual app, starts the Reflex backend on 8000 and frontend on
3000, and supplies the separate model interpreters. The script uses the verified
Python 3.13 installation for Agent 7; set `MERIDIAN_AGENT7_PYTHON` explicitly if
its location differs. Server logs and launch process IDs are under `.runtime/`.

To recreate the Agent 2 environment on this Windows machine:

```powershell
& "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe" -m venv .venv-agent2
& ./.venv-agent2/Scripts/python.exe -m pip install -r backend/app/agents/university_matching_agent/requirements-local.txt
```

To run checks:

```powershell
$env:MERIDIAN_AGENT7_PYTHON = "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe"
python -B -m unittest discover -s tests -p 'test_agent*_integration.py' -v
python -B -m unittest discover -s tests -p test_agent2_live.py -v
& ./.venv-agent2/Scripts/python.exe -B -m unittest discover -s tests -p test_agent2_catalog.py -v
# Requires the running app and a dedicated Chrome debugging session on port 9222:
node tests/agent2_browser_check.cjs
```
