# %% Dataset audit and institution-separated splits
import joblib
import sklearn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import OrdinalEncoder, FunctionTransformer, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.cluster import KMeans
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score, davies_bouldin_score
from threadpoolctl import threadpool_limits
from datetime import datetime, timezone

CAREER_DATA_PATH = AGENT6_DATA / 'agent_6_dataset_final_merged.csv'
CAREER_MODEL_DIR = PROJECT_ROOT / 'backend/app/agents/career_agent/trained_models'
CAREER_REPORT_DIR = PROJECT_ROOT / 'data/processed/agent6'
CAREER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
CAREER_REPORT_DIR.mkdir(parents=True, exist_ok=True)
outcomes = pd.read_csv(CAREER_DATA_PATH, low_memory=False)
data_fingerprint = hashlib.sha256(CAREER_DATA_PATH.read_bytes()).hexdigest()
REG_FEATURES = ['cip_family','cip_code','credential_level','control']
CLUSTER_FEATURES = ['earnings_1yr','earnings_4yr','median_debt_observed']
observed = outcomes.loc[outcomes.row_type.eq('scorecard_observed') & outcomes.in_us_scope.eq(True) & outcomes.unitid.notna()].copy()
identity = ['unitid','cip_code','credential_level']
duplicates = int(observed.duplicated(identity).sum())
# Select evidence count, never the target value, to resolve duplicate field/cohort keys.
observed = observed.sort_values('n_earnings',ascending=False,kind='stable').drop_duplicates(identity).reset_index(drop=True)
for c in CLUSTER_FEATURES:
    observed[c] = pd.to_numeric(observed[c],errors='coerce')
    observed.loc[observed[c] < 0,c] = np.nan
splitter = GroupShuffleSplit(n_splits=1,test_size=.20,random_state=42)
development_i,test_i = next(splitter.split(observed,groups=observed.unitid))
train_rel,dev_rel = next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=43).split(
    observed.iloc[development_i],groups=observed.iloc[development_i].unitid))
train_i,dev_i = development_i[train_rel],development_i[dev_rel]
split_names = pd.Series('',index=observed.index)
for name,indices in [('train',train_i),('dev',dev_i),('test',test_i)]: split_names.loc[indices]=name
assert not (set(observed.iloc[train_i].unitid)&set(observed.iloc[dev_i].unitid))
assert not (set(observed.iloc[development_i].unitid)&set(observed.iloc[test_i].unitid))
audit6 = {'uploaded_rows':len(outcomes),'uploaded_columns':len(outcomes.columns),'sha256':data_fingerprint,
    'row_types':outcomes.row_type.value_counts().to_dict(),'deduplicated_us_observed_rows':len(observed),
    'duplicate_observed_keys_removed':duplicates,'mapped_program_ids':int(outcomes.program_id.nunique()),
    'split_rows':split_names.value_counts().to_dict(),
    'split_institutions':{n:int(observed.loc[split_names.eq(n)].unitid.nunique()) for n in ['train','dev','test']},
    'split_institution_overlap':0,'research_industry_ground_truth_labels':0,
    'placement_status_counts':outcomes.placement_data_status.value_counts().to_dict(),
    'provenance':'Source names and scopes are recorded in the uploaded file; row-level source reconstruction and cohort-year validation are not available.',
    'population_scope':'Uploaded file marks outcomes as proxies for US federal-aid completers, not international-student forecasts.'}
observed[identity].assign(split=split_names).to_csv(CAREER_REPORT_DIR/'institution_splits.csv',index=False)
print(json.dumps(audit6,indent=2))
print('No heuristic job/research score, admission label, or employment proxy is used as a supervised target.')

# %% Supervised four-year cohort earnings regression
def regression_inputs(frame):
    return frame[REG_FEATURES].fillna('Unknown').astype(str)


def earnings_metrics(actual,predicted):
    actual,predicted=np.asarray(actual),np.asarray(predicted)
    return {'n':len(actual),'mae_usd':float(mean_absolute_error(actual,predicted)),
            'rmse_usd':float(np.sqrt(mean_squared_error(actual,predicted))),
            'r2':float(r2_score(actual,predicted)),
            'within_10_percent':float(np.mean(np.abs(predicted-actual)/actual <= .10)),
            'median_absolute_percentage_error':float(np.median(np.abs(predicted-actual)/actual))}


