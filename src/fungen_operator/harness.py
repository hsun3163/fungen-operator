"""Action lifecycle and approval/readiness gates shared by MCP and replay."""

from __future__ import annotations

import copy
import json
import sys
import uuid
from pathlib import Path

import yaml

from .actions import Deployment, PrepareConfig, RunSlots, MODELS, digest, inside, validate_value
from .execution import Executor
from .notebook import Notebook, active, now, recipe_key, verify


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

    def _idle(self, nb):
        # The live server only stages actions. Its approved host entrypoint repeats
        # this check before executing any cell, including configuration writes.
        if not self.executor.can_schedule:
            return
        # Include historical cells: a superseded receipt does not make a job disappear.
        for cell in nb.cells:
            meta = cell.metadata.get("fungen", {})
            if meta.get("action") != "initiate_run":
                continue
            result = meta.get("result", {})
            if result.get("job_id"):
                if result.get("scheduler", {}).get("status") in {"DONE", "EXIT"}:
                    continue
                state = self.executor.scheduler(result["job_id"])
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

    def propose_config(self, args: PrepareConfig):
        book, nb, current = self._context(args)
        previous_cell = current.get("prepare_config")
        previous = yaml.safe_load(previous_cell.metadata.fungen.slots.bindings.config_text) if previous_cell else None
        if previous is None and Path(args.configfile).exists():
            # Adopting an existing run must not silently reset its science to defaults.
            previous = yaml.safe_load(Path(args.configfile).read_text())
            validate_value(previous, self.deployment.defaults(), "configuration")
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
            self._idle(nb)
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
        if values.get("rerun_triggers") is None:
            values.pop("rerun_triggers", None)
        for key in ("job_name", "walltime_minutes", "phase", "log_dir"):
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
            if action == "initiate_run":
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
            result = self.executor.execute(cell)
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
        if not inside(notebook, self.deployment.run_root):
            raise ValueError("notebook must belong to run_root")
        book = Notebook(notebook)
        with book.locked():
            nb = book.read()
            cell = next((c for c in active(nb) if c.id == cell_id), None)
            if cell is None or cell.metadata.fungen.status not in {"prepared", "host_approval_required"}:
                raise ValueError("only an unexecuted active cell can be executed here")
            meta = cell.metadata.fungen
            args = MODELS[meta.action].model_validate(meta.slots.arguments)
            _, _, current = self._context(args)
            self._idle(nb)
            identity = self.deployment.identity()
            if identity != meta.identity:
                raise ValueError("implementation or configuration changed; repeat readiness")
            if meta.action == "prepare_config":
                return self._execute(book, nb, cell)
            cfg = self._matching_config(args, current)
            if self._run_fingerprint(args, identity, cfg) != meta.run_fingerprint:
                raise ValueError("implementation or configuration changed; repeat readiness")
            if meta.action == "initiate_run":
                ready = current.get("check_readiness:before_run")
                if ready is None or ready.metadata.fungen.status not in {"ready", "nothing_to_do"} or ready.metadata.fungen.run_fingerprint != meta.run_fingerprint:
                    raise ValueError("successful matching readiness required")
            return self._execute(book, nb, cell)

    def replay(self, notebook):
        """Replay a snapshot of active intent through the same action gates."""
        if not inside(notebook, self.deployment.run_root):
            raise ValueError("notebook must belong to run_root")
        nb = Notebook(notebook).read()
        self._idle(nb)
        remaining = nb.metadata.fungen.get("replay_remaining")
        recipe = copy.deepcopy([c for c in active(nb) if c.id in remaining] if remaining else active(nb))
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
            if result["status"] not in {"materialized", "ready", "nothing_to_do", "submitted"}:
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

    def inspect(self, request):
        nb = Notebook(request.notebook).read()
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
                entry["scheduler"] = self.executor.scheduler(job)
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
        return {"cells": cells, "paths": observations, "active_cells_valid": True}
