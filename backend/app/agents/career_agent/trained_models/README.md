# Agent 6 fitted artifacts

The fully executed `../Agent6_Career_agent.ipynb` trains, evaluates, saves, reloads and
uses these files. Reproduction and limitations are documented in
`docs/Agent6-Outcomes-Validation.md` at the project root.

```python
from pathlib import Path
import joblib
import pandas as pd

directory = Path('backend/app/agents/career_agent/trained_models')
earnings = joblib.load(directory / 'agent6_earnings_model.joblib')
clusters = joblib.load(directory / 'agent6_outcome_clusters.joblib')
bundle = joblib.load(directory / 'agent6_lookup_bundle.joblib')

# Example: re-predict a known uploaded program's cohort estimate.
row = pd.DataFrame([bundle['programs'][0]])
X = row[bundle['regression_features']].fillna('Unknown').astype(str)
estimated_cohort_earnings = earnings.predict(X)[0]

# Require at least two supplied measurements; no all-missing cluster assignment.
C = row[bundle['cluster_features']].apply(pd.to_numeric, errors='coerce')
cluster = int(clusters.predict(C)[0]) if C.notna().sum(axis=1).iloc[0] >= 2 else None
```

These models estimate cohort earnings and group outcome patterns. Neither is an
individual research/industry classifier or a placement-probability model. Reported
career-path advice in the notebook retains its explicit advisory rules.

Artifacts use standard sklearn objects (trained with scikit-learn 1.8.0) and plain
Python data; no notebook-defined estimator class is required. `manifest.json` records
checksums and input features. Load only trusted joblib files.
