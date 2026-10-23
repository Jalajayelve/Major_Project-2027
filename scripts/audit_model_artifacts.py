"""Inspect every repository joblib without changing or training any model."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import warnings
import joblib

ROOT = Path(__file__).resolve().parents[1]


def audit():
    records = []
    paths = set((ROOT / 'backend').rglob('*.joblib'))
    paths.update((ROOT / 'backend/app/agents/extracurricular_agent/trained_models_A7').iterdir())
    for path in sorted(p for p in paths if p.is_file()):
        record = {'path': path.relative_to(ROOT).as_posix(),
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                obj = joblib.load(path)
            record.update(type=f'{type(obj).__module__}.{type(obj).__name__}',
                          warnings=sorted(set(str(w.message) for w in caught)))
            for attr in ('n_features_in_', 'feature_names_in_', 'classes_'):
                value = getattr(obj, attr, None)
                if value is not None:
                    record[attr] = value.tolist() if hasattr(value, 'tolist') else value
            if isinstance(obj, (list, dict, str, int, float)):
                record['value'] = str(obj)[:4000]
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
            record['header'] = repr(path.read_bytes()[:100])
        records.append(record)
    return {'versions': {p: importlib.metadata.version(p) for p in ('numpy', 'pandas', 'scikit-learn', 'joblib')}, 'artifacts': records}


if __name__ == '__main__':
    result = audit()
    target = ROOT / 'docs/model-artifact-audit.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    for row in result['artifacts']:
        print(row['path'], row.get('type', row.get('error')), row.get('n_features_in_', ''))
