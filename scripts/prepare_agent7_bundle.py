"""Recover four supplied artifacts byte-for-byte; train only the missing classifier.

Explicit offline maintenance command, never called by inference. Uses only the
notebook's synthetic generator and classifier parameters, not admission data.
"""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/app/agents'))
import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
from xgboost import XGBClassifier
from extracurricular_agent.predict import ARTIFACT_TYPES, _load_verified, score_extracurricular
from extracurricular_agent.schema import feature_frame, CLUSTER_COLUMNS

HERE = ROOT / 'backend/app/agents/extracurricular_agent'
RECOVER = {
    'agent7_feature_columns.joblib': 'agent7_archetype_scaler (2).joblib',
    'agent7_gbr_score_model.joblib': 'agent7_scaler (2).joblib',
    'agent7_archetype_kmeans.joblib': 'agent7_resume_archetype_kmeans (2).joblib',
    'agent7_archetype_scaler.joblib': 'agent7_real_p90_thresholds (2).joblib',
}


def main():
    final = HERE / 'trained_models'
    stage = HERE / 'trained_models_candidate'
    if final.exists() or stage.exists():
        raise RuntimeError('Refusing to overwrite an existing bundle.')
    warnings.simplefilter('error', InconsistentVersionWarning)
    originals = HERE / 'trained_models_A7'
    recovered = {name: joblib.load(originals / source) for name, source in RECOVER.items()}
    for name, obj in recovered.items():
        if not isinstance(obj, ARTIFACT_TYPES[name]):
            raise TypeError(f'Unexpected recovered object: {name}')
    notebook = HERE / 'agent7_extracurricular_agent.ipynb'
    nodes, params = [], None
    for cell in json.loads(notebook.read_text(encoding='utf-8'))['cells']:
        if cell['cell_type'] != 'code':
            continue
        try:
            tree = ast.parse(''.join(cell['source']))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'gen_synthetic_extracurricular_data':
                nodes.append(node)
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'best_params' for t in node.targets):
                params = ast.literal_eval(node.value)
    if len(nodes) != 1 or not params:
        raise ValueError('Notebook generator/parameters are ambiguous or absent.')
    ns = dict(np=np, pd=pd, N=4000, RNG=np.random.default_rng(42))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(notebook), 'exec'), ns)
    data = ns['gen_synthetic_extracurricular_data']()
    features = feature_frame(data)
    columns = recovered['agent7_feature_columns.joblib']
    if list(features.columns) != columns:
        raise ValueError('Recovered columns do not match notebook feature construction.')
    reg = recovered['agent7_gbr_score_model.joblib']
    scaler = recovered['agent7_archetype_scaler.joblib']
    cluster = recovered['agent7_archetype_kmeans.joblib']
    if list(reg.feature_names_in_) != columns or list(scaler.feature_names_in_) != CLUSTER_COLUMNS or cluster.n_features_in_ != 6:
        raise ValueError('Recovered models have incompatible feature schemas.')
    target = data.strength_tier.map({'Weak': 0, 'Moderate': 1, 'Strong': 2})
    train, test = train_test_split(np.arange(len(data)), test_size=.2, random_state=42, stratify=target)
    # No compatible XGBoost exists anywhere in the supplied A7 files. The
    # misnamed logistic model needs an absent 22-feature scaler; do not guess it.
    classifier = XGBClassifier(**params, random_state=42, eval_metric='mlogloss', n_jobs=4)
    classifier.fit(features.iloc[train], target.iloc[train])
    scores = reg.predict(features)
    clusters = cluster.predict(scaler.transform(data[CLUSTER_COLUMNS]))
    if not np.isfinite(scores).all() or not np.isfinite(clusters).all():
        raise ValueError('Recovered artifacts failed real inference.')
    stage.mkdir()
    for name, source in RECOVER.items():
        shutil.copyfile(originals / source, stage / name)
    joblib.dump(classifier, stage / 'agent7_xgb_tier_model.joblib')
    manifest = {
        'schema_version': 1, 'training_source': 'synthetic_notebook_rubric',
        'dependencies': {p: importlib.metadata.version(p) for p in ('numpy', 'pandas', 'scikit-learn', 'joblib', 'xgboost')},
        'feature_columns': columns,
        'artifact_sha256': {name: hashlib.sha256((stage / name).read_bytes()).hexdigest() for name in ARTIFACT_TYPES},
        'recovered_byte_for_byte': RECOVER,
        'regenerated': ['agent7_xgb_tier_model.joblib'],
        'reason': 'No supplied A7 XGBoost; misnamed logistic classifier lacks its 22-feature input scaler.',
        'notebook_sha256': hashlib.sha256(notebook.read_bytes()).hexdigest(),
        'seed': 42, 'synthetic_rows': len(data), 'classifier_params': params,
        'train_indices': train.tolist(), 'test_indices': test.tolist(),
        'synthetic_classifier_test_accuracy': float(accuracy_score(target.iloc[test], classifier.predict(features.iloc[test]))),
        'recovered_regressor_synthetic_mae_diagnostic': float(mean_absolute_error(data.profile_strength_score, scores)),
        'limitations': ['Synthetic rubric only; no real admissions validation.',
                       'Original regressor and clusters reused; their original split provenance is unavailable.',
                       'Regressor diagnostic is not a held-out accuracy claim.',
                       'Resume extraction requires missing/unverified NER resources.'],
    }
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    _load_verified(str(stage))
    example = {key: data.iloc[0][key].item() if hasattr(data.iloc[0][key], 'item') else data.iloc[0][key]
               for key in ('degree_level', 'field', *CLUSTER_COLUMNS)}
    print(json.dumps(score_extracurricular(example, model_dir=stage)))
    stage.rename(final)
    print('Recovered four artifacts unchanged; regenerated only the missing classifier.')


if __name__ == '__main__':
    main()
