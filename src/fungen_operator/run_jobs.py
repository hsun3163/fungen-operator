"""Read-only reconciliation of a notebook's native Snakemake/SoS/LSF evidence.

Only retained controller receipts, their exact wrapper submission lines, and
job-ID files under exported per-unit SoS homes establish run membership. A
shared working directory by itself never establishes membership.
"""
from __future__ import annotations

from datetime import datetime
import json
import re
import struct
import subprocess
from pathlib import Path

import yaml


_FIELDS = "jobid stat queue submit_time pend_time sub_cwd command job_name user exit_reason output_file error_file"
_SUBMISSION = re.compile(r"Job (\d+) has been submitted with LSF jobid (\d+) \(log: (.+?)\)\.")
_STAGE = {"coloc_abf": "coloc", "otters_test": "twas", "susie_coloc_gene": "susie_coloc",
          "intact_pair": "intact", "otters_weights": "weights",
          "univariate_rss_gwas": "fine_mapped", "univariate_rss_eqtl": "fine_mapped"}
_TERMINAL = {"EXIT", "DONE", "NOT_FOUND"}


def _text(path):
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def _inside(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def _time(value, current):
    if isinstance(value, (float, int)) or str(value).isdigit():
        return float(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%a %b %d %H:%M:%S %Y", "%b %d %H:%M:%S %Y", "%b %d %H:%M"):
        try:
            parsed = datetime.strptime(str(value), fmt)
            if "%Y" not in fmt:
                parsed = parsed.replace(year=datetime.fromtimestamp(current).year)
                if parsed.timestamp() > current + 86400:
                    parsed = parsed.replace(year=parsed.year - 1)
            return parsed.timestamp()
        except ValueError:
            pass
    return None


def _header(path):
    # The fixed SoS 1/2/3 header prefix contains no pickle payload. Reading it
    # neither imports SoS nor changes its records or task status.
    try:
        with Path(path).open("rb") as handle:
            values = struct.unpack("!2h8d", handle.read(68))
        if values[0] not in {1, 2, 3} or values[1] not in range(7):
            return None
        return {"sos_state": ("new", "pending", "submitted", "running", "aborted", "failed", "completed")[values[1]],
                "submitted_time": values[5], "running_time": values[6]}
    except (OSError, struct.error):
        return None


def _unit(log_path):
    parts = Path(log_path).parts
    for index, part in enumerate(parts):
        if part.startswith("rule_") and index + 1 < len(parts):
            rule = part[5:]
            values = dict(re.findall(r"(?:^|\.\.)([a-zA-Z_]+)=([^=]+?)(?=\.\.[a-zA-Z_]+=|$)", parts[index + 1]))
            # Report pair/dataset identity, without regional gene wildcards.
            values = {k: v for k, v in values.items() if k in {"gwas", "eqtl", "dataset", "pair"}}
            return rule, values
    return None, {}


def _task_dir(workdir, config, rule, unit):
    if rule not in _STAGE:
        return None
    output = Path(config.get("outdir", "."))
    if not output.is_absolute():
        output = Path(workdir, output)
    root = output / "results"
    suffix = Path(config.get("ld_meta_pair", "")).stem.replace(".LD_meta.tsv", "")
    stage = _STAGE[rule]
    if rule == "otters_weights" and unit.get("eqtl"):
        runlog = root / "weights" / f"{unit['eqtl']}.{suffix}" / "runlog"
    elif rule.startswith("univariate_rss_"):
        dataset = unit.get("gwas") or unit.get("eqtl")
        if not dataset:
            return None
        runlog = root / f"{dataset}.{suffix}" / "fine_mapped/runlog"
    elif unit.get("gwas") and unit.get("eqtl"):
        runlog = root / f"{unit['gwas']}.{suffix}" / f"{unit['eqtl']}.{suffix}" / stage / "runlog"
    else:
        return None
    return runlog.resolve() / "sos_runtime/home/.sos/tasks"


def _evidence(deployment, nb):
    evidence, homes, observations = {}, {}, []
    task_dirs = {}
    run_root = Path(deployment.run_root).resolve()
    exported = "sos_runtime" in _text(deployment.snakefile) and "COSI_SOS_EXEC_HOME" in _text(deployment.snakefile)
    for cell in nb.cells:
        meta = cell.metadata.get("fungen", {})
        if meta.get("action") not in {"initiate_run", "check_readiness"}:
            continue
        slots, result = meta.get("slots", {}), meta.get("result", {})
        args, bindings = slots.get("arguments", {}), slots.get("bindings", {})
        job_id = str(result.get("job_id", ""))
        if not job_id.isdigit():
            continue
        workdir = args.get("workdir", deployment.run_root)
        if not _inside(workdir, deployment.run_root):
            continue
        stem = bindings.get("log_stem", "")
        if not stem or not _inside(stem, deployment.run_root):
            continue
        evidence[job_id] = {"job_id": job_id, "kind": "controller", "workdir": workdir,
                            "log_stem": stem, "configfile": args.get("configfile", ""),
                            "rule": None, "unit": {}}
        config = yaml.safe_load(_text(args.get("configfile", ""))) or {}
        # Controller LSF streams retain exact Snakemake submission lines, even
        # while the controller is running. Do not claim unrelated .snakemake logs.
        for suffix in ("out", "err"):
            path = Path(f"{stem}.{job_id}.{suffix}")
            if not path.exists():
                continue
            scheduled_time = None
            with path.open(errors="replace") as handle:
                for line in handle:
                    timestamp = re.match(r"^\[([^]]+)\]$", line.strip())
                    if timestamp:
                        scheduled_time = _time(timestamp.group(1), datetime.now().timestamp())
                    match = _SUBMISSION.search(line)
                    if not match:
                        continue
                    internal, wrapper, log_path = match.groups()
                    if ".." in Path(log_path).parts or not Path(log_path).is_relative_to(workdir):
                        continue
                    rule, unit = _unit(log_path)
                    evidence[wrapper] = {"job_id": wrapper, "kind": "wrapper", "controller_job_id": job_id,
                                         "snakemake_job_id": internal, "rule": rule, "unit": unit, "scheduled_time": scheduled_time,
                                         "log_path": log_path, "workdir": workdir}
                    key = (workdir, config.get("outdir"), config.get("ld_meta_pair"), rule, tuple(sorted(unit.items())))
                    if key not in task_dirs:
                        task_dirs[key] = _task_dir(workdir, config, rule, unit) if exported else None
                    task_dir = task_dirs[key]
                    if task_dir and task_dir.is_relative_to(run_root):
                        homes.setdefault(task_dir, []).append(evidence[wrapper])
    for task_dir, wrappers in homes.items():
        # SoS retains .job_id while submitted/running and removes it on completed
        # task packing. This directory-only census avoids decoding task payloads.
        for job_file in sorted(task_dir.glob("*.job_id")):
            if not _inside(job_file, deployment.run_root):
                continue
            task_id = job_file.name[:-7]
            header = _header(task_dir / f"{task_id}.task")
            if header and header["sos_state"] not in {"submitted", "running"}:
                continue
            ids = yaml.safe_load(_text(job_file))
            child = str(ids.get("job_id", "")) if isinstance(ids, dict) else ""
            if not child.isdigit() or not header:
                observations.append({"task_id": task_id, "status": "unresolved_task_record"})
                continue
            # The submission script must name exactly this task; it is executable
            # evidence, read as text only. Its path remains under the isolated home.
            script = _text(task_dir / f"{task_id}.sh")
            if not re.search(r"\bsos\s+execute\s+" + re.escape(task_id) + r"(?:\s|$)", script):
                observations.append({"task_id": task_id, "status": "missing_submission_script"})
                continue
            # Multiple attempts can have wrappers for the same unit. The newest
            # submission preceding this task is the waiting wrapper; live state
            # below selects a still-active wrapper when present.
            wrapper = wrappers[-1]
            evidence[child] = {"job_id": child, "kind": "child", "task_id": task_id,
                               **header, "task_dir": str(task_dir), "runlog": str(task_dir.parents[3]),
                               "wrapper_job_id": wrapper["job_id"], "wrapper_candidates": list(dict.fromkeys(w["job_id"] for w in wrappers)),
                               "rule": wrapper["rule"], "unit": wrapper["unit"], "workdir": wrapper["workdir"]}
    return evidence, observations


def _history(text, ids):
    records = {}
    for match in re.finditer(r"(?ms)^Job <(\d+)>.*?(?=^Job <|\Z)", text):
        job_id = match.group(1)
        if job_id not in ids:
            continue
        body = re.sub(r"\n\s+", " ", match.group(0))
        if "is not found" in body:
            continue
        states = re.findall(r"Status <(\w+)>", body)
        if re.search(r"Done successfully|Completed <done>", body, re.I):
            state = "DONE"
        elif re.search(r"Exited with exit code|Completed <exit>", body, re.I):
            state = "EXIT"
        else:
            state = states[-1] if states else "UNKNOWN"
        reason = re.search(r"(?:Exited with exit code[^;\n.]*|TERM_[A-Z_]+[^;\n]*)", body)
        records[job_id] = {"job_id": job_id, "status": state, "lsf_state": state,
                           "exit_reason": reason.group(0) if reason else "", "live": False}
    return records


def _lineage(child, evidence, jobs):
    candidates = child["wrapper_candidates"]
    if len(candidates) == 1:
        return candidates[0]
    # An older submitted task can survive a wrapper restart. Match the exact
    # task/job submission in its dated engine log, then bind that engine launch
    # to the controller's dated wrapper submission interval. RUN alone cannot
    # distinguish the original wrapper from a later retry for the same unit.
    engine_times = []
    task = re.compile(re.escape(child["task_id"]) + r".*submitted.*(?:job id|job_id)\s+" + re.escape(child["job_id"]) + r"(?:\s|$)")
    for path in Path(child["runlog"]).glob("*.log"):
        stamp = re.match(r"(\d{8}_\d{6})\.", path.name)
        if not stamp:
            continue
        with path.open(errors="replace") as handle:
            if any(task.search(line) for line in handle):
                engine_times.append(datetime.strptime(stamp.group(1), "%Y%m%d_%H%M%S").timestamp())
    # SoS can reset a task's submission header during a later retry while
    # retaining its original .job_id. The header cannot date wrapper lineage.
    # An exact retained task/job submission log is required across retries.
    if not engine_times:
        return None
    reference_time = max(engine_times)
    eligible = []
    for wrapper in candidates:
        when = evidence[wrapper].get("scheduled_time") or jobs.get(wrapper, {}).get("submit_time")
        if not when:
            return None
        if when <= reference_time:
            eligible.append((when, wrapper))
    if not eligible:
        return None
    latest = max(when for when, _ in eligible)
    matches = [wrapper for when, wrapper in eligible if when == latest]
    return matches[0] if len(matches) == 1 else None


def _decisive(child):
    patterns = re.compile(r"permission denied|Lmod has detected|Unable to parse|TERM_[A-Z_]+|Traceback|Error:|error:|command not found|No such file|\bKilled\b|segmentation fault", re.I)
    runlog, task_id, job = Path(child["runlog"]), child["task_id"], child["job_id"]
    for path in (runlog / f"{job}.err", runlog / f"{job}.out",
                 Path(child["task_dir"], f"{task_id}.err"), Path(child["task_dir"], f"{task_id}.out")):
        if path.exists():
            with path.open(errors="replace") as handle:
                for line in handle:
                    if patterns.search(line):
                        return line.strip()[:2000]
    return None


def _membership(evidence, record):
    if not evidence:
        return False, "job ID is absent from this notebook's controller receipts, wrapper submissions and SoS task directories"
    cwd, command = record.get("sub_cwd", ""), record.get("command", "")
    if evidence["kind"] != "controller" and (not cwd or not _inside(cwd, evidence["workdir"])):
        return False, "live submission working directory differs from this run's recorded job evidence"
    output, error = record.get("output_file", ""), record.get("error_file", "")
    if evidence["kind"] == "controller":
        expected = f"{evidence['log_stem']}.{evidence['job_id']}.out"
        command_match = "snakemake" in command and evidence.get("configfile", "") in command and evidence["workdir"] in command
        matched = output == expected or command_match
    elif evidence["kind"] == "wrapper":
        matched = output == evidence["log_path"] or error == evidence["log_path"]
    else:
        matched = (re.search(r"\bsos\s+execute\s+" + re.escape(evidence["task_id"]) + r"(?:\s|$)", command) is not None
                   or evidence["task_dir"] in command)
        # The task's LSF streams may be relative to its exact per-unit runlog.
        matched = matched and Path(cwd).resolve() == Path(evidence["runlog"]).resolve()
    return matched, "live scheduler record matches retained run evidence" if matched else "live command or scheduler output path differs from this run's recorded job evidence"


def inspect_jobs(deployment, nb, *, grace_minutes=10, runner=subprocess.run, now=None, requested_ids=None):
    """Return a single batch snapshot; scheduler failures always fail closed.

    ``jobs`` includes all currently retained jobs for the current LSF user so an
    explicit outside ID gets an auditable membership refusal. Historical records
    are queried only for active SoS children missing from the one bjobs result.
    The caller owns host approval and must run this function outside the sandbox.
    """
    current = datetime.now().timestamp() if now is None else float(now)
    observations = []
    snapshot = {"jobs": {}, "dead_children": [], "count": 0, "observations": observations,
                "scheduler_ok": False, "grace_minutes": grace_minutes}
    try:
        proc = runner(["bjobs", "-a", "-json", "-o", _FIELDS], text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        observations.append({"status": "scheduler_query_failed", "diagnostic": str(error)})
        return snapshot
    try:
        raw = json.loads(proc.stdout)
        records = raw["RECORDS"]
        if proc.returncode or not isinstance(records, list):
            raise ValueError("scheduler returned an unsuccessful response")
    except (ValueError, KeyError, TypeError):
        observations.append({"status": "scheduler_query_failed", "diagnostic": proc.stderr})
        return snapshot
    snapshot["scheduler_ok"] = True
    # An explicit ID outside the run directory can belong only through a saved
    # controller receipt. Refuse these live outsiders before scanning task homes.
    controllers = {str(c.metadata.get("fungen", {}).get("result", {}).get("job_id"))
                   for c in nb.cells if c.metadata.get("fungen", {}).get("action") in
                   {"initiate_run", "check_readiness"}}
    if requested_ids and all(job not in controllers for job in requested_ids):
        selected = {str(r.get("JOBID", r.get("jobid", ""))): r for r in records}
        if all(job not in selected or not _inside(str(selected[job].get("SUB_CWD", selected[job].get("sub_cwd", "/"))), deployment.run_root)
               for job in requested_ids):
            snapshot["jobs"] = {job: {"job_id": job, "membership": False,
                "membership_reason": "live job is outside this run's task directories and controller receipts"}
                for job in requested_ids}
            return snapshot
    evidence, found = _evidence(deployment, nb)
    observations.extend(found)
    jobs = snapshot["jobs"]
    for raw in records:
        row = {str(k).lower(): v for k, v in raw.items()}
        job = str(row.pop("jobid", ""))
        if not job.isdigit():
            continue
        state = str(row.pop("stat", "UNKNOWN"))
        record = {**evidence.get(job, {}), **row, "job_id": job, "status": state,
                  "lsf_state": state, "live": True}
        record["submit_time"] = _time(row.get("submit_time"), current)
        # LSF's accumulated pending seconds survive requeues; elapsed time
        # since initial submission can include earlier running intervals.
        try:
            pending_seconds = float(row["pend_time"])
        except (KeyError, TypeError, ValueError):
            pending_seconds = current - record["submit_time"] if record["submit_time"] else 0
        record["pending_minutes"] = max(0, pending_seconds / 60) if state == "PEND" else 0
        record["membership"], record["membership_reason"] = _membership(evidence.get(job), record)
        jobs[job] = record
    history_ids = {job for job, ev in evidence.items() if ev["kind"] == "controller"}
    for job, ev in evidence.items():
        if ev.get("sos_state") in {"submitted", "running"}:
            history_ids.add(job)
            history_ids.update(ev["wrapper_candidates"])
    missing = sorted(history_ids - jobs.keys(), key=int)
    history = {}
    if missing:
        try:
            proc = runner(["bhist", "-a", "-l", *sorted(missing, key=int)], text=True, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            proc = subprocess.CompletedProcess([], 1, "", str(error))
        history = _history(proc.stdout, missing)
        # bhist's explicit per-ID absence is distinct from command/network errors.
        absent = {m.group(1) for m in re.finditer(r"Job <(\d+)> is not found", proc.stdout + proc.stderr)}
        if re.fullmatch(r"\s*No matching job found\.?\s*", proc.stdout + proc.stderr):
            absent.update(set(missing) - set(history))
        for job in missing:
            if job in history:
                jobs[job] = {**evidence[job], **history[job], "membership": False,
                             "membership_reason": "historical job is absent from live bjobs"}
            elif job in absent:
                jobs[job] = {**evidence[job], "status": "NOT_FOUND", "lsf_state": "NOT_FOUND", "live": False,
                             "membership": False, "membership_reason": "LSF has no record of this retained task submission", "exit_reason": "LSF has no record"}
            else:
                observations.append({"job_id": job, "status": "history_query_unresolved"})
    for job, child in evidence.items():
        if child.get("sos_state") not in {"submitted", "running"}:
            continue
        record = jobs.get(job, {})
        submitted = child["submitted_time"]
        if submitted <= 0 or current - submitted <= grace_minutes * 60 or record.get("status") not in _TERMINAL:
            continue
        wrapper_id = _lineage(child, evidence, jobs)
        if wrapper_id is None:
            observations.append({"task_id": child["task_id"], "status": "wrapper_lineage_unresolved"})
        snapshot["dead_children"].append({"task_id": child["task_id"], "lsf_job_id": job,
            "job_id": job, "lsf_state": record["status"], "exit_reason": record.get("exit_reason", ""),
            "wrapper_job_id": wrapper_id, "rule": child["rule"], "unit": child["unit"],
            "sos_state": child["sos_state"], "submitted_time": submitted,
            "first_error_line": _decisive(child)})
    snapshot["count"] = len(snapshot["dead_children"])
    return snapshot
