# Project understanding and ongoing notes

Last updated: 2026-10-13

Latest assessment: Agent 2's integration is functional, but its admission estimates and Safe/Target/Reach labels are not validated for real applicants. See [Agent 2 quality review](docs/Agent2-Quality-Review.md). Earlier sections below retain historical observations.

## Profile submission navigation fix (2026-10-13)

- User reported a repeating section loop. Confirmed that final submission errors automatically selected Experience, changing the CTA back to Next section.
- Submission failures now retain the current section and show a prominent error with a Review Experience fields action. After the first submission attempt, Continue to documents remains available from any section, so corrected inputs can be submitted directly.
- Required Agent 7 evidence is still validated; missing values are not fabricated. Runtime failures also stay on the current section. Six Agent 7 regression tests passed and Reflex pages compiled.
- Restarted the local servers to activate the updated backend. Browser regression passed: blank research score displays an error without leaving Programs; correcting it in Experience submits directly to Documents using real Agent 7. Reproduce with `$env:PROFILE_NAV_ONLY='1'; node tests/agent2_browser_check.cjs`.

## Purpose of this file

Keep a running record of what I understand about this project, confirmed decisions, changes made, and open questions. Update this file as we work, keeping confirmed facts separate from assumptions. This is the initial snapshot, not a full project audit.

## Current understanding

- The project is called **Study Abroad AI** in the README and frontend.
- Its stated purpose is to predict study-abroad program suitability and match students with universities using their profile data.
- The intended flow is: enter a student profile, request an MS or MBA prediction, then review university recommendations.
- The frontend uses Streamlit. Its entry point is `frontend/streamlit_app.py`.
- The backend requirements and remaining route implementations use FastAPI. The frontend still describes the backend as Flask; this wording is inconsistent.
- `frontend/utils/api_client.py` calls the backend at `http://localhost:5000` with requests for `/health`, `/predict/ms`, `/predict/mba`, and `/match`.
- Prediction code validates profile inputs, normalizes GPA, and loads an MS or MBA model with joblib. It returns a prediction and, when supported, a probability.
- Backend dependencies include scikit-learn, pandas, joblib, SQLAlchemy, and pytest. Frontend dependencies include Streamlit, requests, and pandas.
- Existing documentation lives in `docs/`, including architecture, features, flow, decisions, constraints, bugs, roadmap, and a test checklist. Their contents have not yet been reviewed.

## Current workspace observations

- The user described this as a fresh set and requested a Markdown file that will be updated as understanding grows.
- IDE tabs mention the Profile Form and About pages, but Git currently reports all three frontend page files as deleted from the working tree.
- Git also reports several backend files as deleted, including the app entry point, configuration, database files, and matching implementation. The reason for these deletions is unknown; they have not been restored or changed.
- The existing health test uses Flask-style `test_client()` calls, while the remaining route code uses FastAPI. Test compatibility needs checking if implementation work is requested.
- No application or tests have been run during this initial documentation task. Runtime behavior and model availability are unverified.

## Confirmed decisions and preferences

- Maintain this file as ongoing project context during future work in this workspace.
- The current request is to document understanding; no application changes were requested.

### Subsequent preferences and scope (2026-10-08)

- The user runs all Git commands; provide suitable commands when requested and do not execute them.
- Ask before running other commands unless already authorized for the current task. Read user attachments directly without asking.
- Integrate model updates with Meridian on `jalaja-backend`. Do not merge or push to `main`.
- The user confirmed that the listed legacy backend/Streamlit files are intentionally unwanted. Their deletions should be considered alongside replacement backend integration, because remaining imports still depend on some deleted modules.

## Frontend branch integration (2026-10-07)

- Active branch: `jalaja-backend`. The user requested frontend integration here before moving it to `main`.
- `origin/meridian-redesign` has unrelated Git history; its frontend files match the staged local frontend before a whitespace cleanup.
- Integrate frontend source, assets, Reflex configuration, root requirements, ignore rules, and these notes with a scoped commit on `jalaja-backend`.
- Leave pre-existing backend/legacy-page deletions and generated `reflex.lock` changes outside this commit. No push or main-branch change is part of this step.
- Python syntax parsing passed for all 26 Meridian/configuration Python files. Runtime behavior remains unverified.

## Open questions

- Where are the four missing updated Agent 2 exports and the three financial-agent exports?
- Can the original Agent 7 artifacts be recovered? Several uploaded files have contents inconsistent with their names.
- Are Agent 1's `admit_probability` and `admission_status` legitimate inference-time features or outcome leakage?
- What implementations/data should support Scholarship and Career agents?

## Model integration audit (2026-10-08)

