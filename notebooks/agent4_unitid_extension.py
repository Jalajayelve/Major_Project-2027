# %% setup
from pathlib import Path
from copy import deepcopy
import ast
import csv
import hashlib
import json
import math
import re
import unicodedata
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

# Small repeated cluster predictions do not benefit from a large BLAS/OpenMP pool.
_a4_thread_limit = threadpool_limits(limits=1)

A4_ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / 'data/raw').is_dir())
A4_DATA = A4_ROOT / 'data/raw/agent4'
A4_RUNS = A4_ROOT / 'data/processed/agent4'
A4_RUNS.mkdir(parents=True, exist_ok=True)
A4_CATALOG_PATH = A4_ROOT / 'data/raw/agent2/agent2_enhanced_program_catalog.csv'
A4_MASTER_PATH = A4_DATA / 'agent4_master_financial_dataset.csv'
A4_REFERENCE_PATH = A4_DATA / 'published_costs_50.csv'

def a4_key(value):
    text = '' if value is None or pd.isna(value) else str(value)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text.replace('&', ' and ')).split())

def a4_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None

def a4_unitid(value):
    number = a4_number(value)
    if number is None or number <= 0 or not number.is_integer():
        raise ValueError(f'Invalid IPEDS UNITID: {value!r}')
    return int(number)

# Crosswalk uses deterministic spelling normalization, never fuzzy campus matching.
a4_catalog = pd.read_csv(A4_CATALOG_PATH)
a4_master = pd.read_csv(A4_MASTER_PATH, low_memory=False)
a4_master['unitid'] = a4_master.UNITID.map(a4_unitid)
a4_master['_name_key'] = a4_master.university_name.map(a4_key)
a4_catalog['_name_key'] = a4_catalog.university_name.map(a4_key)
a4_crosswalk_rows = []
for name, group in a4_catalog.groupby('university_name', sort=False):
    found = a4_master.loc[a4_master._name_key.eq(a4_key(name))]
    ids = found.unitid.unique()
    if len(ids) != 1:
        raise ValueError(f'Crosswalk requires manual campus resolution: {name}: {ids}')
    # Cross-check the state as well as the institution name.
    if {a4_key(x) for x in group.state.dropna()} != {a4_key(x) for x in found.state.dropna()}:
        raise ValueError(f'State mismatch for {name}')
    a4_crosswalk_rows.append({'university_name': name, 'unitid': int(ids[0]),
        'financial_university_name': found.iloc[0].university_name,
        'state': found.iloc[0].state, 'match_method': 'unique_normalized_name_and_state',
        'source': 'uploaded financial dataset UNITID; not a new NCES verification'})
a4_crosswalk = pd.DataFrame(a4_crosswalk_rows)
assert a4_crosswalk.unitid.is_unique, 'Multiple catalog institutions share a UNITID.'
a4_name_to_id = dict(zip(a4_crosswalk.university_name.map(a4_key), a4_crosswalk.unitid))
a4_crosswalk.to_csv(A4_DATA / 'agent2_ipeds_crosswalk.csv', index=False)

# Add only UNITID: preserve the original CSV fields and values as strings.
with A4_CATALOG_PATH.open(encoding='utf-8-sig', newline='') as handle:
    reader = csv.DictReader(handle)
    a4_original_fields = list(reader.fieldnames)
    a4_original_rows = list(reader)
for row in a4_original_rows:
    expected = str(a4_name_to_id[a4_key(row['university_name'])])
    if row.get('unitid', '').strip() and a4_unitid(row['unitid']) != int(expected):
        raise ValueError('Existing catalog UNITID conflicts with the crosswalk.')
    row['unitid'] = expected
if 'unitid' not in a4_original_fields or a4_catalog.unitid.isna().any():
    with A4_CATALOG_PATH.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys([*a4_original_fields, 'unitid'])))
        writer.writeheader()
        writer.writerows(a4_original_rows)
a4_catalog['unitid'] = a4_catalog._name_key.map(a4_name_to_id).astype(int)
a4_catalog['_program_key'] = a4_catalog.program_name.map(a4_key)