def make_earnings_model():
    # Rare category grouping is fitted on training institutions only. No university identity,
    # earnings-derived field aggregates, debt/earnings ratios, or placement proxies enter X.
    return Pipeline([
        ('categories',OrdinalEncoder(handle_unknown='use_encoded_value',unknown_value=-1,
                                     encoded_missing_value=-1,max_categories=200)),
        ('regressor',TransformedTargetRegressor(
            regressor=HistGradientBoostingRegressor(categorical_features=[0,1,2,3],
                max_iter=150,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=5,
                early_stopping=False,random_state=42),func=np.log1p,inverse_func=np.expm1))])


eligible_earnings = observed.earnings_4yr.notna() & observed.earnings_4yr.gt(0)
reg_train=observed.loc[split_names.eq('train') & eligible_earnings]
reg_dev=observed.loc[split_names.eq('dev') & eligible_earnings]
reg_test=observed.loc[split_names.eq('test') & eligible_earnings]
earnings_model=make_earnings_model()
with threadpool_limits(limits=1):
    earnings_model.fit(regression_inputs(reg_train),reg_train.earnings_4yr)
    dev_regression=earnings_metrics(reg_dev.earnings_4yr,earnings_model.predict(regression_inputs(reg_dev)))
print('Development results (not test accuracy):',dev_regression)
# Fixed hyperparameters; refit on train+dev, freeze, then evaluate test once below.
reg_fit=observed.loc[~split_names.eq('test') & eligible_earnings]
with threadpool_limits(limits=1):
    earnings_model.fit(regression_inputs(reg_fit),reg_fit.earnings_4yr)
joblib.dump(earnings_model,CAREER_MODEL_DIR/'agent6_earnings_model.joblib',compress=3)
regression_baseline=float(reg_fit.earnings_4yr.median())
print('Saved fitted earnings model; withheld test institutions have not been used for fitting.')

# %% Unsupervised outcome clustering, selected on development institutions
eligible_clusters=observed[CLUSTER_FEATURES].notna().sum(axis=1).ge(2)
cluster_train=observed.loc[split_names.eq('train') & eligible_clusters,CLUSTER_FEATURES]
cluster_dev=observed.loc[split_names.eq('dev') & eligible_clusters,CLUSTER_FEATURES]
cluster_fit=observed.loc[~split_names.eq('test') & eligible_clusters,CLUSTER_FEATURES]
cluster_test=observed.loc[split_names.eq('test') & eligible_clusters,CLUSTER_FEATURES]


def cluster_preprocessor():
    return Pipeline([('log',FunctionTransformer(np.log1p,feature_names_out='one-to-one')),
                     ('imputer',SimpleImputer(strategy='median')),
                     ('scale',StandardScaler())])


pre=cluster_preprocessor()
with threadpool_limits(limits=1):
    train_z=pre.fit_transform(cluster_train);dev_z=pre.transform(cluster_dev)
    cluster_candidates=[]
    for k in [2,3,4,5,6,7,8]:
        candidate=KMeans(n_clusters=k,n_init=10,random_state=42).fit(train_z)
        labels=candidate.predict(dev_z)
        score=float(silhouette_score(dev_z,labels,sample_size=min(2000,len(dev_z)),random_state=42))
        cluster_candidates.append({'k':k,'development_silhouette':score})
    best_k=max(cluster_candidates,key=lambda row:row['development_silhouette'])['k']
    cluster_model=Pipeline([('preprocess',cluster_preprocessor()),
                            ('kmeans',KMeans(n_clusters=best_k,n_init=10,random_state=42))])
    cluster_model.fit(cluster_fit)
joblib.dump(cluster_model,CAREER_MODEL_DIR/'agent6_outcome_clusters.joblib',compress=3)
cluster_fit_summary=cluster_fit.copy()
with threadpool_limits(limits=1): cluster_fit_summary['cluster']=cluster_model.predict(cluster_fit)
cluster_summary=cluster_fit_summary.groupby('cluster').agg(
    count=('earnings_4yr','size'),median_earnings_1yr=('earnings_1yr','median'),
    median_earnings_4yr=('earnings_4yr','median'),median_observed_debt=('median_debt_observed','median'))
cluster_summary.to_csv(CAREER_REPORT_DIR/'cluster_profiles.csv')
print(pd.DataFrame(cluster_candidates).to_string(index=False))
print('Selected k:',best_k,'(development selection only)')
print(cluster_summary.to_string())
print('Clusters describe earnings/debt patterns. They are not research/industry labels or job-placement classes.')