- The user merged `origin/asmm` into `jalaja-backend` and restored the older `trained_models_A2` folder before committing. The provided status subsequently showed the branch seven commits ahead of `origin/jalaja-backend`.
- The user applied `stash@{0}` with `--index`: intentional legacy-file deletions and `reflex.lock/package.json` were restored as staged changes, and `reflex.lock/package-lock.json` remained untracked. The stash backup was retained. These are user-supplied status observations, not newly executed Git checks.
- Read-only inspection found Agent 1 artifacts, an incomplete new Agent 2 export set, Agent 3/4 references to a removed dataset, missing financial exports, and suspiciously named/typed Agent 7 uploads.
- No models were loaded or predictions tested. No Git commands were run during the audit.
- Created `docs/Model-Artifact-Audit.md` with artifact gaps, notebook input contracts, compatibility limitations, and implementation priorities.
- Meridian remains connected to mock services and static result constants. Real backend integration is outstanding.

- Are the current file deletions intentional as part of the fresh setup?
- What student inputs, datasets, and recommendation rules should the completed application support?
- Which existing documentation reflects the intended current direction?

## Update log

- **2026-10-07:** Created this file after reviewing the root README, documentation index, frontend entry point and API client, dependency files, backend prediction and matching routes, prediction implementation, health test, and Git status.

## Meridian frontend review (2026-10-07)

- The newer frontend is a Python Reflex app under `meridian/`, configured by `rxconfig.py`. The earlier Streamlit description above covers the legacy scaffold, not this newer frontend.
- Routes cover landing, profile, documents, analysis, results, and printable report. Branding uses an ivory/navy/blue dossier and travel-document theme.
- Existing visual effects include a Three.js globe, layered desk parallax, card tilt, scroll reveals, custom cursor, and a dossier opening transition. `assets/scene.js` includes lazy loading, offscreen rendering checks, capped pixel ratio, and reduced-motion handling.
- Service factories currently return `MockEventSource` and `MockReportService`. The event source emits timed progress rather than actual analysis. Most report sections come from shared mock constants; profile edits personalize identifying fields without recomputing recommendations.
- Uploaded files are saved, but the reviewed agent workflow receives only the profile dictionary, not document contents. Real document extraction and analysis remain integration work.
- Profile continuation has no validation gate in the reviewed state handler. Completion measures nonempty fields. Sample profile values are used by default.
- Results section navigation contains a mismatched anchor: the index links to `#extracurricular-strength`, but the section generates `#extracurricular`.
- Profile layout sets two columns inline; verify whether that overrides the responsive `.split` rule on small screens. No browser-based visual or mobile verification was performed in this review.
- Provisional code-based assessment: design direction 7/10; functional product readiness 3/10. These are subjective review scores, not a predicted academic grade.
- Recommended priorities: real profile-dependent results and document processing; validation, persistence, error/retry states; trustworthy source-backed explanations; then mobile polish and purposeful 3D interaction.
- Recommended 3D direction: retain the dossier theme, simplify repeated globes, turn university selection into a useful globe interaction paired with accessible controls, and animate agent outputs only when real backend events arrive.
- Academic preparation should include reproducible setup, dataset provenance, baseline comparisons, evaluation metrics, documented limitations, and a reliable live demonstration. The institution's actual marking rubric has not been provided.

## Agent 2 application connection (2026-10-12)

- The user requested progressing with remaining-agent integration, beginning with Agent 2. Necessary inspection, implementation and scoped verification were authorized by this request. No Git commands were run.
- Added an isolated updated-bundle Agent 2 service and worker. The updated artifacts specify five features; the older nineteen-feature bundle is not substituted or mixed in. No training, dependency installation or model replacement was performed.
- The user confirmed no other local folder contains the four missing updated exports. Agent 2 remains unavailable: admission model, SHAP explainer, applicant clustering medians and applicant feature list are absent.
- Existing updated clustering artifacts record scikit-learn 1.6.1; the current Python 3.13 model runtime has 1.7.2 and lacks SHAP. Activation requires a compatible separate runtime and a coherent complete export set.
- Analysis ignores sample Agent 2 completion events, reports unavailable explicitly and allows the real Agent 7 dossier. Sample university recommendations, probabilities, counts and factors have been removed from results, printable reports and state-generated PDFs. Other agent sections remain labeled demonstrations.
- Profile edits invalidate both results; edits during scoring/analysis reject stale outputs. Results and PDF university data use the same session result.
- Six Agent 2 application tests, two real-catalog retrieval tests, five real Agent 7 regression tests, and compilation of all six Reflex pages passed. Agent 2 successful-output tests use contract fixtures; no real Agent 2 prediction or new browser verification was possible.
- Corrected the legacy matching route import to the existing university matching module. The legacy matcher remains a heuristic; no deleted backend entry point or unwanted Streamlit files were restored.
- Handoff, limitations, checks and activation requirements: `docs/Agent2-Application-Integration.md`. Existing Agent 2 artifact/catalog hashes: `reports/agent2-existing-inputs.sha256.json`.
- Remaining work: restore or separately train/evaluate a coherent Agent 2 bundle and verify real inference; resolve Agent 1 provenance, Agent 3 resources, missing Agent 4 exports, Scholarship/Career implementations and document extraction.