A4_LEVELS = {'ms': "Graduate / Master's", 'msc': "Graduate / Master's",
    'meng': "Graduate / Master's", 'mba': "Graduate / Master's", 'ma': "Graduate / Master's",
    'masters': "Graduate / Master's", 'master': "Graduate / Master's",
    'graduate masters': "Graduate / Master's", 'phd': 'Doctoral / PhD',
    'doctoral phd': 'Doctoral / PhD', 'bs': 'Undergraduate', 'bsc': 'Undergraduate',
    'ba': 'Undergraduate', 'beng': 'Undergraduate', 'undergraduate': 'Undergraduate'}

def a4_level(value):
    # Normalize the canonical labels too: the apostrophe in Master's becomes
    # a separator under a4_key, so hand-written aliases alone are insufficient.
    canonical = {a4_key(label): label for label in set(A4_LEVELS.values())}
    if a4_key(value) in canonical:
        return canonical[a4_key(value)]
    return A4_LEVELS.get(a4_key(value))

if a4_master.duplicated(['unitid', 'program_level']).any():
    raise ValueError('Financial dataset has duplicate UNITID/degree-level rows; resolve before lookup.')
a4_financial_index = a4_master.set_index(['unitid', 'program_level'])
assert a4_financial_index.index.is_unique

