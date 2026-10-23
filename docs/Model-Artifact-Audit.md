# Model artifact audit

Reviewed: 2026-10-08

Application follow-up: Agents 7 and 2 now have verified local inference and
frontend integration. The original uploaded Agent 2 folder remains incomplete;
an authorized local production notebook rerun produced the complete active
bundle in `trained_models_local`. See
[Agent 7 integration](Agent7-Application-Integration.md) and
[Agent 2 integration](Agent2-Application-Integration.md) for current runtime
status. The inspection findings below describe the original audit date.

## Scope and verification limits

This report records read-only inspection of agent notebooks, Python loaders, file names, file sizes, and leading bytes. No models were deserialized, notebooks executed, dependencies installed, or predictions tested. Artifact presence does not establish usability or compatibility. Notebook code describes intended behavior; it does not prove the saved artifacts implement that behavior.

The user manages all Git commands. Integration is on `jalaja-backend`; no merge or push to `main` is authorized.

## Agent readiness

| Agent | Observed implementation | Required follow-up |
| --- | --- | --- |
| 1: Profile | Notebook and five artifacts in `profile_agent/trained_models_A1` | Validate artifact types, feature encoding, label semantics, and training/inference inputs; investigate outcome-related features |
| 2: University | Updated notebook, ten new artifacts in `university_matching_agent/trained models`, twelve older artifacts in `trained_models_A2` | Obtain missing exports from the same updated training run; implement a loader and matching service using one coherent model version |
| 3: Program | Notebook containing embedding/reranking logic | Adapt dataset dependency, identify external model requirements and configuration, and extract inference logic into a service |
| 4: Financial | Notebook with training and export logic | Obtain three model exports, verify financial dataset availability, and adapt the removed catalog dependency |
| 5: Scholarship | No dedicated implementation found in the inspected agent file inventory | Identify implementation/data elsewhere or define an explicit unavailable state |
| 6: Career | No dedicated implementation found in the inspected agent file inventory | Identify implementation/data elsewhere or define an explicit unavailable state |
| 7: Extracurricular | Notebook plus artifact files with duplicate-download suffixes | Recover correctly named, correctly typed exports and verify preprocessing and feature order |

## Agent 1: inputs and leakage review

The notebook's `score_candidate` builds numeric inputs from:

- `gpa_normalized_4`, `gre_score`, `toefl_score`, `has_research`
- `university_rating`, `admit_probability`, `gmat_score`, `work_experience_months`

It encodes categorical fields `track`, `admission_status`, `major`, and `work_industry`, then reindexes against saved feature columns. It returns `Tier1` or `Tier2` plus the probability of class 1.

`admission_status` and `admit_probability` need a training review: these may be outcome information unavailable for new applicants, or may create a circular dependency with Agent 2. This is a suspected issue, not a confirmed leakage finding. Do not invent these values or silently substitute zeros to claim valid predictions. Establish their provenance, target definition, and availability at inference; retrain without them if necessary.

Frontend adapters must map degree goal to `track`, normalize GPA using an explicit scale, derive total GRE correctly, and define research/experience categories using the training conventions. A `Tier1` probability is not automatically an admission probability.

## Agent 2: missing exports and version separation

The updated notebook's export cell lists fourteen artifacts. Ten exist in `trained models`; the following four were not found there:

```text
agent2_admission_model.joblib
agent2_shap_explainer.joblib
applicant_cluster_medians.joblib
applicant_cluster_features.joblib
```

Retrieve these from the same run that produced the new feature list and clustering artifacts. The admission model is required for admission predictions. The explainer is required for the notebook's explanation path. Applicant clustering artifacts are needed when that inference path is used; the notebook also explicitly exports them for future use.

The older `trained_models_A2` folder contains an admission model and explainer. Their existence does not make them compatible with the new artifacts. Do not combine old and new files. Keep complete model versions in distinct folders, with manifests identifying training code, data version, feature order, dependency versions, and artifact hashes.

The updated notebook builds inference features including applicant GPA/GRE, program requirements, and `tier_score`, with clustering features conditional on the selected feature set. Agent 1's tier representation must match Agent 2's expected representation; confirm this from the artifacts before creating the adapter.

The current Python `match.py` uses a hardcoded university list and GPA/tier rules. It does not load Agent 2 artifacts.

