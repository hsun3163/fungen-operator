"""One supervision pass over the runs assigned in a JSON state file.

A trigger (``container/supervise.lsf`` or a cron line) runs this about hourly on
the host. Each pass inspects every watched run through the same harness as the
MCP tools and does one of four things:

- leaves a pending or running run alone;
- records verified completion, from a workflow-native conclusion check;
- resumes a controller that hit its time limit (readiness, then the same
  ``initiate_run``, walltime raised only up to the ceiling set at assignment);
- stops on anything else and records the reason and the next action.

State-changing steps are ordinary notebook actions. The state file holds only
the assignments, their status and a short event record.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .actions import CheckReadiness, InitiateRun, InspectRun, RunSlots
from .notebook import Notebook, active, now, recipe_key

WATCHING, COMPLETED, BLOCKED = "watching", "completed", "blocked"
EXIT_NOTHING_WATCHED, EXIT_BUSY = 3, 4
RUNNING = {"RUN", "PEND", "PSUSP", "USUSP", "SSUSP", "WAIT"}
ENDED = {"DONE", "EXIT"}
UNKNOWN_LIMIT = 3
EVENT_LIMIT = 200

TIME_LIMIT = re.compile(r"TERM_RUNLIMIT|DUE TO TIME LIMIT")
PERMISSION = re.compile(r"permission denied|PermissionError|not authorized", re.I)
FAILURE = re.compile(r"Error in rule|Traceback|Exception|Error:|error:")

NEXT_ACTION = {
    "not_submitted": "Submit the run with initiate_run, then assign the notebook again.",
    "uncertain_submission": "The latest submission has no confirmed scheduler receipt. Check the "
                            "scheduler for its log stem before anything is resubmitted; inspect_run "
                            "records a receipt it can prove. Then assign the notebook again.",
    "not_verified": "The run's child jobs cannot be verified. Run fungen-operator inspect, resolve "
                    "the coverage gap it reports, then assign the notebook again.",
    "scheduler_unknown": "The scheduler has not reported the controller's state for several checks. "
                         "Inspect the run, then assign the notebook again.",
    "source_changed": "The workflow source, runtime or deployment changed after this run was "
                      "submitted. Resuming would mix implementations, so decide yourself whether to "
                      "repeat check_readiness and initiate_run under the new source.",
    "permission": "Fix access to the path or account named in the error, then assign the "
                  "notebook again.",
    "workflow_error": "A workflow step failed. A person needs to read the failing step's log; a "
                      "source defect goes to the workflow developer. Assign the notebook again "
                      "after the fix.",
    "unexplained": "The controller ended for a reason supervision does not repair. Inspect the "
                   "run with inspect_run and decide how to continue.",
    "attempt_limit": "Recovery ran the allowed number of times without finishing. Review the "
                     "attempts in the notebook; assign again (optionally with a higher "
                     "--max-attempts or --max-walltime-minutes) to allow more.",
    "check_failed": "A readiness or conclusion check did not succeed. Inspect its cell in the "
                    "notebook, then assign the notebook again.",
    "refused": "The operator refused the step. Resolve the reason with the operator tools (for "
               "example prepare_config after a configuration change), then assign again.",
}


@contextmanager
def _lock(state_path, *, wait):
    with open(str(state_path) + ".lock", "a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        yield True


def load(state_path):
    path = Path(state_path)
    return json.loads(path.read_text()) if path.exists() else {"runs": {}}


def save(state_path, state):
    path = Path(state_path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".supervision-")
    with os.fdopen(fd, "w") as stream:
        json.dump(state, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, path)


def watching(state_path):
    return any(run["status"] == WATCHING for run in load(state_path)["runs"].values())


def _event(run, **fields):
    run.setdefault("events", []).append({"time": now(), **fields})
    del run["events"][:-EVENT_LIMIT]


def assign(deployment, state_path, notebook, *, max_attempts=3, max_walltime_minutes=None):
    """Watch a notebook's run. Re-assigning a blocked or finished run re-arms it."""
    notebook = str(Path(notebook).resolve())
    deployment.validate_write_path(state_path)
    deployment.validate_write_path(notebook)
    with _lock(state_path, wait=True):
        state = load(state_path)
        run = state["runs"].setdefault(notebook, {})
        run.update(status=WATCHING, max_attempts=max_attempts,
                   max_walltime_minutes=max_walltime_minutes, attempts=0, unknown_checks=0)
        run.pop("blocker", None)
        run.pop("report", None)
        _event(run, decision="assigned", max_attempts=max_attempts,
               max_walltime_minutes=max_walltime_minutes)
        save(state_path, state)
    return run


