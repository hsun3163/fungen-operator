"""Typed, approval-bound control of an exact set of this notebook's jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

JobID = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,15}$")]


class Selector(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["dead_child_wrappers", "pending"]
    queue: Literal["premium", "express"] | None = None
    min_pending_minutes: Annotated[int, Field(ge=0, le=525600)] | None = None

    @model_validator(mode="after")
    def complete(self):
        if self.kind == "pending":
            if self.queue is None or self.min_pending_minutes is None:
                raise ValueError("pending requires queue and min_pending_minutes")
        elif self.queue is not None or self.min_pending_minutes is not None:
            raise ValueError("dead_child_wrappers takes no pending filters")
        return self


class ControlRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    notebook: Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$")]
    operation: Literal["kill", "switch_queue"]
    job_ids: Annotated[list[JobID], Field(min_length=1, max_length=20000)] | None = None
    selector: Selector | None = None
    queue: Literal["premium", "express"] | None = None
    dead_child_grace_minutes: Annotated[int, Field(ge=0, le=10080)] = 10

    @field_validator("notebook")
    @classmethod
    def resolve_notebook(cls, value):
        return str(Path(value).resolve())

    @model_validator(mode="after")
    def selection(self):
        if (self.job_ids is None) == (self.selector is None):
            raise ValueError("supply either job_ids or selector")
        if self.job_ids and len(self.job_ids) != len(set(self.job_ids)):
            raise ValueError("job_ids must be unique")
        if (self.operation == "switch_queue") != (self.queue is not None):
            raise ValueError("only switch_queue requires a destination queue")
        return self


def command(request: ControlRun, job_ids: list[str]) -> list[str]:
    # Validate bindings too: notebook edits never turn into arbitrary shell text.
    resolved = ControlRun.model_validate({**request.model_dump(), "job_ids": job_ids, "selector": None})
    return (["bkill"] if resolved.operation == "kill" else ["bswitch", resolved.queue]) + resolved.job_ids


def render_control(slots):
    import shlex

    request = ControlRun.model_validate(slots["arguments"])
    if set(slots["bindings"]) != {"job_ids"}:
        raise ValueError("invalid control bindings")
    return "%%bash\nset -eo pipefail\n" + shlex.join(command(request, slots["bindings"]["job_ids"])) + "\n"


def approval_fingerprint(arguments, bindings):
    from .actions import digest

    return digest({"arguments": arguments, "bindings": bindings})
