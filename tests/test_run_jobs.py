"""Native SoS startup failure and exact run-membership regression fixtures."""
from datetime import datetime
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import nbformat
import pytest
import yaml

from fungen_operator.run_jobs import inspect_jobs


@pytest.fixture
def native_run(tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    snakefile = tmp_path / "Snakefile"
    snakefile.write_text('export HOME="$root/sos_runtime/home" COSI_SOS_EXEC_HOME="$root/sos_runtime/home"')
    config = root / "config.yaml"
    config.write_text(yaml.safe_dump({"outdir": str(root / "out"), "ld_meta_pair": "reference.LD_meta.tsv"}))
    stem = root / "controller"
    wrapper_log = root / ".snakemake/lsf_logs/rule_otters_test/gwas=study..eqtl=dataset/token.log"
    Path(f"{stem}.100.err").write_text(f"Job 4 has been submitted with LSF jobid 101 (log: {wrapper_log}).\n")
    task_dir = root / "out/results/study.reference.LD_meta/dataset.reference.LD_meta/twas/runlog/sos_runtime/home/.sos/tasks"
    task_dir.mkdir(parents=True)
    task_id = "t47c2496b7e5a91cb"
    submitted = 1_792_368_000.0
    task = task_dir / f"{task_id}.task"
    task.write_bytes(struct.pack("!2h8d", 3, 2, submitted, submitted, submitted, submitted, 0, 0, 0, 0) + b"protected payload never decoded")
    (task_dir / f"{task_id}.job_id").write_text("job_id: 102\nqueue: express\n")
    (task_dir / f"{task_id}.sh").write_text(f"#!/bin/bash\n/safe/bin/sos execute {task_id} -v 2 -s build\n")
    runlog = task_dir.parents[3]
    (runlog / "102.err").write_text('startup\ncouldn\'t read file "/opt/hpc/modulefiles/gcc/.modulerc": permission denied\nLmod has detected the following error\n')
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("", metadata={"fungen": {
        "action": "initiate_run", "slots": {"arguments": {"workdir": str(root), "configfile": str(config)},
        "bindings": {"log_stem": str(stem)}}, "result": {"job_id": "100"}}})])
    records = [
        {"JOBID": "100", "STAT": "RUN", "SUB_CWD": str(tmp_path), "COMMAND": "controller", "OUTPUT_FILE": f"{stem}.100.out"},
        {"JOBID": "101", "STAT": "RUN", "SUB_CWD": str(root), "COMMAND": "wrapper", "OUTPUT_FILE": str(wrapper_log)},
        {"JOBID": "102", "STAT": "EXIT", "SUB_CWD": str(runlog), "COMMAND": f"sos execute {task_id} -v 2", "EXIT_REASON": "Exited with exit code 1"},
        {"JOBID": "999", "STAT": "RUN", "SUB_CWD": str(root), "COMMAND": "codex exec", "QUEUE": "premium"},
    ]
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"RECORDS": records}), stderr="")
    return SimpleNamespace(root=root, deployment=SimpleNamespace(run_root=str(root), snakefile=str(snakefile),
                               registry=SimpleNamespace(task_layout=lambda workdir,config,log_path: {
                                   "rule": "otters_test", "unit": {"gwas": "study", "eqtl": "dataset"},
                                   "task_kind": "otters_test", "task_directory": task_dir})),
                           nb=nb, records=records, runner=runner, calls=calls, task=task, task_dir=task_dir,
                           submitted=submitted, now=submitted + 3600)


def test_startup_lmod_child_exit_leaves_wrapper_running(native_run):
    run = native_run
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["count"] == 1
    child = report["dead_children"][0]
    assert child["task_id"] == "t47c2496b7e5a91cb"
    assert child["lsf_job_id"] == "102" and child["wrapper_job_id"] == "101"
    assert child["rule"] == "otters_test" and child["unit"] == {"gwas": "study", "eqtl": "dataset"}
    assert child["lsf_state"] == "EXIT" and child["exit_reason"] == "Exited with exit code 1"
    assert '.modulerc": permission denied' in child["first_error_line"]
    assert report["jobs"]["101"]["status"] == "RUN"
    assert len(run.calls) == 1 and run.calls[0][:3] == ["bjobs", "-a", "-json"]


def test_membership_requires_native_evidence_even_in_same_cwd(native_run):
    run = native_run
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert all(report["jobs"][job]["membership"] for job in ("100", "101", "102"))
    assert not report["jobs"]["999"]["membership"]
    assert "absent from this notebook" in report["jobs"]["999"]["membership_reason"]
    run.records[1]["OUTPUT_FILE"] = str(run.root / "unrelated.log")
    run.records[2]["COMMAND"] = "sos execute another-task"
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert not report["jobs"]["101"]["membership"]
    assert not report["jobs"]["102"]["membership"]