def supervise(harness, state_path):
    """Run one pass. Returns (exit code, per-notebook decisions)."""
    harness.deployment.validate_write_path(state_path)
    with _lock(state_path, wait=False) as acquired:
        if not acquired:
            return EXIT_BUSY, {"status": "busy", "reason": "another supervision pass holds the lock"}
        state = load(state_path)
        decisions = {}
        for notebook, run in state["runs"].items():
            if run["status"] != WATCHING:
                continue
            def progress(**fields):
                _event(run, **fields)
                save(state_path, state)
            try:
                decision = check(harness, notebook, run, progress)
            except PermissionError as exc:
                decision = blocked("permission", str(exc))
            except (ValueError, OSError, RuntimeError) as exc:
                live = re.match(r"controller (\S+) is (\w+); inspect before changing the run", str(exc))
                decision = ({"decision": "left_alone", "reason": str(exc)} if live and live[2] in RUNNING
                            else blocked("refused", str(exc)))
            if decision["decision"] == "blocked":
                run.update(status=BLOCKED, blocker={k: decision[k] for k in ("kind", "reason", "next_action")})
            elif decision["decision"] == "completed":
                run.update(status=COMPLETED, report=decision["report"])
            run["last_check"] = now()
            _event(run, **decision)
            save(state_path, state)
            decisions[notebook] = decision
        code = 0 if any(r["status"] == WATCHING for r in state["runs"].values()) else EXIT_NOTHING_WATCHED
        return code, decisions


def blocked(kind, reason):
    return {"decision": "blocked", "kind": kind, "reason": reason, "next_action": NEXT_ACTION[kind]}


def _plain(node):
    return json.loads(json.dumps(node))


def diagnose(text):
    """Return the class and line of the decisive native error in controller logs."""
    lines = text.splitlines()
    for kind, pattern in (("time_limit", TIME_LIMIT), ("permission", PERMISSION), ("workflow_error", FAILURE)):
        line = next((line.strip() for line in lines if pattern.search(line)), None)
        if line:
            return kind, line[:2000]
    return "unexplained", None