def estimate_cost_v2(university_name=None, program_level=None, *, unitid=None,
                     program_name=None, degree_type=None, fallback_model=None):
    """Catalog tuition first; exact UNITID + level living lookup; no KNN target lookup.

    fallback_model, if supplied, is a callable accepting the selected financial row
    and returning a tuition estimate. It is never fitted on evaluation references.
    Unknown inputs retain a result with null costs rather than dropping a program.
    """
    uid = a4_unitid(unitid) if unitid is not None else a4_name_to_id.get(a4_key(university_name))
    result = {'unitid': uid, 'tuition': None, 'living': None, 'total_cost': None,
        'currency': 'USD', 'cost_period': 'annual', 'country': 'USA' if uid else None,
        'tuition_source': None, 'living_source': None, 'cost_data_quality': 'NOT_FOUND',
        'cost_source': None,
        'living_cost_is_estimated': True, 'fees': None, 'fees_status': 'not separately documented',
        'academic_year': None, 'months_covered': None, 'program_level': None, 'warnings': []}
    if uid is None:
        result['warnings'].append('Unresolved institution; provide a verified UNITID.')
        return result
    explicit_level = a4_level(program_level)
    degree_level = a4_level(degree_type)
    if (program_level and not explicit_level) or (degree_type and not degree_level):
        result['cost_data_quality'] = 'INVALID_LEVEL'
        return result
    if explicit_level and degree_level and explicit_level != degree_level:
        result['cost_data_quality'] = 'LEVEL_CONFLICT'
        return result
    candidates = a4_catalog.loc[a4_catalog.unitid.eq(uid)]
    if program_name:
        candidates = candidates.loc[candidates._program_key.eq(a4_key(program_name))]
    if degree_type:
        candidates = candidates.loc[candidates.degree_type.map(a4_key).eq(a4_key(degree_type))]
    levels = set(candidates.degree_type.map(a4_level).dropna()) if program_name else set()
    explicit_level = explicit_level or degree_level
    if len(levels) > 1 or (explicit_level and levels and explicit_level not in levels):
        result['cost_data_quality'] = 'LEVEL_CONFLICT'
        result['warnings'].append('Program degree conflicts with the requested level.')
        return result
    level = explicit_level or (next(iter(levels)) if levels else None)
    result['program_level'] = level
    if level is None:
        result['cost_data_quality'] = 'LEVEL_REQUIRED'
        return result
    if (uid, level) not in a4_financial_index.index:
        result['warnings'].append('No financial row for this UNITID and degree level.')
        return result
    financial_row = a4_financial_index.loc[(uid, level)]
    result['financial_data_year'] = int(financial_row.data_year)
    if level:
        candidates = candidates.loc[candidates.degree_type.map(a4_level).eq(level)]
    # A supplied unknown program must not silently become the university's first program.
    if program_name and candidates.empty and uid in set(a4_catalog.unitid):
        result['cost_data_quality'] = 'PROGRAM_NOT_FOUND'
        return result
    tuition_values = pd.to_numeric(candidates.tuition_out_state_usd, errors='coerce').dropna().unique()
    if len(tuition_values) == 1 and tuition_values[0] > 1:
        result['tuition'] = float(tuition_values[0])
        result['tuition_source'] = 'agent2_catalog:tuition_out_state_usd'
        result['cost_data_quality'] = 'CATALOG_TUITION_ESTIMATED_LIVING'
        result['cost_source'] = 'catalog_tuition_plus_estimated_living'
        result['warnings'].append('Catalog tuition is a university-level out-of-state proxy; program-specific fees and catalog price year are unverified.')
    elif len(tuition_values) > 1:
        result['cost_data_quality'] = 'AMBIGUOUS_PROGRAM_TUITION'
        return result
    else:
        # User-requested operational fallback. This same ledger cannot independently
        # validate a total copied from it; the benchmark excludes these cases.
        published = a4_published_coa.loc[
            a4_published_coa.unitid.eq(uid)
            & a4_published_coa.reference_program_level.eq(level)]
        if len(published) == 1:
            ref = published.iloc[0]
            total = a4_number(ref.published_total_usd)
            if total is not None and total > 1 and ref.currency_reference == 'USD' and pd.notna(ref.source_url):
                result.update(total_cost=round(total, 2), cost_source='published_coa',
                    cost_data_quality='PUBLISHED_COA_SCENARIO',
                    academic_year=ref.academic_year_reference,
                    months_covered=a4_number(ref.reference_months),
                    published_source_url=ref.source_url,
                    published_checked_on=ref.checked_on,
                    published_scenario=ref.reference_scenario,
                    living_cost_is_estimated=True,
                    published_components={k: a4_number(ref[k]) for k in [
                        'published_tuition_usd', 'published_fees_usd',
                        'published_housing_food_usd', 'published_other_usd']})
                result['warnings'].append('Published annual COA scenario used because catalog tuition is absent; enrollment/fee scope may differ. Component totals are not inferred. Excluded from scoring against this ledger.')
                return result
        # For these catalog institutions, an absent catalog price and absent COA
        # stay unknown. Do not substitute KNN targets or the old model silently.
        if uid in set(a4_catalog.unitid):
            result['cost_data_quality'] = 'CATALOG_TUITION_AND_PUBLISHED_COA_MISSING'
            return result
    if result['tuition'] is None and financial_row.tuition_data_quality == 'IPEDS_OBSERVED':
        tuition = a4_number(financial_row.annual_tuition_usd)
        if tuition is not None and tuition > 1:
            result['tuition'] = tuition
            result['tuition_source'] = 'IPEDS_OBSERVED:out_of_state_tuition_plus_fees'
            result['cost_data_quality'] = 'OBSERVED_TUITION_ESTIMATED_LIVING'
            result['cost_source'] = 'observed_tuition_plus_estimated_living'
            result['fees_status'] = 'included in IPEDS tuition proxy'
    if result['tuition'] is None and fallback_model is not None:
        prediction = a4_number(fallback_model(financial_row.copy()))
        if prediction is not None and prediction > 1:
            result['tuition'] = prediction
            result['tuition_source'] = 'REGRESSION_FALLBACK'
            result['cost_data_quality'] = 'MODEL_TUITION_ESTIMATED_LIVING'
            result['cost_source'] = 'regression_fallback_plus_estimated_living'
    baseline = a4_number(financial_row.baseline_non_tuition_student_cost_usd)
    parity = a4_number(financial_row.rpp_used_2024)
    if baseline is not None and parity is not None and baseline > 0 and parity > 0:
        result['living'] = round(baseline * parity / 100, 2)
        result['living_source'] = 'baseline_non_tuition_student_cost_usd * rpp_used_2024 / 100'
        result['living_baseline_usd'] = baseline
        result['living_price_parity'] = parity
        result['living_parity_scope'] = financial_row.rpp_source_level
    if result['tuition'] is not None and result['living'] is not None:
        result['tuition'] = round(result['tuition'], 2)
        result['total_cost'] = round(result['tuition'] + result['living'], 2)
    else:
        result['cost_data_quality'] = 'INCOMPLETE_COST'
    return result

