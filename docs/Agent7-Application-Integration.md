# Agent 7 application integration

Verified locally on 2026-10-08. Application integration only: no training,
Agent 2 integration, artifact replacement, or Git operations.

## Running result

Open **http://localhost:3000/results** in the test browser window already opened.
Its profile is explicitly named **TEST PROFILE - Agent 7 integration**. Another
browser/session must submit its own inputs; results are session-specific.

The real test result is:

| Output | Value |
| --- | --- |
| Profile Strength | 55.4 / 100 |
| Strength Tier | Moderate |
| P(Strong) | 0.156443 |
| Achievement Archetype | Cluster 1 |
| Research Evidence | Yes (reported publication count is 3) |

These are predictions for a deliberately constructed software test profile,
not accuracy measurements. P(Strong) is the synthetic rubric's Strong-class
probability, **not admission probability**. Real-world accuracy is unknown.

## Data flow and interface

1. The existing Experience section collects eight blank-by-default inputs.
2. The final **Continue to documents** button validates them and invokes
   `Agent7Service.score_profile(profile)` through Reflex's server-side event
   interface. No new REST server is required.
3. The service starts the configured Python interpreter as an isolated JSON
   stdin/stdout worker. It passes only the eight allowed model fields.
4. The worker calls the existing, unchanged `score_extracurricular()` with an
   absolute path to `backend/app/agents/extracurricular_agent/trained_models/`.
   The existing loader verifies dependency versions, artifact hashes, types
   and feature ordering. No training code is invoked.
5. The real result is stored in the user's Reflex session. The analysis flow
   uses that result; direct entry to analysis scores validated inputs if needed.
   Mock Agent 7 completion events are excluded. Agents 1–6 retain their existing
   demonstration flow, explicitly labelled as such in the UI.
6. The results cover, Profile Strength section, Extracurricular section,
   printable report and downloadable PDF use the same result.

Editing any profile field invalidates the previous result. Missing/invalid
inputs or an unavailable model runtime produce an error, not a substitute
score. An edit during analysis prevents the old snapshot from being published.

## Fields added (all eight were missing as structured inputs)

| MERIDIAN field | Model field | Validation |
| --- | --- | --- |
| leadership_score | leadership_score | finite number, 0–10 |
| research_score | research_score | finite number, 0–10 |
| competition_score | competition_score | finite number, 0–10 |
| volunteering_score | volunteering_score | finite number, 0–10 |
| publication_count | publication_count | integer, 0–2147483647 |
| patent_count | patent_count | integer, 0–2147483647 |
| agent7_degree_level | degree_level | Bachelors / Masters / PhD-applicant |
| agent7_field | field | STEM / Business / SocialSci / Arts / Other |

The existing free-text degree, study field, research and project descriptions
are preserved. They are not parsed to invent model inputs. Separate category
selectors avoid overwriting the existing study field. Unknown values remain
blank and block scoring; an explicit zero means known absence. Numeric inputs
preserve raw text because Reflex's number control otherwise converts blank to
zero; range validation runs server-side.

Test inputs: leadership 6, research 9, competition 5, volunteering 4,
publication count 3, patent count 0, degree Masters, field STEM.

## Start again

This machine has Reflex in Python 3.14 and the verified Agent 7 dependencies
in Python 3.13. From the repository root in PowerShell:

```powershell
$env:MERIDIAN_AGENT7_PYTHON = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
python -B -m reflex run --frontend-port 3000 --backend-port 8000 --backend-host 127.0.0.1
```

The environment variable selects the model interpreter; it is not a hardcoded
user path in application code. If omitted, the service uses the app's interpreter,
which must have the exact versions in Agent 7's existing `requirements.txt`.
No packages were installed or upgraded for this integration.

For this restricted session, the normal Reflex command attempted an unnecessary
frontend package installation. The current preview instead uses the already
installed packages: the current app was compiled with only the package-install
step skipped, then these two processes were started:

```powershell
# Repository root, with MERIDIAN_AGENT7_PYTHON set as above
python -B -m reflex run --backend-only --backend-port 8000 --backend-host 127.0.0.1
```

```powershell
# Separate terminal, from .web
node node_modules/@react-router/dev/bin.cjs dev --host 127.0.0.1 --port 3000
```

The model service and prediction outputs were not mocked during verification.

## Verification

- Five Python integration tests passed, including missing/invalid fields,
  ignoring externally supplied profile scores, missing runtime failure,
  real submission from a foreign working directory, PDF generation,
  result invalidation, and a second real profile producing a different result.
- Browser check passed: blank fields rejected → complete test profile submitted
  → real inference → analysis completed → all five outputs rendered → printable
  report consistent → result preserved after page refresh.
- A second low-activity test produced Weak / 3.5, demonstrating that the displayed
  result is not a fixed value. This is a functional test, not an accuracy claim.
- SHA-256 comparison: all 98 protected backend, dataset, asset, theme and globe
  files were unchanged.

Re-run the inference-only Python tests with the interpreter variable set:

```powershell
python -B -m unittest discover -s tests -p test_agent7_integration.py -v
```

The browser test uses Node's built-in DevTools client, the running app and a
dedicated Chrome test window with debugging enabled on local port 9222. It
submits form events, not fabricated server-side results:

```powershell
node tests/agent7_browser_check.cjs
```

Saved browser evidence: `reports/agent7-integration-browser.json` and
`reports/agent7-integration-test.png`.

## Exact file changes

Added:

- `meridian/services/agent7.py` — application service, explicit input mapping, error handling.
- `meridian/services/agent7_worker.py` — isolated invocation of the unchanged scorer.
- `tests/test_agent7_integration.py` — service, state, real inference and PDF tests.
- `tests/agent7_browser_check.cjs` — actual browser-flow verification.
- `docs/Agent7-Application-Integration.md` — this integration record and run instructions.
- `reports/agent7-integration-browser.json` — browser test evidence.
- `reports/agent7-integration-test.png` — screenshot of the running result.

Modified:

- `meridian/data/mock.py` — only the profile defaults/schema: eight empty input fields.
- `meridian/state.py` — scoring, validation, session result, stale-result handling and PDF data.
- `meridian/pages/profile.py` — existing controls, required-input explanation and error/loading state.
- `meridian/pages/documents.py` — clarify that documents are not parsed by this integration.
- `meridian/pages/analysis.py` — live/demo distinction and scoring-error recovery link.
- `meridian/pages/results.py` — real cover score and live/demo distinction.
- `meridian/pages/report.py` — real report-cover score and live/demo distinction.
- `meridian/components/results_sections.py` — five real outputs and interpretation text.
- `meridian/services/report_pdf.py` — include the Agent 7 interpretation and demo scope.

Reflex also regenerates `.web/` build output and `.states/` local session files
when compiling/running. These are runtime outputs, not model or design changes.

Unchanged: all backend source and models (including Agents 1, 2 and 7), training
notebooks, datasets, artifact manifests, requirement files, Streamlit files,
`rxconfig.py`, theme/CSS, animation JavaScript, 3D/globe source and assets. No Git
commands were run and nothing was pushed.

## Remaining limitations

- Inputs are supplied by the student; this integration does not independently
  verify achievements or derive calibrated activity scores from resumes.
- Resume/NER extraction and SOP/LOR scoring are not connected. Uploads do not
  influence the structured Agent 7 score in this flow.
- Archetypes are numeric cluster identifiers, not validated descriptive ranks.
- Research Evidence means publication_count > 0 or patent_count > 0 according
  to the existing scorer, even if a research activity score was supplied.
- Synthetic training labels do not establish real admissions accuracy.
- Agent 2 remains disconnected; other application recommendations are still
  demonstration content, not predictions based on this Agent 7 result.
- Cold worker startup adds a few seconds per fresh submission; the verified
  result is reused during that profile's analysis flow.
