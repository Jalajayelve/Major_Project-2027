"""Append and execute Agent 4's portable section; preserve all historical cells.

Usage from the repository root: python notebooks/run_agent4_extension.py
The companion .py is the source used to build self-contained notebook cells.
The resulting notebook does not import that companion file.
"""
import os
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[key] = '1'
from pathlib import Path
import contextlib
import hashlib
import io
import json
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
TARGET = ROOT / 'backend/app/agents/financial_agent/Agent4_Financial_agent.ipynb'
source = (ROOT / 'notebooks/agent4_unitid_extension.py').read_text(encoding='utf-8')
ledger_source = (ROOT / 'notebooks/build_agent4_reference_ledger.py').read_text(encoding='utf-8')
ledger_source = ledger_source.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = A4_ROOT')
ledger_source += "\na4_published_coa = pd.read_csv(A4_REFERENCE_PATH)\n"
source = source.replace('# %% checks', '# %% ledger\n' + ledger_source + '\n# %% checks')
notebook = json.loads(TARGET.read_text(encoding='utf-8'))
marker = '## 11. UNITID-based local extension'
start = next((i for i, cell in enumerate(notebook['cells']) if ''.join(cell['source']).startswith(marker)), len(notebook['cells']))
original = notebook['cells'][:start]
original_hash = hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()
notebook['cells'] = original[:]
introductions = {
    'setup': marker + '''

**Run from this section to the end in a fresh local kernel.** All earlier cells and their historical outputs are preserved. The earlier Colab training/upload section was not rerun. This appended section was executed locally on 2026-10-21.

Inputs: Agent 3 `programs`, optional `unitid`/degree metadata, Agent 2 catalog and uploaded financial dataset. Output: `state["finance"]`, one row per input program, including annual USD tuition, estimated living cost, total, country, UNITID, selected degree level and provenance. Unknown inputs stay visible with null costs.

The crosswalk assigns uploaded IPEDS identifiers to all 50 catalog universities after unique normalized-name and state checks. Financial data are joined on **UNITID and program level**, not the first university row. Catalog `tuition_out_state_usd` takes priority for these universities; its price year and program-specific applicability are unconfirmed. Missing catalog tuition falls back to a published total of the same degree level, with `cost_source="published_coa"`, its source URL and scenario. When both are absent, cost stays unknown. Unknown programs are never silently replaced. KNN-imputed tuition is excluded from observed lookup. An explicit regression callable remains available for institutions outside this catalog. Living expenses are still baseline times effective price parity, not observed spending.

The active `financial_agent` is rebound to the new function after this section runs. No preceding function definition is edited.
''',
    'ledger': '''## 11a. Rebuild the official-source cost ledger inside this notebook

The complete transcription code is embedded below; no external builder script is needed when running the notebook. It writes all 50 source records before predictions and evaluation. Totals calculated from published components carry explicit enrollment scenarios. Missing totals are left blank, never invented. The fallback may use this ledger operationally, so any such copied estimate is excluded from accuracy scoring against it. Source dates, currencies and periods remain visible.
''',
    'checks': '''## 12. Executed contract checks and predictions for all 50 universities

A real MS Computer Science catalog entry is selected for every university before reading reference costs: the base title if present, otherwise the alphabetically first CS specialization. Fifteen universities have only specialized CS titles. Selection never uses cost or error. These are lookup checks, not independent predictive labels. Missing or inconsistent inputs are tested explicitly.
''',
    'replay': '''## 13. Replay 20 distinct uploaded applicant records through Agents 2–6

The user authorized these demonstration inputs. Select the first 20 distinct applicant IDs in file order before predictions. Keep recorded academic fields and application targets; leave interests, career goals, nationality and budget unspecified. GPA uses Agent 2's existing four-point training contract. No claim is made that these uploaded training rows are independently verified real students.

Agent 2's actual orchestration, scoring and tier functions execute. The saved admission-model artifact is missing, so this local replay fits a clearly identified replacement calibrated GradientBoosting model on the remaining uploaded applicants with the saved feature contract. Uploaded clustering artifacts were produced with sklearn 1.6.1; this run uses the installed sklearn version and displays compatibility warnings. TF-IDF retrieval replaces unavailable BGE/Qdrant/CrossEncoder services, SHAP factors remain empty, explanations are local templates, and database writes are disabled. This is a functional local chain replay, not a reproduction of the original online pipeline or an independent admission accuracy test. Agents 3, 5 and 6 execute their existing notebook implementations in isolated namespaces. Agent 1 and Agent 7 extraction are not rerun; their recorded inputs are replayed.

Results are saved locally under `data/processed/agent4/`. Missing budget means the funding gap remains unknown. Missing scholarship evidence is never invented to force recommendations.
''',
    'benchmark': '''## 14. Published cost-of-attendance audit

`data/raw/agent4/published_costs_50.csv` records official university budgets, URLs, dates, periods and unresolved details. All 50 institutions remain in the audit. Source totals and explicitly calculated source-component sums are distinguished in the ledger. Published budgets are estimates, not students' observed spending. Estimates using the `published_coa` fallback are excluded from scoring against the ledger; their apparent zero error would be circular.

Descriptive share within ±10% is reported with coverage. Strict program-level accuracy additionally requires matching academic year, enrollment period, program and component scope. The catalog's price year and fee/month coverage are unconfirmed, so current comparisons do **not** establish 96% accuracy. Missing or conflicting references remain unscored and visible.
''',
    'final': '## 15. Final executed results\n\nMatch coverage, contract tests, chain completion and cost accuracy are separate measures.\n',
}
for chunk in source.split('# %% ')[1:]:
    key, code = chunk.split('\n', 1)
    notebook['cells'].append({'cell_type': 'markdown', 'metadata': {}, 'source': introductions[key].splitlines(keepends=True)})
    notebook['cells'].append({'cell_type': 'code', 'metadata': {'tags': ['agent4-unitid-extension']},
        'source': code.splitlines(keepends=True), 'execution_count': None, 'outputs': []})