def check(harness, notebook, run, progress):
    nb = Notebook(notebook, harness.registry).read()
    current = {recipe_key(c.metadata.fungen): c for c in active(nb)}
    conclusion = current.get("check_readiness:conclusion")
    if conclusion is not None and conclusion.metadata.fungen.status == "nothing_to_do":
        return completed(notebook, conclusion, run)
    submissions = [c for c in nb.cells if c.metadata.get("fungen", {}).get("action") == "initiate_run"]
    if not submissions:
        return blocked("not_submitted", "The notebook has no initiate_run.")
    latest = max(submissions, key=lambda c: c.metadata.fungen.sequence)

    observed = harness.inspect(InspectRun(notebook=notebook))
    entry = next(e for e in observed["cells"] if e["cell_id"] == latest.id)
    job = entry["result"].get("job_id")
    if entry["status"] in {"prepared", "host_approval_required", "executing", "unknown"}:
        return blocked("uncertain_submission", f"Submission cell {latest.id} is {entry['status']}.")
    if job is None and entry["status"] != "completed":
        return blocked("check_failed", f"Submission cell {latest.id} is {entry['status']} without a job.")
    state = entry.get("scheduler", {}).get("status", "DONE") if job else "DONE"
    if state in RUNNING:
        run["unknown_checks"] = 0
        return {"decision": "left_alone", "reason": f"controller {job} is {state}"}
    children = sorted(f"{j} {r['status']}" for j, r in observed["jobs"].items()
                      if j != str(job) and r.get("status") in RUNNING)
    if children:
        return {"decision": "left_alone", "reason": "run jobs still active: " + ", ".join(children)}
    if state not in ENDED:
        run["unknown_checks"] = run.get("unknown_checks", 0) + 1
        if run["unknown_checks"] >= UNKNOWN_LIMIT:
            return blocked("scheduler_unknown", f"controller {job} is {state} for {run['unknown_checks']} checks")
        return {"decision": "left_alone", "reason": f"controller {job} is {state}; checking again next pass"}
    run["unknown_checks"] = 0
    if observed["inspection_status"] == "not_verified":
        return blocked("not_verified", "; ".join(map(str, observed["scheduler_observations"])) or "coverage not verified")

    submitted = _plain(latest.metadata.fungen.slots.arguments)
    readiness = {k: v for k, v in submitted.items() if k in RunSlots.model_fields}
    earlier = [c for c in nb.cells if c.metadata.get("fungen", {}).get("action") == "check_readiness"]
    recorded = _plain(max(earlier, key=lambda c: c.metadata.fungen.sequence).metadata.fungen.slots.arguments) if earlier else {}
    readiness.update(walltime_minutes=recorded.get("walltime_minutes", 60),
                     job_name=recorded.get("job_name", readiness["job_name"]))

    final = harness.run("check_readiness", CheckReadiness(**readiness, phase="conclusion"))
    if final["status"] == "nothing_to_do":
        nb = Notebook(notebook, harness.registry).read()
        return completed(notebook, next(c for c in nb.cells if c.id == final["cell_id"]), run)
    if final["status"] != "ready":
        return blocked("check_failed", f"Conclusion check {final['cell_id']} returned {final['status']}.")

    if latest.metadata.fungen.identity != harness.deployment.identity():
        return blocked("source_changed", f"Implementation identity differs from submission cell {latest.id}.")
    logs = entry.get("logs", {})
    text = "\n".join([*(str(v) for v in logs.values()), str(observed["jobs"].get(str(job), {}).get("exit_reason", ""))])
    kind, line = diagnose(text)
    if kind != "time_limit":
        return blocked(kind, line or f"controller {job} ended {state} with work remaining and no decisive error in its logs")
    if run["attempts"] >= run["max_attempts"]:
        return blocked("attempt_limit", f"{run['attempts']} recoveries; last error: {line}")

    old = submitted["walltime_minutes"]
    ceiling = min(run.get("max_walltime_minutes") or old, 720 if submitted["queue"] == "express" else 8640)
    walltime = max(old, min(2 * old, ceiling))
    run["attempts"] += 1
    progress(decision="recovering", error=line, controller=job, walltime_minutes=walltime, attempt=run["attempts"])
    ready = harness.run("check_readiness", CheckReadiness(**readiness))
    if ready["status"] != "ready":
        return blocked("check_failed", f"Readiness check {ready['cell_id']} returned {ready['status']}.")
    resumed = harness.run("initiate_run", InitiateRun(**{**readiness, "walltime_minutes": walltime,
                                                         "job_name": submitted["job_name"]}))
    if resumed["status"] in {"unknown", "executing"}:
        return blocked("uncertain_submission", f"Resubmission cell {resumed['cell_id']} is {resumed['status']}.")
    if resumed["status"] not in {"submitted", "completed"}:
        return blocked("check_failed", f"Resubmission cell {resumed['cell_id']} returned {resumed['status']}.")
    return {"decision": "resumed", "reason": line, "controller": resumed.get("job_id"),
            "walltime_minutes": walltime, "attempt": run["attempts"]}


def completed(notebook, conclusion, run):
    meta = conclusion.metadata.fungen
    report = {"notebook": notebook, "targets": list(meta.slots.arguments.targets),
              "conclusion_cell": conclusion.id, "conclusion_job": meta.get("result", {}).get("job_id"),
              "recoveries": run.get("attempts", 0), "verified": meta.get("finished", now())}
    return {"decision": "completed", "reason": "conclusion check reports nothing to do", "report": report}
