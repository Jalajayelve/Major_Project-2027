# Agent 5 executed answers

The complete delivered notebook is
`backend/app/agents/scholarship_agent/Agent5_Scholarship_agent.executed.ipynb`.
The original notebook changed concurrently after execution, so its latest edits
are preserved and the complete version is delivered separately.
All 13 code cells execute in a fresh Jupyter kernel and retain their outputs.
Its final cell displays a readable, dated funding plan with official source links.

The previous repeated `unknown` answers came from incomplete source data and
overly broad normalization: 9,405 of 9,673 catalog rows lack deadlines, only
18 rows state GPA scales, and none explicitly establish an annual award period.
Placeholder prose also triggered extra review, while country restrictions in
parentheses were discarded. The fixes retain explicit country/citizenship rules,
recognize Stanford graduate degree scope, avoid treating placeholders as extra
rules, and prioritize relevant, sourced records. Scholarships for unrelated
fields or unestablished partner/consortium programmes stay outside the shortlist.

The API retains its three-way eligibility decision for compatibility. Candidate
answers additionally include readable decisions, matching facts, funding details,
deadline information, source requirements and next steps. Dated official-source
corrections travel in `source_review`, update displayed/exported answers, and are
also retained in `reviewed_opportunities`. They apply only to the matching demo
profile and assessment date; they are not a live provider API or general rules.

The explicitly illustrative Indian MS Computer Science / Stanford profile is
assessed on 23 October 2026. Its annual USD 30,000 funding gap remains unchanged
until awards are confirmed. The official guide identifies Knight-Hennessy's
closed 2027 cycle, Aga Khan's next-cycle preparation, J N Tata's loan-scholarship
route, and the published India-specific Fulbright field restriction. Source URLs
and remaining applicant checks appear beside each answer. The raw uploaded
catalog and input state are preserved.

Validation: 18 functional cases and 19 regression checks pass, in addition to
the retained arithmetic and upstream handoff assertions. These are correctness
checks, not an eligibility-accuracy measurement. Independent student outcome
labels remain absent; no 96% accuracy claim is made.

Outputs:

- `data/processed/agent5/executed_answer_report.json`: complete demonstration,
  source guide, structured candidates and check results.
- `data/processed/agent5/catalog_shortlist.csv`: sourced catalog leads and their
  current displayed decisions; these are not confirmed awards.

Reproduce from the project root in an environment with NumPy, pandas,
scikit-learn, ipykernel and jupyter_client installed:

```powershell
python -X utf8 notebooks/execute_notebook.py backend/app/agents/scholarship_agent/Agent5_Scholarship_agent.executed.ipynb
python -X utf8 notebooks/run_agent6_outcomes_notebook.py
```

The shared runner preserves notebook source and captures real Jupyter stream,
Markdown/display, result and error outputs. It clears stale outputs, stops on
failure, saves progress, and marks completion only after all cells succeed.
