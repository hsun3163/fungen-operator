"""Host acceptance of configured controller and resource-aware task-host paths.

Scheduler commands are explicit synthetic test clients. Native SoS interpolation
and the rendered bash cells execute on the host; live site acceptance is separate.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import nbformat
import pytest
import yaml

from fungen_operator import bootstrap as b, cluster, onboarding as o
from fungen_operator.actions import CheckReadiness, Deployment, InitiateRun, PrepareConfig, render
from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook


@pytest.mark.parametrize('sched,client',[('sge','qsub'),('slurm','sbatch')])
def test_handoff_and_real_host_controller_cell(tmp_path,monkeypatch,sched,client):
    deployment=create_fixture(tmp_path/'fixture')
    root=tmp_path/'setup';root.mkdir()
    c=dict(scheduler=sched,account='science',queue='',mamba='/mamba/bin/mamba',software=deployment.conda_env)
    (root/'setup.json').write_text(json.dumps(c))
    # Handoff input products are supplied by the existing fixture. Predecessor
    # science is covered by its own tests, not rerun as part of scheduler tests.
    monkeypatch.setattr(o,'check_step',lambda *a:None)
    monkeypatch.setattr(o,'ask',lambda *a:'yes')
    o.profiles(root,c)
    o.perform(root,'handoff')
    handed=Deployment.load(root/'deployment.json')
    assert handed.backend==sched
    handoff=json.loads((root/'deployment.json').read_text())
    assert handoff['backend']==sched and handoff['scheduler_account']=='science'
    assert handoff['scheduler_queue']==''
    assert str(root/'sos.yaml') in handoff['canonical_source_paths']
    deployment=deployment.model_copy(update={key:handoff[key] for key in ('backend','scheduler_account','scheduler_queue','profile_path')})
    executable=Path(deployment.conda_env)/'bin'/client
    executable.write_text(f'''#!{sys.executable}
import os,re,subprocess,sys
from pathlib import Path
script=sys.stdin.read()
assert 'bsub' not in script
prefix={'#$ -o ' if sched=='sge' else '#SBATCH --output='!r}
errprefix={'#$ -e ' if sched=='sge' else '#SBATCH --error='!r}
out=next(l[len(prefix):] for l in script.splitlines() if l.startswith(prefix)).replace('$JOB_ID','42').replace('%j','42')
err=next(l[len(errprefix):] for l in script.splitlines() if l.startswith(errprefix)).replace('$JOB_ID','42').replace('%j','42')
with open(out,'w') as stdout,open(err,'w') as stderr:
 env=dict(os.environ);env[{'JOB_ID' if sched=='sge' else 'SLURM_JOB_ID'!r}]='42'
 p=subprocess.run(['bash'],input=script,text=True,stdout=stdout,stderr=stderr,env=env)
print('42')
sys.exit(p.returncode)
''')
    executable.chmod(0o755)
    monkeypatch.setenv('PATH',str(executable.parent)+':'+os.environ['PATH'])
    monkeypatch.setenv('FUNGEN_FIXTURE_ROOT',deployment.conda_env)
    monkeypatch.setattr(cluster,'job_status',lambda scheduler,job:'success')
    executor=Executor(deployment,host_approved=True)
    harness=Harness(deployment,executor)
    args=dict(notebook=str(Path(deployment.run_root)/'operator.ipynb'),
              configfile=str(Path(deployment.run_root)/'config.yaml'),workdir=str(Path(deployment.run_root)/'work'))
    harness.prepare_config(harness.propose_config(PrepareConfig(**args)))
    kwargs=dict(args,log_dir=str(Path(deployment.run_root)/'logs'),targets=['all'],workflow_cores=1,walltime_minutes=60)
    ready=harness.run('check_readiness',CheckReadiness(**kwargs))
    assert ready['status']=='ready' and ready['job_id']=='42'
    result=harness.run('initiate_run',InitiateRun(**kwargs))
    assert result['status']=='submitted' and result['scheduler']['status']=='DONE'
    nb=Notebook(args['notebook'],deployment.registry).read()
    cells=[c for c in nb.cells if c.cell_type=='code' and c.metadata.fungen.action!='prepare_config']
    assert all(c.metadata.fungen.slots.bindings.scheduler==sched for c in cells)
    assert all(client in c.source and 'bsub' not in c.source for c in cells)
    assert (Path(args['workdir'])/'output/result.txt').is_file()


@pytest.mark.parametrize('sched',['sge','slurm'])
def test_native_task_host_interpolates_declared_resources(tmp_path,sched):
    sos_python=os.environ.get('FUNGEN_TEST_SOS_PYTHON') or shutil.which('python')
    assert sos_python, 'Provide host SoS and sos-pbs; set FUNGEN_TEST_SOS_PYTHON to its Python'
    c=dict(scheduler=sched,account='science',queue='',software=str(Path(sos_python).parent.parent))
    o.profiles(tmp_path,c)
    host=yaml.safe_load((tmp_path/'sos.yaml').read_text())['hosts'][o.task_queue(c)]
    values=dict(task='tsynthetic',cores=4,mem=8589934592,walltime='01:00:00',workdir=str(tmp_path/'work'),command='true')
    code='import json,sys; from sos.eval import cfg_interpolate; d=json.load(sys.stdin); print(cfg_interpolate(d["template"],d["values"]))'
    result=subprocess.run([sos_python,'-c',code],input=json.dumps(dict(template=host['task_template'],values=values)),
                          capture_output=True,text=True,check=True,timeout=30)
    script=result.stdout
    subprocess.run(['bash','-n'],input=script,text=True,check=True)
    if sched=='sge':assert '#$ -pe smp 4' in script and 'h_vmem=2048M' in script and '#$ -P science' in script
    else:assert '--cpus-per-task=4' in script and '--mem=8192M' in script and '--account=science' in script
    assert '01:00:00' in script and script.endswith('true\n\n')


@pytest.mark.parametrize('scheduler',["sge","slurm"])
def test_executor_queries_configured_scheduler(tmp_path,monkeypatch,scheduler):
    d=create_fixture(tmp_path/'fixture').model_copy(update={'backend':scheduler})
    calls=[]
    monkeypatch.setattr(cluster,'job_status',lambda sched,job:calls.append((sched,job)) or 'success')
    result=Executor(d,host_approved=True).scheduler('42')
    assert calls==[(scheduler,'42')] and result['status']=='DONE' and result['exit_code']==0


@pytest.mark.parametrize('scheduler',['sge','slurm'])
def test_serve_retains_receipt_and_does_not_duplicate_pending_launch(tmp_path,monkeypatch,scheduler):
    config=dict(install=str(tmp_path),backend='local',scheduler=scheduler,model='laguna-xs-2.1:q4_K_M')
    (tmp_path/f'serve.{scheduler}.sh').write_text('#!/bin/bash\n')
    calls=[]
    monkeypatch.setattr(b,'run',lambda cmd,**kw:calls.append(cmd) or SimpleNamespace(stdout='42\n'))
    monkeypatch.setattr(cluster,'job_status',lambda *a:'running')
    b.serve(config)
    assert json.loads((tmp_path/'server-request.json').read_text())==dict(scheduler=scheduler,job_id='42')
    b.serve(config)
    assert len(calls)==1 and calls[0][0]==('qsub' if scheduler=='sge' else 'sbatch')


def test_failed_launch_status_prevents_duplicate_serve(tmp_path,monkeypatch):
    (tmp_path/'server-request.json').write_text(json.dumps(dict(scheduler='sge',job_id='42')))
    def unavailable(*a):raise RuntimeError('qacct retrieval failed')
    monkeypatch.setattr(cluster,'job_status',unavailable)
    monkeypatch.setattr(b,'run',lambda *a,**k:pytest.fail('duplicate submission after failed status retrieval'))
    with pytest.raises(RuntimeError,match='Launch status retrieval failed: qacct retrieval failed'):
        b.serve(dict(install=str(tmp_path),scheduler='sge',backend='local',model='m'))


def test_stale_server_state_does_not_verify_new_launch(tmp_path,monkeypatch):
    (tmp_path/'server.json').write_text(json.dumps(dict(model='m',ready=True,endpoint='http://old',job_id='41')))
    (tmp_path/'server-request.json').write_text(json.dumps(dict(scheduler='sge',job_id='42')))
    monkeypatch.setattr(cluster,'job_status',lambda *a:'running')
    monkeypatch.setattr(b,'api',lambda *a:pytest.fail('stale endpoint queried'))
    good,info,detail=b.runtime_status(dict(install=str(tmp_path),scheduler='sge',model='m'))
    assert good is None and info=={} and 'stale' in detail


@pytest.mark.parametrize('sched',['sge','slurm'])
def test_native_sos_task_executes_through_generated_host(tmp_path,sched):
    sos_python=os.environ.get('FUNGEN_TEST_SOS_PYTHON') or shutil.which('python')
    assert sos_python, 'Provide host SoS and sos-pbs; set FUNGEN_TEST_SOS_PYTHON'
    c=dict(scheduler=sched,account='science',queue='',software=str(Path(sos_python).parent.parent))
    o.profiles(tmp_path,c)
    clients=tmp_path/'clients';clients.mkdir()
    # Explicit synthetic submit client executes the generated resource-bearing
    # job script on this host. All SoS task logic and result checks remain real.
    submit=clients/('qsub' if sched=='sge' else 'sbatch')
    submit.write_text(f"""#!{sys.executable}
