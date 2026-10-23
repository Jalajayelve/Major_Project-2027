"""Agent 3 program ranking extracted from the active notebook implementation.

The runtime uses the notebook's deterministic lexical/TF-IDF path and the
versioned program catalog. Neural models remain optional and disabled.
"""
from pathlib import Path as _A3Path
import math as _a3_math
import re as _a3_re
import warnings as _a3_warnings
import numpy as _a3_np
import pandas as _a3_pd
import joblib as _a3_joblib
from sklearn.feature_extraction.text import TfidfVectorizer as _A3Tfidf
from sklearn.preprocessing import normalize as _a3_normalize

# All notebooks use <repository>/data/raw/agentN/. Explicit overrides also work
# in Colab after mounting/copying the repository; no uploads or installs run here.
AGENT3_CATALOG_PATH = None
AGENT3_JUDGMENTS_PATH = None
AGENT3_ARTIFACT_DIR = _A3Path(__file__).with_name("trained_models_A3")
_a3_roots = (_A3Path.cwd().resolve(), *_A3Path.cwd().resolve().parents)
PROJECT_ROOT = _A3Path(__file__).resolve().parents[4]
if PROJECT_ROOT is None and AGENT3_CATALOG_PATH is None:
    raise FileNotFoundError("Open this notebook inside the project, or set AGENT3_CATALOG_PATH.")



def _a3_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_a3_text(item) for item in value)
    try:
        if _a3_pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _a3_number(value, default=0.5, low=0.0, high=1.0):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return float(_a3_np.clip(number, low, high)) if _a3_math.isfinite(number) else default


def _a3_key(value):
    return " ".join(_a3_text(value).casefold().split())


def _a3_specialization(name):
    pieces = _a3_re.split(r"\s+[-\u2013\u2014]\s+", _a3_text(name), maxsplit=1)
    if len(pieces) == 2 and pieces[1].strip():
        return pieces[1].strip()
    return _a3_re.sub(r"^(?:M\.?S\.?|MSc|MEng|MBA|M\.?A\.?|PhD|BSc|BEng|BS|BA)\s+", "", pieces[0], flags=_a3_re.I).strip()


def _a3_normal_text(value):
    # Shared acronym normalization; these are vocabulary rules, not query-label mappings.
    text = _a3_text(value).casefold()
    for short, long in (("nlp", "natural language processing"), ("iot", "internet of things"),
                        ("ai", "artificial intelligence"), ("vlsi", "very large scale integration")):
        text = _a3_re.sub(r"\b" + long + r"\b", short, text)
    # Domain-specific expansion avoids the ambiguous words "large scale".
    text = _a3_re.sub(r"\bvlsi\b", "vlsi semiconductor integrated circuits", text)
    return " ".join(_a3_re.sub(r"[^\w\s]", " ", text).split())


def load_agent3_catalog_v2(catalog=None):
    required = {"university_name", "program_name"}
    if catalog is not None:
        frame = catalog.copy() if isinstance(catalog, _a3_pd.DataFrame) else _a3_pd.read_csv(catalog)
        source = "explicit catalog"
    else:
        candidate = (_A3Path(AGENT3_CATALOG_PATH) if AGENT3_CATALOG_PATH is not None else
                     PROJECT_ROOT / "data/raw/agent2/agent2_enhanced_program_catalog.csv")
        if not candidate.is_file():
            raise FileNotFoundError(f"Catalog not found: {candidate}. Set AGENT3_CATALOG_PATH explicitly.")
        frame, source = _a3_pd.read_csv(candidate), str(candidate)
    if not required.issubset(frame.columns):
        raise ValueError("Catalog requires university_name and program_name columns.")
    for field in ("university_name", "program_name", "description_text", "curriculum_highlights",
                  "faculty_research_areas", "department", "delivery_mode"):
        if field not in frame.columns:
            frame[field] = ""
        frame[field] = frame[field].map(_a3_text)
    frame = frame.loc[frame["university_name"].ne("") & frame["program_name"].ne("")].copy()
    if frame.empty:
        raise ValueError("Catalog contains no named university/program pairs.")
    frame["_university_key"] = frame["university_name"].map(_a3_key)
    frame["_program_key"] = frame["program_name"].map(_a3_key)
    frame["specialization_v2"] = frame["program_name"].map(_a3_specialization)
    # Resolve duplicate keys deterministically: retain the row with most descriptive content.
    frame["_text_size"] = frame[["description_text", "curriculum_highlights", "faculty_research_areas"]].agg(" ".join, axis=1).str.len()
    before = len(frame)
    frame = frame.sort_values("_text_size", ascending=False, kind="stable").drop_duplicates(["_university_key", "_program_key"])
    frame = frame.sort_values(["_university_key", "_program_key"], kind="stable").reset_index(drop=True)
    frame.attrs.update(source=source, duplicate_rows_removed=before - len(frame))
    return frame


