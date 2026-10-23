"""Execute an existing notebook in a fresh Jupyter kernel, preserving its source.

Uses jupyter_client and ipykernel. Saves actual stream/rich/error outputs after each
cell. Usage: python notebooks/execute_notebook.py path/to/file.ipynb
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from jupyter_client import KernelManager


ROOT = Path(__file__).resolve().parents[1]


def execute_notebook(path: Path, timeout: int = 900) -> dict:
    path = path.resolve()
    notebook = json.loads(path.read_text(encoding="utf-8"))
    original_cells = [(c["cell_type"], c["source"]) for c in notebook["cells"]]
    code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    for cell in code_cells:
        cell["execution_count"] = None
        cell["outputs"] = []
    notebook.setdefault("metadata", {})["kernelspec"] = {
        "name": "python3", "display_name": "Python 3 (ipykernel)", "language": "python"
    }

    def save() -> None:
        # Do not overwrite source edits made while execution is in progress.
        current = json.loads(path.read_text(encoding="utf-8"))
        if [(c["cell_type"], c["source"]) for c in current["cells"]] != original_cells:
            raise RuntimeError(f"Notebook source changed during execution: {path}")
        temporary = path.with_name(path.name + ".executing")
        temporary.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    runtime_root = ROOT / ".cache" / "notebook-execution"
    runtime_root.mkdir(parents=True, exist_ok=True)
    # Python 3.14 TemporaryDirectory applies private Windows ACLs that can exclude
    # a sandbox's secondary token. Ordinary workspace directory inheritance works.
    runtime_path = runtime_root / ("kernel-" + uuid4().hex)
    runtime_path.mkdir()
    with nullcontext(str(runtime_path)) as runtime:
        environment = os.environ.copy()
        environment.update({"IPYTHONDIR": runtime, "JUPYTER_RUNTIME_DIR": runtime,
                            "PYTHONUTF8": "1", "MPLBACKEND": "Agg"})
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            environment[name] = "1"
        manager = KernelManager(kernel_name="python3", connection_file=str(Path(runtime) / "kernel.json"))
        manager.kernel_spec.argv[0] = sys.executable
        client = None
        display_outputs: dict[str, list[dict]] = {}
        try:
            manager.start_kernel(cwd=str(ROOT), env=environment,
                                 extra_arguments=["--HistoryManager.hist_file=:memory:"])
            client = manager.blocking_client()
            client.start_channels()
            client.wait_for_ready(timeout=60)
            client.kernel_info()
            notebook["metadata"]["language_info"] = client.get_shell_msg(timeout=30)["content"]["language_info"]
            notebook["metadata"]["execution"] = {
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "executor": "jupyter_client", "status": "running",
            }
            save()
            for number, cell in enumerate(code_cells, 1):
                print(f"Executing {path.name}: code cell {number}/{len(code_cells)}", flush=True)
                clear_pending = False

                def capture(message: dict) -> None:
                    nonlocal clear_pending
                    kind, content = message["header"]["msg_type"], message["content"]
                    if kind == "execute_input":
                        cell["execution_count"] = content["execution_count"]
                    elif kind == "clear_output":
                        clear_pending = content.get("wait", False)
                        if not clear_pending:
                            cell["outputs"].clear()
                    elif kind in {"stream", "display_data", "execute_result", "error", "update_display_data"}:
                        if clear_pending:
                            cell["outputs"].clear()
                            clear_pending = False
                        if kind == "stream":
                            if cell["outputs"] and cell["outputs"][-1].get("output_type") == "stream" and cell["outputs"][-1]["name"] == content["name"]:
                                cell["outputs"][-1]["text"] += content["text"]
                            else:
                                cell["outputs"].append({"output_type": kind, "name": content["name"], "text": content["text"]})
                        elif kind == "error":
                            cell["outputs"].append({"output_type": kind, **{key: content[key] for key in ("ename", "evalue", "traceback")}})
                        else:
                            display_id = content.get("transient", {}).get("display_id")
                            if kind == "update_display_data":
                                for output in display_outputs.get(display_id, []):
                                    output.update(data=deepcopy(content["data"]), metadata=deepcopy(content["metadata"]))
                            else:
                                output = {"output_type": kind, "data": deepcopy(content["data"]), "metadata": deepcopy(content["metadata"])}
                                if kind == "execute_result":
                                    output["execution_count"] = content["execution_count"]
                                cell["outputs"].append(output)
                                if display_id:
                                    display_outputs.setdefault(display_id, []).append(output)

                reply = client.execute_interactive("".join(cell["source"]), timeout=timeout,
                                                   allow_stdin=False, stop_on_error=True, output_hook=capture)
                cell["execution_count"] = reply["content"]["execution_count"]
                save()
                output_text = "".join(output.get("text", "") for output in cell["outputs"] if output["output_type"] == "stream")
                if output_text:
                    print(output_text[-2400:], flush=True)
                if reply["content"]["status"] != "ok":
                    raise RuntimeError(f"Cell {number} failed: {reply['content'].get('ename')}: {reply['content'].get('evalue')}")
            assert [cell["execution_count"] for cell in code_cells] == list(range(1, len(code_cells) + 1))
            assert not any(output["output_type"] == "error" for cell in code_cells for output in cell["outputs"])
            notebook["metadata"]["execution"].update(status="completed", completed_utc=datetime.now(timezone.utc).isoformat(), code_cells=len(code_cells))
            save()
        except Exception:
            notebook.setdefault("metadata", {}).setdefault("execution", {})["status"] = "failed"
            save()
            raise
        finally:
            if client is not None:
                client.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    print(f"Completed all {len(code_cells)} code cells with no errors: {path}", flush=True)
    return notebook


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--timeout", type=int, default=900, help="Maximum seconds per cell")
    arguments = parser.parse_args()
    execute_notebook(arguments.notebook, arguments.timeout)
