"""Action lifecycle and approval/readiness gates shared by MCP and replay."""

from __future__ import annotations

import copy
import json
import re
import sys
import uuid
from pathlib import Path

import yaml

from .actions import Deployment, PrepareConfig, RunSlots, MODELS, digest, inside
from .execution import Executor
from .notebook import Notebook, active, now, recipe_key, verify
from .live_control import ControlRun, command, commands, approval_fingerprint


def resource_path(path):
    """Only three-component scheduler resource leaves qualify for live edits."""
    return (len(path) == 3 and all(isinstance(p, str) for p in path)
            and re.fullmatch(r"[A-Za-z0-9_-]+", path[1]) is not None
            and ((path[0] == "sos_tasks" and path[2] in {"mem", "walltime", "queue"})
                 or (path[0] == "jobs" and path[2] in {"mem_mb", "runtime", "queue"})))


def changed_paths(before, after, prefix=()):
    """Compare actual mappings, preserving added/deleted parent paths as changes."""
    if isinstance(before, dict) and isinstance(after, dict):
        paths = []
        for key in before.keys() | after.keys():
            path = (*prefix, key)
            if key not in before or key not in after:
                paths.append(path)
            else:
                paths.extend(changed_paths(before[key], after[key], path))
        return paths
    return [] if type(before) is type(after) and before == after else [prefix]


