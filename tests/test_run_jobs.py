"""Native SoS startup failure and exact run-membership regression fixtures."""
from datetime import datetime
import json
from pathlib import Path
import struct
import shlex
import sys
from types import SimpleNamespace

import nbformat
import pytest
import yaml

from fungen_operator.run_jobs import inspect_jobs
from fungen_operator.actions import Deployment
from fungen_operator.fixture import create_fixture


@pytest.fixture
def native_run(tmp_path,monkeypatch):
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
    original=create_fixture(tmp_path/'layout')
    deployment=Deployment.model_validate({**original.model_dump(),'run_root':str(root),'backend':'lsf'})
    Path(deployment.snakefile).write_text(snakefile.read_text())
    registry=deployment.registry
    registry.task_layout=lambda workdir,config,log_path:{'rule':'otters_test','unit':{'gwas':'study','eqtl':'dataset'},'task_kind':'otters_test','task_directory':task_dir}
    from fungen_operator import providers
    load=providers.load_registry
    monkeypatch.setattr(providers,'load_registry',lambda d,f=None:registry if d is deployment else load(d,f))
    return SimpleNamespace(root=root,deployment=deployment,nb=nb,records=records,runner=runner,calls=calls,
                           task=task,task_dir=task_dir,submitted=submitted,now=submitted+3600)


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


@pytest.fixture(params=['sge','slurm'])
def native_scheduler_run(tmp_path,request):
    scheduler=request.param
    root=tmp_path/'run';root.mkdir()
    profile=root/'profile';profile.mkdir()
    logs=root/'rules';logs.mkdir()
    home=root/'runtime-home';tasks=home/'.sos/tasks';tasks.mkdir(parents=True)
    config=root/'config.yaml';config.write_text(yaml.safe_dump({'runtime_home':str(home)}))
    from fungen_operator import cluster
    command=shlex.join([sys.executable,str(Path(cluster.__file__).resolve()),'submit','--scheduler',scheduler,'--logs',str(logs)])
    (profile/'config.yaml').write_text(yaml.safe_dump({'cluster':command}))
    stem=root/'controller'
    Path(f'{stem}.100.out').write_text('')
    Path(f'{stem}.100.err').write_text("Submitted job 4 with external jobid '101'.\n")
    (logs/'101.out').write_text('')
    task='t0123456789abcdef'
    (logs/'101.err').write_text(f'INFO: {task} \x1b[32msubmitted\x1b[0m to fungen_{scheduler} with job id 102\n')
    submitted=1_792_368_000.0
    (tasks/(task+'.task')).write_bytes(struct.pack('!2h8d',3,2,submitted,submitted,submitted,submitted,0,0,0,0))
    (tasks/(task+'.job_id')).write_text('job_id: 102\n')
    (tasks/(task+'.sh')).write_text(f'#!/bin/bash\n/host/bin/sos execute {task} -s build\n')
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('',metadata={'fungen':{
        'action':'initiate_run','status':'submitted','slots':{'arguments':{'workdir':str(root),'configfile':str(config)},
            'bindings':{'log_stem':str(stem)}},'result':{'job_id':'100'}}})])
    original=create_fixture(tmp_path/'layout')
    Path(original.default_config).write_text(config.read_text())
    d=Deployment.model_validate({**original.model_dump(),'run_root':str(root),'profile_path':str(profile),'backend':scheduler})
    from fungen_operator.cluster import journal_event
    journal=logs/'submissions.jsonl'
    shared=dict(scheduler=scheduler,controller='100')
    journal_event(journal,event='begin',kind='controller',job_id='100',**shared)
    for kind,parent,job,attempt,fields in [('wrapper','100','101','wrapper1',{'snakemake_job_id':'4','rule':'test'}),('child','101','102','child1',{'task_id':task})]:
        context=dict(kind=kind,parent=parent,attempt=attempt,**fields,**shared)
        journal_event(journal,event='intent',**context)
        journal_event(journal,event='receipt',job_id=job,**context)
        if kind=='wrapper':journal_event(journal,event='begin',kind='wrapper',parent='100',job_id=job,**shared)
    states={'100':'running','101':'running','102':'failed'};calls=[]
    def runner(cmd,**kw):
        calls.append(cmd)
        job=cmd[2] if cmd[0] in ('qstat','qacct','sacct') else cmd[cmd.index('-j')+1]
        state=states.get(job)
        if cmd[0]=='qstat':rc,out=(0,f'job_number: {job}\n') if state=='running' else (1,'')
        elif cmd[0]=='qacct':
            rc=0 if state in ('success','failed') else 1
            out=f'jobnumber {job}\ntaskid undefined\nfailed 0\nexit_status {1 if state=="failed" else 0}\n' if rc==0 else ''
        elif cmd[0]=='squeue':rc,out=0,(f'{job}|RUNNING\n' if state=='running' else '')
        elif cmd[0]=='sacct':rc,out=0,(f'{job}|FAILED|1:0\n' if state=='failed' else f'{job}|COMPLETED|0:0\n' if state=='success' else '')
        else:pytest.fail('inspection used wrong scheduler client: '+str(cmd))
        return SimpleNamespace(returncode=rc,stdout=out,stderr='')
    return SimpleNamespace(root=root,deployment=d,nb=nb,states=states,calls=calls,runner=runner,
                           task=task,tasks=tasks,logs=logs,submitted=submitted,now=submitted+3600,journal=journal)


