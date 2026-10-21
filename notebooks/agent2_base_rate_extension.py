# %% Setup and input audit
from pathlib import Path
import os
import json
import hashlib
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss, brier_score_loss
from threadpoolctl import threadpool_limits

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
            if (p / 'data/raw/agent2/agent2_training.csv').exists())
OUT = ROOT / 'data/processed/agent2'
OUT.mkdir(parents=True, exist_ok=True)
TRAIN_PATH = ROOT / 'data/raw/agent2/agent2_training.csv'
CATALOG_PATH = ROOT / 'data/raw/agent2/agent2_enhanced_program_catalog.csv'
train_v3 = pd.read_csv(TRAIN_PATH)
catalog_v3 = pd.read_csv(CATALOG_PATH)
assert train_v3.applicant_id.notna().all()
assert train_v3.admit_result.isin([0, 1]).all()
assert catalog_v3.program_id.is_unique
counts = train_v3.applicant_id.value_counts()
rows_a, rows_b = train_test_split(np.arange(len(train_v3)), test_size=.2, random_state=42,
                                stratify=train_v3.admit_result)
audit_v3 = {
    'training_sha256': hashlib.sha256(TRAIN_PATH.read_bytes()).hexdigest(),
    'catalog_sha256': hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest(),
    'rows': len(train_v3), 'applicants': int(train_v3.applicant_id.nunique()),
    'repeated_applicants': int((counts > 1).sum()),
    'extra_rows_for_repeat_applicants': int(train_v3.applicant_id.duplicated().sum()),
    'row_split_overlapping_applicants': len(set(train_v3.iloc[rows_a].applicant_id) & set(train_v3.iloc[rows_b].applicant_id)),
    'repeat_applicants_with_different_outcomes': int((train_v3.groupby('applicant_id').admit_result.nunique() > 1).sum()),
    'profile_strength_std': float(train_v3.profile_strength_score.std()),
    'profile_strength_label_correlation': float(train_v3.profile_strength_score.corr(train_v3.admit_result)),
    'selectivity_label_correlation': float(train_v3.tier_score.corr(train_v3.admit_result)),
    'base_rate_label_correlation': float(train_v3.program_admit_rate.corr(train_v3.admit_result)),
    'base_rate_selectivity_correlation': float(catalog_v3.program_admit_rate.corr(catalog_v3.tier_score)),
    'provenance': 'UNVERIFIED: first added in git commit 313d617; no source URL, collection protocol, application year, or generation script located.',
    'interpretation': 'Repeated applicants have identical labels across programs. Compatible with applicant labels replicated onto a catalog; not verified program-specific admissions outcomes. Correlation alone cannot prove synthetic origin.',
}
rate_line_v3 = np.polyfit(catalog_v3.tier_score, catalog_v3.program_admit_rate, 1)
audit_v3['catalog_rate_linear_formula'] = {'tier_slope':float(rate_line_v3[0]),'intercept':float(rate_line_v3[1]),
    'max_absolute_residual':float(np.max(np.abs(np.polyval(rate_line_v3,catalog_v3.tier_score)-catalog_v3.program_admit_rate)))}
audit_v3['repeat_ids_with_varying_applicant_features'] = train_v3.groupby('applicant_id')[
    ['gpa','gre_quant','gre_verbal','profile_strength_score']].nunique(dropna=False).gt(1).sum().to_dict()
catalog_join_v3 = train_v3.merge(catalog_v3[['program_id','tier_score','program_admit_rate']],on='program_id',
    suffixes=('_training','_catalog'),validate='many_to_one')
audit_v3['catalog_matched_training_rows'] = len(catalog_join_v3)
audit_v3['max_training_catalog_rate_difference'] = float((catalog_join_v3.program_admit_rate_training-catalog_join_v3.program_admit_rate_catalog).abs().max())
audit_v3['max_training_catalog_tier_difference'] = float((catalog_join_v3.tier_score_training-catalog_join_v3.tier_score_catalog).abs().max())
(OUT / 'data_audit.json').write_text(json.dumps(audit_v3, indent=2), encoding='utf-8')
print(json.dumps(audit_v3, indent=2))
print('\nOutcome by program tier (descriptive audit):')
print(train_v3.groupby(pd.cut(train_v3.tier_score, [0,60,70,80,90,100]), observed=True).admit_result.agg(['count','mean']).to_string())

