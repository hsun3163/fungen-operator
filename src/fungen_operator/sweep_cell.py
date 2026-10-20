"""Visible native submission cell for an approved run-local sweep plan."""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import sys
from pathlib import Path


def sweep_bindings(deployment, request, nb):
    from .actions import digest
    from .sweep import SweepPlan

    jq = shutil.which("jq")
    if not jq:
        raise ValueError("jq is required for bounded notebook receipt inspection")
    sequence = 1 + max((c.metadata.get("fungen", {}).get("sequence", 0) for c in nb.cells), default=0)
    attempt = digest({"request": request.model_dump(), "sequence": sequence})[:32]
    stem = str(Path(request.notebook).parent / "logs" / ("sweep-" + attempt))
    plan = SweepPlan(version=1, spec=request.sweep, notebook=request.notebook,
                     run_root=deployment.run_root, snakefile=deployment.snakefile,
                     log_path=stem + ".sweep.log", jq_path=jq)
    return {"plan_text": json.dumps(plan.model_dump(), indent=2, sort_keys=True) + "\n",
            "plan_path": stem + ".sweep.json", "log_stem": stem,
            "operator_python": sys.executable, "job_ids": []}


def render_sweep(request, bindings):
    from .actions import inside
    from .sweep import SweepPlan

    if set(bindings) != {"plan_text", "plan_path", "log_stem", "operator_python", "job_ids"} or bindings["job_ids"]:
        raise ValueError("invalid sweep bindings")
    plan = SweepPlan.model_validate_json(bindings["plan_text"])
    if plan.spec != request.sweep or plan.notebook != request.notebook:
        raise ValueError("sweep plan differs from the approved request")
    for name in ("plan_path", "log_stem", "operator_python"):
        if not re.fullmatch(r"/[A-Za-z0-9_./:+-]+", bindings[name]):
            raise ValueError("invalid sweep runtime path")
    for path in (bindings["plan_path"], bindings["log_stem"], plan.log_path):
        if not inside(path, plan.run_root):
            raise ValueError("sweep artifacts must belong to run_root")
    q = shlex.quote
    content = bindings["plan_text"]
    checksum = hashlib.sha256(content.encode()).hexdigest()
    wait = " -K" if plan.spec.interval_seconds == 0 else ""
    walltime = "01:00" if plan.spec.interval_seconds == 0 else "144:00"
    worker = shlex.join([bindings["operator_python"], "-m", "fungen_operator.sweep",
                         "--plan", bindings["plan_path"], "--sha256", checksum])
    return f'''%%bash
set -eo pipefail
{q(bindings['operator_python'])} - <<'PLAN'
from pathlib import Path
path = Path({bindings['plan_path']!r})
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text({content!r})
PLAN
bsub{wait} <<'LSF'
#BSUB -J fungen_sweep
#BSUB -P acc_LOAD
#BSUB -q premium
#BSUB -W {walltime}
#BSUB -n 1
#BSUB -R "span[hosts=1] rusage[mem=4GB]"
#BSUB -M 4GB
#BSUB -oo {bindings['log_stem']}.%J.out
#BSUB -eo {bindings['log_stem']}.%J.err
set -eo pipefail
cd {q(str(Path(request.notebook).parent))}
{worker}
LSF
'''


def sweep_result(executor, args, bindings, text, error, result):
    """Reconcile the same synchronous receipt and retained one-pass log."""
    import time

    match = re.search(r"Job <(\d+)> is submitted", text)
    if not match:
        return {**result, "status": "unknown", "diagnostic": "No retained sweep scheduler receipt"}
    job_id = match.group(1)
    state = executor.scheduler(job_id)
    if args.sweep.interval_seconds == 0 and not error:
        for delay in (1, 2, 4):
            if state.get("status") in {"DONE", "EXIT"}:
                break
            time.sleep(delay)
            state = executor.scheduler(job_id)
    logs = executor.logs(bindings.log_stem, job_id)
    plan = json.loads(bindings.plan_text)
    lines = Path(plan["log_path"]).read_text().splitlines() if Path(plan["log_path"]).exists() else []
    last = json.loads(lines[-1]) if lines else None
    status = "submitted"
    if args.sweep.interval_seconds == 0:
        status = ("completed" if not error and state.get("status") == "DONE" and last
                  and last.get("scheduler_ok") and not last.get("failures") else "failed" if error or state.get("status") == "EXIT" else "unknown")
    elif error or state.get("status") == "EXIT":
        status = "failed"
    return {**result, "status": status, "job_id": job_id, "scheduler": state,
            "logs": logs, "receipt": text, "sweep_log": plan["log_path"], "last_pass": last}