def test_native_child_inspection_follows_every_retained_job(native_scheduler_run):
    run=native_scheduler_run
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert report['scheduler_ok'] is True and report['count']==1
    assert set(report['jobs'])=={'100','101','102'}
    assert report['jobs']['102']['kind']=='child' and report['jobs']['102']['status']=='EXIT'
    assert all(row['membership'] for row in report['jobs'].values())
    assert report['dead_children'][0]['job_id']=='102' and report['dead_children'][0]['wrapper_job_id']=='101'
    assert report['dead_children'][0]['scheduler']==run.deployment.backend
    assert {cmd[0] for cmd in run.calls}==({'qstat','qacct'} if run.deployment.backend=='sge' else {'squeue','sacct'})


@pytest.mark.parametrize('failed_job',['100','101','102'])
def test_native_unknown_status_is_an_error(native_scheduler_run,failed_job):
    run=native_scheduler_run;run.states.pop(failed_job)
    with pytest.raises(RuntimeError,match='inspection failed for job '+failed_job):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_native_child_grace_uses_actual_sos_submission(native_scheduler_run):
    run=native_scheduler_run
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.submitted+599)
    assert report['count']==0 and report['jobs']['102']['status']=='EXIT'
    run.states['102']='running'
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert report['count']==0 and report['jobs']['102']['status']=='RUN'


@pytest.mark.parametrize('missing',['task','job_id','script','wrapper_log'])
def test_native_missing_child_evidence_never_means_clean(native_scheduler_run,missing):
    run=native_scheduler_run
    # Corrupt contents in place: preserve each test artifact for diagnostics.
    path={'task':run.tasks/(run.task+'.task'),'job_id':run.tasks/(run.task+'.job_id'),
          'script':run.tasks/(run.task+'.sh'),'wrapper_log':run.logs/'101.err'}[missing]
    if missing=='wrapper_log':
        # Point the selected profile at a nonexistent exact stream directory.
        profile=Path(run.deployment.profile_path)/'config.yaml'
        profile.write_text(profile.read_text().replace(str(run.logs),str(run.root/'unavailable-logs')))
    else:path.write_text('invalid\n')
    with pytest.raises(RuntimeError):inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_native_inspection_does_not_adopt_unrelated_shared_home_tasks(native_scheduler_run):
    run=native_scheduler_run
    (run.tasks/'tunrelated.job_id').write_text('job_id: 999\n')
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now,requested_ids=['999'])
    assert report['jobs']['999']['membership'] is False
    assert all('999' not in cmd for cmd in run.calls)


def test_harness_inspection_surfaces_native_child_failure(native_scheduler_run,monkeypatch):
    from fungen_operator import harness as h
    run=native_scheduler_run
    obj=h.Harness.__new__(h.Harness);obj.deployment=run.deployment;obj.registry=run.deployment.registry
    obj.executor=SimpleNamespace(can_schedule=True,can_inspect=True,logs=lambda *a:{})
    monkeypatch.setattr(h,'Notebook',lambda *a:SimpleNamespace(read=lambda:run.nb))
    monkeypatch.setattr('fungen_operator.run_jobs.subprocess.run',run.runner)
    request=SimpleNamespace(notebook='/unused',dead_child_grace_minutes=0,paths=[])
    result=obj.inspect(request)
    assert result['scheduler_ok'] and result['dead_child_count']==1
    assert result['cells'][0]['scheduler']['status']=='RUN'
    run.states.pop('102')
    with pytest.raises(RuntimeError,match='inspection failed for job 102'):obj.inspect(request)