def financial_agent_v2(state, *, fallback_model=None):
    output = deepcopy(state)
    output['finance'] = []
    university_meta = {a4_key(u.get('university') or u.get('university_name')): u
                       for u in state.get('matched_universities', [])}
    for program in output.get('programs', []):
        name = program.get('university') or program.get('university_name')
        meta = university_meta.get(a4_key(name), {})
        uid = program.get('unitid', meta.get('unitid'))
        # Resolve the exact catalog program's degree before consulting profile defaults.
        known = a4_catalog.loc[a4_catalog._program_key.eq(a4_key(program.get('program_name')))]
        known = known.loc[known.unitid.eq(a4_unitid(uid))] if uid is not None else known.loc[known._name_key.eq(a4_key(name))]
        degree = program.get('degree_type')
        if not degree and known.degree_type.nunique() == 1:
            degree = known.degree_type.iloc[0]
        level = program.get('program_level') or (None if degree else state.get('profile', {}).get('target_degree'))
        costs = estimate_cost_v2(name, level, unitid=uid, program_name=program.get('program_name'),
                                 degree_type=degree, fallback_model=fallback_model)
        program['unitid'] = costs['unitid']
        output['finance'].append({**costs,
            'tuition_annual': costs['tuition'], 'living_cost_annual': costs['living'],
            'explainability': None,  # These are sourced estimates, not SHAP attributions.
            'university': name, 'program_name': program.get('program_name'),
            'country': program.get('country') or meta.get('country') or costs.get('country')})
    output['status'] = 'financial_done'
    return output

financial_agent = financial_agent_v2
print(f'Crosswalk: {len(a4_crosswalk)}/{a4_catalog.university_name.nunique()} universities; {len(a4_catalog)} catalog rows have UNITID.')
print('Active entry point: financial_agent = financial_agent_v2. Original cells remain unchanged.')
print('KNN-imputed tuition is never treated as observed truth. Living remains a baseline x parity estimate.')

# %% checks
def run_agent4_checks():
    checks = []
    def check(label, condition):
        checks.append({'check': label, 'passed': bool(condition)})
    first = a4_catalog.iloc[0]
    cost = estimate_cost_v2(first.university_name, degree_type=first.degree_type, program_name=first.program_name)
    check('Catalog tuition takes priority', cost['tuition'] == first.tuition_out_state_usd)
    check('UNITID works when the display name differs', estimate_cost_v2('arbitrary display name', unitid=int(first.unitid), degree_type=first.degree_type, program_name=first.program_name)['total_cost'] == cost['total_cost'])
    check('Blank university cannot match a random row', estimate_cost_v2('', 'MS')['total_cost'] is None)
    check('Wrong degree does not select first university row', estimate_cost_v2(first.university_name, 'BS', program_name=first.program_name)['cost_data_quality'] == 'LEVEL_CONFLICT')
    check('Unknown program remains unknown', estimate_cost_v2(first.university_name, 'MS', program_name='No such program')['total_cost'] is None)
    check('Missing level remains unknown', estimate_cost_v2(first.university_name)['cost_data_quality'] == 'LEVEL_REQUIRED')
    check('Canonical graduate level resolves by UNITID', estimate_cost_v2(unitid=int(first.unitid), program_level="Graduate / Master's", program_name=first.program_name)['total_cost'] == cost['total_cost'])
    check('Invalid explicit level is not silently ignored', estimate_cost_v2(first.university_name, 'invalid', degree_type='MS')['cost_data_quality'] == 'INVALID_LEVEL')
    check('Conflicting explicit degree and level are rejected', estimate_cost_v2(first.university_name, 'BS', degree_type='MS')['cost_data_quality'] == 'LEVEL_CONFLICT')
    grad = a4_financial_index.loc[(int(first.unitid), "Graduate / Master's")]
    check('Living uses chosen graduate row and effective RPP', cost['living'] == round(grad.baseline_non_tuition_student_cost_usd * grad.rpp_used_2024 / 100, 2))
    knn = a4_master.loc[a4_master.tuition_data_quality.eq('KNN_IMPUTED') & ~a4_master.unitid.isin(a4_catalog.unitid)].iloc[0]
    check('KNN target is excluded', estimate_cost_v2(unitid=int(knn.unitid), program_level=knn.program_level)['tuition'] is None)
    check('Regression requires an explicit callable and is labelled', estimate_cost_v2(unitid=int(knn.unitid), program_level=knn.program_level, fallback_model=lambda row: 12345)['tuition_source'] == 'REGRESSION_FALLBACK')
    state = {'profile': {'target_degree': 'BS'}, 'programs': [{'university': first.university_name, 'program_name': first.program_name}]}
    saved = deepcopy(state)
    out = financial_agent(state)
    check('Catalog program level overrides generic profile level', out['finance'][0]['program_level'] == "Graduate / Master's")
    check('Input state is preserved', state == saved)
    check('Legacy annual-cost output fields are preserved', out['finance'][0]['tuition_annual'] == out['finance'][0]['tuition'] and out['finance'][0]['living_cost_annual'] == out['finance'][0]['living'])
    check('Unknown entries are retained for downstream review', len(financial_agent({'programs': [{'university': 'unresolved', 'program_name': 'unknown'}]})['finance']) == 1)
    check('Empty input gives empty finance', financial_agent({'programs': []})['finance'] == [])
    # Deliberately mask one catalog value, then restore it: exercise a fallback
    # that today's complete catalog does not need. This is a contract check.
    mask = a4_catalog.unitid.eq(first.unitid)
    saved_tuition = a4_catalog.loc[mask, 'tuition_out_state_usd'].copy()
    ref_mask = a4_published_coa.unitid.eq(first.unitid)
    saved_total = a4_published_coa.loc[ref_mask, 'published_total_usd'].copy()
    try:
        a4_catalog.loc[mask, 'tuition_out_state_usd'] = np.nan
        fallback = estimate_cost_v2(first.university_name, degree_type=first.degree_type, program_name=first.program_name)
        check('Missing catalog tuition uses published COA', fallback['cost_source'] == 'published_coa' and fallback['total_cost'] == saved_total.iloc[0])
        check('Published fallback carries source and scope', bool(fallback.get('published_source_url')) and bool(fallback.get('published_scenario')))
        a4_published_coa.loc[ref_mask, 'published_total_usd'] = np.nan
        check('Missing catalog and published costs stay unknown', estimate_cost_v2(first.university_name, degree_type=first.degree_type, program_name=first.program_name)['total_cost'] is None)
    finally:
        a4_catalog.loc[mask, 'tuition_out_state_usd'] = saved_tuition
        a4_published_coa.loc[ref_mask, 'published_total_usd'] = saved_total
    return pd.DataFrame(checks)