# %% Frozen evaluation on withheld institutions and portable joblib bundle
frozen_hashes={name:hashlib.sha256((CAREER_MODEL_DIR/name).read_bytes()).hexdigest()
              for name in ['agent6_earnings_model.joblib','agent6_outcome_clusters.joblib']}
with threadpool_limits(limits=1):
    test_earnings_predictions=earnings_model.predict(regression_inputs(reg_test))
    test_cluster_labels=cluster_model.predict(cluster_test)
    test_z=cluster_model.named_steps['preprocess'].transform(cluster_test)
    cluster_test_report={'silhouette':float(silhouette_score(test_z,test_cluster_labels,
        sample_size=min(2000,len(test_z)),random_state=42)),
        'davies_bouldin':float(davies_bouldin_score(test_z,test_cluster_labels)),
        'rows':len(cluster_test),'cluster_count':best_k}
regression_test_report=earnings_metrics(reg_test.earnings_4yr,test_earnings_predictions)
baseline_test_report=earnings_metrics(reg_test.earnings_4yr,np.full(len(reg_test),regression_baseline))
reg_test[identity+['earnings_4yr']].assign(predicted_earnings_4yr=test_earnings_predictions).to_csv(
    CAREER_REPORT_DIR/'earnings_test_predictions.csv',index=False)
print('Held-out earnings model:',regression_test_report)
print('Training-median baseline:',baseline_test_report)
print('Held-out clustering quality (not accuracy):',cluster_test_report)

# Map to exact Agent 2 catalog IDs. Never join on a university alone.
mapped_outcomes=outcomes.loc[outcomes.program_id.notna()].copy()
assert mapped_outcomes.program_id.is_unique
catalog_ids=pd.read_csv(AGENT6_CATALOG_PATH)
assert catalog_ids.program_id.is_unique
mapped_outcomes=mapped_outcomes.merge(catalog_ids[['program_id','unitid','university_name','program_name','degree_type','institution_type']],
    on='program_id',suffixes=('','_catalog'),how='inner',validate='one_to_one')
assert (mapped_outcomes.unitid.isna() | mapped_outcomes.unitid.eq(mapped_outcomes.unitid_catalog)).all()
assert (mapped_outcomes.program_label_agent2 == mapped_outcomes.program_name_catalog).all()
mapped_outcomes['outcome_source_unitid']=mapped_outcomes.unitid
mapped_outcomes['unitid_source']=np.where(mapped_outcomes.unitid.isna(),'exact_catalog_program_identity','uploaded_outcome_identity')
mapped_outcomes['unitid']=mapped_outcomes.unitid.fillna(mapped_outcomes.unitid_catalog)
mapped_outcomes['control']=mapped_outcomes.control.fillna(mapped_outcomes.institution_type.str.lower())
assert mapped_outcomes.credential_level.eq("Master's").all()
assert mapped_outcomes.degree_type.isin(['MS','MEng','MBA']).all()
with threadpool_limits(limits=1):
    mapped_outcomes['model_earnings_4yr']=earnings_model.predict(regression_inputs(mapped_outcomes))
    usable=mapped_outcomes[CLUSTER_FEATURES].notna().sum(axis=1).ge(2)
    mapped_outcomes['outcome_cluster']=pd.Series(pd.NA,index=mapped_outcomes.index,dtype='Int64')
    mapped_outcomes.loc[usable,'outcome_cluster']=cluster_model.predict(mapped_outcomes.loc[usable,CLUSTER_FEATURES])
lookup_bundle={
    'version':'agent6-outcomes-v2','dataset_sha256':data_fingerprint,
    'regression_features':REG_FEATURES,'cluster_features':CLUSTER_FEATURES,
    'programs':json.loads(mapped_outcomes.to_json(orient='records')),
    'cluster_profiles':json.loads(cluster_summary.reset_index().to_json(orient='records')),
    'regression_test':regression_test_report,'baseline_test':baseline_test_report,
    'clustering_test':cluster_test_report,'sklearn_version':sklearn.__version__,
    'scope':'Uploaded cohort observations/estimates, not individual career outcomes; no international salary forecast.'}
joblib.dump(lookup_bundle,CAREER_MODEL_DIR/'agent6_lookup_bundle.joblib',compress=3)
for name,digest in frozen_hashes.items():
    assert hashlib.sha256((CAREER_MODEL_DIR/name).read_bytes()).hexdigest()==digest
print('Saved 3 portable joblib files. Only built-in sklearn estimators and plain-data dictionaries are serialized.')

