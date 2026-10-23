# Agent 6: uploaded outcomes and unsupervised learning

The single final notebook is
`backend/app/agents/career_agent/Agent6_Career_agent.ipynb`. It is executed in place;
the last cell reports the current results. The original notebook is preserved in
`data/backups/Agent6_before_outcomes_v2.zip`, rather than adding another working notebook.
The original advisory function and independent-label training utilities remain available.

The notebook contains 13 executable code cells. Its runner now executes those existing
cells in a fresh Jupyter kernel and preserves source edits; it does not regenerate or
truncate the notebook. Stream output, rich displays and errors are captured in the file.
After restarting a notebook kernel, use **Restart Kernel and Run All**. The final cell
depends on setup and trained models from earlier cells; running it alone previously
produced `NameError: CAREER_MODEL_DIR is not defined`.

## Data and scope

The uploaded `data/raw/agent6/agent_6_dataset_final_merged.csv` has 51,842 rows and
97 columns: 48,809 rows marked `scorecard_observed` and 3,033 estimated program mappings.
The source labels and population scopes are supplied by the dataset; the pipeline does
not independently reconstruct the original source records or cohort years.

There are no independently observed student research/industry labels. The heuristic
job/research scores are not used as ground truth. Employment proxies are not placement
rates. The file marks applicability to international students as proxy-only.
School-level MBA employment figures remain separate context and never become
program-specialization placement rates. Future placement years are withheld for a
historical `as_of` date.

Training uses 48,679 US rows with known institution IDs, marked as observed in the upload.
The 130 excluded observed rows lack the required institution identifier or US scope.
Program estimates do not train either model. Repeated institution/CIP/credential keys,
if encountered, are resolved by evidence count rather than earnings; no duplicates remain
among these eligible observed rows.

Institution-separated splits contain 1,371 train, 457 development and 457 test UNITIDs,
with no overlap. Train/dev/test row counts are 29,276 / 10,208 / 9,195 before task-specific
missing-value exclusions. Splits are saved in `data/processed/agent6/institution_splits.csv`.

## Learning and measurements

The supervised model predicts uploaded four-year cohort earnings using CIP family,
CIP code, credential level and institution control. An ordinal encoder groups rare
categories (maximum 200 per input), and HistGradientBoosting uses native categorical
features with a log-transformed target. Its fixed settings are not tuned on test data.
University identity, outcome-derived averages, salary ratios, admission information,
employment proxies and heuristic track scores are excluded from predictors.

The fitted model uses train+development institutions. Evaluation on 7,171 labelled rows
from withheld institutions gives:

| Metric | Model | Training-median baseline |
|---|---:|---:|
| MAE | $10,321.84 | $19,150.85 |
| RMSE | $16,067.06 | $27,460.87 |
| R² | 0.6343 | -0.0684 |
| Share within ±10% | 48.18% | 23.02% |

These measure reconstruction of uploaded cohort earnings at unseen institutions,
not individual salary forecasting, placement prediction or career-track accuracy.
No historical-year holdout is possible because cohort years are not supplied for these targets.

Unsupervised KMeans groups log-transformed one-year earnings, four-year earnings and
observed median debt, after median imputation and standardization. Rows need at least
two of those three measurements. Candidate k values 2–8 are fitted on train and
compared using development silhouette; k=2 wins. The final model fits train+development
rows and is evaluated on 6,672 eligible withheld-institution rows:

- Silhouette: **0.4134** (higher is better; not an accuracy percentage).
- Davies–Bouldin: **1.0153** (lower is better).

The two clusters describe higher/lower earnings and debt patterns; they are not labelled
research or industry. The regression never consumes these target-containing clusters.
No labels are manufactured from cluster membership or from the student's stated goal.

## Runtime contract and artifacts

`career_agent(state)` consumes Agent 3's program list and preserves its order and the
caller's state. It returns `state['careers']` with the existing career-path/role fields,
plus `outcome_evidence`, `outcome_cluster`, `earnings_context`, `employment_proxy_context`
and `school_placement_context`. Career-path advice and goal alignment remain explicitly
heuristic unless independently labelled student outcomes are supplied to the retained
supervised classification workflow.

Every career row also includes an `answer`: a readable direction, supporting program
evidence, role examples, supplied/model cohort earnings context, placement-data availability
and practical next steps. The handoff and final cells print these answers without a long
single-line JSON dump. Unavailable placement evidence is stated explicitly; no placement
rates or individual salary promises are invented.

Program IDs and labels are checked against the Agent 2 catalog. Exact university/program
identity is used when IDs are absent. Conflicting program IDs or UNITIDs reject enrichment.
The upload maps 3,033 of 3,052 catalog programs; the other 19 keep the advisory fallback.
The 1,251 national-field fallback mappings have no outcome-source UNITID: catalog UNITID
supplies identity only and does not promote field-level estimates to university evidence.

Files in `backend/app/agents/career_agent/trained_models/`:

- `agent6_earnings_model.joblib`: fitted encoder and earnings regressor.
- `agent6_outcome_clusters.joblib`: fitted preprocessing and KMeans pipeline.
- `agent6_lookup_bundle.joblib`: exact program evidence, cached model outputs, cluster
  profiles, feature lists and evaluation metadata.
- `manifest.json`: checksums, training-data fingerprint and scikit-learn version.

All serialized types are standard sklearn estimators or plain dictionaries; loading does
not require a notebook-defined class. The models were produced with scikit-learn 1.8.0.
Use compatible package versions and load trusted joblib files only.

The notebook executes 15 retained advisory checks plus 15 outcome/reload/integration
checks. Its actual Agent 3 handoff uses real catalog programs with an illustrative student;
that demonstration is not an independent student-outcome accuracy test. The earlier
saved Agent 4 replay remains historical and imports the retained baseline Agent 6 cells.
It is not retroactively presented as a replay of the enriched Agent 6 implementation.

Reproduce from the project root:

```powershell
python -X utf8 notebooks/run_agent6_outcomes_notebook.py
```

Execution requires `jupyter_client` and `ipykernel` in the same Python environment as
the model dependencies. On Windows, Jupyter must be able to set secure permissions on
its local connection file. The reusable executor is `notebooks/execute_notebook.py`.

Full results: `data/processed/agent6/validation_report.json`. The uploaded data file remains
unchanged and Git-ignored under the project's existing Agent 6 data rule.

Sources: [Scorecard field-of-study methodology](https://collegescorecard.ed.gov/assets/FieldOfStudyDataDocumentation.pdf),
[HistGradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html),
[silhouette selection](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis).
