"""Approved native sweep rules operate on live pending members only."""

import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from fungen_operator.sweep import (
    MemoryRemap, NotebookMetadata, QueueMove, SweepPlan, SweepSpec,
    load_plan, run_pass, run_sweep,
)


def member(job_id, **changes):
    return {"job_id": str(job_id), "membership": True, "live": True,
            "kind": "child", "status": "PEND", "rule": "univariate_rss_gwas",
            "task_kind": "univariate_rss", "memory_reservation_gb": 56,
            "combined_resreq": "select[type==any] rusage[mem=57344.00] span[hosts=1]",
            "queue": "express", **changes}


def snapshot(*jobs, scheduler_ok=True):
    return {"scheduler_ok": scheduler_ok, "jobs": {job["job_id"]: job for job in jobs}}


@pytest.fixture
def native_runner():
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="Job modified\n", stderr="")
    return runner, calls


@pytest.fixture
def sweep_plan(tmp_path):
    return SweepPlan(
        spec=SweepSpec(queue_move=QueueMove(from_queue="express", to_queue="premium", limit=1000)),
        run_root=str(tmp_path), notebook=str(tmp_path / "operator.ipynb"),
        snakefile=str(tmp_path / "Snakefile"), log_path=str(tmp_path / "logs/sweep.jsonl"),
    )


@pytest.mark.parametrize("settings", [
    {},
    {"memory_remaps": [{"step": "rss", "from_gb": "56", "to_gb": 34}]},
    {"memory_remaps": [{"step": "rss", "from_gb": True, "to_gb": 34}]},
    {"memory_remaps": [{"step": "rss", "from_gb": 56, "to_gb": 56}]},
    {"memory_remaps": [{"step": "rss;command", "from_gb": 56, "to_gb": 34}]},
    {"memory_remaps": [{"step": "rss", "from_gb": 56, "to_gb": 34, "hard_limit_gb": 0}]},
    {"queue_move": {"from_queue": "express", "to_queue": "express", "limit": 1}},
    {"queue_move": {"from_queue": "express", "to_queue": "premium", "limit": 0}},
    {"queue_move": {"from_queue": "express", "to_queue": "premium", "limit": 1}, "interval_seconds": "300"},
    {"queue_move": {"from_queue": "express", "to_queue": "premium", "limit": 1}, "interval_seconds": 86401},
    {"memory_remaps": [{"step": "rss", "from_gb": 56, "to_gb": 34},
                       {"step": "rss", "from_gb": 56, "to_gb": 35}]},
])
def test_sweep_settings_are_typed_complete_and_unique(settings):
    with pytest.raises(ValidationError):
        SweepSpec.model_validate(settings)


def test_native_memory_remaps_match_step_and_reservation_and_preserve_resources(native_runner):
    runner, calls = native_runner
    spec = SweepSpec(memory_remaps=[
        MemoryRemap(step="univariate_rss", from_gb=56, to_gb=34),
        MemoryRemap(step="otters_test", from_gb=24, to_gb=35, hard_limit_gb=35),
    ])
    report = run_pass(spec, snapshot(
        member(1), member(2, rule="univariate_rss_eqtl"),
        member(3, rule="otters_test", task_kind="otters_test", memory_reservation_gb=24,
               combined_resreq="rusage[mem=24576] span[hosts=1]"),
        member(4, status="RUN"), member(5, membership=False),
        member(6, rule="other", task_kind="other"), member(7, memory_reservation_gb=34),
        member(8, live=False),
    ), runner=runner)
    assert report == {"memory_changed": 3, "queue_changed": 0, "active_jobs": 6,
                      "failures": 0, "scheduler_ok": True}
    assert calls[:2] == [["bmod", "-R", "select[type==any] rusage[mem=34G] span[hosts=1]", str(i)] for i in (1, 2)]
    assert calls[2] == ["bmod", "-M", "35G", "-R", "rusage[mem=35G] span[hosts=1]", "3"]


