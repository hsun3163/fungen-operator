"""Prepare or grade MWS-01. Workflow execution uses the existing MCP actions."""

import argparse
import copy
import csv
import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

from fungen_operator.notebook import Notebook, active

ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "benchmark/tasks/regression/MWS-01.yaml"
RUN_ROOT = ROOT / "runs/xqtl/benchmarks/mws01"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def task_path(trial=None):
    snapshot = trial / "task.yaml" if trial is not None else None
    return snapshot if snapshot is not None and snapshot.is_file() else TASK_PATH


def task(trial=None):
    return yaml.safe_load(task_path(trial).read_text())


def inputs(spec):
    return ROOT / spec["initial_environment"].get(
        "input_root", "output/sketch_to_plink1/behavioral_fixture")


def expected_config(trial):
    spec = task(trial)
    input_root = inputs(spec)
    path = Path(spec["initial_environment"]["source"], "code/snakemake/config.yaml")
    if sha256(path) != spec["initial_environment"]["source_config_sha256"]:
        raise ValueError("Canonical default config changed; review and version the task first")
    cfg = yaml.safe_load(path.read_text())
    cfg["cwd"] = str(trial / "work")
    cfg["start_from"] = "phenotype_bed"
    cfg["chromosomes"] = spec["declared_outcome"]["chromosomes"]
    cfg["themes"] = [{"name": "SYN", "phenotype_bed": str(input_root / "traits/phenotypes.bed.gz"),
                       "covariate_file": str(input_root / "traits/covariates.cov.gz")}]
    cfg["genotype"] = {"plink_bed": str(input_root / "genotype.bed"), "vcf_files": [], "basename": ""}
    # Upstream RNA inputs are outside this task; keep no legacy MWE bindings.
    cfg["reference"] = {k: "" for k in cfg["reference"]}
    cfg["resources"]["default"].update(threads=1, mem_mb=32768, runtime=60)
    return cfg


def requests(trial):
    spec = task(trial)
    base = {"notebook": str(trial / "operator.ipynb"), "configfile": str(trial / "config.yaml"),
            "workdir": str(trial / "work")}
    output = trial / "work" / spec["declared_outcome"]["output_subdir"]
    run = {**base, "log_dir": str(trial / "logs"),
           "targets": [str(output / name) for name in spec["declared_outcome"]["manifests"]],
           "job_name": "fungen_mws01", "queue": "express", "memory_gb": 32,
           "controller_cores": 1, "workflow_cores": 72, "jobs": 100, "walltime_minutes": 60}
    return {"prepare_config": {"request": base},
            "check_readiness": {"request": {**run, "walltime_minutes": 10}},
            "initiate_run": {"request": run},
            "conclusion": {"request": {**run, "walltime_minutes": 10, "phase": "conclusion"}}}


def prepare(trial):
    """Benchmark-author setup: the operator receives this declared initial config."""
    cfg = expected_config(trial)
    trial.mkdir(parents=True, exist_ok=False)
    (trial / "task.yaml").write_text(TASK_PATH.read_text())
    (trial / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=True))
    (trial / "requests.json").write_text(json.dumps(requests(trial), indent=2) + "\n")
    (trial / "task.sha256").write_text(sha256(trial / "task.yaml") + "\n")
    return {"trial": str(trial), "status": "prepared", "requests": str(trial / "requests.json")}