@pytest.mark.parametrize("state", ["EXIT", "DONE"])
def test_grace_uses_submission_header_not_file_mtime(native_run, state):
    run = native_run
    run.records[2]["STAT"] = state
    assert inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.submitted + 599)["count"] == 0
    assert inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.submitted + 601)["count"] == 1
    assert inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now, grace_minutes=90)["count"] == 0


def test_only_submitted_or_running_sos_records_are_dead_candidates(native_run):
    run = native_run
    data = bytearray(run.task.read_bytes())
    data[2:4] = struct.pack("!h", 6)
    run.task.write_bytes(data)
    assert inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)["count"] == 0


@pytest.mark.parametrize("history,code,expected", [
    ("Job <102>, Job Name <task>\nMon Oct 19 00:01:01: Exited with exit code 1.\n", 0, "EXIT"),
    ("Job <102> is not found\n", 255, "NOT_FOUND"),
    ("No matching job found\n", 255, "NOT_FOUND"),
    ("Network is unreachable\n", 255, None),
])
def test_missing_children_use_one_batched_history_query(native_run, history, code, expected):
    run = native_run
    run.records[:] = [r for r in run.records if r["JOBID"] != "102"]
    def runner(command, **kwargs):
        run.calls.append(command)
        if command[0] == "bjobs":
            return SimpleNamespace(returncode=0, stdout=json.dumps({"RECORDS": run.records}), stderr="")
        return SimpleNamespace(returncode=code, stdout=history, stderr="")
    report = inspect_jobs(run.deployment, run.nb, runner=runner, now=run.now)
    assert len(run.calls) == 2 and run.calls[1] == ["bhist", "-a", "-l", "102"]
    assert report["count"] == (1 if expected else 0)
    if expected:
        assert report["dead_children"][0]["lsf_state"] == expected
    else:
        assert report["observations"][-1]["status"] == "history_query_unresolved"


def test_bjobs_failure_does_not_mean_child_absent(native_run):
    run = native_run
    def unavailable(command, **kwargs):
        return SimpleNamespace(returncode=255, stdout="", stderr="authentication failed")
    report = inspect_jobs(run.deployment, run.nb, runner=unavailable, now=run.now)
    assert not report["scheduler_ok"] and report["count"] == 0
    assert report["observations"][-1]["status"] == "scheduler_query_failed"


def test_pending_age_and_queue_are_live(native_run):
    run = native_run
    run.records[2].update(STAT="PEND", QUEUE="express", SUBMIT_TIME=str(int(run.submitted)))
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["jobs"]["102"]["pending_minutes"] == 60
    assert report["jobs"]["102"]["queue"] == "express" and report["count"] == 0


def test_dead_child_maps_to_original_wrapper_after_newer_retry(native_run):
    run = native_run
    path = Path(f"{run.root / 'controller'}.100.err")
    lines = path.read_text()
    old = datetime.fromtimestamp(run.submitted - 120).strftime("[%a %b %d %H:%M:%S %Y]")
    new = datetime.fromtimestamp(run.submitted + 1200).strftime("[%a %b %d %H:%M:%S %Y]")
    path.write_text(f"{old}\n{lines}{new}\n" + lines.replace("jobid 101", "jobid 103"))
    run.records.append({**run.records[1], "JOBID": "103", "STAT": "RUN"})
    stamp = datetime.fromtimestamp(run.submitted - 60).strftime("%Y%m%d_%H%M%S")
    (run.task_dir.parents[3] / f"{stamp}.study.dataset.otters_test.log").write_text(
        "INFO: t47c2496b7e5a91cb ``submitted`` to express with job id 102\n")
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["dead_children"][0]["wrapper_job_id"] == "101"


def test_ambiguous_wrapper_lineage_remains_unresolved(native_run):
    run = native_run
    path = Path(f"{run.root / 'controller'}.100.err")
    path.write_text(path.read_text() + path.read_text().replace("jobid 101", "jobid 103"))
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["dead_children"][0]["wrapper_job_id"] is None
    assert report["observations"][-1]["status"] == "wrapper_lineage_unresolved"


@pytest.mark.parametrize("failure", [FileNotFoundError("bjobs missing"), __import__('subprocess').TimeoutExpired("bjobs", 60)])
def test_scheduler_invocation_failure_is_reported(native_run, failure):
    run = native_run
    def failed(command, **kwargs):
        raise failure
    report = inspect_jobs(run.deployment, run.nb, runner=failed, now=run.now)
    assert not report["scheduler_ok"] and report["count"] == 0


def test_explicit_outsider_refusal_skips_unrelated_task_census(native_run, monkeypatch):
    run = native_run
    run.records[3]["SUB_CWD"] = str(run.root.parent)
    def unexpected(*args):
        raise AssertionError("an outside non-controller needs no task census")
    monkeypatch.setattr("fungen_operator.run_jobs._evidence", unexpected)
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now, requested_ids=["999"])
    assert report["scheduler_ok"]
    assert not report["jobs"]["999"]["membership"]
    assert "outside this run" in report["jobs"]["999"]["membership_reason"]
    assert len(run.calls) == 1


@pytest.mark.parametrize("pending,expected", [("120", 2), ("0", 0), ("-", 60)])
def test_pending_age_prefers_native_lsf_pending_seconds(native_run, pending, expected):
    run = native_run
    run.records[2].update(STAT="PEND", QUEUE="express", SUBMIT_TIME=str(int(run.submitted)), PEND_TIME=pending)
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["jobs"]["102"]["pending_minutes"] == expected


def test_retried_group_header_alone_does_not_establish_wrapper_lineage(native_run):
    run = native_run
    path = Path(f"{run.root / 'controller'}.100.err")
    line = path.read_text()
    old = datetime.fromtimestamp(run.submitted - 120).strftime("[%a %b %d %H:%M:%S %Y]")
    retry = datetime.fromtimestamp(run.submitted + 1200).strftime("[%a %b %d %H:%M:%S %Y]")
    path.write_text(f"{old}\n{line}{retry}\n" + line.replace("jobid 101", "jobid 103"))
    run.records.append({**run.records[1], "JOBID": "103", "STAT": "RUN"})
    stamp = datetime.fromtimestamp(run.submitted - 60).strftime("%Y%m%d_%H%M%S")
    (run.task_dir.parents[3] / f"{stamp}.group.log").write_text("INFO: grouped subtasks submitted\n")
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["dead_children"][0]["wrapper_job_id"] is None
    assert report["observations"][-1]["status"] == "wrapper_lineage_unresolved"


def test_same_timestamp_wrapper_candidates_remain_unresolved(native_run):
    run = native_run
    path = Path(f"{run.root / 'controller'}.100.err")
    line = path.read_text()
    stamp = datetime.fromtimestamp(run.submitted - 120).strftime("[%a %b %d %H:%M:%S %Y]")
    path.write_text(f"{stamp}\n{line}" + line.replace("jobid 101", "jobid 103"))
    engine_stamp = datetime.fromtimestamp(run.submitted - 60).strftime("%Y%m%d_%H%M%S")
    (run.task_dir.parents[3] / f"{engine_stamp}.group.log").write_text(
        "INFO: t47c2496b7e5a91cb submitted to express with job id 102\n")
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report["dead_children"][0]["wrapper_job_id"] is None
    assert report["observations"][-1]["status"] == "wrapper_lineage_unresolved"


def test_sweep_receipt_is_a_live_run_member(native_run):
    run = native_run
    stem = str(run.root / 'sweep')
    run.nb.cells.append(nbformat.v4.new_code_cell('', metadata={'fungen': {
        'action': 'control_run', 'slots': {'arguments': {'operation': 'sweep'},
        'bindings': {'log_stem': stem}}, 'result': {'job_id': '201'}}}))
    run.records.append({'JOBID': '201', 'STAT': 'RUN', 'SUB_CWD': str(run.root.parent),
                        'OUTPUT_FILE': stem + '.201.out', 'COMMAND': 'python -m fungen_operator.sweep'})
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report['jobs']['201']['membership'] and report['jobs']['201']['kind'] == 'sweep'
    selected = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now, requested_ids=['201'])
    assert selected['jobs']['201']['membership']


def test_native_resource_memory_and_step_kind_are_exposed(native_run):
    run = native_run
    run.records[2]['COMBINED_RESREQ'] = 'select[mem>0] rusage[mem=57344.00] span[hosts=1]'
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report['jobs']['102']['memory_reservation_gb'] == 56
    assert report['jobs']['102']['task_kind'] == 'otters_test'


def test_json_scheduler_error_record_stays_unknown(native_run):
    run = native_run
    run.records[:] = [{'ERROR': 'scheduler query failed'}]
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert not report['scheduler_ok'] and report['count'] == 0