def test_queue_moves_use_the_approved_cap_and_pending_members(native_runner):
    runner, calls = native_runner
    spec = SweepSpec(queue_move=QueueMove(from_queue="express", to_queue="premium", limit=2))
    report = run_pass(spec, snapshot(
        member(30), member(10), member(20), member(40, membership=False),
        member(50, status="RUN"), member(60, queue="premium"), member(70, kind="sweep"),
    ), runner=runner)
    assert calls == [["bmod", "-q", "premium", "10"], ["bmod", "-q", "premium", "20"]]
    assert report["queue_changed"] == 2 and report["active_jobs"] == 5


def test_one_pass_never_chains_memory_remaps(native_runner):
    runner, calls = native_runner
    spec = SweepSpec(memory_remaps=[MemoryRemap(step="univariate_rss", from_gb=56, to_gb=34),
                                   MemoryRemap(step="univariate_rss", from_gb=34, to_gb=30)])
    assert run_pass(spec, snapshot(member(1)), runner=runner)["memory_changed"] == 1
    assert len(calls) == 1 and "mem=34G" in calls[0][2]


def test_overlapping_rule_and_task_kind_are_refused_for_that_job(native_runner):
    runner, calls = native_runner
    spec = SweepSpec(memory_remaps=[MemoryRemap(step="univariate_rss", from_gb=56, to_gb=34),
                                   MemoryRemap(step="univariate_rss_gwas", from_gb=56, to_gb=30)])
    report = run_pass(spec, snapshot(member(1)), runner=runner)
    assert report["failures"] == 1 and report["memory_changed"] == 0 and calls == []


def test_unknown_scheduler_cannot_modify_jobs(native_runner):
    runner, calls = native_runner
    spec = SweepSpec(queue_move=QueueMove(from_queue="express", to_queue="premium", limit=10))
    report = run_pass(spec, snapshot(member(1), scheduler_ok=False), runner=runner)
    assert not report["scheduler_ok"] and report["failures"] == 1
    assert report["memory_changed"] == report["queue_changed"] == 0 and calls == []


def test_failed_bmod_is_counted_without_reporting_a_change():
    def runner(*args, **kwargs):
        return SimpleNamespace(returncode=255, stdout="", stderr="job no longer pending")
    spec = SweepSpec(queue_move=QueueMove(from_queue="express", to_queue="premium", limit=10))
    report = run_pass(spec, snapshot(member(1)), runner=runner)
    assert report["queue_changed"] == 0 and report["failures"] == 1


def test_sweep_follows_fresh_snapshots_then_stops_without_counting_its_job(sweep_plan, native_runner):
    runner, calls = native_runner
    current = iter([snapshot(member(1)), snapshot(member(99, kind="sweep", status="RUN"))])
    sleeps = []
    result = run_sweep(sweep_plan, snapshotter=lambda: next(current), runner=runner,
                       sleeper=sleeps.append, clock=lambda: "fixed")
    assert result["status"] == "completed" and result["passes"] == 2
    assert sleeps == [300] and calls == [["bmod", "-q", "premium", "1"]]
    lines = [json.loads(line) for line in Path(sweep_plan.log_path).read_text().splitlines()]
    assert [line["queue_changed"] for line in lines] == [1, 0]
    assert [line["active_jobs"] for line in lines] == [1, 0]


def test_interval_zero_runs_once_even_with_running_workflow_jobs(sweep_plan, native_runner):
    runner, calls = native_runner
    sweep_plan.spec.interval_seconds = 0
    reads = []
    def inspect():
        reads.append(True)
        return snapshot(member(1, status="RUN"))
    result = run_sweep(sweep_plan, snapshotter=inspect, runner=runner,
                       sleeper=lambda _: pytest.fail("one pass cannot sleep"))
    assert len(reads) == 1 and result["passes"] == 1 and result["status"] == "completed"
    assert result["queue_changed"] == result["memory_changed"] == 0 and calls == []


