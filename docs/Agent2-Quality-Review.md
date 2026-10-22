# Agent 2 prediction quality review

Reviewed: 2026-10-13. Active bundle: `trained_models_local`.

## Decision

The integration works, but this model is not validated for real admission probabilities or Safe/Target/Reach advice. The high estimates come from the trained model; they are not a frontend percentage-formatting error. Do not solve this by manually lowering MIT/Stanford probabilities or choosing more reassuring cutoffs.

This review ran the saved model against its 3,198-row test split and 70 controlled GPA/GRE scenarios. It verified artifact, catalog and training-data hashes against the manifest. No production model, dataset, threshold or UI was changed.

## Why the estimates are high

GRE dominates the classifier on this dataset. Shuffling GRE increases test Brier error by 0.25946 on average; shuffling GPA increases it by 0.00439, while shuffling program tier changes it by only 0.00007. These are five-repeat permutation diagnostics, not causal effects; GPA/GRE and their derived cluster are correlated.

The model sees only `tier_score`, GPA, GRE Quant, GRE missingness, and a GPA/GRE-derived applicant cluster. It has no university/program identity, program admit rate, minimum GPA, research, SOP or recommendation-letter inputs. Programs with the same tier receive the same probability for the same applicant. Agent 7 changes the matching score, not admission probability. Its contribution is a constant across programs for one student, so that term alone cannot change their ranking.

Controlled predictions at GPA **3.36/4**:

| GRE Quant | MIT model estimate | Stanford model estimate |
| --- | ---: | ---: |
| 130 | 98.1% | 96.7% |
| 150 | 98.1% | 96.7% |
| 155 | 92.0% | 87.6% |
| 160 | 3.5% | 2.2% |
| 165 | 98.9% | 98.3% |
| 170 | 99.3% | 98.9% |
| Missing | 98.0% | 96.7% |

These are diagnostic model outputs, not real admission odds. The 155-to-160-to-165 reversal occurs inside the training GRE range. Values 130, 150 and 170 are outside the observed range of **154.58–168.80**; the application nevertheless accepts them. Missing GRE is encoded as zero for the classifier, but **zero training rows have missing GRE**, so its missingness feature provides no learned protection. Tree predictions outside the training range are not evidence of valid extrapolation.

There are 12,112 fractional GRE values among 15,988 rows. Common exact values have sharply different label rates: GRE 160 has 902 rows and a 2.66% positive fraction. Score transformation/augmentation lineage needs investigation; the audit does not establish how these values were generated. The full exact-value distribution is exported for inspection.

## Labels and leakage

- 15,988 rows: 5,400 Admit, 10,388 Deny and 200 Waitlist. Admit maps to 1; both Deny and Waitlist map to 0. Whether Waitlist means an eventual unsuccessful outcome is undocumented.
- There are no exact duplicate rows. There are 12,388 distinct applicant IDs, including 1,800 repeated-ID groups. All 1,800 vary in GPA, GRE Quant and GRE Verbal. They cannot currently be treated as verified stable student identities.
- Fit/validation/test row indices are disjoint: 10,232 / 2,558 / 3,198. However, **793 applicant IDs cross fit and test**, affecting **929 test rows (29.0%)**. This is confirmed ID overlap, not proof that every overlapping row is the same real student. It prevents claiming a clean unseen-student evaluation.
- The five active predictors do not directly include outcome labels or admission status. No direct outcome-column leakage was found in the active feature list. Data-generation leakage remains unresolved because outcome and augmentation provenance are unverified.
- `tier_score` equals the program catalog value in every training row. The notebook's description of it as Agent 1 applicant strength is misleading; it is a program attribute in this dataset and runtime.
- Local training corrected the original notebook's fit/validation row overlap. However, clustering preprocessing is fitted on all outer fit rows before the five calibration folds, so preprocessing is not independently fitted inside each fold. The external test rows remain excluded from that fitting.
- Model parameters/features were selected in the supplied notebook before this local rerun. Their earlier exposure to these data is not ruled out; these metrics are not a fresh independent benchmark.
- One training GPA exceeds 4 (maximum 4.0583). The admitted frontend GPA range and training distribution also differ at the lower end (training minimum 2.5666).

