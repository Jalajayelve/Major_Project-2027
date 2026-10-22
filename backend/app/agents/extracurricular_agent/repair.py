"""Rebuild Agent 7's five scoring artifacts without changing legacy files.

Uses the notebook's actual generator and XGBoost parameter literal. Training data
is synthetic and remains in memory; no Agent 1/2 dataset is read.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

os.environ.setdefault("OMP_NUM_THREADS","4")
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, mean_absolute_error, r2_score, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from backend.app.agents.extracurricular_agent.predict import ARTIFACT_TYPES
from backend.app.agents.extracurricular_agent.schema import CLUSTER_COLUMNS, REQUIRED_INPUTS, feature_frame


def fingerprint():
    paths=[]
    for name in ['backend','data','meridian','frontend','docs','assets','reflex.lock','experiments']:
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend(p for p in ROOT.iterdir() if p.is_file())
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def write_new(path,value):
    with path.open('x',encoding='utf-8') as f:
        f.write(value if isinstance(value,str) else json.dumps(value,indent=2))


def audit_legacy():
    expected={**ARTIFACT_TYPES,'agent7_rf_tier_model.joblib':RandomForestClassifier,'agent7_lr_tier_model.joblib':LogisticRegression,'agent7_scaler.joblib':StandardScaler,'agent7_keyword_anomaly_model.joblib':__import__('sklearn.ensemble',fromlist=['IsolationForest']).IsolationForest,'agent7_real_p90_thresholds.joblib':dict,'agent7_real_p99_caps.joblib':dict,'agent7_resume_archetype_kmeans.joblib':KMeans,'agent7_resume_archetype_scaler.joblib':StandardScaler}
    audit=[]
    for p in sorted((HERE/'joblibs').iterdir()):
        if not p.is_file():continue
        record={'filename':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
        if p.suffix!='.joblib':
            record.update(status='supplemental_resume_file_unverified',reason='Not a core scoring joblib; no complete loadable NER directory supplied.')
        else:
            name=p.name.replace(' (2)','')
            typ=expected.get(name)
            record['expected_type']=typ.__name__ if typ else 'unknown'
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always');obj=joblib.load(p)
                record.update(actual_type=f'{type(obj).__module__}.{type(obj).__name__}',status='matches' if typ and isinstance(obj,typ) else 'type_mismatch',warnings=[str(w.message) for w in caught])
            except Exception as exc:
                record.update(status='load_error',error=f'{type(exc).__name__}: {exc}')
        audit.append(record)
    return audit


def main():
    stage=HERE/'trained_models_candidate'
    final=HERE/'trained_models'
    reports=HERE/'repair_reports'
    if any(p.exists() for p in [stage,final,reports]):
        raise RuntimeError('A repair directory already exists. Refusing to overwrite artifacts or reports.')
    before=fingerprint()
    print(f'Protected {len(before)} existing files. Auditing all legacy artifacts.',flush=True)
    legacy=audit_legacy()
    notebook=HERE/'agent7_extracurricular_agent.ipynb'
    nb=json.loads(notebook.read_text(encoding='utf-8'))
    # Extract only the documented generator function; never execute notebook cells.
    definitions=[]
    params=None
    generator_source=None
    for cell in nb['cells']:
        if cell.get('cell_type')!='code':continue
        source=''.join(cell.get('source',[]))
        try:tree=ast.parse(source)
        except SyntaxError:continue
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name=='gen_synthetic_extracurricular_data':
                definitions.append(node);generator_source=source
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='best_params' for t in node.targets):
                params=ast.literal_eval(node.value)
    if len(definitions)!=1 or not params:raise RuntimeError('Could not uniquely identify notebook generator and classifier parameters.')
    namespace={'np':np,'pd':pd,'N':4000,'RNG':np.random.default_rng(42)}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(notebook),'exec'),namespace)
    df=namespace['gen_synthetic_extracurricular_data']()
    y=df['strength_tier'].map({'Weak':0,'Moderate':1,'Strong':2})
    tr,te=train_test_split(np.arange(len(df)),test_size=.2,random_state=42,stratify=y)
    raw=df[REQUIRED_INPUTS]
    encoded=feature_frame(raw)
    print('Rebuilding on 4,000 SYNTHETIC rubric examples, not real admission outcomes.',flush=True)
    scaler=StandardScaler().fit(raw.iloc[tr][CLUSTER_COLUMNS])
    scaled=scaler.transform(raw.iloc[tr][CLUSTER_COLUMNS])
    choices=[]
    for k in range(3,9):
        model=KMeans(n_clusters=k,random_state=42,n_init=10).fit(scaled)
        choices.append((float(silhouette_score(scaled,model.labels_)),k,model))
    sil,k,archetype=max(choices,key=lambda x:x[0])
    print(f'Selected {k} achievement archetypes using training data only.',flush=True)
    clf=XGBClassifier(**params,random_state=42,eval_metric='mlogloss',n_jobs=4)
    clf.fit(encoded.iloc[tr],y.iloc[tr])
    reg=GradientBoostingRegressor(random_state=42,n_estimators=300,max_depth=3,learning_rate=.05)
    reg.fit(encoded.iloc[tr],df['profile_strength_score'].iloc[tr])
    pred=clf.predict(encoded.iloc[te])
    benchmark={'data_kind':'synthetic_notebook_rubric_only','real_world_accuracy':None,'train_rows':len(tr),'test_rows':len(te),'tier_accuracy':float(accuracy_score(y.iloc[te],pred)),'macro_f1':float(f1_score(y.iloc[te],pred,average='macro')),'balanced_accuracy':float(balanced_accuracy_score(y.iloc[te],pred)),'confusion_matrix_weak_moderate_strong':confusion_matrix(y.iloc[te],pred,labels=[0,1,2]).tolist(),'score_mae':float(mean_absolute_error(df['profile_strength_score'].iloc[te],reg.predict(encoded.iloc[te]))),'score_r2':float(r2_score(df['profile_strength_score'].iloc[te],reg.predict(encoded.iloc[te])))}
    stage.mkdir();reports.mkdir()
    values={'agent7_xgb_tier_model.joblib':clf,'agent7_gbr_score_model.joblib':reg,'agent7_feature_columns.joblib':list(encoded.columns),'agent7_archetype_kmeans.joblib':archetype,'agent7_archetype_scaler.joblib':scaler}
    for name,obj in values.items():
        with (stage/name).open('xb') as f:joblib.dump(obj,f)
    manifest={'schema_version':1,'training_source':'synthetic_notebook_rubric','repair_date':'2026-10-08','dependencies':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','joblib','xgboost']},'python':sys.version.split()[0],'feature_columns':list(encoded.columns),'required_inputs':REQUIRED_INPUTS,'classes':{'0':'Weak','1':'Moderate','2':'Strong'},'classifier_params':params,'archetypes':k,'archetype_silhouette_training':sil,'notebook_sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),'generator_cell_sha256':hashlib.sha256(generator_source.encode()).hexdigest(),'synthetic_seed':42,'synthetic_rows':len(df),'synthetic_table_sha256':hashlib.sha256(df.to_csv(index=False).encode()).hexdigest(),'training_indices':tr.tolist(),'test_indices':te.tolist(),'artifact_sha256':{name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in values},'limitations':['Synthetic rubric labels; no real-world admission accuracy established.','Core scoring requires documented structured evidence; full resume/NER path unavailable.','SOP blend is a separate heuristic score; P(Strong) remains the core classifier output.']}
    write_new(stage/'manifest.json',manifest)
    write_new(reports/'legacy_artifact_audit.json',legacy)
    write_new(reports/'synthetic_benchmark.json',benchmark)
    print('Checking replacement bundle in a fresh process before promoting the new directory.',flush=True)
    with __import__('tempfile').TemporaryDirectory(prefix='agent7_verify_cwd_') as tmp:
        subprocess.run([sys.executable,'-B',str(HERE/'verify_repair.py'),'--model-dir',str(stage),'--output-json',str(reports/'verification_candidate.json')],cwd=tmp,check=True)
    # The staged artifacts have passed; move only this newly created directory.
    if final.exists():raise RuntimeError('Final directory appeared during repair; refusing to replace it.')
    stage.rename(final)
    subprocess.run([sys.executable,'-B',str(HERE/'verify_repair.py'),'--model-dir',str(final),'--output-json',str(reports/'verification_final.json')],cwd=ROOT,check=True)
    # Check actual default resolution, without passing an override.
    code='import json; from pathlib import Path; from backend.app.agents.extracurricular_agent.predict import score_extracurricular; c=json.loads(Path('+repr(str(HERE/'example_applicants.json'))+').read_text()); print(json.dumps([score_extracurricular(x) for x in c]))'
    with __import__('tempfile').TemporaryDirectory(prefix='agent7_default_cwd_') as tmp:
        env=dict(os.environ,PYTHONPATH=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
        p=subprocess.run([sys.executable,'-B','-c',code],cwd=tmp,env=env,capture_output=True,text=True,check=True)
    checked=json.loads((reports/'verification_final.json').read_text(encoding='utf-8'))
    if json.loads(p.stdout)!=checked['outputs']:raise RuntimeError('Default-directory predictions differ from validated bundle.')
    after=fingerprint()
    changed=[p for p,h in before.items() if after.get(p)!=h]
    outside=[p for p in after.keys()-before.keys() if not p.startswith('backend/app/agents/extracurricular_agent/')]
    if changed or outside:raise RuntimeError(f'Protected-file violation: changed={changed}, outside additions={outside}')
    write_new(reports/'preservation.json',{'existing_files_checked':len(before),'existing_files_changed':changed,'new_files_outside_agent7':outside,'hashes_before':before,'default_directory_fresh_restart':True})
    rows=['| Example | Tier | Score /100 | P(Strong) | Archetype | Research evidence |','| --- | --- | --- | --- | --- | --- |']
    for i,o in enumerate(checked['outputs'],1):rows.append(f"| {i} | {o['strength_tier']} | {o['profile_strength_score']} | {o['P(Strong)']} | {o['achievement_archetype']} | {o['has_research_evidence']} |")
    report=f'''# Agent 7 repair report

Reviewed: 2026-10-08

## What was wrong

All legacy `.joblib` files were loaded in a separate repair process to inspect their actual types. Several contained different objects: the supposed XGBoost artifact contains LogisticRegression; the supposed feature-column artifact contains KMeans; the supposed regressor contains spaCy configuration text; the supposed scaler contains GradientBoostingRegressor. The complete original scoring bundle could not be used as named. See `legacy_artifact_audit.json` for every file and load error.

Notebook inference depended on the working directory and mutable kernel globals, silently defaulted missing inputs, and encoded archetypes differently from training. Its lexical SOP fallback was labeled semantic alignment. An SOP blend could change the score without clarifying what happened to the classifier tier/probability.

## What was repaired

Rebuilt only the five core Agent 7 artifacts using the existing notebook's synthetic-data generator and XGBoost parameter values. Preserved all legacy artifacts and the notebook. Added shared deterministic feature construction, strict input validation, path-relative loading, artifact type/schema/hash/dependency checks, and separate SOP heuristic/optional-provider evaluation. Archetypes are fitted on training data only and are output-only, matching the notebook training design. SOP blending has a separate `blended_profile_strength_score`; the core classifier outputs remain unchanged.

## Exact artifact location

`backend/app/agents/extracurricular_agent/trained_models/`

{chr(10).join('- `'+name+'` ('+type(obj).__name__+')' for name,obj in values.items())}
- `manifest.json`: hashes, schemas, versions, notebook provenance and synthetic split indices.

The candidate bundle passed a fresh-process verification before its new directory was promoted to `trained_models`. No existing directory or artifact was overwritten.

## Deterministic examples

These are five explicitly constructed software smoke tests, not real students or evidence of admission accuracy. Exact inputs:

```json
{json.dumps(checked['inputs'],indent=2)}
```

Exact outputs:

{chr(10).join(rows)}

Machine-readable full inputs/outputs are in `verification_final.json`. It also contains an offline SOP test input, result and blend.

## Fresh restart and tests

**PASS:** {checked['tests_run']} checks passed for the candidate bundle and again for the final bundle. Predictions matched in independent Python processes from unrelated working directories. A further independent process succeeded using the default absolute model directory, with no notebook/kernel state.

Checks covered output fields/ranges, deterministic predictions, invalid inputs, missing/corrupt artifacts, wrong model types, offline SOP, explicit embedding/LLM adapters, separate blending, and unavailable resume processing. Provider adapter tests used test doubles, with no API calls or claims about provider accuracy.

Environment: Python {manifest['python']}, scikit-learn {manifest['dependencies']['scikit-learn']}, XGBoost {manifest['dependencies']['xgboost']}. See Agent 7's own requirements file; no packages were installed or changed.

## Limits

- Core models reproduce **synthetic rubric labels**, not real admissions or human judgment. Synthetic benchmark metrics are labeled as such in `synthetic_benchmark.json`; real-world accuracy is unknown.
- High counts outside the synthetic training distribution can be unreliable; probabilities are not calibrated against real outcomes.
- Structured scores must come from recorded evidence. No admission dataset or its existing profile-strength column was read.
- Full resume NER, real-resume keyword calibration and patent verification cannot be rebuilt without their original data/bundle. `agent7_full_pipeline` raises an actionable error; it does not produce fabricated scores.
- Offline SOP scoring is English keyword/lexical heuristics. Optional embedding/LLM providers must be supplied explicitly. The 0.20 blend weight is a documented heuristic, not an empirically validated weight. No dedicated LOR model was recovered.
- Classifier tier and regressor score are separate predictions; they may disagree near boundaries. Archetype IDs are cluster labels, not ranks.

## Files changed and preserved

Only new files were created under `backend/app/agents/extracurricular_agent/`: `__init__.py`, `schema.py`, `predict.py`, `sop.py`, `repair.py`, `verify_repair.py`, `example_applicants.json`, `requirements.txt`, `README.md`, the six files in `trained_models/`, and the audit/test/report files in `repair_reports/`.

**No existing files changed.** Hash checks verified {len(before)} pre-existing files at repair start. The original Agent 7 notebook and `joblibs/` contents, Agent 1, Agent 2, all existing datasets, frontend, other source files and previous experiments remained unchanged. No Git commands were run, branches changed, models replaced, or integration performed.
'''
    write_new(reports/'REPAIR_REPORT.md',report)
    print(json.dumps({'status':'verified_repair_complete','directory':str(final),'example_outputs':checked['outputs'],'existing_files_changed':changed,'report':str(reports/'REPAIR_REPORT.md')},indent=2),flush=True)


if __name__=='__main__':main()