import subprocess,sys
from pathlib import Path
script=Path(sys.argv[-1]).read_text()
assert {'#$ -pe smp 2' if sched=='sge' else '#SBATCH --cpus-per-task=2'!r} in script
with open({str(tmp_path/'task-native.log')!r},'a') as log:
 p=subprocess.run(['bash',sys.argv[-1]],stdout=log,stderr=log)
print('42')
sys.exit(p.returncode)
""")
    submit.chmod(0o755)
    for name in ('qstat','squeue'):
        path=clients/name;path.write_text('#!/bin/sh\nexit 1\n');path.chmod(0o755)
    product=tmp_path/'task-proof.txt'
    workflow=tmp_path/'proof.sos'
    workflow.write_text('[proof]\noutput: '+repr(str(product))+"\ntask: cores=2, mem='64M', walltime='00:01:00'\nrun: expand=True\n    printf 'native task complete' > {_output:q}\n")
    home=o.guided_run(tmp_path)/'work/sos_runtime/home'
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),
             PATH=str(clients)+':'+str(Path(sos_python).parent)+':'+os.environ['PATH'],
             FUNGEN_CONTROLLER_ID='100',FUNGEN_SUBMISSIONS=str(o.guided_run(tmp_path)/'work/logs/rules/submissions.jsonl'))
    env['JOB_ID' if sched=='sge' else 'SLURM_JOB_ID']='101'
    result=subprocess.run([sos_python,'-m','sos','run',str(workflow),'-c',str(tmp_path/'sos.yaml'),
                    '-q',o.task_queue(c),'-J','1','-j','1'],env=env,cwd=tmp_path,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert product.read_text()=='native task complete'
    records=cluster.journal_records(o.guided_run(tmp_path)/'work/logs/rules/submissions.jsonl',{'100'})
    assert [r['event'] for r in records]==['intent','receipt']
    assert records[1]['kind']=='child' and records[1]['parent']=='101' and records[1]['job_id']=='42'


def test_registered_lsf_account_queue_are_rendered(tmp_path):
    d=create_fixture(tmp_path/'fixture').model_copy(update={'backend':'lsf','scheduler_account':'acc_science','scheduler_queue':'express'})
    args=CheckReadiness(notebook=str(Path(d.run_root)/'run.ipynb'),configfile=str(Path(d.run_root)/'config.yaml'),
                        workdir=str(Path(d.run_root)/'work'),log_dir=str(Path(d.run_root)/'logs'),targets=['all'])
    source=render('check_readiness',dict(arguments=args.model_dump(),bindings=d.runtime_bindings(str(Path(d.run_root)/'logs/a'))))
    assert '#BSUB -P acc_science' in source and '#BSUB -q express' in source
    assert '#BSUB -P acc_LOAD' not in source
    assert 'controller-start --scheduler lsf' in source and 'FUNGEN_SUBMISSIONS' in source


@pytest.mark.parametrize('ready',[False,True])
def test_legacy_lsf_receipt_reuses_verified_launch(tmp_path,monkeypatch,ready):
    request=tmp_path/'server-request.json';request.write_text('{"job_id":"42"}')
    stamp=request.stat().st_mtime_ns
    c=dict(install=str(tmp_path),backend='local',scheduler='lsf',model='m')
    if ready:(tmp_path/'server.json').write_text(json.dumps(dict(model='m',ready=True,endpoint='http://gpu',job_id='42')))
    calls=[]
    monkeypatch.setattr(cluster,'job_status',lambda sched,job:calls.append((sched,job)) or 'running')
    monkeypatch.setattr(b,'api',lambda *a:{'models':[{'name':'m'}]})
    monkeypatch.setattr(b,'run',lambda *a,**k:pytest.fail('duplicate legacy launch'))
    b.serve(c)
    assert calls==[('lsf','42')]
    assert request.read_text()=='{"job_id":"42"}' and request.stat().st_mtime_ns==stamp


def test_terminal_legacy_lsf_receipt_allows_one_native_restart(tmp_path,monkeypatch):
    (tmp_path/'server-request.json').write_text('{"job_id":42}')
    (tmp_path/'serve.lsf.sh').write_text('#!/bin/bash\n')
    monkeypatch.setattr(cluster,'job_status',lambda *a:'success')
    calls=[];monkeypatch.setattr(b,'run',lambda cmd,**kw:calls.append(cmd) or SimpleNamespace(stdout='Job <43> is submitted.\n'))
    b.serve(dict(install=str(tmp_path),backend='local',scheduler='lsf',model='m'))
    assert calls==[['bsub']]
    assert json.loads((tmp_path/'server-request.json').read_text())==dict(job_id='43',scheduler='lsf')


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
def test_legacy_receipt_unknown_or_wrong_scheduler_blocks_submission(tmp_path,monkeypatch,scheduler):
    (tmp_path/'server-request.json').write_text('{"job_id":42}')
    def unavailable(*a):raise RuntimeError('native job status unavailable')
    monkeypatch.setattr(cluster,'job_status',unavailable)
    monkeypatch.setattr(b,'run',lambda *a,**k:pytest.fail('blind legacy resubmission'))
    with pytest.raises(RuntimeError,match='native job status unavailable|Legacy server receipt belongs to LSF'):
        b.serve(dict(install=str(tmp_path),backend='local',scheduler=scheduler,model='m'))


def test_real_local_replay_continues_after_synchronous_completion(tmp_path,monkeypatch):
    d=create_fixture(tmp_path/'fixture').model_copy(update={'backend':'local'})
    monkeypatch.setenv('FUNGEN_FIXTURE_ROOT',d.conda_env)
    executor=Executor(d,host_approved=True)
    monkeypatch.setattr(executor,'scheduler',lambda *a:pytest.fail('local synchronous action queried a scheduler'))
    h=Harness(d,executor)
    args=dict(notebook=str(Path(d.run_root)/'operator.ipynb'),configfile=str(Path(d.run_root)/'config.yaml'),workdir=str(Path(d.run_root)/'work'))
    h.prepare_config(h.propose_config(PrepareConfig(**args)))
    run=dict(args,log_dir=str(Path(d.run_root)/'logs'),targets=['all'],workflow_cores=1,walltime_minutes=60)
    assert h.run('check_readiness',CheckReadiness(**run))['status']=='ready'
    assert h.run('initiate_run',InitiateRun(**run))['status']=='completed'
    assert h.run('check_readiness',CheckReadiness(**run,phase='conclusion'))['status']=='nothing_to_do'
    result=h.replay(args['notebook'])
    assert [x['status'] for x in result]==['materialized','nothing_to_do','completed','nothing_to_do']
    assert 'job_id' not in result[2]
    assert (Path(args['workdir'])/'output/result.txt').is_file()


def local_launch_fixture(tmp_path):
    request=tmp_path/'server-request.json';request.write_text(json.dumps(dict(scheduler='local',pid=22)))
    (tmp_path/'server.json').write_text(json.dumps(dict(model='m',ready=True,endpoint='http://broken',job_id='')))
    (tmp_path/'serve.local.sh').write_text('#!/bin/bash\n')
    return dict(install=str(tmp_path),backend='local',scheduler='local',model='m'),request


def test_live_local_pid_with_failed_endpoint_reports_failure_without_relaunch(tmp_path,monkeypatch):
    c,request=local_launch_fixture(tmp_path);before=(request.read_bytes(),request.stat().st_mtime_ns)
    monkeypatch.setattr(b,'local_process_identity',lambda pid:dict(process_start='100',boot_id='boot'))
    def broken(*a):raise OSError('endpoint connection refused')
    monkeypatch.setattr(b,'api',broken)
    monkeypatch.setattr(b.subprocess,'Popen',lambda *a,**k:pytest.fail('duplicate live local server'))
    observed=b.runtime_observation(c)
    assert observed.ready is False and observed.launch=='running'
    with pytest.raises(RuntimeError,match='endpoint connection refused.*live launch'):b.serve(c)
    assert (request.read_bytes(),request.stat().st_mtime_ns)==before


def test_vanished_local_pid_permits_one_fresh_launch_and_replaces_identity(tmp_path,monkeypatch):
    c,request=local_launch_fixture(tmp_path);calls=[]
    identity=dict(process_start='300',boot_id='new-boot')
    monkeypatch.setattr(b,'local_process_identity',lambda pid:None if int(pid)==22 else identity)
    monkeypatch.setattr(b,'api',lambda *a:pytest.fail('queried stale endpoint for vanished process'))
    monkeypatch.setattr(b.subprocess,'Popen',lambda *a,**k:calls.append((a,k)) or SimpleNamespace(pid=33))
    b.serve(c)
    assert len(calls)==1 and calls[0][1]['start_new_session'] is True
    assert json.loads(request.read_text())==dict(scheduler='local',pid=33,**identity)


def test_local_pid_permission_failure_is_unknown_and_blocks_restart(tmp_path,monkeypatch):
    c,request=local_launch_fixture(tmp_path);before=request.read_bytes()
    def denied(pid):raise PermissionError('cannot inspect local PID')
    monkeypatch.setattr(b,'local_process_identity',denied)
    monkeypatch.setattr(b.subprocess,'Popen',lambda *a,**k:pytest.fail('unknown PID triggered restart'))
    with pytest.raises(RuntimeError,match='Launch status retrieval failed: cannot inspect local PID'):b.serve(c)
    assert request.read_bytes()==before


def test_reused_local_pid_is_distinguished_by_birth_identity(tmp_path,monkeypatch):
    c,request=local_launch_fixture(tmp_path)
    request.write_text(json.dumps(dict(scheduler='local',pid=22,process_start='100',boot_id='boot')))
    (tmp_path/'server.json').write_text(json.dumps(dict(model='m',ready=True,endpoint='http://stale',job_id='')))
    monkeypatch.setattr(b,'local_process_identity',lambda pid:dict(process_start='200' if int(pid)==22 else '300',boot_id='boot'))
    monkeypatch.setattr(b,'api',lambda *a:pytest.fail('reused PID validated stale endpoint'))
    calls=[];monkeypatch.setattr(b.subprocess,'Popen',lambda *a,**k:calls.append(a) or SimpleNamespace(pid=33))
    b.serve(c)
    assert len(calls)==1 and json.loads(request.read_text())['process_start']=='300'


def test_process_lookup_failure_is_positive_not_running(monkeypatch):
    def gone(*a):raise ProcessLookupError('process vanished')
    monkeypatch.setattr(b.os,'kill',gone)
    assert b.local_process_identity(22) is None


def test_live_host_process_birth_identity_is_stable():
    first=b.local_process_identity(os.getpid());second=b.local_process_identity(os.getpid())
    assert first==second and first['process_start'].isdecimal() and first['boot_id']


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
def test_real_native_adapter_journal_establishes_complete_discovery(tmp_path,monkeypatch,scheduler):
    from fungen_operator.run_jobs import inspect_jobs
    d=create_fixture(tmp_path/'layout').model_copy(update={'backend':scheduler})
    root=Path(d.run_root);logs=o.guided_run(root)/'work/logs/rules'
    sos_python=os.environ.get('FUNGEN_TEST_SOS_PYTHON') or shutil.which('python')
    c=dict(scheduler=scheduler,account='science',queue='premium' if scheduler=='lsf' else '',software=str(Path(sos_python).parent.parent))
    o.profiles(root,c);profile=root/'profiles'/scheduler
    d=d.model_copy(update={'profile_path':str(profile)})
    cfg=root/'config.yaml';cfg.write_text(yaml.safe_dump({'runtime_home':str(o.guided_run(root)/'work/sos_runtime/home')}))
    clients=root/'clients';clients.mkdir();client=clients/({'lsf':'bsub','sge':'qsub','slurm':'sbatch'}[scheduler])
    native_env={'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler]
    client.write_text(f"""#!{sys.executable}