# %% Monotone admission model with a fixed logit offset
APPLICANT_FEATURES_V3 = ['gpa', 'gre_quant', 'gre_verbal', 'profile_strength_score']
MODEL_VERSION_V3 = 'agent2-offset-monotone-v3.0'


class OffsetAdmissionModel:
    """Experimental estimator; coefficients fit unverified labels, not real admissions.

    logit(p) = logit(program_admit_rate) + log(3)*tanh(z/log(3))
    z = sum(beta_j * standardized_applicant_j) - gamma*(tier_score-70)/10
    beta_j >= 0, gamma >= 0.1. No free intercept can erase the prior.
    Odds adjustment is bounded to [1/3, 3]; these are declared policy choices,
    fixed before CV, not empirically calibrated admissions constraints.
    """
    def __init__(self, use_profile_strength=True):
        self.features = [f for f in APPLICANT_FEATURES_V3
                         if use_profile_strength or f != 'profile_strength_score']
        self.cap = float(np.log(3.0))
        self.penalty = .01
        self.classes_ = np.array([0, 1])

    def _design(self, frame):
        a = frame[self.features].apply(pd.to_numeric, errors='coerce')
        a = a.fillna(pd.Series(self.medians))
        arr = (a.to_numpy() - np.array([self.medians[f] for f in self.features])) / self.scales
        tier = pd.to_numeric(frame.tier_score, errors='raise').to_numpy(float)
        rate = pd.to_numeric(frame.program_admit_rate, errors='raise').to_numpy(float)
        if not np.isfinite(tier).all() or not ((tier >= 0) & (tier <= 100)).all():
            raise ValueError('Program tier must be finite, between 0 and 100.')
        if not np.isfinite(rate).all() or not ((rate > 0) & (rate < 1)).all():
            raise ValueError('Explicit program_admit_rate in (0,1) required; no university-rate substitution.')
        return np.column_stack([arr, -(tier - 70.) / 10.]), logit(rate)

    def fit(self, frame, y):
        a = frame[self.features].apply(pd.to_numeric, errors='coerce')
        self.medians = a.median().to_dict()
        if not all(np.isfinite(list(self.medians.values()))):
            raise ValueError('Training feature is entirely missing.')
        self.scales = a.fillna(pd.Series(self.medians)).std(ddof=0).clip(lower=1e-6).to_numpy()
        X, offset = self._design(frame)
        y = np.asarray(y, dtype=float)
        # One unit of total weight per applicant despite replicated application rows.
        freq = frame.applicant_id.map(frame.applicant_id.value_counts()).to_numpy(float)
        w = 1. / freq
        w /= w.sum()
        def objective(b):
            t = np.tanh((X @ b) / self.cap)
            logits = offset + self.cap * t
            loss = np.sum(w * (np.logaddexp(0, logits) - y * logits)) + self.penalty * np.sum(b*b)/2
            grad = X.T @ (w * (expit(logits) - y) * (1-t*t)) + self.penalty*b
            return loss, grad
        result = minimize(objective, np.full(X.shape[1], .1), jac=True, method='L-BFGS-B',
                          bounds=[(0, None)] * len(self.features) + [(.1, None)],
                          options={'maxiter': 1000, 'ftol': 1e-12})
        if not result.success:
            raise RuntimeError('Offset optimization failed: ' + result.message)
        self.coef_ = result.x
        return self

    def predict_proba(self, frame):
        X, offset = self._design(frame)
        prob = expit(offset + self.cap * np.tanh((X @ self.coef_) / self.cap))
        return np.column_stack([1-prob, prob])

    def to_dict(self):
        return {'version': MODEL_VERSION_V3, 'features': self.features,
                'medians': self.medians, 'scales': self.scales.tolist(), 'coef': self.coef_.tolist(),
                'cap': self.cap, 'penalty': self.penalty, 'provenance_status': 'unverified'}

    @classmethod
    def from_dict(cls, d):
        obj = cls('profile_strength_score' in d['features'])
        if d['version'] != MODEL_VERSION_V3 or obj.features != d['features']:
            raise ValueError('Model version/feature contract mismatch.')
        obj.medians, obj.scales, obj.coef_ = d['medians'], np.array(d['scales']), np.array(d['coef'])
        obj.cap, obj.penalty = d['cap'], d['penalty']
        return obj


def probability_metrics(y, p):
    return {'accuracy': float(accuracy_score(y, p >= .5)), 'roc_auc': float(roc_auc_score(y, p)),
            'brier_score': float(brier_score_loss(y, p)), 'log_loss': float(log_loss(y, p, labels=[0,1]))}