## Agent 2 live activation (follow-up)

- The user clarified that no new files had been uploaded and explicitly authorized running the notebook as needed, completing integration and running the frontend.
- Installed an isolated project-local `.venv-agent2` with pinned ML/notebook dependencies. Agent 7 continues using its existing verified Python 3.13 environment.
- Executed a local production adaptation of the original Agent 2 notebook: eleven code cells, including fresh clustering, GradientBoosting fitting, calibration, held-out evaluation, SHAP and all fourteen exports. The original notebook's selected features and recorded model parameters were reused; cloud cells and historical model searches were not rerun.
- Fixed the original notebook's training/validation overlap in the local run: 10,232 fit rows, 2,558 validation rows and 3,198 test rows. Local row-holdout accuracy is 0.8727; this does not establish real admissions or unseen-student accuracy because dataset provenance/identity issues remain unresolved.
- The active complete bundle is now `backend/app/agents/university_matching_agent/trained_models_local/`. Its manifest binds hashes, schema, dependencies and input data to this run. The loader handles SHAP's feature names on the saved masker and validates the explained model's feature/class order.
- Original uploaded updated artifacts, source notebook and catalog were checked unchanged. No Git operations were run.
- Sixteen scoped Python tests passed, including three tests using the actual exported Agent 2 bundle. Browser verification passed for real form submission through Agents 7 and 2, ten displayed recommendation rows, printable report/PDF, stale-result invalidation, changed GPA producing different predictions, and session refresh.
- Evidence and the executed notebook are in `reports/agent2-local/`; the current handoff is `docs/Agent2-Application-Integration.md`.
- The frontend is running at `http://localhost:3000` with backend port 8000. Restart using `./scripts/start_meridian.ps1`; process IDs and logs are in `.runtime/`. A fresh browser session must submit its own profile.
- Agent 2's previous missing-export/runtime blockers are resolved for the new local bundle. The original uploaded five-feature folder is still incomplete and is not the active bundle. Agents 1, 3, 4, 5 and 6 remain demonstration content; document extraction is still unconnected.

## Agent 2 quality audit (2026-10-13)

- User authorized reviewing labels, leakage, calibration and thresholds. Added and executed `scripts/audit_agent2_quality.py`; evidence is in `reports/agent2-quality/` and conclusions in `docs/Agent2-Quality-Review.md`.
- Verified active artifact/data hashes, reproduced saved test metrics, measured calibration and permutation importance, and ran 70 controlled GPA/GRE scenarios. Production model, application behavior and training data were unchanged; no Git commands were run.
- Fit/test rows are disjoint, but 793 applicant IDs overlap, affecting 929/3,198 test rows. All 1,800 repeated-ID groups have differing GPA/GRE values. Independent student generalization remains unverified.
- GRE dominates prediction. At GPA 3.36/4, MIT estimates are 92.0%, 3.5% and 98.9% for GRE 155, 160 and 165 respectively. Missing GRE produces 98.0% despite no training examples with missing GRE.
- Row-holdout Brier error is 0.08445 and 10-bin calibration error 0.02530. These characterize the supplied labels, not real admission chances. No direct outcome columns enter the active five-feature model; outcome/augmentation provenance remains unresolved.
- Website category cutoffs 0.35/0.65 are hardcoded and independent of the fitted binary decision threshold 0.42. Retuning these cutoffs alone cannot repair the observed prediction behavior.
- Recommended next work: neutral experimental score presentation and explicit unsupported-input handling, followed by provenance repair and independent grouped/temporal validation before a replacement model is promoted.

## Agent 2 experimental score presentation (2026-10-13)

- User authorized the first corrective step. Results and printable/PDF reports now label percentages as unvalidated model scores and use Higher/Middle/Lower experimental bands instead of Safe/Target/Reach. The notice explains band boundaries and distinguishes catalog match scores from admission chances.
- Missing GRE or GRE outside the verified training range (154.5769–168.8004; accepted integer scores 155–168) produces Insufficient evidence with a reason, no model percentage, and no SHAP explanation. Catalog matches remain available. The range is read from training data after checking its manifest hash.
- Old persisted result contracts cannot render or be reused; analysis must recompute them. The dashboard counts schools with scores rather than target schools.
- Eleven scoped application/live-model checks passed, covering supported scores, missing/out-of-range GRE, invalid result rejection, stale results and PDF generation. All Reflex pages compiled. No trained artifacts or dataset values were changed.
- Full browser verification passed with 11 recorded checks, including experimental labels, missing-GRE results and the unsupported-input printable report. Screenshots: `reports/agent2-local/frontend-results.png` and `frontend-insufficient-evidence.png`. The test now starts a fresh dedicated session and waits for reload/score animations before asserting results.