def test_native_duplicate_retained_receipts_count_a_child_once(native_scheduler_run):
    run=native_scheduler_run
    path=run.root/'controller.100.err';path.write_text(path.read_text()*2)
    path=run.logs/'101.err';path.write_text(path.read_text()*2)
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert report['count']==1
    assert len([cmd for cmd in run.calls if cmd[0] in ('qacct','sacct')])==1


@pytest.mark.parametrize('kind',['wrapper','child'])
def test_native_unsupported_receipt_is_an_error(native_scheduler_run,kind):
    run=native_scheduler_run
    if kind=='wrapper':
        path=run.root/'controller.100.err';path.write_text(path.read_text().replace("'101'","'101.1-4:1'"))
    else:
        path=run.logs/'101.err';path.write_text(path.read_text().replace('job id 102','job id 102.1'))
    with pytest.raises(RuntimeError):inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_missing_scheduler_discriminator_is_rejected_before_query():
    called=[]
    with pytest.raises(AttributeError):
        inspect_jobs(SimpleNamespace(),nbformat.v4.new_notebook(),runner=lambda *a,**k:called.append(a))
    assert called==[]


def test_lsf_fixture_is_a_valid_deployment(native_run):
    assert isinstance(native_run.deployment,Deployment) and native_run.deployment.backend=='lsf'
    native_run.deployment.validate_layout()


def test_public_empty_lsf_inspection_is_not_verified(tmp_path,monkeypatch):
    from fungen_operator import harness as h
    obj=h.Harness.__new__(h.Harness)
    d=create_fixture(tmp_path/'layout');obj.deployment=d.model_copy(update={'backend':'lsf'})
    obj.registry=obj.deployment.registry
    obj.executor=SimpleNamespace(can_schedule=True,can_inspect=True,logs=lambda *a:{})
    monkeypatch.setattr(h,'Notebook',lambda *a:SimpleNamespace(read=nbformat.v4.new_notebook))
    result=obj.inspect(SimpleNamespace(notebook='/unused',dead_child_grace_minutes=0,paths=[]))
    assert result['inspection_status']=='not_verified'
    assert result['scheduler_ok'] is False and result['dead_child_count'] is None
    assert result['discovery_coverage']['verified'] is False
    assert 'No retained controller receipts' in result['discovery_coverage']['reason']
    assert result['jobs']=={}


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
def test_public_cli_incomplete_discovery_exits_nonzero(tmp_path,scheduler):
    import subprocess
    d=create_fixture(tmp_path/'layout').model_copy(update={'backend':scheduler})
    deployment=tmp_path/'deployment.json';deployment.write_text(d.model_dump_json())
    book=Path(d.run_root)/'operator.ipynb';nbformat.write(nbformat.v4.new_notebook(),book)
    result=subprocess.run([sys.executable,'-m','fungen_operator','inspect','--deployment',str(deployment),
                           '--notebook',str(book)],capture_output=True,text=True,timeout=30)
    assert result.returncode==1,result.stderr
    data=json.loads(result.stdout)
    assert data['inspection_status']=='not_verified' and data['scheduler_ok'] is False
    assert data['discovery_coverage']['verified'] is False and data['dead_child_count'] is None


def test_public_lsf_missing_journal_retains_observed_controller(native_run,monkeypatch):
    from fungen_operator import harness as h
    run=native_run
    run.nb.cells[0].metadata.fungen.status='submitted'
    from fungen_operator import cluster
    logs=run.root/'rules';logs.mkdir()
    command=shlex.join([sys.executable,str(Path(cluster.__file__).resolve()),'submit','--scheduler','lsf','--logs',str(logs)])
    (Path(run.deployment.profile_path)/'config.yaml').write_text(yaml.safe_dump({'cluster':command}))
    obj=h.Harness.__new__(h.Harness);obj.deployment=run.deployment;obj.registry=run.deployment.registry
    obj.executor=SimpleNamespace(can_schedule=True,can_inspect=True,logs=lambda *a:{})
    monkeypatch.setattr(h,'Notebook',lambda *a:SimpleNamespace(read=lambda:run.nb))
    monkeypatch.setattr('fungen_operator.cluster.job_status',lambda scheduler,job,**kw:'running')
    result=obj.inspect(SimpleNamespace(notebook='/unused',dead_child_grace_minutes=0,paths=[]))
    assert result['scheduler_ok'] is False and result['dead_child_count'] is None
    assert result['inspection_status']=='not_verified' and result['discovery_coverage']['verified'] is False
    assert result['jobs']['100']['status']=='RUN'
    assert 'submissions.jsonl' in result['discovery_coverage']['reason']