def partition_checks(source, output, chromosomes, tabix):
    """Compare actual products to the supplied data, independently of job status."""
    with gzip.open(source, "rt") as stream:
        header = stream.readline().rstrip("\n")
        rows = [s.rstrip("\n") for s in stream]
    selected = [s for s in rows if s.split("\t", 1)[0] in chromosomes]
    checks = {}
    for chrom in chromosomes:
        bed = output / f"phenotypes.{chrom}.bed.gz"
        expected = [s for s in selected if s.split("\t", 1)[0] == chrom]
        try:
            with gzip.open(bed, "rt") as stream:
                actual = [s.rstrip("\n") for s in stream]
            checks[f"{chrom}_contents"] = actual == [header, *expected]
            fetched = subprocess.run([str(tabix), str(bed), chrom], check=True,
                                     capture_output=True, text=True).stdout.splitlines()
            checks[f"{chrom}_index"] = fetched == expected
        except (OSError, EOFError, subprocess.CalledProcessError):
            checks[f"{chrom}_contents"] = False
            checks[f"{chrom}_index"] = False
    expected_files = {(c.removeprefix("chr"), str(output / f"phenotypes.{c}.bed.gz")) for c in chromosomes}
    coordinates = [s.split("\t")[:4] for s in selected]
    expected_regions = {(*row, str(output / f"phenotypes.{row[0]}.bed.gz")) for row in coordinates}
    for name, expected, fields in [
        ("phenotypes.phenotype_by_chrom_files.txt", expected_files, ["#id", "#dir"]),
        ("phenotypes.phenotype_by_chrom_files.region_list.txt", expected_regions, ["#chr", "start", "end", "ID", "path"]),
    ]:
        try:
            with (output / name).open() as stream:
                reader = csv.DictReader(stream, delimiter="\t")
                actual = [tuple(row[f] for f in fields) for row in reader]
            checks[name] = set(actual) == expected and len(actual) == len(expected)
        except (OSError, KeyError, TypeError):
            checks[name] = False
    return checks, len(header.split("\t")) - 4, len(selected)


def protected_config(cfg):
    value = copy.deepcopy(cfg)
    value.pop("resources", None)  # Exposed operational resource changes are allowed.
    return value


def grade(trial):
    spec = task(trial)
    input_root = inputs(spec)
    source = Path(spec["initial_environment"]["source"])
    outcome = spec["declared_outcome"]
    output = trial / "work" / outcome["output_subdir"]
    g1, samples, phenotypes = partition_checks(input_root / "traits/phenotypes.bed.gz", output,
        outcome["chromosomes"], Path(spec["initial_environment"]["runtime"], "bin/tabix"))
    g1["counts"] = samples == outcome["samples"] and phenotypes == outcome["phenotypes"]
    g2 = {"task_revision": (trial / "task.sha256").read_text().strip() == sha256(task_path(trial)),
          "protected_configuration": protected_config(yaml.safe_load((trial / "config.yaml").read_text()))
              == protected_config(expected_config(trial))}
    for root, hashes, label in [(input_root, spec["input_sha256"], "input"), (source, spec["source_sha256"], "source")]:
        for name, expected in hashes.items():
            path = root / name
            g2[f"{label}:{name}"] = path.is_file() and sha256(path) == expected
    g3 = {}
    try:
        cells = active(Notebook(str(trial / "operator.ipynb")).read())
        g2["notebook_valid"] = bool(cells)
        g3["sequence"] = [c.metadata.fungen.action for c in cells] == [
            "prepare_config", "check_readiness", "initiate_run", "check_readiness"]
        g3["results"] = [c.metadata.fungen.status for c in cells] == [
            "materialized", "ready", "submitted", "nothing_to_do"]
        req = requests(trial)["initiate_run"]["request"]
        for c in cells:
            m = c.metadata.fungen
            if m.action != "prepare_config":
                g2[f"bindings:{c.id}"] = (m.slots.arguments.targets == req["targets"]
                    and m.slots.arguments.workdir == req["workdir"]
                    and m.slots.bindings.snakefile == str(source / "code/snakemake/Snakefile")
                    and m.slots.bindings.profile_path == str(source / "code/snakemake/profiles/lsf")
                    and m.slots.bindings.conda_env == spec["initial_environment"]["runtime"])
    except (ValueError, KeyError, OSError, AttributeError):
        g2["notebook_valid"] = False
        g3["sequence"] = False
    groups = {"G1_outcome": g1, "G2_recorded_contract": g2, "G3_milestones": g3}
    return {"task_id": spec["task_id"], "revision": spec["revision"], "trial": str(trial), "kind": "reference_validation",
            "checks": groups, "joint_pass": all(all(g.values()) for g in groups.values()),
            "samples": samples, "phenotypes": phenotypes,
            "limitation": "External unrecorded actions require separate trajectory review."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "grade"])
    parser.add_argument("--trial", required=True, help="New trial name under runs/xqtl/benchmarks/mws01")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.trial):
        parser.error("trial name must contain only letters, digits, underscore, or hyphen")
    trial = RUN_ROOT / args.trial
    result = prepare(trial) if args.action == "prepare" else grade(trial)
    print(json.dumps(result, indent=2))
    if args.action == "grade" and not result["joint_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
