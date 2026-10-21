"""Build an optional experimental v3 notebook without modifying the retained old notebook.

Run from the project root: python notebooks/run_agent2_base_rate_notebook.py
The active extension is embedded in both notebook files, not imported at run time.
"""
from pathlib import Path
import contextlib
import copy
import io
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS','1')
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ.setdefault(key,'2')
SOURCE = ROOT/'backend/app/agents/university_matching_agent/AGENT2_University_agent.ipynb'
EXECUTED = SOURCE.with_name('Agent2_University_Agent.executed.ipynb')


def markdown(text):
    return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}


intro = '''# Agent 2 — executed base-rate revision

This is the complete active v3 pipeline: input audit, grouped model evaluation,
program-rate evidence, monotonicity tests, real neural retrieval and live explanation attempt.
All code is embedded below. Legacy experimentation is preserved in the original notebook
and its backup; it is not re-executed or represented as current results here.

Run from the project root or a subfolder. Dependencies: numpy, pandas, scipy,
scikit-learn, threadpoolctl, torch, sentence-transformers, qdrant-client, requests.
The matching BAAI models may be downloaded from Hugging Face automatically or prepared
with `python notebooks/download_agent2_models.py` into `.cache/agent2/`.
Configure `GROQ_API_KEY` in the project's ignored `.env`; optional `QDRANT_URL`
and `QDRANT_API_KEY` enable a remote service. Without a URL, actual Qdrant local mode runs.
Only public program facts and model estimates are sent to Groq. PostgreSQL persistence
is not performed by this validation notebook.

The CSV's external provenance and program admission rates are unverified.
The model intentionally constrains probability behavior instead of optimizing agreement
with applicant-level labels replicated across programs. It is an experimental estimator.
Nonnegative coefficients permit zero effects; profile strength is tested, not assumed useful.
Exact model contributions replace SHAP for this explicit additive pre-saturation model.

Sources: [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html),
[bounded SciPy optimization](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html),
[Qdrant local mode](https://github.com/qdrant/qdrant-client),
[BGE model](https://huggingface.co/BAAI/bge-small-en-v1.5),
[BGE reranker](https://huggingface.co/BAAI/bge-reranker-base).
Stanford's [official doctoral dashboard](https://irds.stanford.edu/data-findings/doctoral-admissions)
covers external doctoral applications; it cannot supply an MS Computer Science rate.
No undergraduate rate or enrollment count is substituted for a program's admission rate.
'''
cells = [markdown(intro)]
text=(ROOT/'notebooks/agent2_base_rate_extension.py').read_text(encoding='utf-8')
for section in text.split('# %% ')[1:]:
    title,code=section.split('\n',1)
    cells += [markdown('## '+title),{'cell_type':'code','metadata':{},'source':code.splitlines(keepends=True),
                                      'execution_count':None,'outputs':[]}]
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
           'language_info':{'name':'python','version':sys.version.split()[0]}},'nbformat':4,'nbformat_minor':4}
namespace={'__name__':'__main__'}
index=0
for i,cell in enumerate(cells):
    if cell['cell_type']!='code': continue
    index+=1
    print(f'Executing active cell {index}: {"".join(cells[i-1]["source"])}',flush=True)
    output=io.StringIO()
    try:
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            exec(compile(''.join(cell['source']),f'Agent2-v3-cell-{index}','exec'),namespace)
    except Exception as exc:
        cell['execution_count']=index
        cell['outputs']=[{'output_type':'stream','name':'stdout','text':output.getvalue().splitlines(keepends=True)},
                         {'output_type':'error','ename':type(exc).__name__,'evalue':str(exc),'traceback':traceback.format_exc().splitlines()}]
        EXECUTED.write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
        raise
    cell['execution_count']=index
    cell['outputs']=[{'output_type':'stream','name':'stdout','text':output.getvalue().splitlines(keepends=True)}]
    EXECUTED.write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
    print(output.getvalue()[-3500:],flush=True)

notebook['cells'][0]=markdown(namespace['HEADER_V3']+'\n'+intro.split('\n',1)[1])
EXECUTED.write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
print('Saved optional experimental notebook:',EXECUTED)
print('The retained old Agent 2 notebook was not modified.')
