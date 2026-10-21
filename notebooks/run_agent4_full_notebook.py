"""Produce a fully executed local copy, preserving the source notebook's legacy cells.

Run run_agent4_extension.py first to assemble the self-contained appended cells.
This runner changes only local-environment setup in the output copy. It does not
edit the historical source notebook's cells or change the legacy model settings.
"""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[key] = '1'
from pathlib import Path
import ast
import contextlib
import hashlib
import io
import json
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
SOURCE = ROOT / 'backend/app/agents/financial_agent/Agent4_Financial_agent.ipynb'
TARGET = SOURCE.with_name('Agent4_Financial_agent.executed.ipynb')
notebook = json.loads(SOURCE.read_text(encoding='utf-8'))
source_cells = json.loads(json.dumps(notebook['cells']))

def replace_cell(index, source):
    notebook['cells'][index]['source'] = source.strip().splitlines(keepends=True)

replace_cell(2, '''
# Local setup: replaces Colab package-upgrade commands only.
# Required: pandas, numpy, scikit-learn, joblib, threadpoolctl.
# Optional: shap for legacy SHAP explanations; sqlalchemy for database use.
from pathlib import Path
import importlib.util
from threadpoolctl import threadpool_limits
_local_threads = threadpool_limits(limits=1)
PROJECT_ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / 'data/raw').is_dir())
LOCAL_ARTIFACTS = PROJECT_ROOT / 'data/processed/agent4/legacy_model_artifacts'
LOCAL_ARTIFACTS.mkdir(parents=True, exist_ok=True)
for module in ['pandas', 'numpy', 'sklearn', 'joblib', 'threadpoolctl']:
    if importlib.util.find_spec(module) is None:
        raise ImportError(f'Install required local dependency: {module}')
print('Local dependencies available. Automatic package upgrades are disabled.')
print('Optional SHAP available:', importlib.util.find_spec('shap') is not None)
''')
replace_cell(3, '''
import pandas as pd
import numpy as np
FINANCIAL_CSV = PROJECT_ROOT / 'data/raw/agent4/agent4_master_financial_dataset.csv'
if not FINANCIAL_CSV.exists():
    raise FileNotFoundError(FINANCIAL_CSV)
print('Using uploaded financial dataset:', FINANCIAL_CSV)
''')
replace_cell(4, ''.join(source_cells[4]['source']).replace('"agent4_master_financial_dataset.csv"', 'FINANCIAL_CSV'))
replace_cell(11, ''.join(source_cells[11]['source']).replace('n_jobs=-1', 'n_jobs=1'))
replace_cell(13, '''
# Preserve the optional ranking branch without an interactive Colab upload.
OPTIONAL_AGENT2_CSV = PROJECT_ROOT / 'data/raw/agent2/agent2_final_2tier.csv'
HAS_AGENT2_DATA = OPTIONAL_AGENT2_CSV.exists()
print('Optional legacy ranking file available:', HAS_AGENT2_DATA)
''')
replace_cell(14, ''.join(source_cells[14]['source']).replace('"agent2_final_2tier.csv"', 'OPTIONAL_AGENT2_CSV'))
legacy_shap = ''.join(source_cells[16]['source'])
replace_cell(16, '''
if importlib.util.find_spec('shap') is None:
    shap_explainer = None
    def get_shap_top_factors(X_row_df, top_n=3):
        return None
    print('SHAP is not installed. No SHAP explanations are produced; cost predictions still run.')
else:
''' + '\n'.join('    ' + line for line in legacy_shap.splitlines()))
replace_cell(17, '''
import joblib
joblib.dump(tuition_model, LOCAL_ARTIFACTS / 'agent4_tuition_model.pkl')
joblib.dump(list(X.columns), LOCAL_ARTIFACTS / 'agent4_feature_columns.pkl')
if shap_explainer is not None:
    joblib.dump(shap_explainer, LOCAL_ARTIFACTS / 'agent4_shap_explainer.pkl')
print('Legacy model artifacts saved locally:', LOCAL_ARTIFACTS)
''')
legacy_db = ''.join(source_cells[23]['source'])
legacy_db = legacy_db.replace('from sqlalchemy import create_engine, text', '''try:
    from sqlalchemy import create_engine, text
except ImportError:
    create_engine = text = None''')
legacy_db = legacy_db.replace('    engine = create_engine(POSTGRES_URL)', '''    if create_engine is None:
        raise ImportError('Install sqlalchemy before enabling optional database persistence.')
    engine = create_engine(POSTGRES_URL)''')
# No database credentials are requested or used for an authorized local replay.
start = legacy_db.index('try:\n    from google.colab import userdata')
end = legacy_db.index('\n\ndef save_finance_to_db', start)
legacy_db = legacy_db[:start] + 'POSTGRES_URL = None  # Local execution: no external database writes.\n' + legacy_db[end:]
replace_cell(23, legacy_db)

