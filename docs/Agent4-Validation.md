# Agent 4: executed local validation

The active financial agent is implemented in the appended sections of
`backend/app/agents/financial_agent/Agent4_Financial_agent.ipynb`.
`Agent4_Financial_agent.executed.ipynb` is the complete local execution copy,
including the original regression experiment and the current agent. The final
code cell reports the current measurements. Original historical cells in the
source notebook are preserved; the executed copy adapts nine environment/setup
cells for local files, optional SHAP, local artifact export and disabled database
writes. Random Forest uses one worker because Windows restricted parallel queue
creation. Predictive model settings and split logic are unchanged.

## Input and output

Input is Agent 3's flat `state["programs"]` list, with university, program name,
optional UNITID and degree metadata. Agent 2's `matched_universities` provides
additional UNITID/country metadata. Each program produces one `state["finance"]`
row with `university`, `program_name`, `unitid`, `program_level`, `country`,
`tuition`, `living`, their legacy aliases `tuition_annual`/`living_cost_annual`,
`total_cost`, `currency`, `cost_period`, `cost_source`, source
details and warnings. The agent copies its input state. Unresolved programs remain
visible with null costs instead of silently using another program's price.

The crosswalk links all 50 institutions using unique normalized names and a state
check against the uploaded financial dataset. After resolution, financial records
are joined on **UNITID plus degree level**. A supplied UNITID can resolve a changed
display name. Catalog entries are selected by their actual program names: 15
universities have specialized CS names rather than the bare `MS Computer Science`
title. This caused the earlier missing predictions; their catalog tuition was
present. All 3,052 catalog rows now carry UNITID. Existing catalog field values
were compared with the Git version and verified unchanged.

## Cost priority

1. For catalog institutions, use `tuition_out_state_usd` and the selected degree
   row's living baseline multiplied by effective regional price parity.
2. If catalog tuition is missing, use the same-degree published total from
   `data/raw/agent4/published_costs_50.csv`, tagged `cost_source="published_coa"`.
   Preserve the URL, reference year, known period and enrollment scenario. Do not
   infer a tuition/living decomposition from that total.
3. If both are absent, keep the catalog institution's cost unknown.

Outside this catalog, observed IPEDS tuition may be used; an explicit regression
callable is an optional fallback. KNN-imputed tuition is never an observed lookup
value. Living remains an estimate rather than observed expenditure. Catalog
tuition is a university proxy with an undocumented price year and fee scope.
Published totals may include insurance, books, transport and personal expenses;
these distinctions are retained in the source ledger.

## Published-cost evaluation

Current measurements (2026-10-21):

| Measure | Result |
|---|---:|
| Institution crosswalk coverage | 50/50 |
| Catalog rows with UNITID | 3,052/3,052 |
| Universities with a cost estimate | 50/50 |
| Published numeric totals | 43/50 |
| Independent estimates within 10% of those totals | 13/43 (30.23%) |
| Published-fallback estimates excluded from scoring | 0 in the present catalog run |
| Strictly comparable year/period/program/component cases | 0 |
| Functional checks, including fallback and output compatibility | 20/20 |
| Completed uploaded-applicant demonstrations | 20/20 |
| Priced recommendations in that replay | 200/200 |
| Rerun legacy Random Forest diagnostic | R² 0.526; MAE $3,989 |

The 30.23% figure describes discrepancies with the available published budgets;
it is not verified program-level accuracy. The current catalog contains tuition
for all 50 institutions, so the new published fallback is tested by temporarily
masking a catalog value and restoring it. No live catalog price is erased.

The notebook embeds the complete ledger-building code. It rebuilds 50 official
source records before evaluating the fixed 50-institution prediction list. There
are 43 numeric totals; seven remain unresolved: UT Austin (range), UCSD (dynamic
table), NYU (same-year graduate tuition), Wisconsin (program-specific applicability),
UC Irvine (conflicting source sums), Chicago (annual enrollment/living scope), and
Case Western (annual credit load). Missing references stay visible in the audit.

The descriptive comparison reports the fraction of independently calculated
estimates within 10% of available published totals and the denominator. Estimates
copied from the ledger through `published_coa` are excluded from scoring against
that ledger. A regression check enforces this exclusion. Strict price accuracy
also requires matched year, months, degree and documented program/component scope.
Those conditions are not established by the current catalog, so **96% accuracy is
not verified**. The original regression's row-split R² and dollar errors are
reported separately; its targets include KNN-imputed figures and repeated
institution rows, so they do not establish performance on unseen universities or
independent published COA.

## The 20-record demonstration

The user authorized the first 20 distinct uploaded applicant records in file order.
Their application targets and academic fields are retained; interests, nationality,
career goals and budgets are unspecified. These records are demonstration inputs,
not independently verified research participants or new accuracy labels. Original
applicant IDs are replaced with local demo IDs in saved states. No identifier mapping
is saved. All application rows for these 20 IDs are excluded from the replacement
admission-model fit.

The chain runs Agent 2's actual orchestration/scoring with local TF-IDF retrieval,
the uploaded clustering artifacts, and a replacement calibrated admission model
because the original fitted classifier was not supplied. It then executes the
existing Agent 3, Agent 5 and Agent 6 notebook implementations and this Agent 4.
Agent 1/7 extraction is not rerun: their recorded inputs are supplied. Qdrant,
neural retrieval, hosted explanations and database writes are not exercised.
Saved sklearn artifacts produce version-compatibility warnings, retained in outputs.

Every recommended program has a cost. Funding gaps still remain `None` because
these applicants have no recorded budgets. No budget or confirmed scholarship is
invented. Demo completion measures interface behavior, not admission, scholarship
or career prediction accuracy.

## Files and rerun

- `data/backups/agent2_enhanced_program_catalog.original_without_unitid.csv`: verified
  original catalog, before adding the column.
- `data/backups/agent2_enhanced_program_catalog.before_final_refresh_*.csv`: exact
  backup of the enriched catalog before the final refresh.
- `data/raw/agent4/agent2_ipeds_crosswalk.csv`: institution mapping and provenance.
- `data/raw/agent4/published_costs_50.csv`: official source ledger with dates/notes.
- `data/processed/agent4/catalog_cost_predictions_50.csv`: current estimates.
- `data/processed/agent4/published_cost_comparison_50.csv`: per-university errors.
- `data/processed/agent4/published_cost_metrics.json`: current benchmark counts.
- `data/processed/agent4/demo_20_summary.csv` and `demo_20_states.json`: local demo
  results, excluded from Git.

Run the full local notebook from its first cell, or run the current agent beginning
at section 11. Both include all Agent 4 implementation and ledger-building code.
Data files, uploaded clustering artifacts and the other agents' notebooks must
remain in the project. Developer rebuild commands from the repository root:

```powershell
python notebooks/run_agent4_extension.py
python notebooks/run_agent4_full_notebook.py
```

The first command preserves all original source cells and executes the appended
section. The second executes every code cell in a fresh namespace and saves the
complete local copy. Neither command needs cloud credentials or sends student data
to an external service.