# %% Active career agent: exact program evidence, clustering and conservative placement scope
career_agent_legacy=career_agent


def load_agent6_models(directory=CAREER_MODEL_DIR):
    directory=Path(directory)
    return {'earnings':joblib.load(directory/'agent6_earnings_model.joblib'),
            'clusters':joblib.load(directory/'agent6_outcome_clusters.joblib'),
            'lookup':joblib.load(directory/'agent6_lookup_bundle.joblib')}


agent6_models=load_agent6_models()


def career_answer(row):
    """Give a readable answer while retaining the structured evidence in each row."""
    path = row['career_path']
    if path is None:
        advice = 'Choose a research or industry goal and confirm the program pathway before deciding.'
    elif row['stated_goal'] is not None and path != row['stated_goal']:
        advice = f"This program supports the {path} pathway, which differs from your stated {row['stated_goal']} goal. Review the curriculum before choosing it."
    else:
        advice = f"Suggested direction: {path.capitalize()}."
    reasons = row['track_evidence'].get(path, []) if path else []
    if reasons:
        advice += ' Program evidence: ' + ', '.join(reasons) + '.'
    if row['expected_roles']:
        advice += ' Roles to explore: ' + ', '.join(row['expected_roles']) + '.'
    earnings = row.get('earnings_context')
    if earnings:
        supplied = earnings['uploaded_4yr_earnings_usd']
        if supplied is not None:
            advice += f" Uploaded four-year cohort earnings estimate: ${supplied:,.0f} USD."
        advice += f" Model four-year cohort estimate: ${earnings['model_4yr_earnings_usd']:,.0f} USD."
        advice += ' These describe cohort context, not a personal salary offer.'
    else:
        advice += ' No exact program earnings evidence was supplied.'
    placement = row['avg_placement_stats']
    if placement is not None:
        advice += f" Reported program placement: {placement['placement_rate']:.1%} for the {placement['cohort_year']} cohort."
    else:
        advice += ' Program-specific placement rate is not provided in the supplied data.'
    if path == 'industry':
        advice += ' Next steps: compare internships and capstones, build a relevant project portfolio, and check role requirements.'
    elif path == 'research':
        advice += ' Next steps: compare thesis options, identify matching faculty, and prepare a research proposal.'
    return advice