class ProgramRankerV2:
    """Frozen, unsupervised text ranker; external test judgments never fit its weights."""
    lexical_weights = {"specialization": 0.50, "title": 0.30, "content": 0.20}

    def __init__(self, catalog=None, reuse_loaded_models=False, lexical_weights=None, blend_weights=(.6, .3, .1)):
        self.lexical_weights = dict(type(self).lexical_weights if lexical_weights is None else lexical_weights)
        self.blend_weights = tuple(float(x) for x in blend_weights)
        if (set(self.lexical_weights) != {"specialization", "title", "content"}
                or any(not _a3_math.isfinite(x) or x < 0 for x in self.lexical_weights.values())
                or not _a3_math.isclose(sum(self.lexical_weights.values()), 1.0)
                or len(self.blend_weights) != 3
                or any(not _a3_math.isfinite(x) or x <= 0 for x in self.blend_weights)
                or not _a3_math.isclose(sum(self.blend_weights), 1.0)):
            raise ValueError("Weights must sum to one; blend terms must be positive.")
        self.catalog = load_agent3_catalog_v2(catalog)
        self.key_to_index = {(r["_university_key"], r["_program_key"]): int(i) for i, r in self.catalog.iterrows()}
        self.encoder = globals().get("embed_model") if reuse_loaded_models else None
        self.reranker = globals().get("specialization_reranker") if reuse_loaded_models else None
        if reuse_loaded_models and (self.encoder is None or self.reranker is None):
            raise ValueError("Neural mode requires both embed_model (BGE) and specialization_reranker (CrossEncoder).")
        self._dense = None
        self._query_cache = {}
        self._cross_cache = {}
        self._fields = {}
        bodies = self.catalog[["curriculum_highlights", "faculty_research_areas"]].agg(" ".join, axis=1)
        texts = {"specialization": self.catalog["specialization_v2"],
                 "title": self.catalog["program_name"], "content": bodies}
        self._documents = (self.catalog["program_name"] + ". Specialization: " + self.catalog["specialization_v2"]
                           + ". " + bodies).tolist()
        saved_fields = None
        artifact = AGENT3_ARTIFACT_DIR / "agent3_tfidf_fields.joblib"
        try:
            candidate = _a3_joblib.load(artifact)
            if isinstance(candidate, dict) and set(candidate) == set(texts):
                if all(isinstance(value, tuple) and len(value) == 4 and value[1].shape[0] == len(self.catalog)
                       and value[3].shape[0] == len(self.catalog) for value in candidate.values()):
                    for word, _, char, _ in candidate.values():
                        word.transform(["artifact compatibility check"])
                        char.transform(["artifact compatibility check"])
                    saved_fields = candidate
        except (FileNotFoundError, ImportError, ModuleNotFoundError, TypeError, ValueError, AttributeError):
            saved_fields = None
        for field, values in texts.items():
            if saved_fields is not None:
                self._fields[field] = saved_fields[field]
                continue
            normalized = values.map(_a3_normal_text).tolist()
            # A fallback token only prevents empty-vocabulary errors; it carries no relevance.
            normalized = [text or "catalogmissingtext" for text in normalized]
            word = _A3Tfidf(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")
            char = _A3Tfidf(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, strip_accents="unicode")
            self._fields[field] = (word, word.fit_transform(normalized), char, char.fit_transform(normalized))

    def _lexical(self, query, indices):
        query = _a3_normal_text(query)
        components = {}
        for field, (word, word_matrix, char, char_matrix) in self._fields.items():
            a = (word_matrix[indices] @ word.transform([query]).T).toarray().ravel()
            b = (char_matrix[indices] @ char.transform([query]).T).toarray().ravel()
            components[field] = 0.8 * a + 0.2 * b
        return components

    def score(self, query, indices):
        indices = list(indices)
        if not indices:
            return _a3_np.array([]), {}
        if not _a3_text(query):
            return _a3_np.full(len(indices), 0.5), {"no_interest_text": _a3_np.ones(len(indices))}
        parts = self._lexical(query, indices)
        lexical = sum(self.lexical_weights[field] * parts[field] for field in self.lexical_weights)
        # Explicit specialization phrases are stronger evidence than scattered
        # overlapping words. Early mentions receive a modest, continuous boost.
        # This generic retrieval feature never reads benchmark labels.
        normalized_query = _a3_normal_text(query)
        phrase = []
        for idx in indices:
            specialization = _a3_normal_text(self.catalog.iloc[idx]["specialization_v2"])
            match = _a3_re.search(r"\b" + _a3_re.escape(specialization) + r"\b", normalized_query) if specialization else None
            position = len(normalized_query[:match.start()].split()) if match else 0
            phrase.append(1.0 / (1.0 + 0.1 * position) if match else 0.0)
        parts["specialization_phrase"] = _a3_np.array(phrase)
        lexical = 0.80 * lexical + 0.20 * parts["specialization_phrase"]
        scores = lexical.copy()
        if self.encoder is not None:
            try:
                if self._dense is None:
                    vectors = _a3_np.asarray(self.encoder.encode(self._documents, batch_size=64, show_progress_bar=False), dtype=float)
                    if vectors.ndim != 2 or len(vectors) != len(self.catalog) or not _a3_np.isfinite(vectors).all():
                        raise ValueError("Encoder returned invalid program vectors")
                    self._dense = _a3_normalize(vectors)
                query_key = _a3_text(query)
                if query_key not in self._query_cache:
                    qvec = _a3_np.asarray(self.encoder.encode([query_key], show_progress_bar=False), dtype=float)
                    if qvec.ndim != 2 or len(qvec) != 1 or not _a3_np.isfinite(qvec).all():
                        raise ValueError("Encoder returned an invalid query vector")
                    self._query_cache[query_key] = _a3_normalize(qvec)[0]
                semantic = _a3_np.clip(self._dense[indices] @ self._query_cache[query_key], 0, 1)
                parts["semantic"] = semantic
                scores = 0.75 * lexical + 0.25 * semantic
            except Exception as exc:
                raise RuntimeError("Neural encoder failed; evaluation cannot silently change models.") from exc
        if self.reranker is not None:
            try:
                # Score every shortlisted candidate in a batch. No score discontinuity at a top-k boundary.
                missing = [i for i in indices if (query, i) not in self._cross_cache]
                if missing:
                    raw = _a3_np.asarray(self.reranker.predict([(query, self._documents[i]) for i in missing], batch_size=32, show_progress_bar=False), dtype=float).reshape(-1)
                    if len(raw) != len(missing) or not _a3_np.isfinite(raw).all():
                        raise ValueError("CrossEncoder must return one finite score per pair")
                    for i, value in zip(missing, raw):
                        self._cross_cache[(query, i)] = 1.0 / (1.0 + _a3_math.exp(-float(_a3_np.clip(value, -40, 40))))
                cross = _a3_np.array([self._cross_cache[(query, i)] for i in indices])
                parts["cross_encoder"] = cross
                scores = 0.85 * scores + 0.15 * cross
            except Exception as exc:
                raise RuntimeError("CrossEncoder failed; evaluation cannot silently change models.") from exc
        return _a3_np.clip(scores, 0, 1), parts


def program_agent_v2(state, ranker=None):
    """Return a copied state, ranked strictly within Agent 2's supplied program shortlist."""
    ranker = ProgramRankerV2() if ranker is None else ranker
    output_state = dict(state)
    profile = state.get("profile") or {}
    query = _a3_text(profile.get("interests_text")) or _a3_text(profile.get("academic_interests")) or _a3_text(profile.get("target_program"))
    context = _a3_text(profile.get("target_program"))
    degree_aliases = {"ms": "ms", "msc": "ms", "masterofscience": "ms", "meng": "meng", "masterofengineering": "meng", "mba": "mba", "masterofbusinessadministration": "mba", "phd": "phd", "doctorofphilosophy": "phd", "ma": "ma", "masterofarts": "ma", "bs": "bs", "bsc": "bs", "bachelorofscience": "bs", "ba": "ba", "bachelorofarts": "ba", "beng": "beng", "bachelorofengineering": "beng"}
    degree_key = lambda value: _a3_re.sub(r"[^a-z]", "", _a3_text(value).casefold())
    requested_degree = degree_aliases.get(degree_key(profile.get("target_degree")))
    candidates, skipped = {}, []
    for university in (state.get("matched_universities") or []):
        parent_name = _a3_text(university.get("university_name")) or _a3_text(university.get("university"))
        for program in (university.get("programs") or []):
            uni = _a3_text(program.get("university_name")) or _a3_text(program.get("university")) or parent_name
            name = _a3_text(program.get("program_name"))
            if parent_name and _a3_key(uni) != _a3_key(parent_name):
                skipped.append({"university": uni, "program_name": name, "reason": "university conflicts with shortlist group"})
                continue
            idx = ranker.key_to_index.get((_a3_key(uni), _a3_key(name)))
            if idx is None:
                skipped.append({"university": uni, "program_name": name, "reason": "not in catalog"})
                continue
            catalog_degree = degree_aliases.get(degree_key(ranker.catalog.iloc[idx].get("degree_type"))) or degree_aliases.get(degree_key(name.split()[0]))
            if requested_degree and catalog_degree and catalog_degree != requested_degree:
                skipped.append({"university": uni, "program_name": name, "reason": "requested degree mismatch"})
                continue
            prior = _a3_number(program.get("match_score"))
            if idx not in candidates or prior > candidates[idx][0]:
                candidate = dict(program)
                candidate["country"] = (_a3_text(program.get("country")) or
                                        _a3_text(university.get("country")) or
                                        _a3_text(ranker.catalog.iloc[idx].get("country")))
                candidates[idx] = (prior, candidate)
    indices = list(candidates)
    fit, parts = ranker.score(query, indices)
    if indices and query and context and _a3_normal_text(context) != _a3_normal_text(query):
        # Stated interests stay primary; target field only provides a weak tie-break signal.
        field_context = ranker._lexical(context, indices)["title"]
        parts["field_context"] = field_context
        fit = 0.95 * fit + 0.05 * field_context
    programs = []
    for pos, idx in enumerate(indices):
        row = ranker.catalog.iloc[idx]
        prior, candidate = candidates[idx]
        months = _a3_number(row.get("duration_months"), default=None, low=0, high=1200)
        duration = f"{months:g} months" if months is not None and months > 0 else "Not specified"
        mode = _a3_text(row.get("delivery_mode"))
        probability = _a3_number(candidate.get("admit_probability"), default=None)
        # No admission probability is invented. Renormalize only available terms.
        fit_weight, prior_weight, admit_weight = ranker.blend_weights
        terms = [(prior_weight, prior)]
        if query:
            terms.append((fit_weight, float(fit[pos])))
        if probability is not None:
            terms.append((admit_weight, probability))
        score = sum(weight * value for weight, value in terms) / sum(weight for weight, _ in terms)
        programs.append({"university": row["university_name"], "program_name": row["program_name"],
                         "specialization": row["specialization_v2"], "duration": duration,
                         "mode": mode or "Not specified", "mode_is_placeholder": not bool(mode),
                         "specialization_fit_score": float(fit[pos]), "match_score": float(score),
                         "admit_probability": probability, "tier": candidate.get("tier") or "Unknown",
                         "admission_estimate_available": probability is not None,
                         "country": candidate.get("country") or None,
                         "agent2_match_score": prior,
                         "ranking_components": {key: float(values[pos]) for key, values in parts.items()},
                         "score_type": "relevance_not_probability"})
    output_state["programs"] = sorted(programs, key=lambda item: (-item["match_score"], item["university"], item["program_name"]))
    output_state["status"] = "program_done"
    output_state["programs_skipped"] = skipped
    output_state["programs_warnings"] = (
        [f"{len(skipped)} candidate(s) could not be ranked; inspect programs_skipped."] if skipped else []
    )
    if skipped:
        _a3_warnings.warn(output_state["programs_warnings"][0], RuntimeWarning)
    output_state["program_ranking_diagnostics"] = {"method": "title-aware-hybrid-v2", "query_available": bool(query),
                                                    "skipped_candidates": skipped, "candidate_count": len(indices)}
    return output_state


def rank_programs(profile: dict, matched_universities: list[dict]) -> dict:
    """Rank catalog programs belonging to Agent 2's supplied university shortlist."""
    if not isinstance(profile, dict) or not isinstance(matched_universities, list):
        raise ValueError("Profile and matched_universities are required.")
    ranker = ProgramRankerV2()
    catalog = ranker.catalog
    catalog_by_university = {}
    for _, row in catalog.iterrows():
        catalog_by_university.setdefault(_a3_key(row["university_name"]), []).append(row)
    shortlist = []
    for university in matched_universities:
        name = _a3_text(university.get("name") or university.get("university_name"))
        if not name:
            continue
        rows = catalog_by_university.get(_a3_key(name), [])
        shortlist.append({
            "university_name": name,
            "country": _a3_text(university.get("country")),
            "programs": [
                {
                    "university_name": row["university_name"],
                    "program_name": row["program_name"],
                    "country": row.get("country"),
                    "match_score": university.get("match_score", 0.5),
                    "tier": university.get("tier"),
                }
                for row in rows
            ],
        })
    state = {
        "profile": {
            "interests_text": profile.get("interests_text") or profile.get("field") or "",
            "academic_interests": profile.get("academic_interests", ""),
            "target_program": profile.get("field") or profile.get("target_program", ""),
            "target_degree": profile.get("degree_goal") or profile.get("target_degree", ""),
        },
        "matched_universities": shortlist,
    }
    result = program_agent_v2(state, ranker=ranker)
    return {
        "agent": "program",
        "analysis": "program_ranking",
        "programs": result.get("programs", []),
        "programs_skipped": result.get("programs_skipped", []),
        "programs_warnings": result.get("programs_warnings", []),
        "program_ranking_diagnostics": result.get("program_ranking_diagnostics", {}),
        "notice": "Agent 3 program-fit ranking; scores are relevance scores, not admission probabilities.",
    }


# Deterministic, offline default. To opt in to neural models already loaded in this kernel:
