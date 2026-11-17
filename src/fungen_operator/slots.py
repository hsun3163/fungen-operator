"""Shared strict field types used by built-in and deployment-provided action schemas."""

import re
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def artifact_path_slot(value: str) -> str:
    # Artifact spellings are part of the saved command. Containment checks
    # resolve paths at execution; a later storage alias must not rewrite history.
    if not re.fullmatch(r"/[A-Za-z0-9_./:+-]+", value):
        raise ValueError("PATH must be absolute and contain only letters, digits, _./:+-")
    return value


def path_slot(value: str) -> str:
    # Canonical sources retain physical path normalization.
    return str(Path(artifact_path_slot(value)).resolve())


def target_slot(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_./][A-Za-z0-9_./:+-]*", value):
        raise ValueError("target must be a rule or file path, never a flag or shell fragment")
    if ".." in Path(value).parts:
        raise ValueError("target cannot traverse above the workspace")
    return value


PathSlot = Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$"), AfterValidator(path_slot)]
ArtifactPathSlot = Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$"), AfterValidator(artifact_path_slot)]
Target = Annotated[str, Field(pattern=r"^[A-Za-z0-9_./][A-Za-z0-9_./:+-]*$"), AfterValidator(target_slot)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]


def executable_slot(value: str) -> str:
    # Preserve venv executable symlinks: resolving them selects the base Python.
    path_slot(value)
    return value


ExecutableSlot = Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$"), AfterValidator(executable_slot)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