def career_agent_v2(state,catalog=None,*,model_bundle=None,placement_reports=None,as_of=None,artifacts=None):
    artifacts=agent6_models if artifacts is None else artifacts
    # Preserve existing documented career-path rules and optional independently labelled classifier.
    result=career_agent_legacy(state,catalog=catalog,model_bundle=model_bundle,
                               placement_reports=placement_reports,as_of=as_of)
    reference_year=(pd.Timestamp.now(tz='Asia/Kolkata') if as_of is None else pd.Timestamp(as_of)).year
    entries=artifacts['lookup']['programs']
    by_id={r['program_id']:r for r in entries}
    by_name={(career_key(r['university_name']),career_key(r['program_name_catalog'])):r for r in entries}
    for source,row in zip(state.get('programs') or [],result['careers']):
        key=(career_key(row['university']),career_key(row['program_name']))
        evidence=by_id.get(source.get('program_id')) if source.get('program_id') else by_name.get(key)
        if evidence is not None and key != (career_key(evidence['university_name']),career_key(evidence['program_name_catalog'])):
            evidence=None
            row['warnings'].append('Program ID/name conflict: outcome enrichment rejected.')
        if evidence is not None and source.get('unitid') is not None and float(source['unitid'])!=float(evidence['unitid']):
            evidence=None
            row['warnings'].append('UNITID conflict: outcome enrichment rejected.')
        row.update({'outcome_evidence':None,'outcome_cluster':None,'earnings_context':None,
                    'school_placement_context':None,'research_industry_accuracy':'not_measured'})
        if evidence is None:
            row['warnings'].append('No exact uploaded program-outcome match; existing advisory fallback retained.')
            continue
        row['program_id']=evidence['program_id'];row['unitid']=int(evidence['unitid'])
        row['method']+=' + uploaded_outcomes_and_unsupervised_clusters'
        row['warnings']=[w.replace('Advisory rule result; no outcome-trained model is available.',
            'Career-path advice is heuristic; the separate trained model estimates cohort earnings.') for w in row['warnings']]
        row['outcome_evidence']={k:evidence.get(k) for k in ['row_type','estimate_method','evidence_level',
            'evidence_n','usable_for_scoring','thin_sample_flag','intl_student_applicability','credential_level',
            'outcome_source_unitid','unitid_source']}
        row['outcome_cluster']={'id':evidence.get('outcome_cluster'),
            'meaning':'Similarity of cohort earnings and debt; not a career-track prediction',
            'input_origin':evidence['estimate_method']}
        row['earnings_context']={'uploaded_4yr_earnings_usd':evidence.get('earnings_4yr'),
            'uploaded_estimate_method':evidence['estimate_method'],
            'model_4yr_earnings_usd':evidence['model_earnings_4yr'],
            'model_scope':'Field/credential cohort estimate; not personalized salary or placement probability',
            'currency':'USD','cohort_year':None,'international_applicability':'proxy only'}
        path=row['career_path']
        role_field='expected_roles_research' if path=='research' else 'expected_roles_industry' if path=='industry' else None
        if role_field and career_text(evidence.get(role_field)):
            row['expected_roles']=list(dict.fromkeys(r.strip() for r in evidence[role_field].split('|') if r.strip()))
            row['role_sources']=['Uploaded dataset: '+(evidence.get('roles_source') or 'curated CIP-family mapping')]
        # A financial/employment proxy can never fill avg_placement_stats.
        row['employment_proxy_context']={'value':evidence.get('employment_rate_proxy'),
            'type':'uploaded proxy, NOT a placement rate'}
        if (evidence.get('placement_source') and evidence.get('placement_rate') is not None
            and evidence.get('placement_year') is not None and int(evidence['placement_year']) <= reference_year):
            row['school_placement_context']={k:evidence.get(k) for k in ['placement_source','placement_rate',
                'placement_basis','placement_year','placement_level','placement_window_months','surveyed_count','placed_count']}
            row['school_placement_context']['verification']='as supplied; source page not independently checked in this run'
            row['warnings'].append('Placement evidence is school/cohort scoped and is not assigned to this specialization.')
        if not evidence.get('usable_for_scoring') or evidence.get('thin_sample_flag') or evidence['estimate_method']=='field_national_fallback':
            row['review_required']=True
            row['warnings'].append('Thin or restricted evidence: treat outcome context as provisional.')
        row['warnings'].append('No independent student research/industry labels; clustering does not establish track accuracy.')
    for row in result['careers']:
        row['answer']=career_answer(row)
    return result


career_agent=career_agent_v2
print('Active entry point: career_agent(state), enriched with the uploaded dataset and fitted outcome clusters.')

# %% Executed handoff, catalog coverage and reload regression checks
new_demo=career_agent(agent3_live_demo)
assert agent3_live_demo==demo_original
assert [(r['university'],r['program_name']) for r in new_demo['careers']]==[
    (r['university'],r['program_name']) for r in agent3_live_demo['programs']]
new_coverage=career_agent(coverage_state)
catalog_counts_v2={'catalog_programs':len(new_coverage['careers']),
    'exact_outcome_matches':sum(r['outcome_evidence'] is not None for r in new_coverage['careers']),
    'with_cluster_assignment':sum(r['outcome_cluster'] is not None and r['outcome_cluster']['id'] is not None for r in new_coverage['careers']),
    'with_school_placement_context':sum(r['school_placement_context'] is not None for r in new_coverage['careers']),
    'with_program_placement_stats':sum(r['avg_placement_stats'] is not None for r in new_coverage['careers'])}
checks6=[]
def check6(name,condition):
    assert condition,name
    checks6.append({'check':name,'passed':True})
check6('input_state_preserved',agent3_live_demo==demo_original)
check6('all_catalog_programs_retained',len(new_coverage['careers'])==len(coverage_state['programs']))
check6('exact_mapping_coverage',catalog_counts_v2['exact_outcome_matches']==len(mapped_outcomes))
check6('proxies_not_reported_as_program_placement',catalog_counts_v2['with_program_placement_stats']==0)
check6('no_unseen_institution_overlap',not(set(observed.iloc[development_i].unitid)&set(observed.iloc[test_i].unitid)))
check6('estimates_excluded_from_training',observed.row_type.eq('scorecard_observed').all())
reload6=load_agent6_models()
with threadpool_limits(limits=1):
    check6('earnings_joblib_reload_identical',np.allclose(reload6['earnings'].predict(regression_inputs(reg_test.head(100))),test_earnings_predictions[:100]))
    check6('cluster_joblib_reload_identical',np.array_equal(reload6['clusters'].predict(cluster_test.head(100)),test_cluster_labels[:100]))