# %% Applicant-grouped CV and profile-strength ablation
# Same predetermined folds for both candidates; no hyperparameter search or test-set tuning.
# These OOF scores are dataset-validation metrics, not external real-world test accuracy.
group_cv_v3 = GroupKFold(n_splits=5)
folds_v3 = list(group_cv_v3.split(train_v3, train_v3.admit_result, groups=train_v3.applicant_id))
oof_v3 = pd.DataFrame({'applicant_id': train_v3.applicant_id, 'program_id': train_v3.program_id,
                       'y': train_v3.admit_result, 'fold': -1})
results_v3, fold_checks_v3 = {}, []
with threadpool_limits(limits=1):
    for use_strength in [False, True]:
        name = 'with_profile_strength' if use_strength else 'without_profile_strength'
        p = np.zeros(len(train_v3))
        for fold, (tr, va) in enumerate(folds_v3):
            overlap = set(train_v3.iloc[tr].applicant_id) & set(train_v3.iloc[va].applicant_id)
            assert not overlap
            estimator = OffsetAdmissionModel(use_strength).fit(train_v3.iloc[tr], train_v3.admit_result.iloc[tr])
            p[va] = estimator.predict_proba(train_v3.iloc[va])[:, 1]
            if use_strength:
                oof_v3.loc[va, 'fold'] = fold
                fold_checks_v3.append({'fold': fold, 'train_rows': len(tr), 'validation_rows': len(va),
                                      'overlapping_applicants': len(overlap),
                                      **probability_metrics(train_v3.admit_result.iloc[va], p[va])})
        oof_v3[name] = p
        results_v3[name] = probability_metrics(train_v3.admit_result, p)
    admission_model_v3 = OffsetAdmissionModel(True).fit(train_v3, train_v3.admit_result)
results_v3['prior_only'] = probability_metrics(train_v3.admit_result, train_v3.program_admit_rate)
results_v3['evaluation_scope'] = 'Five-fold GroupKFold by applicant_id; unverified CSV labels; no external test claim.'
results_v3['folds'] = fold_checks_v3
results_v3['profile_strength_accuracy_delta'] = results_v3['with_profile_strength']['accuracy'] - results_v3['without_profile_strength']['accuracy']
oof_v3.to_csv(OUT / 'oof_predictions.csv', index=False)
(OUT / 'group_cv_metrics.json').write_text(json.dumps(results_v3, indent=2), encoding='utf-8')
(OUT / 'offset_admission_model.json').write_text(json.dumps(admission_model_v3.to_dict(), indent=2), encoding='utf-8')
print(pd.DataFrame({k:v for k,v in results_v3.items() if k in ['with_profile_strength','without_profile_strength','prior_only']}).T.to_string())
print('Applicant overlap in every fold: 0')
print('Fitted nonnegative applicant coefficients:', dict(zip(admission_model_v3.features, admission_model_v3.coef_[:-1])))
print('Program selectivity penalty:', admission_model_v3.coef_[-1])

# %% Program-rate evidence, inference adapter and behavior checks
RATE_PATH_V3 = ROOT / 'data/raw/agent2/program_admit_rate_sources.csv'
RATE_COLUMNS_V3 = ['program_id', 'university_name', 'program_name', 'degree_type', 'admission_year',
                   'applicants', 'admitted', 'program_admit_rate', 'source_url', 'checked_on', 'population']
if not RATE_PATH_V3.exists():
    pd.DataFrame(columns=RATE_COLUMNS_V3).to_csv(RATE_PATH_V3, index=False)
rate_evidence_v3 = pd.read_csv(RATE_PATH_V3)
if not rate_evidence_v3.empty:
    if rate_evidence_v3.program_id.duplicated().any():
        raise ValueError('Select one documented admission cohort per program; duplicate overrides are ambiguous.')
    for r in rate_evidence_v3.to_dict('records'):
        if any(pd.isna(r[k]) or not str(r[k]).strip() for k in RATE_COLUMNS_V3):
            raise ValueError('Source overrides need all evidence fields, including counts and population.')
        c = catalog_v3.loc[catalog_v3.program_id == r['program_id']]
        if len(c) != 1 or any(str(c.iloc[0][k]) != str(r[k]) for k in ['university_name','program_name','degree_type']):
            raise ValueError('Rate evidence must match the exact catalog program and degree.')
        if not (0 < float(r['admitted']) < float(r['applicants'])) or not np.isclose(float(r['program_admit_rate']),float(r['admitted'])/float(r['applicants']),atol=1e-5):
            raise ValueError('Rate must equal admitted/applicants, not enrolled/applicants.')
        if not str(r['source_url']).startswith('https://'):
            raise ValueError('Official source URL required.')
        pd.to_datetime(r['checked_on'], errors='raise')


