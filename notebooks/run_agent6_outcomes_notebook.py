"""Execute and update the single canonical Agent 6 notebook, with embedded model code."""
from pathlib import Path
import os
import json
import io
import contextlib
import traceback
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ.setdefault(key,'1')
TARGET=ROOT/'backend/app/agents/career_agent/Agent6_Career_agent.ipynb'
BACKUP=ROOT/'data/backups/Agent6_before_outcomes_v2.zip'
BACKUP.parent.mkdir(parents=True,exist_ok=True)
if not BACKUP.exists():
    with zipfile.ZipFile(BACKUP,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(TARGET.name,TARGET.read_bytes())
notebook=json.loads(TARGET.read_text(encoding='utf-8'))
notebook['cells']=notebook['cells'][:14]
def md(text): return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}
notebook['cells'][0]=md('''# Agent 6 — Career Agent: uploaded outcomes and unsupervised learning

**This is the single final notebook. Run every cell from top to bottom.**
The earlier advisory functions and independent-label evaluation utilities are retained;
the appended outcome extension sets the final `career_agent` entry point.

Input: Agent 3's exact university/program identities, student career goal and optional
program ID/UNITID. Data: `data/raw/agent6/agent_6_dataset_final_merged.csv` plus the
Agent 2 catalog for exact program identity. Output: `state["careers"]` with career-path
advice, goal alignment, role examples, cohort earnings, outcome clusters, evidence scope
and placement context. Input order and the caller's state are preserved.

**Learning components:** supervised HistGradientBoosting regression for uploaded four-year
cohort earnings; unsupervised KMeans for log earnings/debt patterns. Institutions are
separated into train/dev/test. Cluster count is selected on dev only; frozen models are
then evaluated on withheld institutions. Estimated program rows and heuristic job/research
scores are excluded from training targets. Saved joblib models retain preprocessing.

The dataset has no independently labelled student research/industry outcomes. Career-path
advice remains explicit rules; a cluster is not a career class. US federal-aid cohort
figures are not international-student salary forecasts. School-wide MBA placement reports
are context, never specialization placement rates. Uploaded source claims are not
independently verified against every original source in this run.

Final measurements and artifact paths appear in the **last cell**. Model files are saved
under `backend/app/agents/career_agent/trained_models/`. Load only trusted joblib files.
Dependencies: numpy, pandas, scipy, scikit-learn, joblib, threadpoolctl.

References: [College Scorecard field-of-study methodology](https://collegescorecard.ed.gov/assets/FieldOfStudyDataDocumentation.pdf),
[HistGradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html),
[KMeans silhouette evaluation](https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis).

## Retained advisory implementation and its original behavior checks
''')
# Correct stale descriptions while preserving the old function definitions and cell indices
# used by the previously delivered Agent 4 historical replay.
notebook['cells'][2]['source']=''.join(notebook['cells'][2]['source']).replace(
    "print('No career-outcome dataset was supplied. Active method: transparent advisory rules.')",
    "print('Advisory baseline loaded. The uploaded outcome models are trained and activated in the extension below.')").splitlines(keepends=True)
notebook['cells'][12]=md('## Historical advisory baseline results — final enriched results follow below')
notebook['cells'][13]['source']=''.join(notebook['cells'][13]['source']).replace(
    "print('AGENT 6 - FINAL EXECUTED RESULTS')", "print('AGENT 6 - LEGACY ADVISORY BASELINE RESULTS')").replace(
    "no labelled career-outcome dataset supplied.","no independent student track labels supplied.").splitlines(keepends=True)
extension=(ROOT/'notebooks/agent6_outcomes_extension.py').read_text(encoding='utf-8')
for block in extension.split('# %% ')[1:]:
    title,code=block.split('\n',1)
    notebook['cells'] += [md('## '+title),{'cell_type':'code','metadata':{},'source':code.splitlines(keepends=True),
                                        'execution_count':None,'outputs':[]}]
for cell in notebook['cells']:
    if cell['cell_type']=='code':cell['execution_count']=None;cell['outputs']=[]
notebook['metadata']['kernelspec']={'name':'python3','language':'python','display_name':'Python 3'}
notebook['nbformat_minor']=4
def save(): TARGET.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
namespace={'__name__':'__main__'}
count=0
for i,cell in enumerate(notebook['cells']):
    if cell['cell_type']!='code':continue
    count+=1;print(f'Executing Agent 6 cell {count} (index {i})',flush=True)
    captured=io.StringIO()
    try:
        with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
            exec(compile(''.join(cell['source']),f'Agent6-cell-{i}','exec'),namespace)
    except Exception as exc:
        cell['outputs']=[{'output_type':'stream','name':'stdout','text':captured.getvalue().splitlines(keepends=True)},
            {'output_type':'error','ename':type(exc).__name__,'evalue':str(exc),'traceback':traceback.format_exc().splitlines()}]
        cell['execution_count']=count;save();raise
    cell['execution_count']=count
    cell['outputs']=[{'output_type':'stream','name':'stdout','text':captured.getvalue().splitlines(keepends=True)}]
    save();print(captured.getvalue()[-2200:],flush=True)
print('Completed all',count,'code cells:',TARGET,flush=True)
