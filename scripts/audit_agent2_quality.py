"""Audit the active bundle without retraining or modifying application artifacts."""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, accuracy_score, f1_score
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'backend/app/agents/university_matching_agent/trained_models_local'
OUT = ROOT / 'reports/agent2-quality'


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((BUNDLE / 'manifest.json').read_text())
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    training = ROOT / 'data/raw/agent2/agent2_training.csv'
    catalog_path = ROOT / 'data/raw/agent2/agent2_enhanced_program_catalog.csv'
    assert sha(training) == manifest['training_data_sha256']
    assert sha(catalog_path) == manifest['catalog_sha256']
    for name, digest in manifest['artifacts'].items():
        assert sha(BUNDLE / name) == digest
    load = lambda n: joblib.load(BUNDLE / (n + '.joblib'))
    model = load('agent2_admission_model')
    features = load('agent2_feature_columns')
    scaler = load('applicant_cluster_scaler')
    cluster = load('applicant_cluster_model')
    medians = load('applicant_cluster_medians')
    threshold = float(load('agent2_decision_threshold'))
    df = pd.read_csv(training)
    catalog = pd.read_csv(catalog_path)
    assert catalog.program_id.is_unique
    def frame(gpa, gre, tier):
        x = pd.DataFrame({'gpa_numeric':gpa, 'gre_numeric':gre, 'tier_score':tier}, dtype=float)
        x['gre_missing'] = x.gre_numeric.isna().astype(int)
        x['applicant_cluster'] = cluster.predict(scaler.transform(x[['gpa_numeric','gre_numeric']].fillna(medians)))
        x['gre_numeric'] = x.gre_numeric.fillna(0)
        return x[features]
    x = frame(df.gpa, df.gre_quant, df.tier_score)
    y = df.admit_result.astype(int)
    splits = json.loads((ROOT / 'reports/agent2-local/split_indices.json').read_text())
    sets = {k:set(v) for k,v in splits.items()}
    assert len(set.union(*sets.values())) == len(df)
    assert all(sets[a].isdisjoint(sets[b]) for a,b in [('fit','validation'),('fit','test'),('validation','test')])
    test = splits['test']
    xt, yt = x.loc[test], y.loc[test]
    p = model.predict_proba(xt)[:,list(model.classes_).index(1)]
    def bin_stats(mask, lo, hi):
        return {'lower':lo,'upper':hi,'rows':int(mask.sum()),
                'mean_prediction':float(p[mask].mean()) if mask.any() else None,
                'observed_positive_fraction':float(yt.to_numpy()[mask].mean()) if mask.any() else None}
    bins = [bin_stats((p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1)),i/10,(i+1)/10) for i in range(10)]
    ece = sum(b['rows']/len(p)*abs(b['mean_prediction']-b['observed_positive_fraction']) for b in bins if b['rows'])
    categories = {name:bin_stats(mask,None,None) for name,mask in {
        'Safe':p>=.65,'Target':(p>=.35)&(p<.65),'Reach':p<.35,'at_least_95_percent':p>=.95}.items()}
    groups = df.groupby('applicant_id')
    ids = {k:set(df.loc[v,'applicant_id']) for k,v in splits.items()}
    overlap = {a+'_'+b:len(ids[a]&ids[b]) for a,b in [('fit','validation'),('fit','test'),('validation','test')]}
    pi = permutation_importance(model,xt,yt,scoring='neg_brier_score',n_repeats=5,random_state=42)
    sweeps=[]
    chosen=catalog[catalog.university_name.isin(['Massachusetts Institute of Technology','Stanford University']) & catalog.program_name.eq('MS Computer Science - Data Science')]
    assert len(chosen)==2
    for _, prog in chosen.iterrows():
        for gpa in [2.4,3.0,3.36,3.92,4.0]:
            for gre in [130,150,155,160,165,170,None]:
                prob=float(model.predict_proba(frame([gpa],[gre],[prog.tier_score]))[0,1])
                sweeps.append({'university':prog.university_name,'gpa_4':gpa,'gre_quant':gre,'tier_score':prog.tier_score,'probability':prob})
    pd.DataFrame(sweeps).to_csv(OUT/'sensitivity.csv',index=False)
    gre_groups = df.assign(gre_band=pd.cut(df.gre_quant,[129,150,155,160,165,170],include_lowest=True)).groupby('gre_band',observed=True).admit_result.agg(['count','mean']).reset_index()
    gre_groups['gre_band']=gre_groups.gre_band.astype(str)
    joined=df.merge(catalog[['program_id','tier_score']],on='program_id',suffixes=('_train','_catalog'),validate='many_to_one')
    exact_gre = df.groupby('gre_quant').admit_result.agg(['count','mean']).reset_index()
    exact_gre.to_csv(OUT/'gre_label_distribution.csv',index=False)
    result={
        'scope':'Diagnostics on supplied dataset; not validated real admissions probabilities or unseen-student performance.',
        'input_hashes_verified':True,'features':features,'rows':len(df),'positive_rows':int(y.sum()),
        'label_cross_tab':pd.crosstab(df.target_admission_status,df.admit_result).to_dict(),
        'exact_duplicate_rows':int(df.duplicated().sum()),'unique_applicant_ids':df.applicant_id.nunique(),
        'repeated_id_groups':int((groups.size()>1).sum()),
        'conflicting_id_groups':{c:int((groups[c].nunique()>1).sum()) for c in ['gpa','gre_quant','gre_verbal','major']},
        'split_rows':{k:len(v) for k,v in splits.items()},'split_row_overlap':0,'split_applicant_id_overlap':overlap,
        'test_rows_with_fit_applicant_id':int(df.loc[test,'applicant_id'].isin(ids['fit']).sum()),
        'tier_matches_catalog_rows':int(np.isclose(joined.tier_score_train,joined.tier_score_catalog).sum()),
        'metrics':{'accuracy':accuracy_score(yt,p>=threshold),'f1':f1_score(yt,p>=threshold),
                   'roc_auc':roc_auc_score(yt,p),'brier':brier_score_loss(yt,p),'log_loss':log_loss(yt,p),
                   'ece_10_equal_width_bins':ece,'decision_threshold':threshold,
                   'constant_fit_prevalence_brier':brier_score_loss(yt,np.full(len(yt),y.loc[splits['fit']].mean()))},
        'calibration_bins':bins,'categories':categories,
        'permutation_brier_increase':{f:{'mean':float(m),'std':float(s)} for f,m,s in zip(features,pi.importances_mean,pi.importances_std)},
        'training_gre_bands':gre_groups.to_dict(orient='records'),
        'feature_ranges':{c:{'min':float(x[c].min()),'max':float(x[c].max())} for c in features},
        'missing_gre_training_rows':int(df.gre_quant.isna().sum()),
        'fractional_gre_training_rows':int((~np.isclose(df.gre_quant,df.gre_quant.round(),rtol=0,atol=1e-8)).sum()),
        'gpa_above_four_rows':int((df.gpa>4).sum()),
        'sensitivity_rows':len(sweeps),
    }
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