class Harness:
    def __init__(self, deployment: Deployment, executor=None, deployment_file=None):
        deployment.validate_layout()
        self.deployment = deployment
        self.executor = executor or Executor(deployment)
        self.deployment_file = deployment_file

    def _context(self, args):
        self.deployment.validate_arguments(args)
        book = Notebook(args.notebook)
        nb = book.read()
        current = {recipe_key(c.metadata.fungen): c for c in active(nb)}
        if current:
            first = next(iter(current.values())).metadata.fungen.slots.arguments
            for key in ("notebook", "configfile", "workdir"):
                if first[key] != getattr(args, key):
                    raise ValueError("one notebook owns one config/output graph; create another notebook")
        return book, nb, current

    def _idle(self, nb, *, resource_edit=False):
        # The live server only stages actions. Its approved host entrypoint repeats
        # this check before executing any cell, including configuration writes.
        if not self.executor.can_schedule:
            return
        # Include historical cells: a superseded receipt does not make a job disappear.
        for cell in nb.cells:
            meta = cell.metadata.get("fungen", {})
            if meta.get("action") not in {"initiate_run"}:
                continue
            result = meta.get("result", {})
            if result.get("job_id"):
                if result.get("scheduler", {}).get("status") in {"DONE", "EXIT"}:
                    continue
                state = self.executor.scheduler(result["job_id"])
                if resource_edit and state["status"] in {"RUN", "PEND"}:
                    continue
                if state["status"] not in {"DONE", "EXIT"}:
                    raise ValueError(f"controller {result['job_id']} is {state['status']}; inspect before changing the run")
                result["scheduler"] = state
                result["terminal_observed"] = now()
                logs = self.executor.logs(meta["slots"]["bindings"]["log_stem"], result["job_id"])
                result["logs"] = logs
                import nbformat
                for stream, text in logs.items():
                    cell.outputs.append(nbformat.v4.new_output("stream", name="stdout",
                        text=f"\n--- terminal scheduler {stream}: job {result['job_id']} ---\n{text}"))
            elif meta.get("status") in {"executing", "unknown"}:
                raise ValueError("unresolved submission outcome; reconcile before changing the run")

    def _config_idle(self, nb, args, proposed):
        # Pending cells supersede the accepted cell in recipe order. Recover the
        # last materialized baseline by sequence, including retained history.
        accepted = [c for c in nb.cells if c.metadata.get("fungen", {}).get("action") == "prepare_config"
                    and c.metadata.fungen.get("status") == "materialized"]
        baseline = max(accepted, key=lambda c: c.metadata.fungen.sequence) if accepted else None
        actual = yaml.safe_load(Path(args.configfile).read_text()) if Path(args.configfile).exists() else None
        before = yaml.safe_load(baseline.metadata.fungen.slots.bindings.config_text) if baseline else actual
        paths = changed_paths(before, proposed)
        resource_edit = bool(baseline and paths and all(resource_path(p) for p in paths)
                             and all(resource_path(tuple(p.split("."))) for p in args.parameters))
        if resource_edit:
            recorded = baseline.metadata.fungen.slots.arguments
            if any(recorded[k] != getattr(args, k) for k in ("notebook", "configfile", "workdir")):
                raise ValueError("resource edit must retain the accepted config/output graph")
            if (actual != before or Path(args.configfile).read_text()
                    != baseline.metadata.fungen.slots.bindings.config_text):
                raise ValueError("external configuration drift; reconcile before resource edit")
            self.deployment.validate_config(proposed)
        self._idle(nb, resource_edit=resource_edit)

    def propose_config(self, args: PrepareConfig):
        book, nb, current = self._context(args)
        previous_cell = current.get("prepare_config")
        previous = yaml.safe_load(previous_cell.metadata.fungen.slots.bindings.config_text) if previous_cell else None
        if previous is None and Path(args.configfile).exists():
            # Adopting an existing run must not silently reset its science to defaults.
            previous = yaml.safe_load(Path(args.configfile).read_text())
            self.deployment.validate_config(previous)
        config, changes = self.deployment.config(args, previous)
        if previous_cell and Path(args.configfile).exists():
            actual = yaml.safe_load(Path(args.configfile).read_text())
            if not isinstance(actual, dict):
                raise ValueError("existing configuration must be a YAML mapping")
            # Restoring an externally changed scientific value is a change too.
            changes.update(self.deployment.scientific_diff(actual, config))
        identity = self.deployment.identity()
        proposal = {"arguments": args.model_dump(), "config": config, "scientific_changes": changes,
                    "identity": identity, "notebook_hash": digest(nb) if book.path.exists() else None}
        proposal["fingerprint"] = digest(proposal)
        return proposal

    def prepare_config(self, proposal, approval=None):
        args = PrepareConfig.model_validate(proposal["arguments"])
        fresh = self.propose_config(args)
        if proposal["fingerprint"] != fresh["fingerprint"]:
            raise ValueError("proposal changed while awaiting approval; request approval again")
        if proposal["scientific_changes"]:
            if not approval or approval.get("fingerprint") != proposal["fingerprint"]:
                raise ValueError("scientific approval required before materialization")
        book = Notebook(args.notebook)
        with book.locked():
            # Recheck after acquiring the lock, including competing writers.
            if self.propose_config(args)["fingerprint"] != proposal["fingerprint"]:
                raise ValueError("stale configuration approval")
            _, nb, _ = self._context(args)
            self._config_idle(nb, args, proposal["config"])
            slots = {"arguments": args.model_dump(), "bindings": {
                "config_text": yaml.safe_dump(proposal["config"], sort_keys=True)}}
            cell = book.append(nb, "prepare_config", slots, proposal["identity"], uuid.uuid4().hex,
                               approval=approval)
            return self._execute(book, nb, cell)

    def _matching_config(self, args, current):
        cfg = current.get("prepare_config")
        if cfg is None or cfg.metadata.fungen.status != "materialized":
            raise ValueError("prepare_config must successfully materialize first")
        text = cfg.metadata.fungen.slots.bindings.config_text
        if not Path(args.configfile).exists() or Path(args.configfile).read_text() != text:
            raise ValueError("configuration differs from notebook recipe; prepare_config again")
        return text

    def _run_fingerprint(self, args, identity, config_text):
        values = args.model_dump()
        # Keep pre-option recipes/fingerprints stable when the option is absent.
        for option in ("rerun_triggers", "sos_j", "sos_max_running_jobs", "sos_queue"):
            if values.get(option) is None:
                values.pop(option, None)
        for key in ("job_name", "walltime_minutes", "phase", "log_dir", "depends_on", "defer_readiness"):
            values.pop(key, None)
        return digest({"arguments": values, "identity": identity, "config": config_text})

    def run(self, action: str, args: RunSlots):
        if action not in {"check_readiness", "initiate_run"}:
            raise ValueError("unsupported run action")
        args = MODELS[action].model_validate(args.model_dump())
        book = Notebook(args.notebook)
        # Validate before even creating a lock outside permitted paths.
        self._context(args)
        with book.locked():
            _, nb, current = self._context(args)
            self._idle(nb)
            text = self._matching_config(args, current)
            identity = self.deployment.identity()
            fingerprint = self._run_fingerprint(args, identity, text)
            if action == "initiate_run" and not args.defer_readiness:
                ready = current.get("check_readiness:before_run")
                if (ready is None or ready.metadata.fungen.status not in {"ready", "nothing_to_do"}
                        or ready.metadata.fungen.get("run_fingerprint") != fingerprint):
                    raise ValueError("a successful matching check_readiness is required")
            cell_id = uuid.uuid4().hex
            slots = {"arguments": args.model_dump(), "bindings": {
                "snakefile": self.deployment.snakefile, "profile_path": self.deployment.profile_path,
                "conda_sh": self.deployment.conda_sh, "conda_env": self.deployment.conda_env,
                "log_stem": str(Path(args.log_dir, cell_id))}}
            cell = book.append(nb, action, slots, identity, cell_id)
            if action == "initiate_run" and args.defer_readiness:
                cell.metadata.fungen["readiness_policy"] = "canonical_dry_run_at_controller_start"
            cell.metadata.fungen["run_fingerprint"] = fingerprint
            book.save(nb)
            return self._execute(book, nb, cell)

    def _execute(self, book, nb, cell):
        meta = cell.metadata.fungen
        if not self.executor.can_schedule:
            meta.status = "host_approval_required"
            book.save(nb)
            return {"cell_id": cell.id, "notebook": str(book.path), "status": meta.status,
                    "host_command": [sys.executable, "-m", "fungen_operator", "execute",
                                     "--deployment", self.deployment_file or "DEPLOYMENT.json",
                                     "--notebook", str(book.path), "--cell", cell.id],
                    "instruction": "Run this exact entrypoint through require_escalated; do not run it in the sandbox."}
        meta.status = "executing"
        meta["started"] = now()
        book.save(nb)
        try:
            result = self.executor.execute(cell, Path(book.path).resolve().parent)
        except Exception as exc:
            meta.status = "unknown"
            meta["error"] = f"{type(exc).__name__}: {exc}"
            book.save(nb)
            raise
        meta["result"] = result
        meta.status = result["status"]
        meta["finished"] = now()
        book.save(nb)
        return {"cell_id": cell.id, "notebook": str(book.path), **result}

    def execute_pending(self, notebook, cell_id):
        self.deployment.validate_write_path(notebook)
        book = Notebook(notebook)
        with book.locked():
            nb = book.read()
            cell = next((c for c in active(nb) if c.id == cell_id), None)
            if cell is None or cell.metadata.fungen.status not in {"prepared", "host_approval_required"}:
                raise ValueError("only an unexecuted active cell can be executed here")
            meta = cell.metadata.fungen
            args = MODELS[meta.action].model_validate(meta.slots.arguments)
            if meta.action == "control_run":
                self.validate_control_cell(nb, cell)
                return self._execute(book, nb, cell)
            _, _, current = self._context(args)
            identity = self.deployment.identity()
            if identity != meta.identity:
                raise ValueError("implementation or configuration changed; repeat readiness")
            if meta.action == "prepare_config":
                proposed = yaml.safe_load(meta.slots.bindings.config_text)
                self.deployment.validate_config(proposed)
                # Reconstruct the saved proposal through the typed catalog. This
                # also checks shell values, selectors and unregistered fields.
                accepted = [c for c in nb.cells if c.metadata.get("fungen", {}).get("action") == "prepare_config"
                            and c.metadata.fungen.get("status") == "materialized"]
                prior = max(accepted, key=lambda c: c.metadata.fungen.sequence) if accepted else None
                before = (yaml.safe_load(prior.metadata.fungen.slots.bindings.config_text) if prior
                          else yaml.safe_load(Path(args.configfile).read_text()) if Path(args.configfile).exists()
                          else None)
                expected, changes = self.deployment.config(args, before)
                if proposed != expected:
                    raise ValueError("saved configuration differs from typed proposal; prepare again")
                if Path(args.configfile).exists():
                    changes.update(self.deployment.scientific_diff(
                        yaml.safe_load(Path(args.configfile).read_text()), proposed))
                if changes and not (meta.get("approval") or {}).get("fingerprint"):
                    raise ValueError("scientific approval required before materialization")
                self._config_idle(nb, args, proposed)
                return self._execute(book, nb, cell)
            self._idle(nb)
            cfg = self._matching_config(args, current)
            if self._run_fingerprint(args, identity, cfg) != meta.run_fingerprint:
                raise ValueError("implementation or configuration changed; repeat readiness")
            if meta.action == "initiate_run" and not args.defer_readiness:
                ready = current.get("check_readiness:before_run")
                if ready is None or ready.metadata.fungen.status not in {"ready", "nothing_to_do"} or ready.metadata.fungen.run_fingerprint != meta.run_fingerprint:
                    raise ValueError("successful matching readiness required")
            return self._execute(book, nb, cell)

    def replay(self, notebook):
        """Replay a snapshot of active intent through the same action gates."""
        self.deployment.validate_write_path(notebook)
        nb = Notebook(notebook).read()
        self._idle(nb)
        remaining = nb.metadata.fungen.get("replay_remaining")
        recipe = copy.deepcopy([c for c in active(nb) if c.id in remaining] if remaining else active(nb))
        recipe = [c for c in recipe if c.metadata.fungen.action != "control_run"]
        results = []
        for index, old in enumerate(recipe):
            meta = old.metadata.fungen
            if meta.identity != self.deployment.identity():
                raise ValueError("implementation identity changed; rebind the recipe")
            action = meta.action
            args = MODELS[action].model_validate(meta.slots.arguments)
            if action == "prepare_config":
                # Replay the complete recorded configuration, including approved science.
                recorded = yaml.safe_load(meta.slots.bindings.config_text)
                params = {key: value for key, value in recorded.items() if key != "cwd"}
                args = args.model_copy(update={"parameters": params})
                proposal = self.propose_config(args)
                if proposal["scientific_changes"]:
                    raise ValueError("replay would change scientific values; use prepare_config approval")
                result = self.prepare_config(proposal, approval=meta.approval)
            else:
                result = self.run(action, args)
            results.append(result)
            if result["status"] not in {"materialized", "ready", "nothing_to_do", "submitted", "completed"}:
                break
            if action == "initiate_run":
                state = self.executor.scheduler(result["job_id"])["status"]
                if state not in {"DONE", "EXIT"}:
                    # Keep the unexecuted suffix active and resume it on the next
                    # replay call, rather than submitting another controller.
                    book = Notebook(notebook)
                    with book.locked():
                        nb = book.read()
                        pending = []
                        for future in recipe[index + 1:]:
                            m = future.metadata.fungen
                            slots = copy.deepcopy(m.slots)
                            new_id = uuid.uuid4().hex
                            slots.bindings.log_stem = str(Path(slots.arguments.log_dir, new_id))
                            cell = book.append(nb, m.action, slots, m.identity, new_id)
                            cell.metadata.fungen.status = "awaiting_controller"
                            pending.append(new_id)
                        nb.metadata.fungen["replay_remaining"] = pending
                        book.save(nb)
                    return results
        book = Notebook(notebook)
        with book.locked():
            nb = book.read()
            nb.metadata.fungen.pop("replay_remaining", None)
            book.save(nb)
        verify(Notebook(notebook).read())
        return results

    def _control_notebook(self, notebook):
        if not inside(notebook, self.deployment.run_root):
            raise ValueError("notebook must belong to run_root")
        if hasattr(self.deployment, "validate_write_path"):
            self.deployment.validate_write_path(notebook)
        return Notebook(notebook)

    def _job_snapshot(self, nb, grace_minutes=10, job_ids=None):
        from .run_jobs import inspect_jobs
        if not getattr(self.executor, "can_inspect", self.executor.can_schedule):
            return {"count": 0, "dead_children": [], "jobs": {}, "scheduler_ok": False,
                    "observations": ["host_approval_required"]}
        return inspect_jobs(self.deployment, nb, grace_minutes=grace_minutes, requested_ids=job_ids)

    def propose_control(self, request: ControlRun):
        book = self._control_notebook(request.notebook)
        nb = book.read()
        if request.operation == "sweep":
            from .sweep_cell import sweep_bindings
            from .actions import render
            bindings = sweep_bindings(self.deployment, request, nb)
            slots = {"arguments": request.model_dump(), "bindings": bindings}
            proposal = {"status": "approval_required", **slots, "job_ids": [],
                        "command": ["bsub"], "sweep_spec": request.sweep.model_dump(),
                        "source": render("control_run", slots),
                        "notebook_hash": digest(nb) if book.path.exists() else None}
            proposal["fingerprint"] = approval_fingerprint(proposal["arguments"], bindings)
            return proposal
        snapshot = self._job_snapshot(nb, request.dead_child_grace_minutes, request.job_ids)
        if not snapshot["scheduler_ok"]:
            return {"status": "refused", "reason": "live run membership is unavailable",
                    "observations": snapshot.get("observations", [])}
        if request.job_ids is not None:
            ids = request.job_ids
        elif request.selector.kind == "dead_child_wrappers":
            ids = sorted({child["wrapper_job_id"] for child in snapshot["dead_children"]
                          if child.get("wrapper_job_id")}, key=int)
        elif request.selector.kind == "step":
            ids = sorted([job_id for job_id, job in snapshot["jobs"].items()
                          if job.get("membership")
                          and request.selector.step in {job.get("rule"), job.get("task_kind")}
                          and job.get("memory_reservation_gb") == request.selector.memory_reservation_gb], key=int)
        else:
            ids = sorted([job_id for job_id, job in snapshot["jobs"].items()
                          if job.get("membership") and job.get("status", job.get("state")) == "PEND"
                          and job.get("queue") == request.selector.queue
                          and job.get("pending_minutes", -1) > request.selector.min_pending_minutes], key=int)
        refusals = self._control_refusals(request, ids, snapshot)
        if refusals:
            return {"status": "refused", "refusals": refusals, "job_ids": ids}
        if not ids:
            return {"status": "nothing_to_do", "job_ids": []}
        bindings = {"job_ids": ids}
        if request.operation == "modify" and request.memory_reservation_gb is not None:
            bindings["resource_requirements"] = {job_id: snapshot["jobs"][job_id].get("combined_resreq", "")
                                                for job_id in ids}
        literal_commands = commands(request, ids, bindings.get("resource_requirements"))
        proposal = {"status": "approval_required", "arguments": request.model_dump(),
                    "bindings": bindings, "command": literal_commands[0], "commands": literal_commands,
                    "job_ids": ids, "notebook_hash": digest(nb) if book.path.exists() else None}
        proposal["fingerprint"] = approval_fingerprint(proposal["arguments"], bindings)
        return proposal

    @staticmethod
    def _control_refusals(request, ids, snapshot):
        refusals = []
        for job_id in ids:
            job = snapshot["jobs"].get(job_id, {})
            reason = None
            if not job.get("membership"):
                reason = job.get("membership_reason", "job is outside this run's receipts, wrappers and task directories")
            elif job.get("status", job.get("state")) not in {"PEND", "RUN", "PSUSP", "USUSP", "SSUSP", "WAIT"}:
                reason = "job has no live controllable LSF state"
            if reason:
                refusals.append({"job_id": job_id, "reason": reason})
        return refusals

    def control_run(self, proposal, approval=None):
        if proposal.get("status") != "approval_required":
            return proposal
        if not approval or approval.get("fingerprint") != proposal["fingerprint"]:
            raise ValueError("job control approval required")
        request = ControlRun.model_validate(proposal["arguments"])
        bindings = proposal["bindings"]
        if approval_fingerprint(proposal["arguments"], bindings) != proposal["fingerprint"]:
            raise ValueError("stale job control approval")
        book = self._control_notebook(request.notebook)
        with book.locked():
            nb = book.read()
            if (digest(nb) if book.path.exists() else None) != proposal["notebook_hash"]:
                raise ValueError("notebook changed while awaiting approval; request approval again")
            # Recheck the frozen list; a selector is never expanded after approval.
            snapshot = (self._job_snapshot(nb, request.dead_child_grace_minutes, bindings["job_ids"])
                        if request.operation != "sweep" else {"scheduler_ok": True, "jobs": {}})
            if not snapshot["scheduler_ok"]:
                return {"status": "refused", "reason": "live run membership is unavailable"}
            refusals = self._control_refusals(request, bindings["job_ids"], snapshot)
            if refusals:
                return {"status": "refused", "refusals": refusals}
            self._control_resources(bindings, snapshot)
            cell = book.append(nb, "control_run", {"arguments": copy.deepcopy(proposal["arguments"]), "bindings": bindings},
                               self.deployment.identity(), uuid.uuid4().hex, approval=approval)
            return self._execute(book, nb, cell)

    @staticmethod
    def _control_resources(bindings, snapshot):
        for job_id, original in bindings.get("resource_requirements", {}).items():
            if snapshot["jobs"].get(job_id, {}).get("combined_resreq") != original:
                raise ValueError("live resource requirements changed; request approval again")

    def validate_control_cell(self, nb, cell):
        meta = cell.metadata.fungen
        request = ControlRun.model_validate(meta.slots.arguments)
        self._control_notebook(request.notebook)
        if (meta.get("approval") or {}).get("fingerprint") != approval_fingerprint(
                meta.slots.arguments, meta.slots.bindings):
            raise ValueError("job control approval required for this exact command and IDs")
        if request.operation == "sweep":
            from .sweep import SweepPlan
            plan = SweepPlan.model_validate_json(meta.slots.bindings.plan_text)
            if plan.run_root != self.deployment.run_root or plan.snakefile != self.deployment.snakefile:
                raise ValueError("sweep plan differs from the registered deployment")
            return
        snapshot = self._job_snapshot(nb, request.dead_child_grace_minutes, meta.slots.bindings.job_ids)
        if not snapshot["scheduler_ok"]:
            raise ValueError("live run membership is unavailable")
        refusals = self._control_refusals(request, meta.slots.bindings.job_ids, snapshot)
        if refusals:
            raise ValueError("job control refused: " + json.dumps(refusals))
        self._control_resources(meta.slots.bindings, snapshot)

    def inspect(self, request):
        nb = Notebook(request.notebook).read()
        snapshot = (self._job_snapshot(nb, request.dead_child_grace_minutes)
                    if self.deployment.backend == "lsf" else
                    {"count": 0, "dead_children": [], "jobs": {}, "scheduler_ok": True})
        cells = []
        for c in nb.cells:
            if c.cell_type != "code":
                continue
            meta = c.metadata.fungen
            entry = {"cell_id": c.id, "action": meta.action, "status": meta.status,
                     "superseded": "superseded" in c.metadata.get("tags", []),
                     "result": meta.get("result", {})}
            job = entry["result"].get("job_id")
            if job:
                entry["scheduler"] = (snapshot["jobs"].get(str(job), {"status": "UNKNOWN"})
                                      if self.deployment.backend == "lsf" else self.executor.scheduler(job))
                entry["logs"] = self.executor.logs(meta.slots.bindings.log_stem, job)
            cells.append(entry)
        observations = {}
        for name in request.paths:
            p = Path(name)
            record = {"exists": p.exists(), "is_file": p.is_file()}
            if p.is_file():
                record["size"] = p.stat().st_size
                with p.open("rb") as stream:
                    record["prefix"] = stream.read(request.max_bytes).decode("utf-8", errors="replace")
            observations[name] = record
        return {"cells": cells, "paths": observations, "active_cells_valid": True,
                "dead_children": snapshot["dead_children"], "dead_child_count": snapshot["count"],
                "scheduler_ok": snapshot["scheduler_ok"],
                "scheduler_observations": snapshot.get("observations", [])}