def test_lsf_uses_the_common_positive_journal_verifier(native_scheduler_run):
    """The same graph/stream proof works for LSF; query success alone does not."""
    run=native_scheduler_run
    from fungen_operator import cluster
    d=run.deployment.model_copy(update={'backend':'lsf'})
    profile=Path(d.profile_path)/'config.yaml'
    command=shlex.join([sys.executable,str(Path(cluster.__file__).resolve()),'submit','--scheduler','lsf','--logs',str(run.logs)])
    profile.write_text(yaml.safe_dump({'cluster':command}))
    records=[json.loads(line) for line in run.journal.read_text().splitlines()]
    run.journal.write_text(''.join(json.dumps(dict(row,scheduler='lsf'))+'\n' for row in records))
    calls=[]
    def runner(cmd,**kwargs):
        calls.append(cmd);assert cmd[0]=='bjobs'
        job=cmd[-1];state={'running':'RUN','success':'DONE','failed':'EXIT'}[run.states[job]]
        return SimpleNamespace(returncode=0,stdout=state+'\n',stderr='')
    result=inspect_jobs(d,run.nb,runner=runner,now=run.now,require_coverage=True)
    assert result['coverage']==dict(verified=True,controllers=1,wrappers=1,tasks=1)
    assert result['scheduler_ok'] is True and result['count']==1
    assert set(result['jobs'])=={'100','101','102'}
    assert len(calls)==3
    # Controller-only historical journals cannot account for emitted wrappers.
    run.journal.write_text(''.join(json.dumps(dict(row,scheduler='lsf'))+'\n' for row in records if row['kind']=='controller'))
    result=inspect_jobs(d,run.nb,runner=runner,now=run.now,require_coverage=True)
    assert result['coverage']['verified'] is False and result['scheduler_ok'] is False
    assert result['count'] is None
    assert 'Controller stream does not establish' in result['coverage']['reason']


@pytest.mark.parametrize('stream,content',[
    ('controller',''),('wrapper',''),
    ('controller',"Submitted job 4 with external jobid '101'"),
    ('controller','Submitted job 4 with unrecognized receipt data\n'),
    ('wrapper','INFO: t0123456789abcdef submitted to fungen_sge with job id\n'),
    ('wrapper','workflow noise without submission evidence\n')])
def test_readable_incomplete_native_stream_never_claims_coverage(native_scheduler_run,stream,content):
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run
    path=run.root/'controller.100.err' if stream=='controller' else run.logs/'101.err'
    path.write_text(content)
    with pytest.raises(NativeDiscoveryIncomplete) as error:
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert error.value.coverage_verified is False
    assert error.value.observed_jobs['100']['status']=='RUN'
    if stream=='wrapper':assert error.value.observed_jobs['101']['status']=='RUN'