check6('lookup_reload_identical',reload6['lookup']['dataset_sha256']==data_fingerprint)
unknown=career_agent({'profile':{'career_goal':'industry'},'programs':[{'university':'Unknown university','program_name':'Unknown program'}]})['careers'][0]
check6('unknown_program_no_fabricated_outcomes',unknown['outcome_evidence'] is None and unknown['earnings_context'] is None)
conflict=deepcopy(agent3_live_demo)
conflict['programs'][0]['program_id']=mapped_outcomes.iloc[0].program_id
conflict_result=career_agent(conflict)['careers'][0]
check6('conflicting_program_identity_rejected',conflict_result['outcome_evidence'] is None)
check6('no_supervised_track_classifier_fabricated',all(r['research_industry_accuracy']=='not_measured' for r in new_coverage['careers']))
mba=next(r for r in agent6_models['lookup']['programs'] if r.get('placement_rate') is not None)
historical=career_agent({'profile':{'career_goal':'industry'},'programs':[
    {'university':mba['university_name'],'program_name':mba['program_name_catalog']}]},as_of='2000-01-01')
check6('future_placement_cohort_withheld',historical['careers'][0]['school_placement_context'] is None)
check6('readable_answers_for_every_program',all(bool(r['answer'].strip()) for r in new_coverage['careers']))
check6('illustrative_industry_answers_have_roles',all(r['career_path']=='industry' and r['expected_roles'] for r in new_demo['careers']))
print('Checks:',len(checks6),'passed')
print('Catalog coverage:',catalog_counts_v2)
print('Actual Agent 3 -> Agent 6 result:')
from textwrap import fill
for index,row in enumerate(new_demo['careers'],1):
    print(f"\n{index}. {row['university']} | {row['program_name']}")
    print(fill(row['answer'],width=100))
(CAREER_REPORT_DIR/'demo_predictions.json').write_text(json.dumps(new_demo['careers'],indent=2),encoding='utf-8')

# %% Final executed metrics and artifact manifest
manifest6={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
           for p in CAREER_MODEL_DIR.glob('*.joblib')}
report6={'version':'agent6-outcomes-v2','created_utc':datetime.now(timezone.utc).isoformat(),
    'audit':audit6,'regression_test':regression_test_report,'baseline_test':baseline_test_report,
    'clustering_test':cluster_test_report,'clustering_dev_candidates':cluster_candidates,
    'catalog_coverage':catalog_counts_v2,'functional_checks':checks6,'artifacts':manifest6,
    'sklearn_version':sklearn.__version__,'research_industry_classification_accuracy':None,
    'note':'Earnings metrics compare held-out uploaded cohort figures. Clustering metrics are not accuracy. Source rows and years are not independently reconstructed.'}
(CAREER_REPORT_DIR/'validation_report.json').write_text(json.dumps(report6,indent=2),encoding='utf-8')
(CAREER_MODEL_DIR/'manifest.json').write_text(json.dumps({'artifacts':manifest6,'dataset_sha256':data_fingerprint,
    'sklearn_version':sklearn.__version__,'regression_features':REG_FEATURES,'cluster_features':CLUSTER_FEATURES},indent=2),encoding='utf-8')
print('AGENT 6 — FINAL EXECUTED RESULTS')
print(f"Uploaded data: {len(outcomes):,} rows; exact program matches: {catalog_counts_v2['exact_outcome_matches']}/{catalog_counts_v2['catalog_programs']}")
print(f"Held-out earnings MAE: ${regression_test_report['mae_usd']:,.2f}; median baseline MAE: ${baseline_test_report['mae_usd']:,.2f}")
print(f"Held-out earnings R²: {regression_test_report['r2']:.4f}; share within ±10%: {regression_test_report['within_10_percent']:.2%}")
print(f"Unsupervised clusters: {best_k}; held-out silhouette: {cluster_test_report['silhouette']:.4f}; Davies–Bouldin: {cluster_test_report['davies_bouldin']:.4f}")
print(f"Functional checks: {len(checks6)}/{len(checks6)}; all three joblib artifacts saved and reloaded successfully.")
print('Research-versus-industry accuracy: NOT MEASURED — no independent track labels in uploaded data.')
print('Joblib directory:',CAREER_MODEL_DIR)
print('\nCAREER ANSWERS FOR THE DEMONSTRATION STUDENT')
for index,row in enumerate(new_demo['careers'],1):
    print(f"\n{index}. {row['university']} | {row['program_name']}")
    print(fill(row['answer'],width=100))
