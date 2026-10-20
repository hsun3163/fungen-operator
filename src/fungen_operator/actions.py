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


from .slots import (Model, PathSlot, Target, Identifier, ExecutableSlot, path_slot, target_slot)


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
    depends_on: Annotated[list[Annotated[str, Field(pattern=r"^[1-9][0-9]{0,19}$")]],
                          Field(max_length=32)] = Field(default_factory=list)
    defer_readiness: bool = False


class InspectRun(Model):
    notebook: PathSlot
    paths: list[PathSlot] = Field(default_factory=list)
    max_bytes: Annotated[int, Field(ge=1, le=100000)] = 10000
    dead_child_grace_minutes: Annotated[int, Field(ge=0, le=10080)] = 10


# Loaded after base slot types so capability schemas share the same validation.

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
    # Study names are data, while each study's fields retain a registered schema.
    mapping_parameters: dict[str, dict[str, JsonValue]] = Field(default_factory=dict)

    # Native workflows may keep generated work alongside their source. Each
    # writable file/directory is explicitly registered by the deployment.
    native_run_paths: list[PathSlot] = Field(default_factory=list)
    canonical_source_paths: list[PathSlot] = Field(default_factory=list)

    def source_paths(self):
        return [self.snakefile, self.default_config, self.profile_path,
                str(Path(self.repository, ".git")), *self.canonical_source_paths]

    def validate_write_path(self, path):
        if (not any(inside(path, root) for root in [self.run_root, *self.native_run_paths])
                or any(inside(path, source) for source in self.source_paths())):
            raise ValueError("write path must belong to run_root or declared native run paths outside canonical source")

    def validate_layout(self):
        if inside(self.run_root, self.repository) or inside(self.repository, self.run_root):
            raise ValueError("run_root and canonical repository must be disjoint")
        for root in self.native_run_paths:
            if not inside(root, self.repository):
                raise ValueError("native run paths must belong to canonical repository")
            if any(inside(root, source) or inside(source, root) for source in self.source_paths()):
                raise ValueError("native run paths must be disjoint from canonical source paths")
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
            if value:
                # The repository itself is a working directory, never a write grant.
                if name == "workdir" and self.native_run_paths and value == self.repository:
                    continue
                self.validate_write_path(value)
        if args.notebook == args.configfile:
            raise ValueError("notebook and configfile must differ")
        if isinstance(args, RunSlots):
            if isinstance(args, InitiateRun) and args.defer_readiness and not args.depends_on:
                raise ValueError("deferred readiness requires native LSF prerequisites")
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
            exemplar = self.parameter_exemplar(defaults, key)
            validate_value(value, exemplar, key, self.mapping_parameters)
            if key == "cwd" and value != args.workdir:
                raise ValueError("cwd is bound to workdir")
            # Executable/source selectors belong to the registered runtime.
            if key in {"modular_script_dir", "sos_bin", "python_bin", "rscript_bin"}:
                if value != exemplar:
                    raise ValueError(f"{key} requires a developer-registered runtime")
            set_parameter(cfg, key, value, create=True)
        if "cwd" in defaults:
            cfg["cwd"] = args.workdir
        for selector in ("modular_script_dir", "sos_bin", "python_bin", "rscript_bin"):
            if selector in cfg and cfg[selector] != defaults.get(selector):
                raise ValueError(f"{selector} requires a developer-registered runtime")
        return cfg, self.scientific_diff(baseline, cfg)

    def parameter_exemplar(self, defaults, key):
        for prefix, schema in self.mapping_parameters.items():
            if key == prefix:
                return get_parameter(defaults, key)
            if key.startswith(prefix + "."):
                member, _, field = key[len(prefix) + 1:].partition(".")
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", member):
                    raise ValueError(f"invalid mapping member: {member}")
                return get_parameter(schema, field) if field else schema
        return get_parameter(defaults, key)

    def validate_config(self, config):
        validate_value(config, self.defaults(), "configuration", {
            "configuration." + key: schema for key, schema in self.mapping_parameters.items()
        })

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
        # Enumerate the deployment's source catalog ourselves. In a nested Git
        # checkout, `ls-files --others` walks enormous untracked result trees even
        # when its pathspec looks bounded. Never use it for implementation identity.
        repository = Path(self.repository)
        interfaces = {Path(self.snakefile), Path(self.default_config)}
        interfaces.update(p for p in Path(self.profile_path).rglob("*") if p.is_file())
        interfaces.update(p for p in (repository / "pipeline").glob("*.ipynb") if p.is_symlink())
        sources = {str(p): p for p in interfaces}
        for name in self.canonical_source_paths:
            root = Path(name)
            if not root.exists():
                raise ValueError(f"missing declared source: {root}")
            for p in ([root] if root.is_file() else root.rglob("*")):
                if p not in interfaces and p.is_file():
                    key = p.relative_to(repository).as_posix() if p.is_relative_to(repository) else str(p)
                    sources[key] = p
        fingerprints = {}
        for name, p in sorted(sources.items()):
            if any(inside(p, root) for root in self.native_run_paths):
                continue
            sha = hashlib.sha256()
            with p.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    sha.update(block)
            fingerprints[name] = sha.hexdigest()
        # Git receives literal, existing source FILES, never a directory or '.'.
        relative_files = sorted({p.relative_to(repository).as_posix() for p in sources.values()
                                 if p.is_relative_to(repository) and
                                 not any(inside(p, root) for root in self.native_run_paths)})
        specs = [":(literal)" + name for name in relative_files]
        names = git("diff", "--name-only", "HEAD", "-z", "--", *specs).split("\0")
        tracked = set(git("ls-files", "--cached", "-z", "--", *specs).split("\0"))
        diff_names = [name for name in names if name and
                      (Path(name).suffix in {".smk", ".py", ".R", ".r", ".yaml", ".yml", ".sh"}
                       or Path(name).name == "Snakefile")]
        return {"repository": self.repository, "commit": git("rev-parse", "HEAD"),
                "dirty": any(names) or bool(set(relative_files) - tracked),
                "dirty_diff": git("diff", "HEAD", "--", *[":(literal)" + n for n in diff_names]) if diff_names else "",
                "source_scope": [self.snakefile, self.default_config, self.profile_path, *self.canonical_source_paths],
                "source_hashes": fingerprints, "snakefile": self.snakefile,
                "profile": self.profile_path, "runtime": self.conda_env,
                "runtime_activation_sha256": hashlib.sha256(Path(self.conda_sh).read_bytes()).hexdigest(),
                "backend": self.backend, "mapping_parameters": copy.deepcopy(self.mapping_parameters)}


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


