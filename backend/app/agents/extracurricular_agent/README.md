# Agent 7: repaired standalone scoring

This component scores documented extracurricular evidence and optionally evaluates SOP text. It does not integrate with another agent. Its models learn the original notebook's **synthetic rubric**, not real admission outcomes.

## Run

Use Python 3.13 with the versions in this folder's `requirements.txt`. The repair was verified with the already installed environment at `C:\Users\Naresh Yelev\AppData\Local\Programs\Python\Python313\python.exe`; default Python 3.14 lacks the required ML packages.

From the project root:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -B -m backend.app.agents.extracurricular_agent.predict --input-json backend/app/agents/extracurricular_agent/example_applicants.json
```

In Python (with the project root on `sys.path` / `PYTHONPATH`):

```python
from backend.app.agents.extracurricular_agent.predict import score_extracurricular

result = score_extracurricular({
    "degree_level": "Masters", "field": "STEM",
    "leadership_score": 7.5, "research_score": 6.0,
    "competition_score": 4.0, "volunteering_score": 5.5,
    "publication_count": 1, "patent_count": 0,
})
```

The default model path is always resolved from `predict.py`, never the working directory. Core artifacts are cached per absolute model directory; restart the process if an independently rebuilt bundle is later installed.

## Input and output contract

- All eight fields are required. Extra fields, including externally supplied `profile_strength_score`, are rejected.
- Activity scores must be finite numbers from 0 to 10. Publication/patent counts must be nonnegative integers.
- `degree_level`: `Bachelors`, `Masters`, `PhD-applicant`.
- `field`: `STEM`, `Business`, `SocialSci`, `Arts`, `Other`.
- Returns `strength_tier`, `profile_strength_score`, `P(Strong)`, `achievement_archetype`, `has_research_evidence`.
- `P(Strong)` is confidence in a synthetic strength tier, not admission probability. Archetypes are output-only cluster IDs.

## SOP

`sop.score_sop(text, university, program, description)` runs offline structural and lexical heuristics. Its semantic alignment is `None` unless a real embedding provider is supplied. An LLM rubric is unavailable unless an explicit provider is supplied. No default provider or network call is used.

`predict.agent7_output_to_state` accepts the same documented candidate and optional SOP context. It returns output; it does not mutate another agent. `sop.combine_scores` keeps the core model's score/tier/probability and adds a separate heuristic `blended_profile_strength_score`.

Full resume extraction is unavailable without the original NER bundle and evidence/calibration data. `agent7_full_pipeline` raises a clear dependency error. There is no recovered dedicated LOR model. Do not fill missing structured evidence with guessed scores.

## Artifacts and validation

All five model/metadata joblibs and `manifest.json` live in `trained_models/`. The loader checks SHA-256, object types, feature order, labels and dependency versions. `repair_reports/REPAIR_REPORT.md` records exact files, old artifact problems, deterministic inputs and outputs, and fresh-process tests.

The existing notebook and legacy `joblibs/` directory are preserved as historical material. Use the Python module above for repaired inference; the old notebook's scoring cell is not the repaired entry point.

`repair.py` extracted the notebook's original generator and classifier settings, rebuilt into a new candidate directory, verified it in an independent process, and promoted only that new directory. It refuses to overwrite existing repair directories. It does not train Agent 1/2 or read their data. It does not run Git commands.