def resolve_program_rate_v3(payload):
    evidence = rate_evidence_v3.loc[rate_evidence_v3.program_id == payload.get('program_id')]
    if len(evidence):
        r = evidence.iloc[0]
        return float(r.program_admit_rate), {'status':'source_documented_program_rate',
            'source_url':r.source_url, 'admission_year':str(r.admission_year), 'population':r.population}
    rate = float(payload.get('program_admit_rate', np.nan))
    if not np.isfinite(rate) or not 0 < rate < 1:
        raise ValueError('Program rate missing; cannot estimate admission probability.')
    return rate, {'status':'unverified_catalog_prior', 'source_url':None, 'admission_year':None}


def admission_prediction_v3(profile, payload, strength=None):
    scale = float(profile.get('gpa_scale', 4))
    gpa = float(profile['gpa']) * 4 / scale if scale > 0 else np.nan
    if not np.isfinite(gpa) or not 0 <= gpa <= 4:
        raise ValueError('GPA must be valid on its stated scale.')
    if strength is None:
        strength = profile.get('profile_strength_score')
    if strength is not None and not 0 <= float(strength) <= 100:
        raise ValueError('profile_strength_score must be on the 0-100 scale.')
    gre_block = (profile.get('test_scores') or {}).get('GRE', {})
    row = {'gpa':gpa, 'gre_quant':gre_block.get('quant',profile.get('gre_quant')),
           'gre_verbal':gre_block.get('verbal',profile.get('gre_verbal')), 'profile_strength_score':strength,
           'tier_score':payload['tier_score']}
    for key in ['gre_quant', 'gre_verbal']:
        if row[key] not in (None, '') and not 130 <= float(row[key]) <= 170:
            raise ValueError('GRE component must be on the 130-170 scale or missing.')
    row['program_admit_rate'], evidence = resolve_program_rate_v3(payload)
    frame = pd.DataFrame([row])
    p = float(admission_model_v3.predict_proba(frame)[0,1])
    X, offset = admission_model_v3._design(frame)
    terms = X[0]*admission_model_v3.coef_
    names = admission_model_v3.features + ['program_selectivity']
    factors = [{'feature':k,'value':float(v),'direction':'increases' if v > 0 else 'decreases' if v < 0 else 'neutral',
                'method':'linear_log_odds_term_before_bounded_adjustment'} for k,v in zip(names,terms)]
    return {'admit_probability':p, 'tier':'Safe' if p >= .65 else 'Target' if p >= .35 else 'Reach',
            'program_admit_rate_used':row['program_admit_rate'], 'base_rate_evidence':evidence,
            'probability_status':'experimental_unverified_training_labels',
            'imputed_features':[f for f in admission_model_v3.features if pd.isna(pd.to_numeric(row[f], errors='coerce'))],
            'explainability':factors, 'normalized_gpa':gpa}


def compute_tier_ml(profile, payload, extracurricular_score=None):
    # Compatibility with the earlier orchestration: this argument uses a 0-1 fraction.
    strength = None if extracurricular_score is None else float(extracurricular_score)*100
    pred = admission_prediction_v3(profile, payload, strength)
    return pred['tier'], pred['admit_probability'], pred['explainability'], pred['normalized_gpa'], float(payload['tier_score'])