agent4_checks = run_agent4_checks()
print(agent4_checks.to_string(index=False))
assert agent4_checks.passed.all(), 'An Agent 4 contract check failed.'
# Select a real CS catalog entry for each institution without using prices or targets:
# prefer the base title, otherwise the first specialization in alphabetical order.
a4_cost_predictions = []
for row in a4_crosswalk.itertuples(index=False):
    cs_options = a4_catalog.loc[a4_catalog.unitid.eq(row.unitid) & a4_catalog.program_name.str.startswith('MS Computer Science')].sort_values('program_name', kind='stable')
    selected_name = cs_options.iloc[0].program_name
    pred = estimate_cost_v2(unitid=row.unitid, program_name=selected_name, degree_type='MS')
    a4_cost_predictions.append({'university_name': row.university_name, 'program_name': selected_name, **pred})
a4_cost_predictions = pd.DataFrame(a4_cost_predictions)
a4_cost_predictions.to_csv(A4_RUNS / 'catalog_cost_predictions_50.csv', index=False)
print('Cost lookup coverage:', a4_cost_predictions.total_cost.notna().sum(), '/', len(a4_cost_predictions))

# %% replay
import joblib
from types import SimpleNamespace
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV

def a4_notebook(relative):
    return json.loads((A4_ROOT / 'backend/app/agents' / relative).read_text(encoding='utf-8'))

def a4_exec_cell(notebook, index, namespace):
    exec(compile(''.join(notebook['cells'][index]['source']), f'notebook-cell-{index}', 'exec'), namespace)

a4_applicants = pd.read_csv(A4_ROOT / 'data/raw/agent2/agent2_training.csv')
# Fixed selection independent of predictions or admission outcomes; all application rows
# for these applicant IDs are excluded from this demo's replacement admission-model fit.
a4_demo_records = a4_applicants.drop_duplicates('applicant_id').head(20).copy()
assert len(a4_demo_records) == 20
a4_fit = a4_applicants.loc[~a4_applicants.applicant_id.isin(a4_demo_records.applicant_id)].copy()
a2 = {'np': np, 'pd': pd}
a2_nb = a4_notebook('university_matching_agent/Agent2_University_Agent.ipynb')
for idx in [16, 52, 58]:
    a4_exec_cell(a2_nb, idx, a2)