changed = [i for i, cell in enumerate(notebook['cells']) if cell['source'] != source_cells[i]['source']]
assert changed == [2, 3, 4, 11, 13, 14, 16, 17, 23]
notice = '''# Fully executed local Agent 4 notebook

All code cells below were executed in one fresh Python namespace on 2026-10-21.
The original notebook remains alongside this copy with its earlier cells preserved.
Only nine legacy cells were adapted here for local execution: dependency checks replace package
upgrades; local files replace Colab uploads/downloads; SHAP is optional and explicitly
unavailable if not installed; database writes are disabled; Random Forest runs with
one worker because Windows restricted parallel queue creation. Legacy model algorithms,
predictive hyperparameters, splits and inference functions are unchanged. Their row-split metrics
include imputed training targets and are diagnostics, not independent price accuracy.

Sections 11 onward contain the active UNITID-based agent, the complete source-ledger
builder, missing-tuition fallback, functional checks, 20-record local chain replay and
published-cost benchmark. Run those sections for the current agent. The last code cell
prints all current results. All Agent 4 implementation and ledger-building code is
embedded here; data files and other agents' notebooks remain project dependencies.
'''
notebook['cells'].insert(0, {'cell_type': 'markdown', 'metadata': {}, 'source': notice.splitlines(keepends=True)})
notebook.setdefault('metadata', {})['agent4_local_execution'] = {
    'source_notebook': SOURCE.name, 'adapted_legacy_cell_indices': changed,
    'source_legacy_cells_sha256': hashlib.sha256(json.dumps(source_cells[:28], sort_keys=True).encode()).hexdigest(),
    'execution_scope': 'all code cells; one fresh namespace; no external services',
}
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        cell['execution_count'] = None
        cell['outputs'] = []

def save():
    TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

class Tee(io.StringIO):
    def __init__(self, stream): super().__init__(); self.stream = stream
    def write(self, text):
        self.stream.write(text); self.stream.flush()
        return super().write(text)
    def flush(self): self.stream.flush()

namespace = {'__name__': '__main__'}
counter = 0
save()
for index, cell in enumerate(notebook['cells']):
    if cell['cell_type'] != 'code': continue
    # Legacy training writes only its own artifacts. When another process is
    # refreshing the active section, wait before touching shared audit files.
    if index == 30 and '--wait-for-source-run' in sys.argv:
        print('Legacy section finished; waiting for the source extension run to finish.', flush=True)
        deadline = time.time() + 1800
        while True:
            try:
                current = json.loads(SOURCE.read_text(encoding='utf-8'))
                appended = [c for c in current['cells'][28:] if c['cell_type'] == 'code']
                ready = appended and all(c.get('execution_count') is not None for c in appended)
                if any(o.get('output_type') == 'error' for c in appended for o in c.get('outputs', [])):
                    raise RuntimeError('Source extension failed; inspect its saved error before continuing.')
                if ready: break
            except json.JSONDecodeError:
                pass  # The other process is currently saving the notebook.
            if time.time() > deadline:
                raise TimeoutError('Source extension is still running; rerun this command once it finishes.')
            time.sleep(1)
    counter += 1
    print(f'Executing code cell {counter} (notebook index {index})', flush=True)
    out, err = Tee(sys.stdout), Tee(sys.stderr)
    started = time.time()
    result_value = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            tree = ast.parse(''.join(cell['source']))
            # Preserve notebook last-expression display without running it twice.
            last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
            exec(compile(tree, f'{TARGET.name}:cell-{index}', 'exec'), namespace)
            if last is not None:
                result_value = eval(compile(ast.Expression(last.value), f'{TARGET.name}:cell-{index}', 'eval'), namespace)
    except Exception:
        cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout', 'text': out.getvalue().splitlines(keepends=True)},
            {'output_type': 'error', 'ename': sys.exc_info()[0].__name__, 'evalue': str(sys.exc_info()[1]), 'traceback': traceback.format_exc().splitlines()}]
        save()
        raise
    cell['execution_count'] = counter
    cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout', 'text': out.getvalue().splitlines(keepends=True)}]
    if err.getvalue():
        cell['outputs'].append({'output_type': 'stream', 'name': 'stderr', 'text': err.getvalue().splitlines(keepends=True)})
    if result_value is not None:
        cell['outputs'].append({'output_type': 'execute_result', 'execution_count': counter, 'metadata': {},
            'data': {'text/plain': repr(result_value).splitlines(keepends=True)}})
    cell['metadata']['execution_seconds'] = round(time.time() - started, 2)
    save()
print(f'All {counter} code cells executed; saved {TARGET}', flush=True)
# Mirror only the identical appended section into the preserved source notebook.
# Never replace or reexecute any of its 28 historical cells.
preserved = json.loads(SOURCE.read_text(encoding='utf-8'))
for i in range(28, len(preserved['cells'])):
    assert preserved['cells'][i]['source'] == notebook['cells'][i+1]['source']
    if preserved['cells'][i]['cell_type'] == 'code':
        for key in ['outputs', 'execution_count', 'metadata']:
            preserved['cells'][i][key] = notebook['cells'][i+1][key]
preserved['metadata']['agent4_extension']['execution_scope'] = 'appended cells executed in the complete local copy; all historical source cells preserved'
SOURCE.write_text(json.dumps(preserved, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Current appended outputs mirrored into the preserved source notebook.', flush=True)
