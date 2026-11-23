"""Execute exactly one rendered notebook cell, then attach native evidence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from .actions import Deployment, inside


class Executor:
    def __init__(self, deployment: Deployment, host_approved=False, host_inspection=False):
        self.deployment = deployment
        self.host_approved = host_approved
        self.host_inspection = host_inspection

    @property
    def can_schedule(self):
        return self.deployment.backend == "fixture" or self.host_approved

    @property
    def can_inspect(self):
        return self.can_schedule or self.host_inspection

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
        if self.deployment.backend in ('slurm','sge'):
            from .cluster import job_status
            try:
                status=job_status(self.deployment.backend,str(job_id))
                return {'job_id':str(job_id),'status':{'success':'DONE','failed':'EXIT','running':'RUN'}[status],
                        'exit_code':0 if status=='success' else None}
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
                return {'job_id':str(job_id),'status':'UNKNOWN','diagnostic':str(exc)}
        # Fixed read-only scheduler command; unknown never means finished.
        proc = subprocess.run(["bjobs", "-json", "-o", "jobid stat exit_code", str(int(job_id))],
                              env=self.environment(), text=True, capture_output=True)
        try:
            records = json.loads(proc.stdout)["RECORDS"]
            record = records[0]
            # LSF purges terminal jobs from bjobs before their accounting expires.
            # Only an explicit missing-job response permits this terminal lookup;
            # connection failures and malformed responses remain unknown.
            if record.get("ERROR") == f"Job <{int(job_id)}> is not found":
                return self._accounted_scheduler(job_id)
            status = record.get("STAT", record.get("stat", "UNKNOWN"))
            return {"job_id": str(job_id), "status": status,
                    "exit_code": record.get("EXIT_CODE", record.get("exit_code"))}
        except (ValueError, KeyError, IndexError):
            return {"job_id": str(job_id), "status": "UNKNOWN", "diagnostic": proc.stderr}

    def _accounted_scheduler(self, job_id):
        unknown = {"job_id": str(job_id), "status": "UNKNOWN",
                   "inactive": True,
                   "diagnostic": "Job absent from bjobs; terminal accounting unavailable"}
        try:
            proc = subprocess.run(["bacct", "-l", str(int(job_id))],
                                  env=self.environment(), text=True, capture_output=True,
                                  timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return unknown
        if proc.returncode != 0:
            return unknown
        # Anchor to the requested native record header, before its command text.
        header = re.search(rf"(?m)^Job <{int(job_id)}>,[^\n]*(?:\n[ \t]+[^\n]*)*", proc.stdout)
        if not header:
            return unknown
        fields = re.split(r"\bCommand\s*<", header.group(0), maxsplit=1)[0]
        state = re.search(r"\bStatus\s*<(DONE|EXIT)>", fields)
        if not state:
            return unknown
        return {"job_id": str(job_id), "status": state.group(1),
                "exit_code": None, "source": "bacct"}

    def execute(self, cell, folder):
        meta = cell.metadata.fungen
        registry = self.deployment.registry
        spec = registry.spec(meta.action)
        if cell.source != registry.render(meta.action, meta.slots, meta.template_version):
            raise ValueError("executor refused a cell that does not re-render")
        args = registry.models[meta.action].model_validate(meta.slots.arguments)
        if meta.action == "control_run":
            from .harness import Harness
            from .notebook import Notebook
            Harness(self.deployment, self).validate_control_cell(Notebook(args.notebook, registry).read(), cell)
        else:
            self.deployment.validate_arguments(args)
            if spec.validate:
                spec.validate(self.deployment, args)
        if spec.validate_bindings:
            spec.validate_bindings(self.deployment, args, meta.slots.bindings)
        elif meta.action in {"check_readiness", "initiate_run"}:
            b = meta.slots.bindings
            for key in ("snakefile", "profile_path", "conda_sh", "conda_env"):
                if b[key] != getattr(self.deployment, key):
                    raise ValueError(f"recorded {key} differs from the registered deployment")
            if dict(b)!=self.deployment.runtime_bindings(b.log_stem):
                raise ValueError("runtime scheduler bindings differ from the registered deployment")
            if not inside(b.log_stem, args.log_dir):
                raise ValueError("log stem must belong to the action log directory")
        if meta.action != "prepare_config" and not self.can_schedule:
            return {"status": "host_approval_required"}
        one = nbformat.v4.new_notebook(cells=[cell])
        # A fresh Python kernel runs the actual %%bash magic, not a reconstructed command.
        # Like Jupyter, it runs in the notebook's folder (the run folder), where LSF then starts the job.
        client = NotebookClient(one, timeout=None, startup_timeout=300,
                                kernel_name="python3", allow_errors=True,
                                resources={"metadata": {"path": str(folder)}})
        client.km = client.create_kernel_manager()
        # The harness interpreter owns notebook execution. Do not accidentally use
        # a user's globally registered kernel or the workflow's shell `python`.
        client.km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        submitted_at_ns = time.time_ns()
        previous_outputs = ({name: self._output_stamp(Path(getattr(args, name)))
                             for name in spec.output_fields}
                            if spec.output_fields else {})
        client.execute(env=self.environment())
        cell.outputs = one.cells[0].outputs
        cell.execution_count = one.cells[0].execution_count
        text = "".join(o.get("text", "") for o in cell.outputs)
        error = any(o.output_type == "error" for o in cell.outputs)
        result = {"status": "failed" if error else "materialized", "backend": self.deployment.backend,
                  "notebook_interpreter": sys.executable, "notebook_python": sys.version.split()[0]}
        if meta.action == "prepare_config":
            return result
        if spec.synchronous:
            return {**result, "status": "failed" if error else "completed", "logs": {"stdout": text}}
        if meta.action == "control_run":
            if args.operation == "sweep":
                from .sweep_cell import sweep_result
                receipt = sweep_result(self, args, meta.slots.bindings, text, error, result)
                if receipt.get("last_pass"):
                    cell.outputs.append(nbformat.v4.new_output("stream", name="stdout",
                        text="\n--- sweep pass ---\n" + json.dumps(receipt["last_pass"], sort_keys=True) + "\n"))
                return receipt
            from .live_control import commands
            literal = commands(args, meta.slots.bindings.job_ids, meta.slots.bindings.get("resource_requirements"))
            return {**result, "status": "failed" if error else "controlled",
                    "command": literal[0], "commands": literal,
                    "job_ids": list(meta.slots.bindings.job_ids), "receipt": text}
        if self.deployment.backend=='local':
            if error:return {**result,'status':'failed','logs':{}}
            if meta.action=='check_readiness':
                if re.search(r'(?m)^Nothing to be done(?:\.|\s|$)',text):status='nothing_to_do'
                elif re.search(r'(?m)^(?:This was a dry-run(?:\s|$)|Job stats:\s*$)',text):status='ready'
                else:status='unknown'
                return {**result,'status':status,'logs':{'stdout':text}}
            return {**result,'status':'completed','logs':{'stdout':text}}
        receipt = (re.search(r"Job <(\d+)> is submitted", text) if self.deployment.backend in ('lsf','fixture')
                   else re.search(r"(?m)^(\d+)(?:;[^\s]+)?\s*$",text))
        if not receipt:
            # Nonzero bsub without a receipt can still be ambiguous. Never retry blindly.
            return {**result, "status": "unknown", "diagnostic": "No retained scheduler receipt"}
        job_id = receipt.group(1)
        result["job_id"] = job_id
        if spec.reconcile:
            result["submitted_at_ns"] = submitted_at_ns
            result.update(spec.reconcile(self, args, meta.slots.bindings, job_id, error, previous_outputs))
        elif meta.action == "check_readiness":
            result.update(self._reconcile_readiness(job_id, meta.slots.bindings.log_stem, error))
        else:
            result.update(status="submitted", scheduler=self.scheduler(job_id),
                          logs=self.logs(meta.slots.bindings.log_stem, job_id))
            if getattr(args, "defer_readiness", False):
                result["readiness_policy"] = "canonical_dry_run_at_controller_start"
        for name, body in result["logs"].items():
            cell.outputs.append(nbformat.v4.new_output("stream", name="stdout",
                                text=f"\n--- scheduler {name}: job {job_id} ---\n{body}"))
        return result

    @staticmethod
    def _output_stamp(path):
        if not path.is_file():
            return None
        stat = path.stat()
        return [stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino]

    def recover_readiness(self, cell):
        """Recover an interrupted synchronous call from its unique native log stem."""
        return self._recover_native_controller(cell, readiness=True)

    def recover_submission(self, cell):
        """Recover an interrupted submission without executing or resubmitting it."""
        return self._recover_native_controller(cell, readiness=False)

    def _recover_native_controller(self, cell, *, readiness):
        if self.deployment.backend != 'lsf' or not self.can_inspect:
            return None
        stem = Path(cell.metadata.fungen.slots.bindings.log_stem)
        known = str(cell.metadata.fungen.get('result', {}).get('job_id', ''))
        jobs = {known} if re.fullmatch(r'[1-9][0-9]*', known) else set()
        for path in ([] if jobs else stem.parent.glob(stem.name + '.*.out')):
            match = re.fullmatch(re.escape(stem.name) + r'\.([1-9][0-9]*)\.out', path.name)
            if match:
                jobs.add(match[1])
        # LSF can buffer the output file until termination. Discover only the
        # exact saved output stem, never another job sharing the graph/name.
        if not jobs:
            proc = subprocess.run(['bjobs', '-a', '-json', '-o', 'jobid stat output_file'],
                                  capture_output=True, text=True, timeout=60)
            if proc.returncode:
                return None
            for record in json.loads(proc.stdout).get('RECORDS', []):
                job = str(record.get('JOBID', ''))
                output = record.get('OUTPUT_FILE', '')
                if (re.fullmatch(r'[1-9][0-9]*', job)
                        and output in {str(stem) + '.' + job + '.out', str(stem) + '.%J.out'}):
                    jobs.add(job)
        if len(jobs) != 1:
            return None
        job = jobs.pop()
        state = self.controller_scheduler(str(stem), job)
        logs = self.logs(str(stem), job)
        status = 'unknown'
        if not readiness:
            if state['status'] in {'RUN', 'PEND', 'DONE', 'PSUSP', 'USUSP', 'SSUSP', 'WAIT'}:
                status = 'submitted'
            elif state['status'] == 'EXIT':
                status = 'failed'
        elif state['status'] == 'EXIT':
            status = 'failed'
        elif state['status'] in {'RUN', 'PEND'}:
            status = 'executing'
        elif state['status'] == 'DONE':
            native = logs.get('stdout', '') + logs.get('stderr', '')
            if re.search(r'(?m)^Nothing to be done(?:\.|\s|$)', native):
                status = 'nothing_to_do'
            elif re.search(r'(?m)^(?:This was a dry-run(?:\s|$)|Job stats:\s*$)', native):
                status = 'ready'
        return {'status': status, 'backend': 'lsf', 'job_id': job,
                'scheduler': state, 'logs': logs, 'recovered_from': 'native_log_stem'}

    def _reconcile_readiness(self, job_id, stem, error):
        # bsub -K has returned, but bjobs and shared-filesystem logs can lag it.
        # Recheck this receipt only, for at most seven seconds of backoff. This
        # is not polling an asynchronous production controller or resubmitting.
        result = {"status": "unknown", "synchronous_exit_code": None if error else 0,
                  "scheduler_observations": []}
        for delay in (0, 1, 2, 4):
            if delay:
                time.sleep(delay)
            scheduler = self.scheduler(job_id)
            logs = self.logs(stem, job_id)
            result.update(scheduler=scheduler, logs=logs)
            result["scheduler_observations"].append(scheduler)
            state = scheduler["status"]
            exit_code = scheduler.get("exit_code")
            # LSF leaves EXIT_CODE blank for DONE. The successfully executed
            # set -e bash cell supplies exit 0 from synchronous bsub -K.
            if state == "DONE" and exit_code in (None, "") and not error:
                exit_code = 0
            try:
                exit_code = int(exit_code)
            except (ValueError, TypeError):
                exit_code = None
            if error or state == "EXIT" or (exit_code is not None and exit_code != 0):
                result["status"] = "failed"
                break
            native = logs.get("stdout", "") + logs.get("stderr", "")
            if state == "DONE" and exit_code == 0:
                if re.search(r"(?m)^Nothing to be done(?:\.|\s|$)", native):
                    result["status"] = "nothing_to_do"
                    break
                if re.search(r"(?m)^(?:This was a dry-run(?:\s|$)|Job stats:\s*$)", native):
                    result["status"] = "ready"
                    break
            if state not in {"PEND", "RUN", "DONE"}:
                break
        return result

    def controller_scheduler(self, stem, job_id):
        """Use a matching native LSF footer only after explicit history expiry."""
        state = self.scheduler(job_id)
        if (state.get("status") != "UNKNOWN" or self.deployment.backend != "lsf"
                or not state.get("diagnostic", "").startswith("Job absent from bjobs")):
            return state
        text = self.logs(stem, job_id).get("stdout", "").split("The output (if any) follows:", 1)[0]
        if not re.search(r"(?m)^Sender: LSF System", text):
            return state
        header = re.search(r"(?m)^Subject: Job " + re.escape(str(job_id)) + r":[^\n]*\b(Done|Exited)\s*$", text)
        if not header:
            return state
        if header.group(1) == "Done" and "Successfully completed." in text:
            return {"job_id": str(job_id), "status": "DONE", "exit_code": 0, "source": "native_lsf_footer"}
        code = re.search(r"Exited with exit code ([0-9]+)", text)
        if header.group(1) == "Exited" and code:
            return {"job_id": str(job_id), "status": "EXIT", "exit_code": int(code.group(1)), "source": "native_lsf_footer"}
        return state

    def live_logs(self, stem, job_id):
        """Read saved streams, or the approved live LSF spool before flush."""
        logs = self.logs(stem, job_id)
        if logs.get("stdout") or self.deployment.backend != "lsf" or not self.can_inspect:
            return logs
        if not re.fullmatch(r"[1-9][0-9]{0,15}", str(job_id)):
            raise ValueError("live log inspection requires an exact positive job ID")
        try:
            proc = subprocess.run(["bpeek", str(job_id)], env=self.environment(),
                                  text=True, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {**logs, "live_diagnostic": str(exc)}
        if proc.returncode:
            return {**logs, "live_diagnostic": proc.stderr.strip() or "bpeek returned no live stream"}
        return {**logs, "live_stdout": proc.stdout}

    @staticmethod
    def logs(stem, job_id):
        logs = {}
        for stream, suffix in (("stdout", "out"), ("stderr", "err")):
            path = Path(f"{stem}.{int(job_id)}.{suffix}")
            if path.exists():
                logs[stream] = path.read_text(errors="replace")
        return logs
