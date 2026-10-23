"""Private offline inference worker for the updated five-feature Agent 2 bundle.

No admission training, artifact writes, notebook execution, or external services.
The supplied repository bundle is trusted pickle input, never a user upload.
"""
from pathlib import Path
import json
import sys
import warnings


def retrieve_candidates(candidate):
    """Offline catalog text retrieval, independently of admission artifacts."""
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from meridian.services.agent2 import CATALOG

    catalog = pd.read_csv(CATALOG)
    eligible = catalog[catalog["degree_type"] == candidate["degree"]].copy()
    text_columns = ["program_name", "university_name", "description_text", "curriculum_highlights", "faculty_research_areas"]
    texts = catalog[text_columns].fillna("").astype(str).agg(" ".join, axis=1)
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    # Fit a text index over the catalog; this does not retrain any ML artifact.
    matrix = vectorizer.fit_transform(texts)
    # Degree is already a hard filter. Including 'MS' in the text query would
    # retrieve unrelated fields even when the requested field has no overlap.
    similarities = cosine_similarity(vectorizer.transform([candidate["field"]]), matrix)[0]
    eligible["similarity"] = similarities[eligible.index]
    return eligible[eligible["similarity"] > 0].sort_values("similarity", ascending=False, kind="stable").head(20)


def match(candidate):
    from meridian.services.agent2 import MODEL_DIR, ROOT, NOTICE, require_bundle, validate_result, score_band
    import importlib.metadata
    manifest = require_bundle()
    for package, expected_version in manifest["versions"].items():
        if importlib.metadata.version(package) != expected_version:
            raise ValueError(f"Agent 2 requires {package}=={expected_version} from its training runtime.")
    import joblib
    import numpy as np
    import pandas as pd
    import hashlib
    import shap
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.cluster import KMeans
    from sklearn.exceptions import InconsistentVersionWarning
    from sklearn.preprocessing import StandardScaler
    # Serialized sklearn objects must come from a compatible training runtime.
    warnings.simplefilter("error", InconsistentVersionWarning)
    load = lambda name: joblib.load(MODEL_DIR / (name + ".joblib"))
    training_path = ROOT / "data/raw/agent2/agent2_training.csv"
    if hashlib.sha256(training_path.read_bytes()).hexdigest() != manifest["training_data_sha256"]:
        raise ValueError("Cannot verify the model's supported GRE range.")
    training_gre = pd.read_csv(training_path, usecols=["gre_quant"])["gre_quant"].dropna()
    gre_lo, gre_hi = float(training_gre.min()), float(training_gre.max())
    if candidate["gre_missing"]:
        evidence_reason = "Insufficient evidence: GRE Quant is missing; the training data contains no missing-GRE examples."
    elif not gre_lo <= candidate["gre_numeric"] <= gre_hi:
        evidence_reason = f"Insufficient evidence: GRE Quant is outside this model's observed training range ({gre_lo:.2f} to {gre_hi:.2f})."
    else:
        evidence_reason = ""
    features = load("agent2_feature_columns")
    expected = ["tier_score", "gpa_numeric", "gre_numeric", "gre_missing", "applicant_cluster"]
    if features != expected or load("agent2_agent1_tier_features") != ["tier_score"]:
        raise ValueError("Unsupported Agent 2 feature bundle; do not combine model versions.")
    representation = load("agent2_agent1_tier_representation")
    if representation["column"] != "tier_score" or representation["dtype"] != "float":
        raise ValueError("Invalid tier representation.")
    lo, hi = representation["valid_range"]
    if not np.isfinite([lo, hi]).all() or not 0 <= lo < hi <= 100:
        raise ValueError("Invalid tier training range.")
    model = load("agent2_admission_model")
    if not isinstance(model, CalibratedClassifierCV) or model.n_features_in_ != len(features):
        raise ValueError("Expected the updated calibrated admission classifier.")
    if list(model.feature_names_in_) != features or set(model.classes_) != {0, 1}:
        raise ValueError("Admission model feature/class mismatch.")
    threshold = float(load("agent2_decision_threshold"))
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid admission decision threshold.")
    cluster_features = load("applicant_cluster_features")
    if cluster_features != ["gpa_numeric", "gre_numeric"]:
        raise ValueError("Applicant cluster feature mismatch.")
    medians = load("applicant_cluster_medians")
    if set(medians) != set(cluster_features) or not np.isfinite(list(medians.values())).all():
        raise ValueError("Invalid applicant clustering medians.")
    scaler, cluster = load("applicant_cluster_scaler"), load("applicant_cluster_model")
    if not isinstance(scaler, StandardScaler) or not isinstance(cluster, KMeans):
        raise ValueError("Invalid applicant clustering objects.")
    if list(scaler.feature_names_in_) != cluster_features or cluster.n_features_in_ != 2:
        raise ValueError("Applicant clustering order mismatch.")
    explainer = load("agent2_shap_explainer")
    if not isinstance(explainer, shap.Explainer):
        raise ValueError("Invalid SHAP object.")
    # ExactExplainer retains DataFrame names on its masker, while its own
    # feature_names may be None. Validate the saved background and bound model.
    explanation_names = explainer.feature_names
    if explanation_names is None:
        explanation_names = getattr(explainer.masker, "feature_names", [])
    explained_model = getattr(explainer.model.inner_model, "__self__", None)
    if (list(explanation_names) != features or
            list(getattr(explained_model, "feature_names_in_", [])) != features or
            set(getattr(explained_model, "classes_", [])) != {0, 1}):
        raise ValueError("SHAP feature mismatch.")
    explanation_positive = list(explained_model.classes_).index(1)

    eligible = retrieve_candidates(candidate)
    gre = medians["gre_numeric"] if candidate["gre_missing"] else candidate["gre_numeric"]
    applicant = pd.DataFrame([[candidate["gpa_numeric"], gre]], columns=cluster_features)
    applicant_cluster = int(cluster.predict(scaler.transform(applicant))[0])
    positive = list(model.classes_).index(1)
    rows = []
    for _, program in eligible.iterrows():
        tier = float(program["tier_score"])
        min_gpa = float(program["min_gpa"])
        if not np.isfinite([tier, min_gpa]).all() or not 0 <= tier <= 100 or not 0 <= min_gpa <= 4:
            raise ValueError("Invalid required catalog GPA/tier.")
        frame = pd.DataFrame([[tier, candidate["gpa_numeric"],
            0 if candidate["gre_missing"] else candidate["gre_numeric"],
            candidate["gre_missing"], applicant_cluster]], columns=features)
        probability = None if evidence_reason else float(model.predict_proba(frame)[0, positive])
        factors = []
        if not evidence_reason:
            values = np.asarray(explainer(frame).values)
            if values.shape != (1, len(features), 2):
                raise ValueError("Unexpected SHAP class/feature dimensions.")
            impacts = values[0, :, explanation_positive]
            if len(impacts) != len(features) or not np.isfinite(impacts).all():
                raise ValueError("Invalid SHAP result.")
            factors = [{"feature": f, "impact": float(v)} for f, v in
                       sorted(zip(features, impacts), key=lambda p: abs(p[1]), reverse=True)[:3]]
        # Offline variation of notebook default weights: use TF-IDF cosine
        # directly, rather than applying the reranker's sigmoid to it.
        fit = max(0, min(1, 1 - abs(candidate["gpa_numeric"] - min_gpa) / 4))
        score = .35 * float(program["similarity"]) + .25 * tier / 100 + .25 * fit + .15 * candidate["profile_strength_score"] / 100
        tuition = None if pd.isna(program["tuition_out_state_usd"]) else float(program["tuition_out_state_usd"])
        note = "Matched using catalog text, program tier, GPA fit and your Agent 7 score."
        if evidence_reason:
            note += " " + evidence_reason
        if not lo <= tier <= hi:
            note += " Program tier is outside the model's training range."
        rows.append({"id": str(program["program_id"]), "name": str(program["university_name"]),
            "program": str(program["program_name"]), "country": str(program["country"]),
            "region": str(program["region"]), "institution_type": str(program["institution_type"]),
            "tier": "Insufficient evidence" if evidence_reason else score_band(probability),
            "evidence_reason": evidence_reason,
            "probability": probability, "prob_str": "Insufficient evidence" if evidence_reason else f"{probability:.1%}",
            "match_score": score, "match_str": f"{score:.1%}", "tier_score": tier,
            "tuition": tuition, "tuition_str": f"${tuition:,.0f}" if tuition is not None else "Not listed",
            "factors": factors, "note": note})
    rows.sort(key=lambda r: (-r["match_score"], r["id"]))
    return validate_result({"universities": rows[:10], "notice": NOTICE, "retrieval": "TF-IDF"})


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    print(json.dumps(match(json.load(sys.stdin)), allow_nan=False))


if __name__ == "__main__":
    main()