a2_artifacts = A4_ROOT / 'backend/app/agents/university_matching_agent/trained models'
for var, filename in {
    'FINAL_FEATURES': 'agent2_feature_columns.joblib',
    'AGENT1_TIER_REPRESENTATION': 'agent2_agent1_tier_representation.joblib',
    'UNIV_CLUSTER_COLS': 'university_cluster_features.joblib',
    'university_cluster_scaler': 'university_cluster_scaler.joblib',
    'university_cluster_model': 'university_cluster_model.joblib',
    'applicant_scaler': 'applicant_cluster_scaler.joblib',
    'applicant_kmeans': 'applicant_cluster_model.joblib',
}.items():
    a2[var] = joblib.load(a2_artifacts / filename)
a2['APPLICANT_CLUSTER_FEATURES'] = list(a2['applicant_scaler'].feature_names_in_)
a2['applicant_cluster_medians'] = {'gre_numeric': float(a4_fit.gre_quant.median())}
a4_features = pd.DataFrame({'tier_score': a4_fit.tier_score, 'gpa_numeric': a4_fit.gpa,
    'gre_numeric': a4_fit.gre_quant.fillna(0), 'gre_missing': a4_fit.gre_quant.isna().astype(int)})
a4_cluster_input = a4_features[['gpa_numeric', 'gre_numeric']].copy()
a4_cluster_input.loc[a4_features.gre_missing.eq(1), 'gre_numeric'] = a2['applicant_cluster_medians']['gre_numeric']
a4_features['applicant_cluster'] = a2['applicant_kmeans'].predict(a2['applicant_scaler'].transform(a4_cluster_input))
# The fitted admission model is absent from the uploaded artifact directory.
# Fit a documented demonstration replacement using the saved feature contract.
# This is NOT the original notebook's saved model and has no reported accuracy here.
a2['admit_model'] = CalibratedClassifierCV(
    GradientBoostingClassifier(n_estimators=100, max_depth=2, learning_rate=0.05, random_state=42),
    cv=3, method='sigmoid')
a2['admit_model'].fit(a4_features[a2['FINAL_FEATURES']], a4_fit.admit_result.astype(int))
a4_retrieval_catalog = a4_catalog.fillna('').copy()
a4_text = a4_retrieval_catalog[['program_name', 'description_text', 'curriculum_highlights', 'faculty_research_areas']].agg(' '.join, axis=1)
a4_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
a4_vectors = a4_vectorizer.fit_transform(a4_text)

def a4_retrieve(profile, preferences, top_k=20):
    query = f"{profile['target_degree']} {profile['target_program']}"
    sims = cosine_similarity(a4_vectorizer.transform([query]), a4_vectors)[0]
    indices = a4_retrieval_catalog.index[a4_retrieval_catalog.degree_type.eq(profile['target_degree'])]
    ranked = sorted(indices, key=lambda i: (-sims[i], int(i)))[:top_k]
    return [SimpleNamespace(payload=a4_retrieval_catalog.loc[i].to_dict(), score=float(sims[i])) for i in ranked]

a2['retrieve_candidates'] = a4_retrieve
a2['rerank'] = lambda query, candidates, top_n=10: [(c, c.score) for c in candidates[:top_n]]
a2['get_shap_top_factors'] = lambda X: []  # SHAP unavailable, never fabricate feature attributions.
a2['generate_explanation'] = lambda university, program, gpa, target, tier, score, factors, description, **kwargs: f'Local demo: TF-IDF retrieval, recorded GPA {gpa:.2f}, replacement admission classifier; {tier}. SHAP and LLM explanation unavailable.'
a2['tag_budget_signal'] = lambda payload, preferences: None  # No budgets recorded in these uploaded applicants.
a2['save_matches_to_db'] = lambda *args: None  # Replay has no external persistence.
a3, a5, a6 = {}, {}, {}
a4_exec_cell(a4_notebook('program_agent/Agent3_Program_agent.ipynb'), 2, a3)
for idx in [2, 4, 6, 8]:
    a4_exec_cell(a4_notebook('scholarship_agent/Agent5_Scholarship_agent.ipynb'), idx, a5)
