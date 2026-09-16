# Integrating Multi-Agent Systems in Study Abroad Counseling
## An Engineering Framework for Enhanced Decision-Making

---

## 1. System Overview

Seven specialized agents, each an independent microservice, coordinated by a central orchestrator (LangGraph), sharing a common student-context object and writing/reading from a shared PostgreSQL + Qdrant backend. This extends your existing Agent 2 (University Matching) stack — same orchestration, DB, and RAG pattern — to the full pipeline.

```
                        ┌─────────────────────────┐
                        │   React Frontend (3D)   │
                        └────────────┬────────────┘
                                     │ REST/WebSocket
                        ┌────────────▼────────────┐
                        │   FastAPI Gateway (BFF)  │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  LangGraph Orchestrator  │
                        │   (StateGraph, shared    │
                        │    student_state object) │
                        └────────────┬────────────┘
        ┌───────┬───────┬───────┬───┴───┬───────┬───────┬───────┐
        ▼       ▼       ▼       ▼       ▼       ▼       ▼
     Agent1  Agent2  Agent3  Agent4  Agent5  Agent6  Agent7
    (Profile)(Univ) (Program)(Finance)(Scholar)(Career)(ExtraC)
        │       │       │       │       │       │       │
        └───────┴───────┴───────┴───────┴───────┴───────┴────► PostgreSQL + Qdrant
```

---

## 2. Agent-by-Agent Design

### Agent 1 — Student Profile Agent (foundation node — runs first, always)
- **Input:** onboarding form / uploaded transcripts, resume (PDF/docx parsed via `pdfplumber`/`python-docx`)
- **Model:** lightweight NER + classification (spaCy/HuggingFace `bert-base` fine-tuned) to extract GPA, test scores (GRE/IELTS/TOEFL/SAT), work experience, degree level, target intake
- **Output:** structured `StudentProfile` JSON — this becomes the shared context object every downstream agent reads
- **Storage:** PostgreSQL `students` table (structured fields) + Qdrant `student_profile_vectors` collection (embedding of free-text bio/SOP for later semantic matching)

### Agent 2 — University Agent (yours — reused as-is)
- RAG pipeline: Qdrant + BAAI embeddings + CrossEncoder reranker + Groq LLaMA explanations, RandomForestClassifier for admit-probability
- **Input:** `StudentProfile` (from Agent 1)
- **Output:** ranked list of `{university, country, type: public/private, region, admit_probability, reasoning}`
- **Feeds into:** Agent 3 (Program), Agent 4 (Financial) — both scoped per shortlisted university

### Agent 3 — Program Agent
- **Input:** shortlist from Agent 2 + student's academic background/interests from Agent 1
- **Model:** semantic similarity search (sentence-transformers) over a `programs` Qdrant collection (course catalogs, specializations, syllabi scraped/ingested per university) + optional LLM re-ranking for "fit explanation"
- **Output:** `{university, program_name, specialization, duration, mode, match_score}`
- **Feeds into:** Agent 4, Agent 6 (Career)

### Agent 4 — Financial Agent
- **Input:** university + program shortlist
- **Model:** rule-based/regression estimator trained on tuition + cost-of-living datasets (Numbeo API, university fee pages, IPEDS cost data) — a Gradient Boosting Regressor predicting total annual cost by region/university/program-level
- **Output:** `{university, tuition_annual, living_cost_annual, total_cost, currency}`
- **Feeds into:** Agent 5 (Scholarship)

### Agent 5 — Scholarship Agent
- **Input:** cost estimate from Agent 4 + student profile (merit indicators from Agent 1, Agent 7)
- **Model:** classification model (funding-gap detector) + RAG over a scholarships/grants Qdrant collection, filtered by eligibility rules (nationality, GPA cutoff, field of study)
- **Output:** `{scholarship_name, coverage_%, eligibility_match, deadline}` + computed `funding_gap`

### Agent 6 — Career Agent
- **Input:** Program Agent output + Student Profile
- **Model:** classification (Research-track vs Job-track alignment) using a fine-tuned classifier on outcomes data (LinkedIn/university outcome reports if available) — outputs alignment score against student's stated goal
- **Output:** `{career_path: research/industry, alignment_score, expected_roles, avg_placement_stats}`

