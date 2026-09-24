"""Execute exactly one rendered notebook cell, then attach native evidence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from .actions import Deployment, MODELS, inside, render


class Executor:
    def __init__(self, deployment: Deployment, host_approved=False):
        self.deployment = deployment
        self.host_approved = host_approved

    @property
    def can_schedule(self):
        return self.deployment.backend == "fixture" or self.host_approved

    def environment(self):
        env = dict(os.environ)
        env["IPYTHONDIR"] = str(Path(self.deployment.run_root, ".ipython"))
        env["JUPYTER_RUNTIME_DIR"] = str(Path(self.deployment.run_root, ".jupyter"))
        if self.deployment.backend == "fixture":
            env["PATH"] = self.deployment.conda_env + "/bin:" + env.get("PATH", "")
            env["FUNGEN_FIXTURE_ROOT"] = self.deployment.conda_env
        return env

    def scheduler(self, job_id):
        if not self.can_schedule:
            return {"status": "host_approval_required", "job_id": job_id}
        # Fixed read-only scheduler command; unknown never means finished.
        proc = subprocess.run(["bjobs", "-json", "-o", "jobid stat exit_code", str(int(job_id))],
                              env=self.environment(), text=True, capture_output=True)
        try:
            records = json.loads(proc.stdout)["RECORDS"]
            record = records[0]
            status = record.get("STAT", record.get("stat", "UNKNOWN"))
            return {"job_id": str(job_id), "status": status,
                    "exit_code": record.get("EXIT_CODE", record.get("exit_code"))}
        except (ValueError, KeyError, IndexError):
            return {"job_id": str(job_id), "status": "UNKNOWN", "diagnostic": proc.stderr}

    def execute(self, cell):
        meta = cell.metadata.fungen
        if cell.source != render(meta.action, meta.slots):
            raise ValueError("executor refused a cell that does not re-render")
        args = MODELS[meta.action].model_validate(meta.slots.arguments)
        self.deployment.validate_arguments(args)
        if meta.action != "prepare_config":
            b = meta.slots.bindings
            for key in ("snakefile", "profile_path", "conda_sh", "conda_env"):
                if b[key] != getattr(self.deployment, key):
                    raise ValueError(f"recorded {key} differs from the registered deployment")
            if not inside(b.log_stem, args.log_dir):
                raise ValueError("log stem must belong to the action log directory")
        if meta.action != "prepare_config" and not self.can_schedule:
            return {"status": "host_approval_required"}
        one = nbformat.v4.new_notebook(cells=[cell])
        # A fresh Python kernel runs the actual %%bash magic, not a reconstructed command.
        client = NotebookClient(one, timeout=None, startup_timeout=300,
                                kernel_name="python3", allow_errors=True)
        client.km = client.create_kernel_manager()
        # The harness interpreter owns notebook execution. Do not accidentally use
        # a user's globally registered kernel or the workflow's shell `python`.
        client.km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client.execute(env=self.environment())
        cell.outputs = one.cells[0].outputs
        cell.execution_count = one.cells[0].execution_count
        text = "".join(o.get("text", "") for o in cell.outputs)
        error = any(o.output_type == "error" for o in cell.outputs)
        result = {"status": "failed" if error else "materialized", "backend": self.deployment.backend,
                  "notebook_interpreter": sys.executable, "notebook_python": sys.version.split()[0]}
        if meta.action == "prepare_config":
            return result
        receipt = re.search(r"Job <(\d+)> is submitted", text)
        if not receipt:
            # Nonzero bsub without a receipt can still be ambiguous. Never retry blindly.
            return {**result, "status": "unknown", "diagnostic": "No retained scheduler receipt"}
        job_id = receipt.group(1)
        result["job_id"] = job_id
        result["scheduler"] = self.scheduler(job_id)
        logs = self.logs(meta.slots.bindings.log_stem, job_id)
        result["logs"] = logs
        for name, body in logs.items():
            cell.outputs.append(nbformat.v4.new_output("stream", name="stdout",
                                text=f"\n--- scheduler {name}: job {job_id} ---\n{body}"))
        if meta.action == "initiate_run":
            result["status"] = "submitted"
        else:
            scheduler = result["scheduler"]
            successful = not error and scheduler["status"] == "DONE"
            native = logs.get("stdout", "") + logs.get("stderr", "")
            if successful and re.search(r"(?m)^Nothing to be done(?:\.|\s|$)", native):
                result["status"] = "nothing_to_do"
            elif successful and ("This was a dry-run" in native or "Job stats:" in native):
                result["status"] = "ready"
            elif error or scheduler["status"] == "EXIT":
                result["status"] = "failed"
            else:
                result["status"] = "unknown"
        return result

    @staticmethod
    def logs(stem, job_id):
        logs = {}
        for stream, suffix in (("stdout", "out"), ("stderr", "err")):
            path = Path(f"{stem}.{int(job_id)}.{suffix}")
            if path.exists():
                logs[stream] = path.read_text(errors="replace")
        return logs