def run_model_checks_v3():
    base = {**admission_model_v3.medians, 'tier_score':70., 'program_admit_rate':.25}
    basep = admission_model_v3.predict_proba(pd.DataFrame([base]))[0,1]
    assert np.isclose(basep,.25), 'Neutral profile at reference tier must reproduce prior.'
    tests = ['neutral_profile_preserves_prior']
    for f in admission_model_v3.features:
        rows = pd.DataFrame([base]*101)
        lo,hi = {'gpa':(0,4),'gre_quant':(130,170),'gre_verbal':(130,170),'profile_strength_score':(0,100)}[f]
        rows[f] = np.linspace(lo,hi,101)
        assert np.all(np.diff(admission_model_v3.predict_proba(rows)[:,1]) >= -1e-12)
        tests.append(f+'_monotone')
    rows = pd.DataFrame([base]*101); rows['tier_score'] = np.linspace(0,100,101)
    assert np.all(np.diff(admission_model_v3.predict_proba(rows)[:,1]) <= 1e-12)
    tests.append('selectivity_monotone_at_fixed_base_rate')
    counterfactual = pd.DataFrame([{**base,'tier_score':60},{**base,'tier_score':88}])
    a,b = admission_model_v3.predict_proba(counterfactual)[:,1]
    assert b < a
    tests.append('same_applicant_tier88_lower_than_tier60')
    rows = pd.DataFrame([base]*99); rows['program_admit_rate'] = np.linspace(.01,.99,99)
    assert (np.diff(admission_model_v3.predict_proba(rows)[:,1]) > 0).all()
    tests.append('base_rate_monotone')
    reload = OffsetAdmissionModel.from_dict(json.loads((OUT/'offset_admission_model.json').read_text()))
    assert np.allclose(reload.predict_proba(train_v3.head(100)), admission_model_v3.predict_proba(train_v3.head(100)))
    tests.append('serialization_round_trip')
    invalid = pd.DataFrame([base]); invalid['program_admit_rate'] = np.nan
    try:
        admission_model_v3.predict_proba(invalid)
        raise AssertionError('Missing prior accepted')
    except ValueError:
        tests.append('missing_prior_rejected')
    p = admission_model_v3.predict_proba(train_v3)[:,1]
    ratio = np.exp(logit(p)-logit(train_v3.program_admit_rate.to_numpy()))
    assert ((ratio >= 1/3-1e-10) & (ratio <= 3+1e-10)).all()
    tests.append('odds_adjustment_bounded')
    assert all(f['overlapping_applicants'] == 0 for f in fold_checks_v3)
    tests.append('all_group_folds_disjoint')
    return {'passed':len(tests),'checks':tests,'tier60_probability':float(a),'tier88_probability':float(b)}


checks_v3 = run_model_checks_v3()
print(json.dumps(checks_v3, indent=2))
demo_rows_v3 = catalog_v3.loc[(catalog_v3.program_name == 'MS Computer Science') &
    catalog_v3.university_name.isin(['Stanford University','University of Delaware','Arizona State University Campus Immersion'])].copy()
for feature,value in admission_model_v3.medians.items(): demo_rows_v3[feature] = value
demo_rows_v3['estimated_probability'] = admission_model_v3.predict_proba(demo_rows_v3)[:,1]
print('\nSame median applicant, catalog priors UNVERIFIED:')
print(demo_rows_v3[['university_name','program_name','tier_score','program_admit_rate','estimated_probability']].to_string(index=False))
(OUT/'behavior_checks.json').write_text(json.dumps(checks_v3,indent=2),encoding='utf-8')

# %% Actual BGE, Qdrant and CrossEncoder retrieval; live Groq when configured
import requests
import torch
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# Read only recognized settings. Never echo keys or error messages containing credentials.
def load_agent2_local_settings():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value = line.split('=',1)
                if key.strip() in ['GROQ_API_KEY','GROQ_MODEL','QDRANT_URL','QDRANT_API_KEY']:
                    os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))


load_agent2_local_settings()
torch.set_num_threads(2)
cache_v3 = ROOT / '.cache/agent2'
embed_path_v3 = cache_v3 / 'bge-small-en-v1.5'
rerank_path_v3 = cache_v3 / 'bge-reranker-base'
online_status_v3 = {'embedding':'not_run','qdrant':'not_run','reranker':'not_run','groq':'not_run'}
embed_model_v3 = SentenceTransformer(str(embed_path_v3) if embed_path_v3.exists() else 'BAAI/bge-small-en-v1.5', device='cpu')
reranker_v3 = CrossEncoder(str(rerank_path_v3) if rerank_path_v3.exists() else 'BAAI/bge-reranker-base', device='cpu', max_length=512)
collection_v3 = 'agent2_base_rate_v3_' + audit_v3['catalog_sha256'][:10]
if os.environ.get('QDRANT_URL'):
    qdrant_v3 = QdrantClient(url=os.environ['QDRANT_URL'],api_key=os.environ.get('QDRANT_API_KEY'),timeout=60)
    online_status_v3['qdrant_mode'] = 'remote_service'
else:
    qdrant_v3 = QdrantClient(':memory:')
    online_status_v3['qdrant_mode'] = 'actual_qdrant_local_engine; remote URL not configured'
