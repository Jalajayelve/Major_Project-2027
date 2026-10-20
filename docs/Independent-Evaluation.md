# Independent evaluation of Agents 3 and 5

The notebooks contain the implementation. Their last cells show saved executed results.
No independent accuracy is claimed until real consented profiles and human judgments are
available. Catalogs and author-written diagnostics are not labelled student outcomes.
Do not tune on test labels, manufacture labels, remove failures, or describe development
scores as test accuracy.

## Private files and collection

Use the header-only templates under `data/raw/`. They contain **no example students or
invented labels**. Research profiles, annotation files, manifests, context snapshots and
evaluation reports are excluded by `.gitignore`. Keep the identity mapping outside this
repository. Obtain research consent and remove names, emails, phone numbers, institutions,
cities and identifying detail from free text. Git ignore does not protect a local file
from access or remove previously tracked data. Do not commit notebook outputs containing
real profiles or per-student predictions.

`student_profiles/student_profiles_anonymized.csv` has:

```text
student_id,query_group,interests_text,target_program,target_degree,gpa,gpa_scale,nationality,budget_annual,budget_currency,profile_strength_score,work_experience_years,split
```

Use one row per student and one query_group per student. Fix approximately 40% of groups
as dev and 60% as test before viewing output. All paraphrases and university queries for
that student inherit the same group and split. GPA scale and budget currency are explicit;
the budget is annual, and profile strength uses 0–100. The loader rejects missing required
values instead of supplying synthetic defaults.

## Agent 3 collection and annotation

1. Initialize Agent 2's production functions and dependencies through
   `university_matching_agent`. Execute the new export cell and call:

   ```python
   export_agent3_annotation_shortlists()
   ```

   This actually calls Agent 2 once per profile with `standalone_mode=False`. Its real
   upstream Agent 1 tier information and Agent 7 score are required. The later Agent 2
   local-demo section replaces retrieval; rerun the production retrieval definition if
   the exporter reports that conflict. The exporter itself was validated with isolated
   contract fixtures; the real production export cannot run until real profiles and the
   initialized Agent 2 services/models are available.

2. The export writes `agent3_shortlists_for_annotation.csv` and an immutable
   `agent3_shortlists_for_annotation.manifest.json`. The prespecified default takes the
   **first university returned by Agent 2** per student, retaining all its programs.
   This gives one university query per independent student without consulting Agent 3.
   Optional `university_policy="all"` exports every university, but correlated queries
   then prevent the ordinary independent-query Wilson claim.
   A query is one student's interests and one university's complete shortlist. No Agent 3
   scores are run or exported. Empty results and single-program queries are visible in
   the audit; never replace them with hand-picked programs or silently filter them out.
   If the actual shortlists do not provide contrastive candidates, revise the prospective
   collection protocol and collect a new cohort before evaluation.

3. In Agent 3, call `prepare_agent3_blind_packets()`. Give `agent3_annotator_1.csv` and
   `agent3_annotator_2.csv` to different people. These files omit numeric Agent 2 scores
   and each other's labels. Each person independently fills `relevance`, `annotator_id`,
   `labelled_on` (ISO date) and notes. They must not see ranker predictions.
   Labels: 0 irrelevant, 1 partial, 2 relevant, 3 highly relevant.

4. After both submissions, adjudicate into the original packet's `relevance_final`
   column. Put a reason in `notes` for every disagreement. Do not change query inputs or
   candidates. Call:

   ```python
   finalize_agent3_annotations(
       adjudicator_id="YOUR_PSEUDONYMOUS_REVIEWER_ID",
       adjudicated_on="YYYY-MM-DD",
       independence_confirmed=True,
   )
   ```

   This validates every candidate against the export and writes separate
   `agent3_relevance_judgments_dev.csv` and `agent3_relevance_judgments_test.csv`.
   Each query must contain at least one grade >=2 and one grade <2. Two-rater exact
   agreement, ordinary Cohen's kappa and quadratic-weighted kappa are recorded separately
   in `.audit.json` sidecars. Kappa is undefined for a constant single-category rating set.
   The boolean records a human attestation; software cannot prove that raters were
   independent. A custodian should keep test labels and test agreement sealed.

5. Use `evaluate_agent3_judgments_v2()` on dev only. Its `failures` table shows actual
   mistakes. All candidate rows and real Agent 2 prior scores are required.
   To enable the neural path, load BGE as `embed_model` and a CrossEncoder as
   `specialization_reranker` in this kernel, then instantiate
   `ProgramRankerV2(reuse_loaded_models=True)`. Both must be present and work: no silent
   neural-to-lexical fallback is allowed. No models are downloaded automatically.
   Adjust `lexical_weights` and `blend_weights` using dev only. Defaults are
   specialization/title/content = 50/30/20 and fit/Agent2 match/admission = 60/30/10.