import os,subprocess,sys
from pathlib import Path
path=Path(sys.argv[-1]) if len(sys.argv)>1 else Path({str(root/'child.sh')!r})
if len(sys.argv)==1:path.write_text(sys.stdin.read())
script=path.read_text();rule='# properties =' in script
job='101' if rule else '102'
env=dict(os.environ);env[{native_env!r}]=job
logroot=Path({str(logs)!r});logroot.mkdir(parents=True,exist_ok=True)
with (logroot/(job+'.out')).open('w') as out,(logroot/(job+'.err')).open('w') as err:
 p=subprocess.run(['bash',str(path)],env=env,stdout=out,stderr=err)
print('Job <'+job+'> is submitted to queue <premium>.' if {scheduler!r}=='lsf' else job)
sys.exit(p.returncode)
""");client.chmod(0o755)
    monkeypatch.setenv('PATH',str(clients)+':'+str(Path(sos_python).parent)+':'+os.environ['PATH'])
    monkeypatch.setenv('JOB_ID','100');monkeypatch.setenv('SLURM_JOB_ID','100')
    monkeypatch.setenv('LSB_JOBID','100')
    monkeypatch.setenv('HOME',str(o.guided_run(root)/'work/sos_runtime/home'))
    monkeypatch.setenv('FUNGEN_CONTROLLER_ID','100');monkeypatch.setenv('FUNGEN_SUBMISSIONS',str(logs/'submissions.jsonl'))
    import contextlib,io
    output=io.StringIO()
    with contextlib.redirect_stdout(output):cluster.main(['controller-start','--scheduler',scheduler,'--profile',str(profile)])
    assert output.getvalue().strip()==str(logs/'submissions.jsonl')
    proof=root/'proof.txt';workflow=root/'proof.sos'
    workflow.write_text('[proof]\noutput: '+repr(str(proof))+"\ntask: cores=1, mem='64M', walltime='00:01:00'\nrun: expand=True\n    printf complete > {_output:q}\n")
    task_command=b.shlex.join([sos_python,'-m','sos','run',str(workflow),'-c',str(root/'sos.yaml'),'-q',o.task_queue(c),'-J','1','-j','1'])
    rule=root/'rule.sh';props={'type':'single','rule':'proof','jobid':4,'threads':1,'resources':{'mem_mb':4000,'runtime':1}}
    rule.write_text('#!/bin/bash\n# properties = '+json.dumps(props)+'\n'+task_command+'\n')
    output=io.StringIO()
    with contextlib.redirect_stdout(output):cluster.main(['submit','--scheduler',scheduler,'--logs',str(logs),str(rule)])
    assert output.getvalue().strip()=='101' and proof.read_text()=='complete'
    cluster.main(['controller-end','--scheduler',scheduler,'--logs',str(logs),'0'])
    stem=root/'controller';Path(str(stem)+'.100.out').write_text('')
    Path(str(stem)+'.100.err').write_text("Submitted job 4 with external jobid '101'.\n")
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('',metadata={'fungen':{'action':'initiate_run','slots':{'arguments':{'workdir':str(root),'configfile':str(cfg)},'bindings':{'log_stem':str(stem)}},'result':{'job_id':'100'}}})])
    def accounted(cmd,**kw):
        if cmd[0]=='bjobs':return subprocess.CompletedProcess(cmd,0,'DONE\n','')
        job=cmd[2] if cmd[0] in ('qstat','qacct','sacct') else cmd[cmd.index('-j')+1]
        if cmd[0]=='qstat':return subprocess.CompletedProcess(cmd,1,'','')
        text=(f'jobnumber {job}\ntaskid undefined\nfailed 0\nexit_status 0\n' if cmd[0]=='qacct' else '' if cmd[0]=='squeue' else f'{job}|COMPLETED|0:0\n')
        return subprocess.CompletedProcess(cmd,0,text,'')
    report=inspect_jobs(d,nb,runner=accounted,require_coverage=True)
    assert report['coverage']==dict(verified=True,controllers=1,wrappers=1,tasks=1)
    assert report['count']==0 and report['jobs']['102']['sos_state']=='completed'