### Agent 7 — Extracurricular Agent
- **Input:** resume/CV text, publications, patents
- **Model:** NER + scoring heuristic (weighted rubric: leadership, volunteering, competitions, publications, patents) → normalized `profile_strength_score`, plus this feeds BACK into Agent 2's RandomForestClassifier as a feature and into Agent 5 (merit-based scholarship eligibility)
- **Output:** `{leadership_score, research_score, achievements: [...], profile_strength_score}`
- **Sub-module — SOP/LOR Evaluation:** scores uploaded Statement of Purpose / Letters of Recommendation and feeds a `sop_score` into `profile_strength_score`. Three cheap, reuse-existing-infra layers instead of training a custom model:
  1. **Structural scoring** (rule-based, no ML): length, personalization (mentions target university/program by name), narrative coherence (motivation → experience → goals present)
  2. **Semantic alignment**: embed the SOP with the same sentence-transformer/BAAI embedding model Agent 2 already uses, cosine-similarity against the target program description (from Agent 3's `programs` Qdrant collection)
  3. **LLM rubric pass**: one Groq LLaMA call scoring clarity, specificity of goals, program alignment, and authenticity red flags, returned as structured JSON — no fine-tuning needed, reuses existing Groq integration

  ```python
  def score_sop(sop_text: str, program_description: str) -> dict:
      embedding = embed_model.encode(sop_text)
      program_embedding = embed_model.encode(program_description)
      alignment_score = cosine_similarity(embedding, program_embedding)

      rubric_result = groq_llm.invoke(f"""
      Score this SOP on: clarity (1-10), specificity of goals (1-10),
      program alignment (1-10), authenticity flags (list).
      Program context: {program_description}
      SOP: {sop_text}
      Return JSON only.
      """)
      return {"alignment_score": alignment_score, **json.loads(rubric_result)}
  ```
  Runs once per student (not per-university) — cheap even with LLM calls, and triangulating three signals is more defensible in evaluation than a single opaque score.

---

## 3. Orchestration & Data Flow (LangGraph StateGraph)

```
START → Agent1(Profile)
      → Agent7(Extracurricular)   [parallel with Agent1's later stage]
      → Agent2(University)        [needs Profile + Extracurricular score]
      → [Agent3(Program), Agent4(Financial)]  [parallel, both need Agent2 output]
      → Agent4 → Agent5(Scholarship)
      → Agent3 → Agent6(Career)
      → JOIN → Recommendation Synthesizer node (Groq LLaMA) → Final Report
      → END
```

- Shared state = single Pydantic `GraphState` object passed node-to-node; each agent reads what it needs, writes its own namespaced output key.
- A final **Synthesizer node** (LLM call) merges all 7 outputs into one narrative counseling report + a structured recommendation table — this is what the frontend renders.
- Failure handling: LangGraph conditional edges retry a node once, then fall back to a rule-based default (e.g., if Scholarship Agent times out, show cost without funding suggestions rather than blocking the pipeline).

---

## 4. Explainability Layer — SHAP

SHAP applies only to the tabular/tree-based models, not the LLM calls — it explains *why* a model made its call, turning opaque predictions into an auditable report.

| Model | Agent | SHAP explains |
|---|---|---|
| RandomForestClassifier (admit probability) | Agent 2 | which features pushed admit-probability up/down (GPA, test scores, extracurricular_score, etc.) |
| GradientBoostingRegressor (cost estimate) | Agent 4 | which factors drove the tuition/living-cost prediction |
| Funding-gap classifier | Agent 5 | which features triggered a scholarship-eligibility flag |

```python
import shap

explainer = shap.TreeExplainer(admit_rf_model)
shap_values = explainer.shap_values(student_feature_vector)

top_factors = sorted(
    zip(feature_names, shap_values[0]),
    key=lambda x: abs(x[1]), reverse=True
)[:5]
# e.g. [("GPA", +0.18), ("extracurricular_score", +0.09), ("test_score", -0.04)]
```

Each tabular-model agent returns `explainability: top_factors` alongside its normal output.

**Where it surfaces:**
- **Synthesizer node**: fed as grounding context so the LLM's narrative explanation is based on real feature weights instead of an ungrounded rationale
- **Frontend**: a SHAP waterfall/bar chart (Recharts) per recommendation — feature contributions per university/cost estimate/scholarship flag

Add `shap` to requirements — pip-installable, works directly with scikit-learn models, no compatibility issues with the existing stack.

---

## 5. Backend Stack (Python-first)

| Layer | Technology | Why |
|---|---|---|
| Orchestration | LangGraph | matches your existing Agent 2 setup |
| API Gateway | FastAPI (async) | native Python, pairs with all ML code |
| Vector DB | Qdrant | already used in Agent 2; one collection per agent (`programs`, `scholarships`, `student_profile_vectors`) |
| Relational DB | PostgreSQL (SQLAlchemy + Alembic) | structured student/university/cost data |
| ML models | scikit-learn (RF, GBR), HuggingFace Transformers, sentence-transformers | training compatible, all Python |
| Explainability | SHAP | model-agnostic feature attribution for Agents 2, 4, 5 |
| LLM inference | Groq (LLaMA) | already integrated, fast + cheap for explanations/synthesis |
| Task queue | Celery + Redis | run long agent chains async, avoid blocking API |
| Auth | FastAPI + JWT (OAuth2 password flow) | standard |
| Containerization | Docker Compose (7 agent services + gateway + Postgres + Qdrant + Redis) | mirrors microservice-per-agent design |

## 6. Frontend Stack (Responsive + 3D)

| Layer | Technology |
|---|---|
| Framework | React + Vite + TypeScript |
| Styling | Tailwind CSS (responsive grid/flex) |
| 3D | Three.js via `@react-three/fiber` + `@react-three/drei` — e.g., an interactive 3D globe for university/region visualization, animated "agent pipeline" visualization showing each agent lighting up as it completes |
| State | Zustand or Redux Toolkit |
| Data viz | Recharts (cost comparisons, scholarship coverage, admit-probability bars, SHAP waterfall/bar charts) |
| Realtime | WebSocket to FastAPI for live agent-progress updates as the pipeline runs |

---

## 7. Database Schema (core tables)

- `students` (profile fields, FK to uploads)
- `universities` (name, country, region, type public/private)
- `programs` (FK universities, specialization, duration)
- `costs` (FK universities/programs, tuition, living cost, currency, year)
- `scholarships` (name, coverage_%, eligibility_json, deadline)
- `career_outcomes` (FK programs, track, placement_stats)
- `extracurricular_scores` (FK students, category scores, evidence_json)
- `recommendations` (FK students, final synthesized report, timestamp)

Qdrant collections mirror the text-heavy ones: `student_profile_vectors`, `university_vectors` (yours), `program_vectors`, `scholarship_vectors`.

---

## 8. End-to-End Request Flow

1. Student submits profile + documents → React form → FastAPI → Agent 1 parses & stores.
2. Frontend triggers `/run-pipeline` → Celery task kicks off LangGraph run.
3. WebSocket streams per-agent status (`profile_done`, `university_done`, ...) to the 3D pipeline visualization.
4. Each agent writes its output to Postgres/Qdrant and appends to `GraphState`.
5. Synthesizer node produces final report → stored in `recommendations`, pushed to frontend.
6. Frontend renders: 3D globe of shortlisted universities, program/cost/scholarship comparison tables, career-alignment chart, downloadable PDF report.

---

## 9. Suggested Build Order (team of 4+ mapped to your existing capstone)

1. Agent 1 (Profile) — foundation, unblocks everyone
2. Agent 2 (University) — already done by you
3. Agent 3 + Agent 4 in parallel (Program, Financial)
4. Agent 5 (Scholarship) — depends on 4
5. Agent 6 (Career) — depends on 3
6. Agent 7 (Extracurricular) — can be built anytime after Agent 1, feeds back into Agent 2's classifier as bonus feature
7. Orchestrator + Synthesizer wiring
8. Frontend (start early in parallel with mock JSON, swap to live API once gateway is up)

---

*Next step options: I can turn any one agent into working Python code, scaffold the FastAPI gateway + LangGraph graph, wire up the SHAP explainer or SOP/LOR scorer, or build the 3D React pipeline visualization — say which one and I'll build it out.*
