# Test Checklist

## Backend checklist
- [ ] Health endpoint returns 200
- [ ] /predict/ms accepts valid student profile payload
- [ ] /predict/mba accepts valid student profile payload
- [ ] /match returns a filtered university list
- [ ] Invalid payload returns clean validation error
- [ ] Model path is available when prediction is executed

## Frontend checklist
- [ ] Streamlit app loads successfully
- [ ] Profile form renders correctly
- [ ] MS/MBA branching fields function as expected
- [ ] Recommendation page loads matched universities
- [ ] API client connects to localhost:5000 correctly

## Integration checklist
- [ ] Backend server runs on port 5000
- [ ] Frontend calls backend successfully
- [ ] Sample prediction request succeeds end-to-end
- [ ] Sample recommendation request succeeds end-to-end

## Completion checklist
- [ ] Real model files validated
- [ ] Project dataset finalized
- [ ] Matching dataset finalized
- [ ] Final ML metrics reviewed
- [ ] Final capstone report prepared

## Current stage
In progress: starter demo flow works and project tracking documents are in place.
Pending: final real-data and model validation.

## Independent evaluation protocol checks — 2026-10-21

- [x] Agent 3 and Agent 5 code cells executed against the uploaded catalogs; outputs saved,
  including the final accuracy-status cells.
- [x] Isolated fictional contract checks exercised profile validation, the Agent 2 export
  interface, two blind packets, adjudication/kappa, and exact shortlist preservation.
- [x] Agent 3 rejects test data through its dev evaluator, changed frozen configurations,
  and previously consumed test students, including under a new version name.
- [x] Best-fit Top-1 distinguishes a highest-grade program from a merely relevant program.
- [x] Agent 5 uses the actual public agent for each evaluated pair, separates eligibility
  from monetary completeness, and reports correct selective-accuracy/abstention denominators.
- [x] Agent 5's full frozen-run/report path and repeated-test blocking passed isolated
  fictional fixtures. Fixture accuracy is not evidence of real-world accuracy.
- [x] Eight input CSV templates contain headers only; the 1,238-row Tier A source queue
  contains catalog identifiers/links and blank human-review fields.
- [ ] Collect consented real profiles and independent annotations.
- [ ] Run Agent 2 production retrieval/services on those profiles and export real shortlists.
- [ ] Complete official scholarship-source verification and evaluate real recommendation coverage.
- [ ] Establish >=96% held-out accuracy with the specified confidence and independence requirements.

## Executed prediction checks and Agent 6 — 2026-10-21

- [x] Agent 3 rerun: 24/24 existing author-written development cases rank an expected
  program first; Top-1 100%, Hit@3 100%, MRR 1.0. These candidate sets are diagnostic
  catalog lists, not independently collected student/Agent 2 shortlists.
- [x] Agent 5 rerun: 18/18 explicitly fictional rule-contract cases pass, including
  eligibility, abstention, merit scale, missing award units and confirmed-award arithmetic.
  The 100% functional pass rate is not independent eligibility accuracy.
- [x] Agent 6 created and executed: actual Agent 3 handoff preserves program order and
  caller state; all 3,052 catalog programs produce an output without fabricated placements.
- [x] Agent 6's 15/15 functional examples pass, including ambiguous/missing goals,
  negation, absent programs, missing admission estimates, and invalid placement counts.
- [x] Optional Agent 6 classifier training/freeze/test API checked using isolated fictional
  fixtures. Provenance opt-in, student separation, stable freeze hashing, once-only test
  cohorts and small-sample confidence rejection passed. These checks do not supply real labels.
- [ ] Real outcome-based accuracy for Agent 6 (no career dataset supplied).
- [ ] Real scholarship recommendation coverage after resolving missing source details;
  the illustrative full-catalog run still has zero fully recommendable records.