texts_v3 = [f"{r.program_name} at {r.university_name}. {r.description_text} {r.curriculum_highlights} {r.faculty_research_areas}"
            for r in catalog_v3.fillna('').itertuples()]
vector_fingerprint_v3 = hashlib.sha256(('BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a\n'+ '\n'.join(texts_v3)).encode()).hexdigest()
vector_cache_v3 = cache_v3 / ('vectors_'+vector_fingerprint_v3+'.npy')
if vector_cache_v3.exists():
    vectors_v3 = np.load(vector_cache_v3,allow_pickle=False)
    assert vectors_v3.shape == (len(texts_v3),384) and np.isfinite(vectors_v3).all()
    online_status_v3['embedding'] = f'loaded actual BGE catalog embeddings ({len(texts_v3)} programs); query embedding executed live locally'
else:
    vectors_v3 = embed_model_v3.encode(texts_v3, batch_size=32, normalize_embeddings=True,show_progress_bar=False)
    cache_v3.mkdir(parents=True,exist_ok=True)
    np.save(vector_cache_v3,vectors_v3,allow_pickle=False)
    online_status_v3['embedding'] = f'executed BAAI/bge-small-en-v1.5 on {len(texts_v3)} programs'
if not qdrant_v3.collection_exists(collection_v3):
    qdrant_v3.create_collection(collection_v3,vectors_config=VectorParams(size=vectors_v3.shape[1],distance=Distance.COSINE))
records_v3 = json.loads(catalog_v3.to_json(orient='records'))
for start in range(0,len(records_v3),128):
    qdrant_v3.upsert(collection_v3,points=[PointStruct(id=i,vector=vectors_v3[i].tolist(),
                       payload={**records_v3[i],'full_text':texts_v3[i]})
                       for i in range(start,min(start+128,len(records_v3)))])


def retrieve_candidates_v3(profile, preferences, top_k=20):
    query = f"{profile['target_degree']} {profile['target_program']} {profile.get('interests_text','')}".strip()
    vector = embed_model_v3.encode('Represent this sentence for searching relevant passages: '+query,normalize_embeddings=True).tolist()
    points = qdrant_v3.query_points(collection_name=collection_v3,query=vector,
        query_filter=Filter(must=[FieldCondition(key='degree_type',match=MatchValue(value=profile['target_degree']))]),limit=top_k).points
    online_status_v3['qdrant'] = 'executed vector retrieval with degree filter'
    return points


def rerank_v3(query, candidates, top_n=10):
    if not candidates: return []
    scores = reranker_v3.predict([(query,c.payload['full_text']) for c in candidates],batch_size=8,show_progress_bar=False,
                                activation_fn=torch.nn.Identity())
    online_status_v3['reranker'] = 'executed BAAI/bge-reranker-base CrossEncoder'
    return sorted(zip(candidates,scores),key=lambda pair:float(pair[1]),reverse=True)[:top_n]


def explain_batch_v3(matches):
    # Only public catalog fields and computed probability evidence leave the machine.
    # No applicant ID, raw personal fields, interest text or .env contents are sent.
    load_agent2_local_settings()
    key = os.environ.get('GROQ_API_KEY')
    if not key:
        online_status_v3['groq'] = 'BLOCKED: GROQ_API_KEY missing'
        return {}
    facts = [{'program_id':m['program_id'],'university':m['university_name'],
              'program':m['program_name'],'estimated_probability':m['admit_probability'],
              'prior_status':m['base_rate_evidence']['status'],'probability_status':m['probability_status']}
             for m in matches]
    session = requests.Session(); session.trust_env = False
    response = session.post('https://api.groq.com/openai/v1/chat/completions',
        headers={'Authorization':'Bearer '+key}, timeout=90,
        json={'model':os.environ.get('GROQ_MODEL','openai/gpt-oss-120b'),
              **({'reasoning_effort':'low'} if 'gpt-oss' in os.environ.get('GROQ_MODEL','openai/gpt-oss-120b') else {}),
              'temperature':0,'max_tokens':2400,'response_format':{'type':'json_object'},
              'messages':[{'role':'system','content':'Return a JSON object mapping each program_id to a brief explanation. Use only provided facts. State that probabilities are experimental with unverified training labels. Do not claim verified admissions chances, safety, guaranteed admission, or unpublished program rates.'},
                          {'role':'user','content':json.dumps(facts)}]})
    if response.status_code != 200:
        online_status_v3['groq'] = f'FAILED: HTTP {response.status_code}; response body withheld'
        return {}
    try:
        explanations = json.loads(response.json()['choices'][0]['message']['content'])
        if not all(isinstance(explanations.get(m['program_id']),str) and explanations[m['program_id']].strip() for m in matches):
            raise ValueError('Incomplete explanation mapping')
    except (ValueError,KeyError,TypeError):
        online_status_v3['groq'] = 'FAILED: invalid JSON explanation contract'
        return {}
    online_status_v3['groq'] = 'executed live Groq API: '+os.environ.get('GROQ_MODEL','openai/gpt-oss-120b')
    online_status_v3['groq_response_id'] = response.json().get('id')
    online_status_v3['groq_usage'] = response.json().get('usage')
    return explanations