## Agent 3 and Agent 4: dataset dependencies

Both notebooks reference `agent2_final_2tier.csv`, removed by the incoming changes. The newer catalog is `data/raw/agent2/agent2_enhanced_program_catalog.csv`. Compare schemas and units before adapting references; a path replacement alone may be insufficient.

Agent 3 uses interest text, curriculum/research descriptions, and specialization clusters in its scoring pipeline. Its embedding/reranking resources and preprocessing must be identified before runtime integration.

Agent 4 reads `agent4_master_financial_dataset.csv` and exports:

```text
agent4_tuition_model.pkl
agent4_shap_explainer.pkl
agent4_feature_columns.pkl
```

These exports were not found in the inspected agent artifact inventory. Financial dataset availability has not been verified. Its inference adapter must use the trained feature definitions and distinguish annual tuition from living costs and total program cost.

## Agent 7: suspicious artifact contents

The notebook loader expects these core files without duplicate-download suffixes:

```text
agent7_feature_columns.joblib
agent7_xgb_tier_model.joblib
agent7_gbr_score_model.joblib
agent7_archetype_kmeans.joblib
agent7_archetype_scaler.joblib
```

The uploaded files use ` (2)` suffixes, and some contents do not match their apparent names:

| File in `extracurricular_agent/joblibs` | Observed leading content |
| --- | --- |
| `agent7_gbr_score_model (2).joblib` | Configuration text beginning `[paths]` |
| `agent7_keyword_anomaly_model (2).joblib` | JSON beginning with a `lang` field |
| `agent7_lr_tier_model (2).joblib` | JSON beginning with a `moves` field |
| `meta (2).json` | Non-UTF-8 binary content; could not be read as UTF-8 JSON |

Other files have pickle-like or other binary headers, but their object types remain unverified. Headers alone cannot identify a usable classifier, scaler, or feature list. Renaming these uploads is insufficient; recover the original export set and verify each object against its expected role.

The notebook's scorer expects leadership, research, competition, and volunteering scores; publication and patent counts; degree level; and field. It derives achievement archetypes, one-hot categories, log counts, and interaction features before prediction. Uploaded resume text needs a defined extraction/scoring step; the scorer does not directly accept a raw PDF.

## Backend and frontend integration gaps

- Pending cleanup deletes the backend entry point and configuration. The remaining profile predictor imports `app.config.Config`, so that import currently cannot be satisfied by the reviewed files.
- The legacy predictor expects `ms_model.pkl` and `mba_model.pkl`; these names do not match Agent 1's trained tier artifacts.
- `normalize_gpa` divides values above 4 by 10, incorrectly converting an 8/10 GPA to 0.8 instead of 3.2 on a proportional 4-point scale. Define an explicit scale-aware policy consistent with training.
- The matching route previously referenced `app.agents.matching_agent.match`; validate and update it for the actual `university_matching_agent` module.
- Meridian service factories return `MockEventSource` and `MockReportService`. Results components also read mock constants directly, so replacing factories alone will not make the full dashboard dynamic.
- Uploaded documents are saved, but the current event source receives only a profile dictionary. Add extraction, student confirmation, and structured document input to the analysis contract.
- Agent event payloads need to populate state used by results and PDF generation. Error/unavailable states must remain explicit rather than displaying invented results or marking unavailable agents complete.

## Recommended implementation order

1. Recover and validate coherent artifact sets; record dependency versions and feature schemas. Resolve Agent 1's input provenance before claiming applicant inference.
2. Implement backend startup and configuration that support the selected services while honoring intentional legacy cleanup.
3. Extract inference functions from notebooks into adapters with validated input/output schemas. Begin with one verified end-to-end agent.
4. Connect real progress and result payloads to Meridian state, results components, and PDF generation. Keep sample mode explicitly labeled and separate.
5. Add document extraction and confirmation; implement remaining agents only when their data and artifacts are verified.
6. Verify changed inputs affect results, invalid inputs fail clearly, missing artifacts report unavailable states, and the dashboard/PDF use the same report. Evaluate model quality separately from integration tests.

## Current unresolved work

Missing artifacts, artifact object types, dependency compatibility, data schemas, actual predictions, and runtime behavior remain unverified. This audit makes those gaps reviewable; it does not complete frontend integration.
