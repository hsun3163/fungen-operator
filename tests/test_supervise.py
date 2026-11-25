"""Hourly supervision on the synthetic fixture: real notebook cells, simulated scheduler."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from fungen_operator import supervise
from fungen_operator.actions import CheckReadiness, InitiateRun, PrepareConfig
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, active, verify

ROOT = Path(__file__).resolve().parents[1]
RUNLIMIT = "TERM_RUNLIMIT: job killed after reaching LSF run time limit."


@pytest.fixture
def run(tmp_path):
    """A submitted run whose controller stopped after its first output."""
    deployment = create_fixture(tmp_path / "fixture")
    harness = Harness(deployment)
    root = Path(deployment.run_root)
    paths = dict(notebook=str(root / "operator.ipynb"), configfile=str(root / "config.yaml"),
                 workdir=str(root / "work"))
    harness.prepare_config(harness.propose_config(PrepareConfig(**paths)))
    args = {**paths, "log_dir": str(root / "logs"), "targets": ["all"]}
    harness.run("check_readiness", CheckReadiness(**args))
    state = str(root / "supervision.json")

    def submit(reason=RUNLIMIT, walltime=60):
        Path(deployment.conda_env, "interrupt-next").write_text(reason)
        result = harness.run("initiate_run", InitiateRun(**args, walltime_minutes=walltime))
        assert result["scheduler"]["status"] == "EXIT"
        return result
    submit.args = args
    return harness, deployment, paths, state, submit


def cells(notebook, action):
    """Cells of one action in execution order (the notebook lists active cells first)."""
    return sorted((c for c in Notebook(notebook).read().cells
                   if c.metadata.get("fungen", {}).get("action") == action),
                  key=lambda c: c.metadata.fungen.sequence)


def set_job(deployment, job, status, notebook=None):
    """Make the simulated controller live. The fixture's bsub is synchronous, so
    a live controller also needs the receipt a real bsub records while pending."""
    path = Path(deployment.conda_env, "scheduler.json")
    jobs = json.loads(path.read_text())
    jobs[job]["STAT"] = status
    path.write_text(json.dumps(jobs))
    if notebook:
        import nbformat
        nb = nbformat.read(notebook, as_version=4)
        for cell in nb.cells:
            if cell.metadata.get("fungen", {}).get("result", {}).get("job_id") == job:
                cell.metadata.fungen.result.scheduler.status = "PEND"
        nbformat.write(nb, notebook)


def test_time_limit_is_resumed_without_redoing_work_then_completion_stops(run):
    harness, deployment, paths, state, submit = run
    first = submit()
    supervise.assign(deployment, state, paths["notebook"], max_walltime_minutes=240)
    done = Path(paths["workdir"], "output/result.txt")
    stamp, config = done.stat().st_mtime_ns, Path(paths["configfile"]).read_text()

    code, decisions = supervise.supervise(harness, state)
    decision = decisions[paths["notebook"]]
    assert code == 0 and decision["decision"] == "resumed"
    assert decision["reason"] == RUNLIMIT and decision["walltime_minutes"] == 120
    # Valid work is reused and scientific settings are untouched.
    assert done.stat().st_mtime_ns == stamp
    assert Path(paths["configfile"]).read_text() == config
    resumed = cells(paths["notebook"], "initiate_run")
    assert [c.metadata.fungen.slots.arguments.walltime_minutes for c in resumed] == [60, 120]
    assert resumed[0].metadata.fungen.run_fingerprint == resumed[1].metadata.fungen.run_fingerprint

    # The notebook keeps the interrupted attempt, its log and every executed step.
    nb = Notebook(paths["notebook"]).read()
    verify(nb)
    old = next(c for c in nb.cells if c.id == first["cell_id"])
    assert "superseded" in old.metadata.tags
    assert RUNLIMIT in "".join(o.get("text", "") for o in old.outputs)
    assert [c.metadata.fungen.status for c in cells(paths["notebook"], "check_readiness")] == [
        "ready", "ready", "ready"]

    # A separate process restores the state and verifies completion.
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    deployment_file = str(Path(deployment.run_root).parent / "deployment.json")
    proc = subprocess.run([sys.executable, "-m", "fungen_operator", "supervise", "--deployment",
                           deployment_file, "--state", state], capture_output=True, text=True, env=env)
    assert proc.returncode == supervise.EXIT_NOTHING_WATCHED, proc.stderr
    report = json.loads(proc.stdout)["decisions"][paths["notebook"]]
    assert report["decision"] == "completed"
    saved = json.loads(Path(state).read_text())["runs"][paths["notebook"]]
    assert saved["status"] == "completed" and saved["report"]["recoveries"] == 1
    assert saved["report"]["targets"] == ["all"]
    assert [a.metadata.fungen.action for a in active(Notebook(paths["notebook"]).read())] == [
        "prepare_config", "check_readiness", "initiate_run", "check_readiness"]

    # Monitoring of the completed run has stopped.
    assert supervise.supervise(harness, state) == (supervise.EXIT_NOTHING_WATCHED, {})
    assert not supervise.watching(state)


def test_pass_killed_mid_recovery_restores_state_and_stays_bounded(run, monkeypatch):
    harness, deployment, paths, state, submit = run
    submit()
    supervise.assign(deployment, state, paths["notebook"], max_attempts=1)
    original = harness.run
    def killed(action, args):
        if action == "check_readiness" and args.phase == "before_run":
            raise KeyboardInterrupt  # The trigger job dies after recording the attempt.
        return original(action, args)
    monkeypatch.setattr(harness, "run", killed)
    with pytest.raises(KeyboardInterrupt):
        supervise.supervise(harness, state)
    saved = json.loads(Path(state).read_text())["runs"][paths["notebook"]]
    assert saved["status"] == "watching" and saved["attempts"] == 1
    assert saved["events"][-1]["decision"] == "recovering"
    restarted = Harness(type(deployment).load(Path(deployment.run_root).parent / "deployment.json"))
    code, decisions = supervise.supervise(restarted, state)
    assert decisions[paths["notebook"]]["kind"] == "attempt_limit"
    assert code == supervise.EXIT_NOTHING_WATCHED
    assert len(cells(paths["notebook"], "initiate_run")) == 1


def test_healthy_controller_is_left_alone_and_no_second_controller_starts(run):
    harness, deployment, paths, state, submit = run
    job = submit()["job_id"]
    set_job(deployment, job, "RUN", paths["notebook"])
    supervise.assign(deployment, state, paths["notebook"])
    before = Notebook(paths["notebook"]).read()
    for _ in range(2):
        code, decisions = supervise.supervise(harness, state)
        assert code == 0 and decisions[paths["notebook"]]["decision"] == "left_alone"
    assert Notebook(paths["notebook"]).read() == before
    # Any other route to a second controller is refused by the harness too.
    with pytest.raises(ValueError, match="is RUN"):
        harness.run("initiate_run", InitiateRun(**submit.args))


def test_overlapping_pass_does_nothing(run):
    harness, deployment, paths, state, submit = run
    submit()
    supervise.assign(deployment, state, paths["notebook"])
    before = Notebook(paths["notebook"]).read()
    with open(state + ".lock", "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        assert supervise.supervise(harness, state)[0] == supervise.EXIT_BUSY
    assert Notebook(paths["notebook"]).read() == before


@pytest.mark.parametrize("reason,kind", [
    ("bash: /data/project/input.bed: Permission denied", "permission"),
    ("Error in rule artifact:", "workflow_error"),
    ("", "unexplained"),
])
def test_blockers_stay_visible_and_pending(run, reason, kind):
    harness, deployment, paths, state, submit = run
    submit(reason=reason or " ")
    supervise.assign(deployment, state, paths["notebook"])
    code, decisions = supervise.supervise(harness, state)
    decision = decisions[paths["notebook"]]
    assert decision["decision"] == "blocked" and decision["kind"] == kind
    assert decision["next_action"] == supervise.NEXT_ACTION[kind]
    assert len(cells(paths["notebook"], "initiate_run")) == 1
    # Later passes leave the blocker in place; re-assigning re-arms the run.
    assert supervise.supervise(harness, state) == (supervise.EXIT_NOTHING_WATCHED, {})
    saved = json.loads(Path(state).read_text())["runs"][paths["notebook"]]
    assert saved["status"] == "blocked" and saved["blocker"]["kind"] == kind
    supervise.assign(deployment, state, paths["notebook"])
    assert supervise.watching(state)


def test_source_change_is_a_decision_for_a_person(run):
    harness, deployment, paths, state, submit = run
    submit()
    Path(deployment.snakefile).write_text(Path(deployment.snakefile).read_text() + "# edited\n")
    supervise.assign(deployment, state, paths["notebook"])
    decision = supervise.supervise(harness, state)[1][paths["notebook"]]
    assert decision["kind"] == "source_changed"
    assert len(cells(paths["notebook"], "initiate_run")) == 1


def test_uncertain_submission_is_preserved_for_review(run):
    harness, deployment, paths, state, submit = run
    submit()
    book = Notebook(paths["notebook"])
    nb = book.read()
    cell = next(c for c in nb.cells if c.metadata.get("fungen", {}).get("action") == "initiate_run")
    cell.metadata.fungen.status = "unknown"
    cell.metadata.fungen.result.pop("job_id")
    import nbformat
    nbformat.write(nb, book.path)  # A deliberately damaged record, as after a lost receipt.
    supervise.assign(deployment, state, paths["notebook"])
    decision = supervise.supervise(harness, state)[1][paths["notebook"]]
    assert decision["kind"] == "uncertain_submission"
    assert len(cells(paths["notebook"], "initiate_run")) == 1


@pytest.mark.parametrize("text,kind", [
    ("slurmstepd: error: *** JOB 7 ON n1 CANCELLED AT 2026-11-24T10:00:00 DUE TO TIME LIMIT ***", "time_limit"),
    ("Exited with exit code 140.\nTERM_RUNLIMIT: job killed after reaching LSF run time limit.", "time_limit"),
    ("PermissionError: [Errno 13]", "permission"),
    ("Traceback (most recent call last):", "workflow_error"),
    ("Exited with exit code 1.", "unexplained"),
])
def test_decisive_error(text, kind):
    assert supervise.diagnose(text)[0] == kind


def fake_lsf(folder, pending=""):
    folder.mkdir()
    (folder / "bsub").write_text(f'#!/bin/bash\necho "$@" >> {folder}/bsub.args\ncat > {folder}/bsub.stdin\n')
    (folder / "bjobs").write_text(f"#!/bin/bash\nprintf '{pending}'\n")
    for name in ("bsub", "bjobs"):
        (folder / name).chmod(0o755)
    return folder


@pytest.mark.parametrize("watched,pending,queued", [(True, "", True), (True, "4242\\n", False), (False, "", False)])
def test_trigger_queues_the_next_hourly_pass(run, tmp_path, watched, pending, queued):
    harness, deployment, paths, state, submit = run
    job = submit()["job_id"]
    set_job(deployment, job, "RUN")
    if watched:
        supervise.assign(deployment, state, paths["notebook"])
    folder = Path(deployment.run_root)
    shutil.copy(ROOT / "container/supervise.lsf", folder)
    lsf = fake_lsf(tmp_path / "lsf", pending)
    env = {**os.environ, "PATH": f"{lsf}:{os.environ['PATH']}", "PYTHONPATH": str(ROOT / "src"),
           "FUNGEN_PYTHON": sys.executable,
           "FUNGEN_DEPLOYMENT": str(folder.parent / "deployment.json")}
    later = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    proc = subprocess.run(["bash", "supervise.lsf"], cwd=folder, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (lsf / "bsub.args").exists() == queued
    if queued:
        assert (lsf / "bsub.args").read_text().split()[0] == "-b"
        assert (lsf / "bsub.args").read_text().split()[1] in {later, (datetime.now() + timedelta(hours=1)).strftime("%H:%M")}
        assert (lsf / "bsub.stdin").read_text() == (ROOT / "container/supervise.lsf").read_text()


@pytest.mark.parametrize("text", [
    "Error in rule artifact:\nTERM_RUNLIMIT: job killed after reaching LSF run time limit.",
    "TERM_RUNLIMIT: job killed after reaching LSF run time limit.\nError in rule artifact:"])
def test_failed_rule_is_not_resumed_as_a_time_limit(text):
    assert supervise.diagnose(text)[0] == "workflow_error"


def test_scheduler_outage_is_retried_before_blocking(run, monkeypatch):
    harness, deployment, paths, state, submit = run
    submit()
    supervise.assign(deployment, state, paths["notebook"])
    def outage(request):
        raise RuntimeError("LSF inspection failed for job 7: mbatchd not responding")
    monkeypatch.setattr(harness, "inspect", outage)
    for _ in range(supervise.UNKNOWN_LIMIT - 1):
        assert supervise.supervise(harness, state)[1][paths["notebook"]]["decision"] == "left_alone"
    decision = supervise.supervise(harness, state)[1][paths["notebook"]]
    assert decision["decision"] == "blocked" and decision["kind"] == "scheduler_unknown"


def test_unexpected_error_blocks_one_run_without_ending_the_pass(run, monkeypatch):
    harness, deployment, paths, state, submit = run
    submit()
    supervise.assign(deployment, state, paths["notebook"])
    monkeypatch.setattr(supervise, "check", lambda *a: (_ for _ in ()).throw(KeyError("job_name")))
    code, decisions = supervise.supervise(harness, state)
    assert decisions[paths["notebook"]]["decision"] == "blocked"
    assert oct(Path(state).stat().st_mode & 0o777) == "0o644"