notebook.setdefault('metadata', {})['agent4_extension'] = {
    'original_cells_preserved': start, 'original_cells_sha256': original_hash,
    'execution_scope': 'appended cells only; historical Colab cells not reexecuted',
}
TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
if '--build-only' in sys.argv:
    print('Self-contained appended cells rebuilt; execution outputs will be supplied by the full local run.')
    sys.exit(0)

class Tee(io.StringIO):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream
    def write(self, text):
        self.stream.write(text)
        self.stream.flush()
        return super().write(text)
    def flush(self):
        self.stream.flush()

namespace = {'__name__': '__main__'}
counter = 0
for index in range(start, len(notebook['cells'])):
    cell = notebook['cells'][index]
    if cell['cell_type'] != 'code':
        continue
    counter += 1
    print(f'Executing appended code cell {counter} (notebook cell {index})', flush=True)
    capture = Tee(sys.stdout)
    errors = Tee(sys.stderr)
    started = time.time()
    try:
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(errors):
            exec(compile(''.join(cell['source']), f'{TARGET.name}:cell-{index}', 'exec'), namespace)
    except Exception:
        cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout', 'text': capture.getvalue().splitlines(keepends=True)},
            {'output_type': 'error', 'ename': sys.exc_info()[0].__name__, 'evalue': str(sys.exc_info()[1]), 'traceback': traceback.format_exc().splitlines()}]
        TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        raise
    cell['execution_count'] = counter
    cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout', 'text': capture.getvalue().splitlines(keepends=True)}]
    if errors.getvalue():
        cell['outputs'].append({'output_type': 'stream', 'name': 'stderr', 'text': errors.getvalue().splitlines(keepends=True)})
    cell['metadata']['execution_seconds'] = round(time.time() - started, 2)
    TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
assert hashlib.sha256(json.dumps(notebook['cells'][:start], sort_keys=True).encode()).hexdigest() == original_hash
print('Original cells preserved exactly; executed appended outputs saved.', flush=True)
