"""Typed action surface, developer-owned deployment, and fixed cell renderer."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import shlex
import subprocess
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, AfterValidator, field_validator

from .live_control import ControlRun, render_control

VERSION = "1"


def path_slot(value: str) -> str:
    # Also safe in #BSUB directives, which are not interpreted by the shell.
    if not re.fullmatch(r"/[A-Za-z0-9_./:+-]+", value):
        raise ValueError("PATH must be absolute and contain only letters, digits, _./:+-")
    return str(Path(value).resolve())


def target_slot(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_./][A-Za-z0-9_./:+-]*", value):
        raise ValueError("target must be a rule or file path, never a flag or shell fragment")
    if ".." in Path(value).parts:
        raise ValueError("target cannot traverse above the workspace")
    return value


PathSlot = Annotated[str, Field(pattern=r"^/[A-Za-z0-9_./:+-]+$"), AfterValidator(path_slot)]
Target = Annotated[str, Field(pattern=r"^[A-Za-z0-9_./][A-Za-z0-9_./:+-]*$"), AfterValidator(target_slot)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class PrepareConfig(Model):
    notebook: PathSlot
    configfile: PathSlot
    workdir: PathSlot
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class RunSlots(Model):
    notebook: PathSlot
    configfile: PathSlot
    workdir: PathSlot
    log_dir: PathSlot
    targets: Annotated[list[Target], Field(min_length=1, max_length=1000)]
    job_name: Identifier = "fungen"
    queue: Literal["premium", "express"] = "premium"
    project: Literal["acc_LOAD"] = "acc_LOAD"
    profile: Literal["canonical_lsf"] = "canonical_lsf"
    runtime: Literal["canonical"] = "canonical"
    controller_cores: Annotated[int, Field(ge=1, le=72)] = 1
    workflow_cores: Annotated[int, Field(ge=1, le=512)] = 72
    memory_gb: Annotated[int, Field(ge=32, le=1000)] = 40
    jobs: Annotated[int, Field(ge=1, le=10000)] = 2000
    sos_j: Annotated[int, Field(ge=1, le=10000)] | None = None
    sos_max_running_jobs: Annotated[int, Field(ge=1, le=10000)] | None = None
    sos_queue: Literal["premium", "express"] | None = None
    latency_wait: Annotated[int, Field(ge=1, le=3600)] = 120
    # Execution policy only; scientific inputs and targets remain in the recipe.
    rerun_triggers: Annotated[
        list[Literal["mtime", "params", "input", "software-env", "code"]],
        Field(min_length=1, max_length=5),
    ] | None = None
    walltime_minutes: Annotated[int, Field(ge=1, le=8640)] = 8640

    @field_validator("rerun_triggers")
    @classmethod
    def unique_rerun_triggers(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("rerun_triggers must be unique")
        return value


class CheckReadiness(RunSlots):
    walltime_minutes: Annotated[int, Field(ge=1, le=8640)] = 60
    phase: Literal["before_run", "conclusion"] = "before_run"


class InitiateRun(RunSlots):
    pass


class InspectRun(Model):
    notebook: PathSlot
    paths: list[PathSlot] = Field(default_factory=list)
    max_bytes: Annotated[int, Field(ge=1, le=100000)] = 10000
    dead_child_grace_minutes: Annotated[int, Field(ge=0, le=10080)] = 10


MODELS = {"prepare_config": PrepareConfig, "check_readiness": CheckReadiness,
          "initiate_run": InitiateRun, "control_run": ControlRun}


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def inside(path: str | Path, root: str | Path) -> bool:
    return Path(path).resolve().is_relative_to(Path(root).resolve())


class Deployment(Model):
    """Chosen by the developer at server startup, never supplied as action arguments."""

    repository: PathSlot
    snakefile: PathSlot
    default_config: PathSlot
    profile_path: PathSlot
    conda_sh: PathSlot
    conda_env: PathSlot
    run_root: PathSlot
    backend: Literal["lsf", "fixture"] = "lsf"
    # Optional canonical fields absent from the example YAML can be registered here.
    parameter_defaults: dict[str, JsonValue] = Field(default_factory=dict)
    operational_parameters: list[str] = Field(default_factory=lambda: ["cwd", "resources"])

    def validate_layout(self):
        if inside(self.run_root, self.repository) or inside(self.repository, self.run_root):
            raise ValueError("run_root and canonical repository must be disjoint")
        if not inside(self.snakefile, self.repository):
            raise ValueError("Snakefile must belong to the canonical repository")
        for field in (self.snakefile, self.default_config, self.profile_path,
                      self.conda_sh, self.conda_env):
            if not Path(field).exists():
                raise ValueError(f"missing deployment path: {field}")

    def validate_arguments(self, args: PrepareConfig | RunSlots):
        self.validate_layout()
        for name in ("notebook", "configfile", "workdir", "log_dir"):
            value = getattr(args, name, None)
            if value and (not inside(value, self.run_root) or inside(value, self.repository)):
                raise ValueError(f"{name} must belong to run_root outside canonical source")
        if args.notebook == args.configfile:
            raise ValueError("notebook and configfile must differ")
        if isinstance(args, RunSlots):
            if args.queue == "express" and args.walltime_minutes > 720:
                raise ValueError("express prototype walltime is at most 12 hours")
            for target in args.targets:
                if target.startswith("/") and not inside(target, args.workdir):
                    raise ValueError("absolute file targets must belong to workdir")

    def defaults(self) -> dict:
        cfg = yaml.safe_load(Path(self.default_config).read_text())
        if not isinstance(cfg, dict):
            raise ValueError("canonical default config must be a mapping")
        for key, value in self.parameter_defaults.items():
            set_parameter(cfg, key, value, create=True)
        return cfg

    def config(self, args: PrepareConfig, previous: dict | None) -> tuple[dict, dict]:
        cfg = copy.deepcopy(previous if previous is not None else self.defaults())
        defaults = self.defaults()
        baseline = copy.deepcopy(cfg)
        keys = sorted(args.parameters)
        if any(b.startswith(a + ".") for a, b in zip(keys, keys[1:])):
            raise ValueError("parameter overrides cannot overlap parent and child paths")
        for key, value in args.parameters.items():
            exemplar = get_parameter(defaults, key)
            validate_value(value, exemplar, key)
            if key == "cwd" and value != args.workdir:
                raise ValueError("cwd is bound to workdir")
            # Executable/source selectors belong to the registered runtime.
            if key in {"modular_script_dir", "sos_bin", "python_bin", "rscript_bin"}:
                if value != exemplar:
                    raise ValueError(f"{key} requires a developer-registered runtime")
            set_parameter(cfg, key, value, create=True)
        cfg["cwd"] = args.workdir
        for selector in ("modular_script_dir", "sos_bin", "python_bin", "rscript_bin"):
            if selector in cfg and cfg[selector] != defaults.get(selector):
                raise ValueError(f"{selector} requires a developer-registered runtime")
        return cfg, self.scientific_diff(baseline, cfg)

    def scientific_diff(self, before, after, prefix=""):
        changes = {}
        if any(prefix == p or prefix.startswith(p + ".") for p in self.operational_parameters):
            return changes
        if isinstance(before, dict) and isinstance(after, dict):
            for key in sorted(before.keys() | after.keys()):
                path = f"{prefix}.{key}" if prefix else key
                changes.update(self.scientific_diff(before.get(key), after.get(key), path))
        elif before != after:
            changes[prefix] = {"before": before, "after": after}
        return changes

    def identity(self) -> dict:
        def git(*args):
            return subprocess.check_output(["git", "-C", self.repository, *args], text=True).strip()
        # Source identities exclude data and generated work. Retain the dirty diff too.
        names = git("diff", "--name-only", "HEAD", "-z").split("\0")
        untracked = git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
        fingerprints = {}
        interfaces = [self.snakefile, self.default_config]
        interfaces += [str(p) for p in Path(self.profile_path).rglob("*") if p.is_file()]
        # A commit identifies unchanged tracked source. Hash dirty source plus
        # active interfaces and symlinked pipeline implementations, not every
        # historical notebook/output in a large research checkout.
        interfaces += [str(p) for p in Path(self.repository, "pipeline").glob("*.ipynb") if p.is_symlink()]
        for name in sorted(set(names + untracked + interfaces)):
            p = Path(self.repository, name)
            if name and p.is_file() and (p.suffix in {".smk", ".py", ".r", ".R", ".ipynb", ".yml", ".yaml", ".sh"} or p.name == "Snakefile"):
                fingerprints[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return {"repository": self.repository, "commit": git("rev-parse", "HEAD"),
                "dirty": bool(git("status", "--porcelain")),
                "dirty_diff": git("diff", "HEAD", "--", "*.smk", "*.py", "*.R", "*.r", "*.yaml", "*.yml", "*.sh", "*Snakefile"),
                "source_hashes": fingerprints, "snakefile": self.snakefile,
                "profile": self.profile_path, "runtime": self.conda_env,
                "runtime_activation_sha256": hashlib.sha256(Path(self.conda_sh).read_bytes()).hexdigest(),
                "backend": self.backend}


def get_parameter(cfg: dict, key: str):
    node = cfg
    try:
        for part in key.split("."):
            node = node[part]
        return node
    except (KeyError, TypeError) as e:
        raise ValueError(f"unregistered canonical parameter: {key}") from e


def set_parameter(cfg: dict, key: str, value, create=False):
    parts = key.split(".")
    node = cfg
    for part in parts[:-1]:
        if create:
            node = node.setdefault(part, {})
        else:
            node = node[part]
    node[parts[-1]] = copy.deepcopy(value)


def validate_value(value, exemplar, key):
    if isinstance(exemplar, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        for k, v in value.items():
            if k not in exemplar:
                raise ValueError(f"unregistered canonical parameter: {key}.{k}")
            validate_value(v, exemplar[k], f"{key}.{k}")
    elif isinstance(exemplar, list):
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        for v in value:
            if exemplar:
                validate_value(v, exemplar[0], key)
    elif exemplar is not None and type(value) is not type(exemplar):
        if not (type(exemplar) is float and type(value) is int):
            raise ValueError(f"{key} expects {type(exemplar).__name__}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{key} must be finite")
    if isinstance(value, str) and re.search(r"[\x00-\x1f`$;|&<>]", value):
        raise ValueError(f"{key} contains control characters or shell syntax")


def render(action: str, slots: dict) -> str:
    """Pure renderer. Bindings are retained verbatim, so source can be audited later."""
    if action not in MODELS or set(slots) != {"arguments", "bindings"}:
        raise ValueError("unknown action or slot envelope")
    args = MODELS[action].model_validate(slots["arguments"])
    b = slots["bindings"]
    if action == "control_run":
        return render_control(slots)
    if action == "prepare_config":
        if set(b) != {"config_text"}:
            raise ValueError("invalid config bindings")
        return ("from pathlib import Path\nimport os, tempfile\n"
                f"Path({args.workdir!r}).mkdir(parents=True, exist_ok=True)\n"
                f"path = Path({args.configfile!r})\ncontent = {b['config_text']!r}\n"
                "path.parent.mkdir(parents=True, exist_ok=True)\n"
                "if not path.exists() or path.read_text() != content:\n"
                "    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.config-')\n"
                "    with os.fdopen(fd, 'w') as stream:\n        stream.write(content)\n"
                "    os.replace(temporary, path)\n"
                "print(f'Configuration materialized: {path}')\n")
    if set(b) != {"snakefile", "profile_path", "conda_sh", "conda_env", "log_stem"}:
        raise ValueError("invalid runtime bindings")
    for value in b.values():
        path_slot(value)
    q = shlex.quote
    wait = " -K" if action == "check_readiness" else ""
    hours, minutes = divmod(args.walltime_minutes, 60)
    tail = " --dry-run" if action == "check_readiness" else ""
    execution_options = ("  --rerun-triggers " + " ".join(args.rerun_triggers) + " \\\n"
                         if args.rerun_triggers is not None else "")
    # Keep omitted options absent so every retained cell keeps its exact source.
    sos_settings = {name: getattr(args, name) for name in
                    ("sos_j", "sos_max_running_jobs", "sos_queue")
                    if getattr(args, name) is not None}
    if sos_settings:
        sos_settings["sos_config"] = b["log_stem"] + ".sos.yml"
        execution_options += ("  --config " + " ".join(
            q(f"fungen_{name}={value}") for name, value in sos_settings.items()
        ) + " \\\n")
    return f'''%%bash
set -eo pipefail
mkdir -p {q(args.log_dir)} {q(args.workdir)}
bsub{wait} <<'LSF'
#BSUB -J {args.job_name}
#BSUB -P {args.project}
#BSUB -q {args.queue}
#BSUB -W {hours:02d}:{minutes:02d}
#BSUB -n {args.controller_cores}
#BSUB -R "span[hosts=1] rusage[mem={args.memory_gb}GB]"
#BSUB -M {args.memory_gb}GB
#BSUB -oo {b['log_stem']}.%J.out
#BSUB -eo {b['log_stem']}.%J.err
set -eo pipefail
source {q(b['conda_sh'])}
conda activate {q(b['conda_env'])}
export PATH="{b['conda_env']}/bin:$PATH"
hash -r
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd {q(args.workdir)}
python -m snakemake \\
  --snakefile {q(b['snakefile'])} \\
  --configfile {q(args.configfile)} \\
  --profile {q(b['profile_path'])} \\
  --cores {args.workflow_cores} --jobs {args.jobs} \\
  --latency-wait {args.latency_wait} \\
{execution_options}  --printshellcmds{tail} \\
  {' '.join(q(t) for t in args.targets)}
LSF
'''