def university_matching_agent_v3(state, standalone_mode=False):
    profile = state['profile']; preferences = dict(state.get('preferences') or {})
    if preferences.get('budget_max_usd') is not None:
        preferences.setdefault('budget_period','annual')
        preferences.setdefault('budget_currency','USD')
        preferences.setdefault('budget_period_source','legacy_project_contract')
    state['preferences']=preferences
    strength = (state.get('extracurricular') or {}).get('profile_strength_score',profile.get('profile_strength_score'))
    if strength is None and not standalone_mode:
        raise ValueError('Agent 7 profile_strength_score is required for the integrated chain.')
    candidates = retrieve_candidates_v3(profile,preferences)
    query = f"{profile['target_degree']} {profile['target_program']} {profile.get('interests_text','')}".strip()
    reranked = rerank_v3(query,candidates)
    matches=[]
    for c,score in reranked:
        p = c.payload; prediction = admission_prediction_v3(profile,p,strength)
        # Preserve the existing notebook's matching blend; this is separate from P(admit).
        weights = {'ranking':(.30,.35,.20,.15),'research':(.40,.20,.20,.20),
                   'cost':(.30,.20,.30,.20),'location':(.30,.25,.25,.20),
                   'default':(.35,.25,.25,.15)}
        w = weights.get(preferences.get('priority','default'),weights['default'])
        min_gpa=float(p.get('min_gpa') or 3.)
        gpa_fit=max(0.,min(1.,1.-abs(prediction['normalized_gpa']-min_gpa)/4.))
        strength_fit=float(strength if strength is not None else admission_model_v3.medians['profile_strength_score'])/100.
        fit=round(w[0]*float(expit(float(score)))+w[1]*float(p['tier_score'])/100.+w[2]*gpa_fit+w[3]*strength_fit,3)
        budget=preferences.get('budget_max_usd'); tuition=p.get('tuition_out_state_usd')
        budget_signal=bool(float(tuition)<=float(budget)*1.15) if budget and tuition else None
        matches.append({'university_name':p['university_name'],'program_name':p['program_name'],
            'program_id':p['program_id'],'unitid':p.get('unitid'),'country':p.get('country'),
            'region':p.get('region'),'type':p.get('institution_type'),'agent1_tier':float(p['tier_score']),
            'extracurricular_score':strength,'match_score':float(fit),'semantic_score':float(score),
            'within_stated_budget':budget_signal,**prediction})
    explanations = explain_batch_v3(matches) if matches else {}
    grouped={}
    for m in matches:
        m['explanation'] = explanations.get(m['program_id'],'Live explanation unavailable. Admission estimate uses an unverified training dataset; inspect base_rate_evidence.')
        m['explanation_source'] = 'groq' if m['program_id'] in explanations else 'unavailable'
        uni=grouped.setdefault(m['university_name'],{'university':m['university_name'],'unitid':m['unitid'],
            'country':m['country'],'region':m['region'],'type':m['type'],'programs':[]})
        uni['programs'].append(m)
    for uni in grouped.values():
        best=max(uni['programs'],key=lambda p:p['admit_probability'])
        uni.update({k:best[k] for k in ['admit_probability','agent1_tier','extracurricular_score','probability_status','base_rate_evidence']})
        uni['match_score']=float(np.mean([p['match_score'] for p in uni['programs']]))
        uni['overall_score']=.6*uni['match_score']+.4*uni['admit_probability']
        uni['reasoning']=best['explanation']
    state['matched_universities']=sorted(grouped.values(),key=lambda u:u['overall_score'],reverse=True)
    state['status']='university_done'
    state['agent2_execution']={**online_status_v3,'model_version':MODEL_VERSION_V3}
    return state