def test_terminal_exit_reason_includes_native_exit_code(native_run):
    run = native_run
    run.records[2].update(EXIT_REASON="", EXIT_CODE="1")
    report = inspect_jobs(run.deployment, run.nb, runner=run.runner, now=run.now)
    assert report['dead_children'][0]['exit_reason'] == 'Exited with exit code 1'


def test_shared_task_directory_is_resolved_once_for_distinct_wrapper_logs(native_run, monkeypatch):
    from fungen_operator.run_jobs import _evidence
    run = native_run
    path = Path(f"{run.root / 'controller'}.100.err")
    line = path.read_text()
    path.write_text(line + line.replace("jobid 101", "jobid 103").replace("token.log", "region.log"))
    original = Path.resolve
    calls = []
    def counted(path, *args, **kwargs):
        if path == run.task_dir:
            calls.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "resolve", counted)
    evidence, _ = _evidence(run.deployment, run.nb)
    assert set(evidence) == {"100", "101", "102", "103"}
    assert evidence["102"]["wrapper_candidates"] == ["101", "103"]
    assert calls == [run.task_dir]


def test_task_directory_symlink_outside_run_root_is_refused(native_run):
    from fungen_operator.run_jobs import _evidence
    run = native_run
    outside = run.root.parent / "outside_tasks"
    outside.mkdir()
    for path in run.task_dir.iterdir():
        (outside / path.name).write_bytes(path.read_bytes())
    alias = run.root / "exported_tasks"
    alias.symlink_to(outside, target_is_directory=True)
    run.deployment.registry.task_layout = lambda workdir, config, log_path: {
        "rule": "otters_test", "unit": {}, "task_directory": alias}
    evidence, _ = _evidence(run.deployment, run.nb)
    assert set(evidence) == {"100", "101"}


_NATIVE_CONTROLLER_HISTORY = """Job <100>, Job Name <controller>, User <operator>, Status <DONE>
Mon Oct 19 00:01:01: Submitted from host <login>, to Queue <premium>;
Mon Oct 19 00:01:02: Done successfully. The CPU time used is 1 seconds.
Summary of time in seconds spent in various states by Mon Oct 19 00:01:02
  PEND     PSUSP    RUN      USUSP    SSUSP    UNKWN    TOTAL
  0        0        1        0        0        0        1
"""


def _mixed_history_report(run, body, code=0, diagnostic=""):
    run.records[:] = [record for record in run.records if record["JOBID"] not in {"100", "102"}]
    def runner(command, **kwargs):
        run.calls.append(command)
        if command[0] == "bjobs":
            return SimpleNamespace(returncode=0, stdout=json.dumps({"RECORDS": run.records}), stderr="")
        return SimpleNamespace(returncode=code, stdout=body, stderr=diagnostic)
    return inspect_jobs(run.deployment, run.nb, runner=runner, now=run.now)


def test_successful_native_history_batch_can_silently_omit_absent_child(native_run):
    run = native_run
    report = _mixed_history_report(run, _NATIVE_CONTROLLER_HISTORY)
    assert run.calls[-1] == ["bhist", "-a", "-l", "100", "102"]
    assert report["count"] == 1
    child = report["dead_children"][0]
    assert child["lsf_job_id"] == "102" and child["wrapper_job_id"] == "101"
    assert child["lsf_state"] == "NOT_FOUND" and child["exit_reason"] == "LSF has no record"
    assert report["jobs"]["100"]["status"] == "DONE"


@pytest.mark.parametrize("body,code,diagnostic", [
    (_NATIVE_CONTROLLER_HISTORY, 0, "Network is unreachable"),
    (_NATIVE_CONTROLLER_HISTORY, 1, ""),
    (_NATIVE_CONTROLLER_HISTORY.split("Summary of time")[0], 0, ""),
    (_NATIVE_CONTROLLER_HISTORY + "Job <102>, Job Name <child>\n", 0, ""),
    (_NATIVE_CONTROLLER_HISTORY + "scheduler query failed\n", 0, ""),
    ("malformed response\n", 0, ""),
])
def test_partial_error_or_truncated_history_does_not_imply_absent_child(native_run, body, code, diagnostic):
    report = _mixed_history_report(native_run, body, code, diagnostic)
    assert report["count"] == 0
    assert "102" not in report["jobs"] or report["jobs"]["102"]["status"] != "NOT_FOUND"
    if "102" not in report["jobs"]:
        assert any(entry == {"job_id": "102", "status": "history_query_unresolved"}
                   for entry in report["observations"])
    else:
        assert report["jobs"]["102"]["status"] == "UNKNOWN"
