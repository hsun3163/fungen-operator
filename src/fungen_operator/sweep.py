"""Run-local, approval-bound upkeep of pending workflow jobs through LSF."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MemoryGB = Annotated[int, Field(ge=1, le=1000)]
Step = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class MemoryRemap(_Model):
    step: Step
    from_gb: MemoryGB
    to_gb: MemoryGB
    hard_limit_gb: MemoryGB | None = None

    @model_validator(mode="after")
    def changed(self):
        if self.from_gb == self.to_gb:
            raise ValueError("a memory remap requires different reservations")
        return self


class QueueMove(_Model):
    from_queue: Literal["premium", "express"]
    to_queue: Literal["premium", "express"]
    limit: Annotated[int, Field(ge=1, le=20000)]

    @model_validator(mode="after")
    def changed(self):
        if self.from_queue == self.to_queue:
            raise ValueError("a queue move requires different queues")
        return self


class SweepSpec(_Model):
    memory_remaps: Annotated[list[MemoryRemap], Field(max_length=1000)] = Field(default_factory=list)
    queue_move: QueueMove | None = None
    interval_seconds: Annotated[int, Field(ge=0, le=86400)] = 300

    @model_validator(mode="after")
    def complete(self):
        if not self.memory_remaps and self.queue_move is None:
            raise ValueError("a sweep requires at least one memory remap or queue move")
        keys = [(rule.step, rule.from_gb) for rule in self.memory_remaps]
        if len(keys) != len(set(keys)):
            raise ValueError("memory remaps require unique step and from_gb pairs")
        return self


class SweepPlan(_Model):
    version: Literal[1] = 1
    spec: SweepSpec
    notebook: str
    run_root: str
    snakefile: str
    log_path: str
    jq_path: str = "jq"

    @field_validator("notebook", "run_root", "snakefile", "log_path")
    @classmethod
    def absolute_path(cls, value):
        if not Path(value).is_absolute():
            raise ValueError("sweep paths must be absolute")
        return str(Path(value).resolve())

    @model_validator(mode="after")
    def local_files(self):
        root = Path(self.run_root)
        if not all(Path(path).is_relative_to(root) for path in (self.notebook, self.log_path)):
            raise ValueError("sweep notebook and log must belong to the run root")
        return self


def load_plan(path, sha256):
    """Verify the exact approved plan bytes before interpreting any settings."""
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("invalid sweep plan digest")
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("sweep plan differs from its approved digest")
    plan = SweepPlan.model_validate_json(raw)
    if not Path(path).resolve().is_relative_to(Path(plan.run_root)):
        raise ValueError("sweep plan must belong to the run root")
    return plan


# Streaming jq retains at most one JSON scalar. Only the fields used to
# establish native job lineage leave jq; notebook outputs and result logs do
# not enter Python. The cache refreshes when a new controller receipt is saved.
_JQ_METADATA = r'''select(length == 2 and (.[0] | length) >= 5
  and .[0][0] == "cells" and .[0][2:4] == ["metadata", "fungen"]
  and ((.[0][4:] == ["action"])
    or (.[0][4:] == ["slots", "arguments", "operation"])
    or (.[0][4:] == ["slots", "arguments", "notebook"])
    or (.[0][4:] == ["slots", "arguments", "workdir"])
    or (.[0][4:] == ["slots", "arguments", "configfile"])
    or (.[0][4:] == ["slots", "arguments", "sweep", "interval_seconds"])
    or (.[0][4:] == ["slots", "bindings", "log_stem"])
    or (.[0][4:] == ["slots", "bindings", "plan_path"])
    or (.[0][4:] == ["slots", "bindings", "log_path"])
    or (.[0][4:] == ["slots", "bindings", "sha256"])
    or (.[0][4:] == ["result", "job_id"])))'''


class NotebookMetadata:
    def __init__(self, path, jq_path="jq", runner=subprocess.run):
        self.path = Path(path)
        self.jq_path = jq_path
        self.runner = runner
        self._signature = None
        self._notebook = None

    def read(self):
        stat = self.path.stat()
        signature = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if signature == self._signature:
            return self._notebook
        proc = self.runner([self.jq_path, "--stream", "-c", _JQ_METADATA, str(self.path)],
                           text=True, capture_output=True, timeout=300)
        if proc.returncode:
            raise ValueError("cannot read sweep notebook metadata: " + proc.stderr[:2000])
        cells = {}
        for line in proc.stdout.splitlines():
            path, value = json.loads(line)
            if len(path) < 5 or path[0] != "cells" or not isinstance(path[1], int):
                raise ValueError("invalid streaming notebook metadata")
            node = cells.setdefault(path[1], {})
            for key in path[4:-1]:
                node = node.setdefault(key, {})
            node[path[-1]] = value
        self._notebook = SimpleNamespace(cells=[SimpleNamespace(metadata={"fungen": cells[key]})
                                               for key in sorted(cells)])
        self._signature = signature
        return self._notebook


def _invoke(command, runner):
    try:
        result = runner(command, text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    return result.returncode == 0, (result.stderr or result.stdout).strip()[:2000]


def run_pass(spec, snapshot, *, runner=subprocess.run):
    """Apply approved rules to exact live pending members in one native snapshot."""
    spec = SweepSpec.model_validate(spec)
    counts = {"memory_changed": 0, "queue_changed": 0, "active_jobs": 0,
              "failures": 0, "scheduler_ok": bool(snapshot.get("scheduler_ok"))}
    if not counts["scheduler_ok"]:
        counts["failures"] = 1
        return counts
    jobs = [job for job in snapshot.get("jobs", {}).values()
            if job.get("membership") and job.get("live") and job.get("kind") != "sweep"]
    counts["active_jobs"] = sum(job.get("status") in {"PEND", "RUN"} for job in jobs)
    pending = sorted((job for job in jobs if job.get("status") == "PEND"),
                     key=lambda job: int(job["job_id"]))
    for job in pending:
        # Match once against this pass's original reservation. A requested A->B
        # and B->C rule set cannot accidentally chain within one pass.
        matched = [rule for rule in spec.memory_remaps
                   if rule.step in {job.get("rule"), job.get("task_kind")}
                   and job.get("memory_reservation_gb") == rule.from_gb]
        if len(matched) > 1:
            counts["failures"] += 1
            continue
        if not matched:
            continue
        from .live_control import update_reservation
        rule = matched[0]
        try:
            requirement = update_reservation(job.get("combined_resreq", ""), rule.to_gb)
        except ValueError:
            counts["failures"] += 1
            continue
        command = ["bmod"]
        if rule.hard_limit_gb is not None:
            command += ["-M", f"{rule.hard_limit_gb}G"]
        command += ["-R", requirement, job["job_id"]]
        okay, _ = _invoke(command, runner)
        counts["memory_changed"] += int(okay)
        counts["failures"] += int(not okay)
    if spec.queue_move:
        move = spec.queue_move
        selected = [job for job in pending if job.get("queue") == move.from_queue][:move.limit]
        for job in selected:
            okay, _ = _invoke(["bmod", "-q", move.to_queue, job["job_id"]], runner)
            counts["queue_changed"] += int(okay)
            counts["failures"] += int(not okay)
    return counts


def run_sweep(plan, *, snapshotter=None, runner=subprocess.run, sleeper=time.sleep, clock=None):
    """Follow future notebook receipts and end after the final workflow job."""
    plan = SweepPlan.model_validate(plan)
    if snapshotter is None:
        from .run_jobs import inspect_jobs
        metadata = NotebookMetadata(plan.notebook, plan.jq_path, runner)
        deployment = SimpleNamespace(run_root=plan.run_root, snakefile=plan.snakefile)
        snapshotter = lambda: inspect_jobs(deployment, metadata.read(), runner=runner)
    clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
    Path(plan.log_path).parent.mkdir(parents=True, exist_ok=True)
    passes = 0
    while True:
        try:
            snapshot = snapshotter()
        except (OSError, ValueError, subprocess.TimeoutExpired):
            snapshot = {"scheduler_ok": False}
        counts = run_pass(plan.spec, snapshot, runner=runner)
        passes += 1
        line = {"timestamp": clock(), "pass": passes, **counts}
        with Path(plan.log_path).open("a") as handle:
            handle.write(json.dumps(line, sort_keys=True) + "\n")
            handle.flush()
        print(json.dumps(line, sort_keys=True), flush=True)
        if not counts["scheduler_ok"]:
            return {"status": "failed", "passes": passes, **counts}
        if plan.spec.interval_seconds == 0 or counts["active_jobs"] == 0:
            return {"status": "failed" if counts["failures"] else "completed", "passes": passes, **counts}
        sleeper(plan.spec.interval_seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        result = run_sweep(load_plan(args.plan, args.sha256))
    except (OSError, ValueError) as error:
        parser.exit(1, f"sweep: {error}\n")
    raise SystemExit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