def validate_value(value, exemplar, key, mapping_parameters=None):
    if isinstance(exemplar, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        for k, v in value.items():
            if key in (mapping_parameters or {}):
                if not isinstance(k, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", k):
                    raise ValueError(f"invalid mapping member: {k}")
                validate_value(v, mapping_parameters[key], f"{key}.{k}", mapping_parameters)
                continue
            if k not in exemplar:
                raise ValueError(f"unregistered canonical parameter: {key}.{k}")
            validate_value(v, exemplar[k], f"{key}.{k}", mapping_parameters)
    elif isinstance(exemplar, list):
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        for v in value:
            if exemplar:
                validate_value(v, exemplar[0], key, mapping_parameters)
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
    dependency = ("\n#BSUB -w \"" + " && ".join(f"done({job})" for job in args.depends_on) + "\""
                  if isinstance(args, InitiateRun) and args.depends_on else "")
    workflow_command = f'''python -m snakemake \\
  --snakefile {q(b['snakefile'])} \\
  --configfile {q(args.configfile)} \\
  --profile {q(b['profile_path'])} \\
  --cores {args.workflow_cores} --jobs {args.jobs} \\
  --latency-wait {args.latency_wait} \\
{execution_options}  --printshellcmds{{tail}} \\
  {' '.join(q(t) for t in args.targets)}'''
    preflight = (workflow_command.format(tail=" --dry-run") + "\n"
                 if isinstance(args, InitiateRun) and args.defer_readiness else "")
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
#BSUB -M {args.memory_gb}GB{dependency}
#BSUB -oo {b['log_stem']}.%J.out
#BSUB -eo {b['log_stem']}.%J.err
set -eo pipefail
source {q(b['conda_sh'])}
conda activate {q(b['conda_env'])}
export PATH="{b['conda_env']}/bin:$PATH"
hash -r
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd {q(args.workdir)}
{preflight}{workflow_command.format(tail=tail)}
LSF
'''
