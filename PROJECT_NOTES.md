# Project understanding and ongoing notes

Last updated: 2026-10-07

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

## Frontend branch integration (2026-10-07)

- Active branch: `jalaja-backend`. The user requested frontend integration here before moving it to `main`.
- `origin/meridian-redesign` has unrelated Git history; its frontend files match the staged local frontend before a whitespace cleanup.
- Integrate frontend source, assets, Reflex configuration, root requirements, ignore rules, and these notes with a scoped commit on `jalaja-backend`.
- Leave pre-existing backend/legacy-page deletions and generated `reflex.lock` changes outside this commit. No push or main-branch change is part of this step.
- Python syntax parsing passed for all 26 Meridian/configuration Python files. Runtime behavior remains unverified.

## Open questions

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