## Calibration on the supplied test rows

| Metric | Result |
| --- | ---: |
| Accuracy at saved 0.42 decision threshold | 87.27% |
| F1 | 0.7988 |
| ROC AUC | 0.9339 |
| Brier error, lower is better | 0.08445 |
| Constant fit-prevalence baseline Brier error | 0.22366 |
| Log loss | 0.26957 |
| Expected calibration error, 10 equal-width bins | 0.02530 |

The original saved evaluation metrics were reproduced. Aggregate calibration on these supplied rows is reasonably close; it does **not** establish calibration on real university outcomes. In the 631 test rows predicted at least 95%, the mean estimate is 98.11% and all labels are positive. Thus these rows do not show aggregate overconfidence at the top end. This unusually easy high-score region merits source-data investigation rather than arbitrary probability suppression.

Aggregate metrics also hide local errors: the 40–50% bin averages 44.07% predicted versus 32.12% positive across 193 rows. Several upper-middle bins contain very few rows. Bin counts and observed fractions are in the audit JSON; these estimates are descriptive and have not been given independence-based confidence intervals because identity lineage is unresolved.

## Category thresholds

The saved **0.42** threshold maximizes validation F1 for a binary decision. The worker loads and validates it but does not use it to assign website categories. Categories are independently hardcoded as Safe ≥0.65, Target ≥0.35 and Reach <0.35, and the service validator enforces the same rule. No category-specific validation or acceptable-risk policy was found.

On the supplied test split, the Safe category contains 720 rows with a 97.92% positive fraction; that result is conditional on this dataset and its problems. The term “Safe” cannot be justified for actual universities from this evaluation. Changing 0.65 to 0.90 would still label the problematic MIT/Stanford examples Safe.

## Recommended corrective work

1. Replace categorical safety claims with neutral experimental score bands and clearly distinguish a dataset-model score from admission odds. Handle missing/out-of-range GRE explicitly rather than reporting confident admission estimates. Preserve raw model outputs in diagnostic reports.
2. Establish source records, outcome dates and meanings, GRE transformation rules, and augmentation parent IDs. Resolve conflicting identities and waitlist outcomes before retraining. Do not invent missing provenance or replace scores with university-wide admit rates.
3. Split verified original students/augmentation families before preprocessing or resampling, preferably with a later application cohort as the final holdout. Fit transformations inside each training/calibration fold. Obtain program-level real outcomes before claiming program-level calibration.
4. Compare a simple baseline with the current model and a candidate using justified program-specific predictors. Audit sensitivity, missing inputs, calibration and performance by program and relevant applicant groups. Tune on validation data and evaluate once on the independent holdout.
5. Select any future category thresholds against an explicit risk policy on that validated population. Do not optimize them to make the current examples look plausible.

Follow-up implementation: the user authorized item 1 on 2026-10-13. Website/print/PDF now use Higher/Middle/Lower experimental bands and unvalidated model-score labels. Missing GRE or GRE outside the manifest-bound training range retains catalog matches but returns no model percentage or SHAP factors, with an explicit insufficient-evidence reason. Old result contracts are rejected until recomputed. Artifacts and band boundaries remain unchanged. Items 2–5 remain future work; independent real-admissions validation requires provenance and outcome evidence absent from the current reviewed material.

## Reproduction and evidence

Run from the project root:

```powershell
.venv-agent2/Scripts/python.exe scripts/audit_agent2_quality.py
```

- Script: `scripts/audit_agent2_quality.py`
- Metrics, identity overlap, label mapping and calibration bins: `reports/agent2-quality/audit.json`
- Seventy controlled predictions: `reports/agent2-quality/sensitivity.csv`
- Exact GRE values and label rates: `reports/agent2-quality/gre_label_distribution.csv`
- Runtime inference and category rules: `meridian/services/agent2_worker.py`
- Production execution/splits: `scripts/run_agent2_notebook.py`, `reports/agent2-local/split_indices.json`

All claims here concern local code, supplied data or measured model outputs. No external university admission rates were used.