# The last definition is the active entry point; old cells remain historical reference.
university_matching_agent = university_matching_agent_v3
demo_applicant_v3 = train_v3.drop_duplicates('applicant_id').iloc[0]
demo_program_v3 = catalog_v3.loc[catalog_v3.program_id == demo_applicant_v3.program_id].iloc[0]
demo_state_v3 = {'student_id':'uploaded-demo-001', 'profile':{
    **{f:float(demo_applicant_v3[f]) for f in APPLICANT_FEATURES_V3}, 'gpa_scale':4.,
    'target_degree':demo_program_v3.degree_type,'target_program':demo_applicant_v3.program_name,
    'interests_text':''}, 'preferences':{},
    'extracurricular':{'profile_strength_score':float(demo_applicant_v3.profile_strength_score)}}
with threadpool_limits(limits=2):
    demo_result_v3 = university_matching_agent(demo_state_v3)
assert demo_result_v3['matched_universities'], 'Real retrieval returned no candidates.'
(OUT/'online_demo_states.json').write_text(json.dumps(demo_result_v3,indent=2),encoding='utf-8')
print(json.dumps(online_status_v3,indent=2))
print(pd.DataFrame([{'university':u['university'],'program':p['program_name'],
    'prior':p['program_admit_rate_used'],'admit_probability':p['admit_probability'],
    'explanation_source':p['explanation_source']} for u in demo_result_v3['matched_universities'] for p in u['programs']]).to_string(index=False))

# %% Final measured results and generated notebook header
FINAL_FEATURES_V3 = admission_model_v3.features + ['tier_score','program_admit_rate (fixed offset)']
final_report_v3 = {'model_version':MODEL_VERSION_V3,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
    'feature_count':len(FINAL_FEATURES_V3),'features':FINAL_FEATURES_V3,
    'group_cv':results_v3,'functional_checks':checks_v3,'online_execution':online_status_v3,
    'training_provenance':'UNVERIFIED','real_world_admission_accuracy':'NOT MEASURED',
    'documented_program_rate_overrides':len(rate_evidence_v3),'data_audit':audit_v3}
(OUT/'final_report.json').write_text(json.dumps(final_report_v3,indent=2),encoding='utf-8')
HEADER_V3 = f'''# Agent 2 — University Matching Agent

Current implementation: **{MODEL_VERSION_V3}**, a fixed program-rate logit offset with a bounded, monotone applicant adjustment.

**Generated from this execution:** {len(FINAL_FEATURES_V3)} inputs: {', '.join(FINAL_FEATURES_V3)}.
Five-fold applicant-grouped CV accuracy: **{results_v3['with_profile_strength']['accuracy']:.2%}**;
ROC-AUC **{results_v3['with_profile_strength']['roc_auc']:.4f}**, Brier **{results_v3['with_profile_strength']['brier_score']:.4f}**.
These are scores against unverified CSV labels, not measured real-world admissions accuracy.
No 96% accuracy claim is supported. Functional checks: {checks_v3['passed']}/{checks_v3['passed']}.

Input: Agent 1 profile and program preferences, Agent 7 profile strength (0–100), catalog program tier/rate.
Output: ranked universities with programs, UNITID, country, match score, estimated admission probability,
prior provenance, missing-feature flags, transparent model contributions, and Groq explanations when available.
Program selectivity is a catalog attribute, not an applicant-strength score.

Live stack execution: {json.dumps({k:v for k,v in online_status_v3.items() if k not in ['groq_response_id','groq_usage']})}.
The active code is the appended v3 section (also delivered as a clean executed notebook).
Earlier experiments below are historical and superseded; their metrics and provenance claims are not current.
'''
print('AGENT 2 FINAL MEASURED RESULTS')
print(f"GroupKFold CV accuracy (unverified labels): {results_v3['with_profile_strength']['accuracy']:.2%}")
print(f"ROC-AUC: {results_v3['with_profile_strength']['roc_auc']:.4f}; Brier: {results_v3['with_profile_strength']['brier_score']:.4f}")
print(f"Profile-strength ablation accuracy delta: {results_v3['profile_strength_accuracy_delta']*100:+.3f} percentage points")
print(f"Functional checks: {checks_v3['passed']}/{checks_v3['passed']}; applicant overlap: 0 in all folds")
print(f"Same applicant: tier 60 = {checks_v3['tier60_probability']:.2%}, tier 88 = {checks_v3['tier88_probability']:.2%}")
print('Real-world admissions accuracy: NOT MEASURED; program priors unverified unless an exact source override exists.')
print('Online execution:',json.dumps(online_status_v3))