for idx in [2, 4]:
    a4_exec_cell(a4_notebook('career_agent/Agent6_Career_agent.ipynb'), idx, a6)

agent4_replay_summary, agent4_replay_states = [], []
for number, record in enumerate(a4_demo_records.to_dict('records'), start=1):
    recorded_program = a4_catalog.loc[a4_catalog.program_id.eq(record['program_id'])]
    if len(recorded_program) != 1:
        raise ValueError('Recorded application program must map uniquely to catalog program_id.')
    recorded_program = recorded_program.iloc[0]
    profile = {k: record[k] for k in ['gpa', 'gre_quant', 'gre_verbal', 'work_experience_years',
        'research_publications', 'undergrad_tier_score', 'major', 'work_industry', 'sop_score', 'lor_score', 'profile_strength_score']}
    profile.update(gpa_scale=4.0, target_degree=recorded_program.degree_type,
        target_program=record['program_name'], interests_text='', career_goal=None)
    state = {'student_id': f'uploaded-demo-{number:02d}', 'profile': profile, 'preferences': {},
        'extracurricular': {'profile_strength_score': record['profile_strength_score']},
        'demo_provenance': 'Uploaded training-row replay; recorded application target; not new research participants or an accuracy test.'}
    state = a2['university_matching_agent'](state)
    for university in state['matched_universities']:
        university['unitid'] = a4_name_to_id[a4_key(university['university'])]
        for program in university['programs']:
            program['unitid'] = university['unitid']
    state = a3['program_agent'](state)
    state = financial_agent(state)
    state = a5['scholarship_agent'](state, a5['scholarship_catalog'], as_of='2026-10-21')
    state = a6['career_agent'](state)
    counts = {key: len(state.get(key, [])) for key in ['matched_universities', 'programs', 'finance', 'scholarships', 'careers']}
    complete = counts['programs'] > 0 and all(counts[key] == counts['programs'] for key in ['finance', 'scholarships', 'careers'])
    priced = sum(row['total_cost'] is not None for row in state['finance'])
    assert all(row['unitid'] is not None for row in state['finance'])
    assert all(row['funding_gap'] is None for row in state['scholarships']), 'Unrecorded budget must not be invented.'
    agent4_replay_summary.append({'student_id': state['student_id'], **counts, 'priced_programs': priced,
        'fully_recommendable_scholarships': sum(row['catalog_counts']['fully_recommendable'] for row in state['scholarships']),
        'chain_completed': complete, 'all_costs_available': priced == counts['programs']})
    # Do not persist the full per-scholarship review arrays (large and redundant).
    for row in state['scholarships']:
        row.pop('eligibility_review', None)
    agent4_replay_states.append(state)
    print(f"{state['student_id']}: {counts['programs']} programs, {priced} costs, chain completed={complete}")
agent4_replay_summary = pd.DataFrame(agent4_replay_summary)
agent4_replay_summary.to_csv(A4_RUNS / 'demo_20_summary.csv', index=False)
(A4_RUNS / 'demo_20_states.json').write_text(json.dumps(agent4_replay_states, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)), encoding='utf-8')
print('Replay inputs use recorded fields; interests, nationality, budget and career goals remain unspecified.')
print('Agent 1/7 extraction was not rerun: uploaded fields/scores were supplied. Agent 2 uses its actual orchestration and scoring functions with local retrieval and a replacement fitted model.')