def test_unfinished_native_submission_intent_is_unverified(native_scheduler_run):
    from fungen_operator.cluster import journal_event
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run
    journal_event(run.journal,event='intent',kind='wrapper',controller='100',parent='100',scheduler=run.deployment.backend,attempt='unresolved',snakemake_job_id='5',rule='test')
    with pytest.raises(NativeDiscoveryIncomplete,match='intent has no complete receipt'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_positive_child_free_wrapper_requires_closed_native_boundary(native_scheduler_run):
    from fungen_operator.cluster import journal_event
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run
    records=[json.loads(line) for line in run.journal.read_text().splitlines()]
    run.journal.write_text(''.join(json.dumps(r)+'\n' for r in records if r['kind']!='child'))
    (run.logs/'101.err').write_text('Non-SoS rule completed.\n')
    run.states['101']='success'
    with pytest.raises(NativeDiscoveryIncomplete,match='child-free completion boundary'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    journal_event(run.journal,event='end',kind='wrapper',controller='100',parent='100',job_id='101',scheduler=run.deployment.backend,exit_code=0)
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert report['count']==0 and report['coverage']==dict(verified=True,controllers=1,wrappers=1,tasks=0)
    assert report['jobs']['101']['status']=='DONE'


def test_positive_zero_rule_controller_requires_closed_native_boundary(native_scheduler_run):
    from fungen_operator.cluster import journal_event
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run
    records=[json.loads(line) for line in run.journal.read_text().splitlines()]
    run.journal.write_text(''.join(json.dumps(r)+'\n' for r in records if r['kind']=='controller'))
    (run.root/'controller.100.err').write_text('Nothing to be done (all requested files are present and up to date).\n')
    run.states['100']='success'
    with pytest.raises(NativeDiscoveryIncomplete,match='zero-submission completion boundary'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    journal_event(run.journal,event='end',kind='controller',controller='100',job_id='100',scheduler=run.deployment.backend,exit_code=0)
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert report['count']==0 and report['coverage']==dict(verified=True,controllers=1,wrappers=0,tasks=0)


def test_partial_valid_stream_cannot_hide_a_second_receipt(native_scheduler_run):
    from fungen_operator.cluster import journal_event
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run
    event=dict(kind='child',controller='100',parent='101',scheduler=run.deployment.backend,attempt='second',task_id='tsecond')
    journal_event(run.journal,event='intent',**event)
    journal_event(run.journal,event='receipt',job_id='103',**event)
    with pytest.raises(NativeDiscoveryIncomplete,match='Wrapper stream does not establish'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_native_journal_change_during_status_queries_is_incomplete(native_scheduler_run,monkeypatch):
    from fungen_operator import cluster
    from fungen_operator.run_jobs import NativeDiscoveryIncomplete
    run=native_scheduler_run;read=cluster.journal_records;calls=[]
    def changing(path,controllers):
        calls.append(1)
        if len(calls)==2:
            cluster.journal_event(path,event='intent',kind='child',controller='100',parent='101',scheduler=run.deployment.backend,attempt='new',task_id='tnew')
        return read(path,controllers)
    monkeypatch.setattr(cluster,'journal_records',changing)
    with pytest.raises(NativeDiscoveryIncomplete,match='Submission set changed'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_native_profile_cannot_bypass_submission_journaling(native_scheduler_run):
    run=native_scheduler_run
    path=Path(run.deployment.profile_path)/'config.yaml'
    doc=yaml.safe_load(path.read_text());doc['cluster']=doc['cluster'].replace('cluster.py','untracked.py');path.write_text(yaml.safe_dump(doc))
    with pytest.raises(RuntimeError,match='canonical tracked cluster adapter'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_native_task_host_cannot_bypass_submission_journaling(native_scheduler_run):
    run=native_scheduler_run
    host=run.root/'untracked.yaml';host.write_text(yaml.safe_dump({'hosts':{'bad':{'queue_type':'pbs','submit_cmd':'qsub -terse {job_file}'}}}))
    path=run.root/'config.yaml';doc=yaml.safe_load(path.read_text());doc['minerva']=str(host);path.write_text(yaml.safe_dump(doc))
    with pytest.raises(RuntimeError,match='SoS task host does not use the canonical tracked'):
        inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)


def test_local_deployment_never_selects_lsf_inspection(tmp_path):
    original=create_fixture(tmp_path/'local-layout')
    deployment=Deployment.model_validate({**original.model_dump(),'backend':'local'})
    with pytest.raises(ValueError,match='not applicable to backend local'):
        inspect_jobs(deployment,nbformat.v4.new_notebook(),runner=lambda *a,**k:pytest.fail('local backend selected LSF'))


def test_lsf_canonical_adapter_receipts_link_exact_native_children(native_run):
    from fungen_operator import cluster
    run=native_run
    logs=run.root/'logs/rules';logs.mkdir(parents=True)
    profile=Path(run.deployment.profile_path)
    (profile/'config.yaml').write_text(yaml.safe_dump({'cluster':shlex.join([
        sys.executable,str(Path(cluster.__file__).resolve()),'submit','--scheduler','lsf','--logs',str(logs)])}))
    Path(str(run.root/'controller')+'.100.err').write_text("Submitted job 4 with external jobid '101'.\n")
    (logs/'101.out').write_text('INFO: t47c2496b7e5a91cb submitted to premium with job id 102\n')
    (logs/'101.err').write_text('')
    run.records[1]['OUTPUT_FILE']=str(logs/'101.out')
    report=inspect_jobs(run.deployment,run.nb,runner=run.runner,now=run.now)
    assert all(report['jobs'][job]['membership'] for job in ('100','101','102'))
    assert report['count']==1 and report['dead_children'][0]['wrapper_job_id']=='101'