def test_empty_run_logs_zero_changes_and_stops_without_sleep(sweep_plan, native_runner):
    runner, calls = native_runner
    result = run_sweep(sweep_plan, snapshotter=lambda: snapshot(), runner=runner,
                       sleeper=lambda _: pytest.fail("completed run cannot sleep"))
    line = json.loads(Path(sweep_plan.log_path).read_text())
    assert result["status"] == "completed" and result["passes"] == 1
    assert line["active_jobs"] == line["memory_changed"] == line["queue_changed"] == 0 and calls == []


def test_periodic_sweep_counts_a_raced_mutation_and_follows_later_jobs(sweep_plan):
    current = iter([snapshot(member(1)), snapshot()])
    sleeps = []
    def unavailable(*args, **kwargs):
        return SimpleNamespace(returncode=255, stdout="", stderr="job no longer pending")
    result = run_sweep(sweep_plan, snapshotter=lambda: next(current), runner=unavailable,
                       sleeper=sleeps.append)
    lines = [json.loads(line) for line in Path(sweep_plan.log_path).read_text().splitlines()]
    assert result["status"] == "completed" and result["passes"] == 2 and sleeps == [300]
    assert lines[0]["failures"] == 1 and lines[0]["queue_changed"] == 0
    assert lines[1]["active_jobs"] == 0


def test_scheduler_failure_is_logged_and_ends_the_worker(sweep_plan, native_runner):
    runner, calls = native_runner
    def inspect():
        raise ValueError("scheduler unavailable")
    result = run_sweep(sweep_plan, snapshotter=inspect, runner=runner,
                       sleeper=lambda _: pytest.fail("failed sweep cannot sleep"))
    line = json.loads(Path(sweep_plan.log_path).read_text())
    assert result["status"] == "failed" and result["passes"] == 1 and line["failures"] == 1
    assert line["memory_changed"] == line["queue_changed"] == 0 and calls == []


def test_approved_plan_is_bound_to_exact_raw_bytes_and_run_root(sweep_plan, tmp_path):
    path = tmp_path / "plan.json"
    text = sweep_plan.model_dump_json(indent=2) + "\n"
    path.write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    assert load_plan(path, digest) == sweep_plan
    path.write_text(text + "\n")
    with pytest.raises(ValueError, match="approved digest"):
        load_plan(path, digest)
    with pytest.raises(ValidationError, match="run root"):
        SweepPlan.model_validate({**sweep_plan.model_dump(), "log_path": str(tmp_path.parent / "outside")})


def test_metadata_stream_retains_receipts_and_refreshes_after_notebook_changes(tmp_path):
    jq = shutil.which("jq")
    if not jq:
        pytest.skip("streaming metadata reader requires jq")
    path = tmp_path / "operator.ipynb"
    def write(job_id):
        path.write_text(json.dumps({"cells": [{"metadata": {"fungen": {
            "action": "initiate_run", "slots": {"arguments": {"workdir": str(tmp_path), "configfile": "config.yaml"},
                                                      "bindings": {"log_stem": "controller"}},
            "result": {"job_id": job_id, "logs": {"stdout": "large output " * 100_000}},
        }}, "outputs": [{"text": "large output " * 100_000}]}]}))
    write("100")
    reader = NotebookMetadata(path, jq)
    first = reader.read()
    assert first.cells[0].metadata["fungen"]["result"] == {"job_id": "100"}
    assert reader.read() is first
    write("101")
    assert reader.read().cells[0].metadata["fungen"]["result"] == {"job_id": "101"}


def test_metadata_read_error_does_not_reuse_stale_receipts(tmp_path):
    path = tmp_path / "operator.ipynb"
    path.write_text("{}")
    def unavailable(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="invalid JSON")
    with pytest.raises(ValueError, match="cannot read sweep notebook metadata"):
        NotebookMetadata(path, runner=unavailable).read()