# %% benchmark
def evaluate_published_costs(predictions, references):
    """Fixed 50-institution audit. Missing/incomparable references stay visible.

    Descriptive discrepancy is separate from strict matched-scope accuracy.
    Published-COA fallback outputs are identified and excluded from scoring.
    """
    if references.unitid.duplicated().any():
        raise ValueError('Expected one preregistered reference scenario per UNITID.')
    audit = predictions.merge(references, on='unitid', how='left', suffixes=('', '_reference'), validate='one_to_one')
    audit['published_total_usd'] = pd.to_numeric(audit['published_total_usd'], errors='coerce')
    audit['absolute_percentage_error'] = (audit.total_cost - audit.published_total_usd).abs() / audit.published_total_usd
    audit['reference_available'] = audit.published_total_usd.gt(0)
    audit['paired_prediction_available'] = audit.reference_available & audit.total_cost.notna()
    audit['independent_estimate'] = audit.paired_prediction_available & ~audit.cost_source.eq('published_coa')
    audit['within_10_percent'] = audit.paired_prediction_available & audit.absolute_percentage_error.le(0.10)
    # Catalog price year/covered months/fee scope are currently unconfirmed.
    # Do not relabel a cross-year broad-budget comparison as program-level accuracy.
    audit['strictly_comparable'] = (
        audit.independent_estimate & audit['comparison_status'].eq('matched_year_period_program_components')
        & audit.academic_year.notna() & audit.academic_year.eq(audit.academic_year_reference)
        & audit.months_covered.notna() & audit.months_covered.eq(audit.reference_months)
        & audit.program_level.eq(audit.reference_program_level))
    n = int(audit.independent_estimate.sum())
    strict_n = int(audit.strictly_comparable.sum())
    report = {'universities_requested': len(audit), 'published_totals_available': int(audit.reference_available.sum()),
        'prediction_coverage': float(audit.total_cost.notna().mean()),
        'reference_coverage': float(audit.reference_available.mean()), 'scored_estimates': n,
        'published_fallback_cases_excluded': int(audit.cost_source.eq('published_coa').sum()),
        'within_10_percent_count': int(audit.loc[audit.independent_estimate, 'within_10_percent'].sum()),
        'descriptive_share_within_10_percent': float(audit.loc[audit.independent_estimate, 'within_10_percent'].mean()) if n else None,
        'strictly_comparable_cases': strict_n,
        'strict_accuracy_within_10_percent': float(audit.loc[audit.strictly_comparable, 'within_10_percent'].mean()) if strict_n else None}
    return audit, report

if not A4_REFERENCE_PATH.exists():
    raise FileNotFoundError('Published-cost research ledger is required; do not invent reference costs.')
a4_references = pd.read_csv(A4_REFERENCE_PATH)
agent4_cost_audit, agent4_cost_report = evaluate_published_costs(a4_cost_predictions, a4_references)
# Regression guard: copied references must not produce a perfect accuracy score.
_copied = a4_cost_predictions.copy()
_copied['cost_source'] = 'published_coa'
assert evaluate_published_costs(_copied, a4_references)[1]['scored_estimates'] == 0
agent4_cost_audit.to_csv(A4_RUNS / 'published_cost_comparison_50.csv', index=False)
(A4_RUNS / 'published_cost_metrics.json').write_text(json.dumps(agent4_cost_report, indent=2), encoding='utf-8')
print(agent4_cost_audit[['university_name', 'total_cost', 'published_total_usd', 'absolute_percentage_error', 'comparison_status']].to_string(index=False))

# %% final
print('AGENT 4 - EXECUTED FINAL RESULTS')
print(f"University crosswalk: {len(a4_crosswalk)}/50 ({len(a4_crosswalk)/50:.1%}); catalog UNITID coverage: {a4_catalog.unitid.notna().mean():.1%}")
print(f"Functional checks: {int(agent4_checks.passed.sum())}/{len(agent4_checks)} passed (not predictive accuracy).")
print(f"Uploaded applicant replay: {int(agent4_replay_summary.chain_completed.sum())}/20 completed Agent 2 -> 3 -> 4 -> 5 -> 6.")
print(f"Priced programs: {agent4_replay_summary.priced_programs.sum()}/{agent4_replay_summary.programs.sum()}.")
print('Demo applicants have no recorded budgets: funding gaps remain None even when program costs are available.')
print('Replay configuration: offline TF-IDF, replacement fitted Agent 2 admission model; recorded Agent 1/7 inputs; no external services.')
print('Published-cost benchmark:', json.dumps(agent4_cost_report, indent=2))
print('Strict program-level accuracy is NOT MEASURED unless the published reference and estimate agree on year, period, program and cost components.')
if 'results' in globals() and 'best_name' in globals():
    print(f"Reexecuted legacy regression diagnostic: {best_name}, R2={results[best_name]['test_r2']:.4f}, MAE=${results[best_name]['mae']:,.2f}. Row split includes imputed targets; not independent COA accuracy.")
else:
    print('Historical regression fallback only: stored original notebook R2 ~0.53, MAE ~$4,000; not remeasured in this extension.')
print('No 96% cost-accuracy claim. Matching/functional success and price accuracy are different measures.')