6. Freeze, then run test explicitly once:

   ```python
   freeze_agent3_version("v1")
   test_report = run_agent3_test_once("v1")
   ```

   The test action writes the combined `agent3_relevance_judgments.csv` only after
   freezing. `AGENT3_JUDGMENTS_PATH` overrides that final combined output path.
   Run All does not read combined/test labels or run test predictions. It may display
   an existing matching-version report.

The primary Top-1 metric requires a program with the **maximum human grade** to rank
first. Ties at that maximum count as correct. This is stricter than counting a grade-2
program correct when a grade-3 program is available. Hit@3 and MRR use grade >=2.
Report all queries, Top-1, Hit@3, MRR, NDCG@3 and the two-sided 95% Wilson interval.
The 96% criterion uses the **lower interval bound**, not the point estimate.

With independent test queries and the conventional 95% normal quantile, the minimum
query counts for 0, 1, 2, 3, 5 and 8 errors are 93, 138, 179, 217, 288 and 390.
Multiple queries from a student are correlated: all remain in the report, but the ordinary
query-level Wilson interval does not justify an independent-sample claim. Collect a
prospectively designed cohort with one query per independent student for that claim,
or use a separately specified clustered analysis. Never select the best query afterward.

The freeze records ranking code, catalog, configuration and loaded neural parameter
hashes. Test student groups are consumed before predictions, including failed runs.
Re-tuning requires a fresh test cohort. JSON locks are audit controls, not a security
boundary: protect files with a human test custodian and access controls. Do not reset
consumed records to reuse test students.

## Agent 5 eligibility evaluation

Fill `agent5/agent5_eligibility_judgments.csv`:

```text
pair_id,student_id,split,scholarship_id,human_decision,source_url,checked_on,annotator_1,annotator_2,notes
```

Use `eligible`, `ineligible` or `cannot_determine`. `annotator_1` and `annotator_2` are
distinct reviewer IDs; retain their independent assessments and adjudication evidence
in notes or a separate private source record. Check the official scholarship page, not
merely the uploaded catalog. Use ISO review dates. The evaluator sets `as_of=checked_on`.
A source URL alone does not verify the review.

The supplied pair schema does not identify a destination university/program. Save the
actual Agent 4 context for each pair, before annotation, rather than inventing one:

```python
# Values come from your real pipeline. Each state has exactly one selected finance entry.
export_agent5_evaluation_states(pair_states)
# Writes data/raw/agent5/agent5_evaluation_states.json
```

Each state needs its student_id and finance entry with university, program_name, country,
currency, explicit annual cost period and internally consistent annual costs. The shared
profile file is authoritative for personal fields; context snapshots supply destination
and financial facts. Multiple destinations for a student require distinct planned pairs.

Use `evaluate_agent5_eligibility_dev()` for development. Once ready:

```python
freeze_agent5_eligibility_version("v1")
result = run_agent5_eligibility_test_once("v1", human_sources_verified=True)
```

Test requires at least 200 pairs including Tier A and non-Tier A scholarships. Every
pair is passed to the public `scholarship_agent`; none are silently discarded.
Report:

- Selective accuracy on agent decisions with a resolvable human label, including the
  exact numerator/denominator and Wilson interval.
- Decision coverage over all pairs and unknown share.
- Decisions made where humans said `cannot_determine`, separately from scored decisions.
- Three-way agreement, confusion counts, Tier A/non-Tier A results, and recommendations.

All-unknown output has **undefined accuracy, zero coverage**. High selective accuracy
with low coverage is not overall recommendation accuracy. Repeated students are retained
but block the independent-sample Wilson claim. The final cell displays saved matching
reports without rerunning test inference.

## Catalog source review and funding outcomes

`agent5_tier_a_source_review_queue.csv` lists the 1,238 uploaded Tier A records and source
links for review. It is not a verified outcome dataset. Fill
`agent5_source_enrichments.csv` only from explicit official statements:

```text
scholarship_id,field,value,source_url,checked_on,reviewer_id,evidence
```

Supported fields: `gpa_scale`, `amount_period`, `coverage_basis` (`tuition` or `total`).
Annual coverage still requires an explicitly annual period. The enrichment loader never
waives unresolved English/academic rules and never converts an unconfirmed award into
confirmed funding. Missing periods/scales remain unknown.

The full-catalog demo currently has zero fully recommendable scholarships for its
illustrative profile. That is a data-completeness finding, not an eligibility accuracy
measurement. Source review and real contexts are necessary to assess real recommendations.

Funding gap is tested arithmetic, not a learned prediction. The separate funding-support
classifier uses `agent5_labelled_outcomes.csv`, independent real outcomes/provenance and
at least 30 students; `evaluate_agent5_real_labels(..., labels_are_real=True)` is explicit.
It is never automatically run by Run All. Keep its test cohort untouched and record the
result separately. Do not derive `needs_financial_support` from the gap formula.

Methods: [NIST Wilson interval](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
and [scikit-learn Cohen's kappa](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html).
