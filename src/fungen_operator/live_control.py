"""Typed, approval-bound control of an exact set of this notebook's jobs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .sweep import SweepSpec

JobID = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,15}$")]
MemoryGB = Annotated[int, Field(ge=1, le=1000)]


class Selector(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["dead_child_wrappers", "pending", "step"]
    queue: Literal["premium", "express"] | None = None
    min_pending_minutes: Annotated[int, Field(ge=0, le=525600)] | None = None
    step: Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")] | None = None
    memory_reservation_gb: MemoryGB | None = None

    @model_validator(mode="after")
    def complete(self):
        if self.kind == "pending":
            if self.queue is None or self.min_pending_minutes is None:
                raise ValueError("pending requires queue and min_pending_minutes")
            if self.step is not None or self.memory_reservation_gb is not None:
                raise ValueError("pending takes no step filters")
        elif self.kind == "step":
            if self.step is None or self.memory_reservation_gb is None:
                raise ValueError("step requires step and memory_reservation_gb")
            if self.queue is not None or self.min_pending_minutes is not None:
                raise ValueError("step takes no pending filters")
        elif any(value is not None for value in (
                self.queue, self.min_pending_minutes, self.step, self.memory_reservation_gb)):
            raise ValueError("dead_child_wrappers takes no filters")
        return self


class ControlRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    notebook: Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$")]
    operation: Literal["kill", "switch_queue", "modify", "sweep"]
    job_ids: Annotated[list[JobID], Field(min_length=1, max_length=20000)] | None = None
    selector: Selector | None = None
    queue: Literal["premium", "express"] | None = None
    memory_reservation_gb: MemoryGB | None = None
    memory_limit_gb: MemoryGB | None = None
    walltime_minutes: Annotated[int, Field(ge=1, le=8640)] | None = None
    cores: Annotated[int, Field(ge=1, le=512)] | None = None
    sweep: SweepSpec | None = None
    dead_child_grace_minutes: Annotated[int, Field(ge=0, le=10080)] = 10

    @field_validator("notebook")
    @classmethod
    def resolve_notebook(cls, value):
        return str(Path(value).resolve())

    @model_validator(mode="after")
    def selection(self):
        modifications = (self.memory_reservation_gb, self.memory_limit_gb,
                         self.walltime_minutes, self.cores)
        if self.operation == "sweep":
            if self.sweep is None:
                raise ValueError("sweep requires its rule set")
            if self.job_ids is not None or self.selector is not None:
                raise ValueError("sweep uses its rule set rather than a job selection")
            if self.queue is not None or any(value is not None for value in modifications):
                raise ValueError("sweep resource settings belong in its rule set")
            return self
        if self.sweep is not None:
            raise ValueError("only sweep accepts a rule set")
        if (self.job_ids is None) == (self.selector is None):
            raise ValueError("supply either job_ids or selector")
        if self.job_ids and len(self.job_ids) != len(set(self.job_ids)):
            raise ValueError("job_ids must be unique")
        if self.operation == "modify":
            if self.queue is None and all(value is None for value in modifications):
                raise ValueError("modify requires at least one resource setting")
        else:
            if any(value is not None for value in modifications):
                raise ValueError("only modify accepts resource settings")
            if (self.operation == "switch_queue") != (self.queue is not None):
                raise ValueError("only switch_queue requires a destination queue")
        return self


def update_reservation(requirement: str, memory_gb: int) -> str:
    """Replace the one native rusage.mem value and retain all other constraints.

    Compound or missing memory requests require a new explicit review rather
    than guessing how LSF would combine or replace resource requirements.
    """
    if type(memory_gb) is not int or not 1 <= memory_gb <= 1000:
        raise ValueError("memory reservation must be an integer from 1 to 1000 GB")
    if not isinstance(requirement, str) or not requirement.strip() or any(
            marker in requirement for marker in ("\x00", "\r", "\n")):
        raise ValueError("a retained native resource requirement is required")
    clauses = list(re.finditer(r"\brusage\[([^\[\]]*)\]", requirement))
    if len(clauses) != 1 or len(re.findall(r"\brusage\s*\[", requirement)) != 1:
        raise ValueError("resource requirement must contain exactly one rusage clause")
    clause = clauses[0]
    memory = list(re.finditer(
        r"(?<![A-Za-z0-9_])mem\s*=\s*([0-9]+(?:\.[0-9]+)?(?:[KMGT](?:B)?)?)(?=\s*(?:[:,\]]|$))",
        clause.group(1), re.I))
    if len(memory) != 1 or len(re.findall(r"(?<![A-Za-z0-9_])mem\s*=", clause.group(1))) != 1:
        raise ValueError("resource requirement must contain exactly one rusage mem value")
    start, end = memory[0].span(1)
    start += clause.start(1)
    end += clause.start(1)
    return requirement[:start] + f"{memory_gb}G" + requirement[end:]


def _resolved(request: ControlRun, job_ids: list[str]) -> ControlRun:
    # Validate bindings too: notebook edits never turn into arbitrary shell text.
    return ControlRun.model_validate({**request.model_dump(), "job_ids": job_ids, "selector": None})


def modify_commands(request: ControlRun, job_ids: list[str],
                    resource_requirements: dict[str, str] | None = None) -> list[list[str]]:
    resolved = _resolved(request, job_ids)
    if resolved.operation != "modify":
        raise ValueError("modify_commands requires operation modify")
    if resolved.memory_reservation_gb is not None:
        if not isinstance(resource_requirements, dict) or set(resource_requirements) != set(job_ids):
            raise ValueError("memory modification requires each job's frozen native resource requirement")
        groups: dict[str | None, list[str]] = {}
        for job_id in job_ids:
            updated = update_reservation(resource_requirements[job_id], resolved.memory_reservation_gb)
            groups.setdefault(updated, []).append(job_id)
    else:
        if resource_requirements is not None:
            raise ValueError("resource requirements are bound only for memory reservation changes")
        groups = {None: list(job_ids)}
    result = []
    for requirement, ids in groups.items():
        args = ["bmod"]
        if requirement is not None:
            args += ["-R", requirement]
        if resolved.memory_limit_gb is not None:
            args += ["-M", f"{resolved.memory_limit_gb}G"]
        if resolved.walltime_minutes is not None:
            args += ["-W", str(resolved.walltime_minutes)]
        if resolved.cores is not None:
            args += ["-n", str(resolved.cores)]
        if resolved.queue is not None:
            args += ["-q", resolved.queue]
        result.append(args + ids)
    return result


def commands(request: ControlRun, job_ids: list[str],
             resource_requirements: dict[str, str] | None = None) -> list[list[str]]:
    if request.operation == "modify":
        return modify_commands(request, job_ids, resource_requirements)
    if request.operation == "sweep":
        raise ValueError("sweep uses its retained submission command")
    if resource_requirements is not None:
        raise ValueError("resource requirements are bound only for memory reservation changes")
    resolved = _resolved(request, job_ids)
    return [(["bkill"] if resolved.operation == "kill" else ["bswitch", resolved.queue]) + resolved.job_ids]


def command(request: ControlRun, job_ids: list[str]) -> list[str]:
    """Return the legacy single command or a modify command without grouping."""
    result = commands(request, job_ids)
    if len(result) != 1:
        raise ValueError("control requires multiple native commands")
    return result[0]


def render_control(slots):
    import shlex

    request = ControlRun.model_validate(slots["arguments"])
    if request.operation == "sweep":
        from .sweep_cell import render_sweep
        return render_sweep(request, slots["bindings"])
    expected = {"job_ids"}
    if request.operation == "modify" and request.memory_reservation_gb is not None:
        expected.add("resource_requirements")
    if set(slots["bindings"]) != expected:
        raise ValueError("invalid control bindings")
    argv = commands(request, slots["bindings"]["job_ids"], slots["bindings"].get("resource_requirements"))
    return "%%bash\nset -eo pipefail\n" + "\n".join(shlex.join(args) for args in argv) + "\n"


def approval_fingerprint(arguments, bindings):
    from .actions import digest

    return digest({"arguments": arguments, "bindings": bindings})
