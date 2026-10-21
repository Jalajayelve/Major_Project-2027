> Current project selection: the old 66-cell Agent 2 notebook has been restored at `backend/app/agents/university_matching_agent/Agent2_University_Agent.ipynb`. The v3 executed notebook and pre-v3 backup have been removed. The audit below is historical; the experimental Python source and metrics remain for reference. Its optional builder now creates only an experimental executed copy and does not replace the old notebook.

# Agent 2 base-rate revision

The active implementation is embedded in the v3 appendix of
`backend/app/agents/university_matching_agent/AGENT2_University_agent.ipynb`.
The clean executed copy is `Agent2_University_Agent.executed.ipynb` in that directory.
Both end with measured results; the header is generated from the same variables.
The original notebook is backed up at
`data/backups/Agent2_University_Agent.before_base_rate_v3.ipynb`.
Existing code cells are preserved as historical experiments. Run the v3 appendix in a
fresh kernel, or run the clean executed copy from the beginning.

## What the input audit establishes

The CSV first appears in Git commit `313d617`, titled “Agent 2 : changing dataset and
improving accuracy”. No external source, collection protocol, admission year, license,
or generation script was located in the project. The earlier assertion that this is
real admissions data is unsupported; the audit does not establish its external origin.

There are 15,988 rows and 12,388 applicant IDs. Exactly 1,800 IDs have repeat rows,
accounting for 3,600 extra rows. Every repeated ID has the same outcome across its
programs. GPA, GRE and profile-strength values vary within all 1,800 repeated IDs, so
the file does not establish that these are consistent longitudinal applicant records.
An illustrative row-stratified 80/20 split with seed 42 puts 859 IDs on both sides.
That is an overlap demonstration, not a reconstruction of every historical split.

Program tier/outcome correlation is +0.01305. Program-rate/outcome correlation is
-0.01305. Neither result alone proves how labels were produced. However, the identical
labels across programs and missing provenance make these unsuitable as verified
program-specific admissions outcomes.

All 3,052 catalog priors satisfy the same formula to floating-point precision:

```text
program_admit_rate = 1.8313150425733213 - 0.01892147587511828 * tier_score
maximum absolute residual = 1.33e-15
```

These numbers cannot be presented as independently sourced program admission rates.
All training program IDs and their tier/rate values match the current catalog.
Neither CSV is modified by this revision.

## Probability behavior and evaluation

```text
logit(P(admit)) = logit(program_admit_rate) + log(3) * tanh(z / log(3))
z = sum(beta_j * standardized_applicant_j) - gamma * (tier_score - 70) / 10
beta_j >= 0; gamma >= 0.1
```

The four applicant inputs are GPA, GRE quantitative, GRE verbal and profile strength.
Tier and the fixed rate offset bring the input count to six. Training-fold medians and
scales are used for preprocessing; there is no fitted intercept that can erase the prior.
Missing optional applicant features use training medians and are flagged at inference.
GPA is required. A missing program rate fails explicitly rather than borrowing a university rate.

The odds cap of three, tier reference of 70, minimum tier penalty and regularization
are explicit modeling policies fixed before evaluation. They are not empirical admissions
facts. The median applicant at tier 70 reproduces the prior; an arbitrary applicant or
the mean of all applicants need not. This model is not established as calibrated.

Five-fold `GroupKFold(applicant_id)` has zero ID overlap in every fold. Repeat rows receive
weights giving each applicant equal total weight during training. Reported pooled scores
are per application row, at the fixed 0.5 classification threshold. No hyperparameter
selection or test-set tuning is performed. These are CV metrics, not independent test accuracy.

| Model | CV accuracy | ROC-AUC | Brier | Log loss |
|---|---:|---:|---:|---:|
| Offset model with profile strength | 68.56% | 0.71629 | 0.20369 | 0.59330 |
| Same model without profile strength | 68.56% | 0.71629 | 0.20369 | 0.59330 |
| Catalog prior only | 56.02% | 0.49163 | 0.24839 | 0.69151 |

The model change and evaluation protocol differ from the old GradientBoosting run.
The accuracy difference must not be attributed solely to removing applicant overlap.
No model was selected to reproduce the old 86.7%/88.4% figures or to reach 96%.

Profile strength has standard deviation 8.25477 and marginal label correlation 0.10272;
the zero-variance claim is stale. Its constrained coefficient in the all-data fit is zero,
and the grouped ablation yields no classification-accuracy gain. A monotonic constraint
allows a zero effect: a higher score must not lower the estimate, but need not raise it.
GRE verbal also receives a zero coefficient. GPA and GRE quantitative receive positive effects.

Twelve checks cover monotonicity, rate sensitivity, serialization, missing priors, bounded
adjustments, the prior anchor and group isolation. Holding the applicant and prior (25%)
fixed gives 30.57% at tier 60 versus 17.13% at tier 88. These are behavior tests, not accuracy.

The same median applicant gets 13.64% for Stanford MS Computer Science, 32.19% for ASU,
and 61.86% for Delaware using the current catalog priors. These are experimental examples,
**not verified admissions chances**. Stanford's official doctoral dashboard covers external
doctoral applicants and cannot establish its MS CS admission rate. A 3–4% undergraduate
rate cannot be substituted for a graduate-program rate.

## Program-rate evidence and live execution

`data/raw/agent2/program_admit_rate_sources.csv` is an empty evidence template, not generated
labels. A documented override requires an exact catalog program/degree match, admission
year, applicants, admits, rate, official source URL, review date and applicant population.
The rate must equal admits/applicants, not enrolled/applicants. Source quality and scope
still need human verification. No source override is filled without that evidence.

The runtime uses actual BGE embeddings, Qdrant vector search with degree filtering, and
the BGE CrossEncoder. Groq uses the live API when configured. There is no TF-IDF substitute.
The completed run embedded all 3,052 catalog programs, retrieved and reranked candidates,
and returned ten live Groq explanations using `openai/gpt-oss-120b`. The account's model
list no longer included the initially attempted Llama model; the unsupported call returned
404 and was replaced with the available GPT-OSS model before the final executed copy was saved.
Without `QDRANT_URL`, the actual Qdrant local engine runs; this is not a remote Qdrant
service. Per-component execution status is stored in `data/processed/agent2/final_report.json`
and shown in the notebook's final cell. PostgreSQL writes are outside this validation run.
The original matching weights and university-level blend are preserved; probability terms
are explicit additive contributions, not SHAP values.

Put credentials in the ignored project-root `.env`:

```text
GROQ_API_KEY=your_key_here
# Optional remote vector service:
# QDRANT_URL=https://your-qdrant-endpoint
# QDRANT_API_KEY=your_qdrant_key
```

The loader never prints credential values. Groq receives public program names and model
estimates, without applicant IDs, raw academic records or interest statements. The saved
OOF predictions and demo state are Git-ignored. Models download to ignored `.cache/agent2/`.

Reproduce with:

```powershell
python notebooks/download_agent2_models.py
python notebooks/run_agent2_base_rate_notebook.py
python -m unittest discover -s backend/tests -p test_agent2_base_rate.py -v
```

Sources: [GroupKFold documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html),
[SciPy bounded optimization](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html),
[Stanford doctoral data scope](https://irds.stanford.edu/data-findings/doctoral-admissions),
[Qdrant local mode](https://github.com/qdrant/qdrant-client),
[BGE reranker](https://huggingface.co/BAAI/bge-reranker-base),
[Groq model API](https://console.groq.com/docs/model/llama-3.3-70b-versatile).
