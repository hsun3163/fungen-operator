import json
import subprocess

import pytest

from fungen_operator import cluster


def jobscript(tmp_path, threads=4):
    props={'type':'single','jobid':4,'rule':'finemapping','threads':threads,'resources':{'mem_mb':8000,'runtime':90}}
    path=tmp_path/'job.sh';path.write_text('#!/bin/bash\n# properties = '+json.dumps(props)+'\necho hi\n')
    return str(path)


def fake_run(monkeypatch, *results):
    calls=[];queue=list(results)
    def run(cmd,**kw):
        calls.append(cmd);rc,out=queue.pop(0)
        return subprocess.CompletedProcess(cmd,rc,out,'')
    monkeypatch.setattr(cluster.subprocess,'run',run)
    return calls


def test_sge_submit_builds_native_qsub(tmp_path, monkeypatch, capsys):
    native_tracking(monkeypatch,tmp_path/'logs')
    calls=fake_run(monkeypatch,(0,'12345\n'))
    logs=tmp_path/'logs'
    cluster.main(['submit','--scheduler','sge','--account','xqtl','--logs',str(logs),jobscript(tmp_path)])
    cmd=calls[0]
    assert cmd[:8]==['qsub','-terse','-S','/bin/bash','-N','finemapping','-P','xqtl']
    assert cmd[cmd.index('-pe')+1:cmd.index('-pe')+3]==['smp','4']
    assert cmd[cmd.index('-l')+1]=='h_vmem=2000M,h_rt=1:30:00'
    assert cmd[cmd.index('-o')+1]==str(logs/'$JOB_ID.out') and cmd[cmd.index('-e')+1]==str(logs/'$JOB_ID.err')
    assert '-q' not in cmd and cmd[-1].endswith('job.sh')
    assert capsys.readouterr().out=='12345\n'


def test_sge_single_slot_without_project_omits_pe_and_project(tmp_path, monkeypatch, capsys):
    native_tracking(monkeypatch,tmp_path/'logs')
    calls=fake_run(monkeypatch,(0,'77\n'))
    cluster.main(['submit','--scheduler','sge','--account','','--logs',str(tmp_path/'logs'),jobscript(tmp_path,1)])
    assert '-pe' not in calls[0] and '-P' not in calls[0] and 'h_vmem=8000M,h_rt=1:30:00' in calls[0]
    assert capsys.readouterr().out=='77\n'


@pytest.mark.parametrize('results,expected',[
    ([(0,'job_number: 5\n')],'running'),
    ([(1,''),(0,'jobnumber    5\ntaskid       undefined\nfailed       0    \nexit_status  0\n')],'success'),
    ([(1,''),(0,'jobnumber    5\ntaskid       undefined\nfailed       0    \nexit_status  1\n')],'failed'),
    ([(1,''),(0,'jobnumber    5\ntaskid       undefined\nfailed       100  : assumedly after job\nexit_status  0\n')],'failed'),
    ([(1,''),(0,'jobnumber    5\ntaskid       undefined\nfailed       0\nexit_status  1\n================================\njobnumber 5\ntaskid undefined\nfailed       0\nexit_status  0\n')],'failed'),
])
def test_sge_status(tmp_path, monkeypatch, capsys, results, expected):
    calls=fake_run(monkeypatch,*results)
    cluster.main(['status','--scheduler','sge','--logs',str(tmp_path),'5'])
    assert capsys.readouterr().out.strip()==expected
    assert calls[0]==['qstat','-j','5'] and all(c==['qacct','-j','5'] for c in calls[1:])


def test_sge_status_requires_accounting(tmp_path, monkeypatch):
    fake_run(monkeypatch,(1,''),(1,''))
    with pytest.raises(RuntimeError,match='qstat/qacct'):
        cluster.main(['status','--scheduler','sge','--logs',str(tmp_path),'5'])


def test_lsf_and_slurm_submit_unchanged(tmp_path, monkeypatch, capsys):
    native_tracking(monkeypatch,tmp_path/'logs')
    calls=fake_run(monkeypatch,(0,'Job <42> is submitted to queue <premium>.\n'),(0,'43\n'))
    script=jobscript(tmp_path)
    cluster.main(['submit','--scheduler','lsf','--logs',str(tmp_path/'logs'),script])
    jobscript(tmp_path)  # A separate scheduler submission owns a fresh native script.
    cluster.main(['submit','--scheduler','slurm','--logs',str(tmp_path/'logs'),script])
    assert calls[0][0]=='bsub' and calls[0][-2:]==['bash',script]
    assert calls[1][:2]==['sbatch','--parsable'] and calls[1][-1]==script
    assert capsys.readouterr().out=='42\n43\n'


def test_sge_rejects_array_receipt(tmp_path,monkeypatch):
    native_tracking(monkeypatch,tmp_path)
    fake_run(monkeypatch,(0,'77.1-10:1\n'))
    with pytest.raises(RuntimeError,match='array or ambiguous receipt unsupported'):
        cluster.main(['submit','--scheduler','sge','--logs',str(tmp_path),jobscript(tmp_path)])


@pytest.mark.parametrize('accounting',[
    'jobnumber 5\ntaskid undefined\nfailed 0\n',
    'jobnumber 6\ntaskid undefined\nfailed 0\nexit_status 0\n',
    'jobnumber 5\ntaskid 1\nfailed 0\nexit_status 0\n',
    'jobnumber 5\ntaskid undefined\nfailed 0\nexit_status 0\n====\njobnumber 5\ntaskid undefined\nfailed 0\n'])
def test_sge_unknown_identity_or_incomplete_records_block(tmp_path,monkeypatch,accounting):
    fake_run(monkeypatch,(1,''),(0,accounting))
    with pytest.raises(RuntimeError):cluster.main(['status','--scheduler','sge','--logs',str(tmp_path),'5'])


def test_sge_failed_array_task_is_never_hidden_by_success(tmp_path,monkeypatch,capsys):
    text='jobnumber 5\ntaskid 1\nfailed 0\nexit_status 1\n====\njobnumber 5\ntaskid 2\nfailed 0\nexit_status 0\n'
    fake_run(monkeypatch,(1,''),(0,text))
    cluster.main(['status','--scheduler','sge','--logs',str(tmp_path),'5'])
    assert capsys.readouterr().out.strip()=='failed'


def test_sge_live_error_is_failed(tmp_path,monkeypatch,capsys):
    fake_run(monkeypatch,(0,'job_number: 5\nerror reason 1: unable to start job\n'))
    cluster.main(['status','--scheduler','sge','--logs',str(tmp_path),'5'])
    assert capsys.readouterr().out.strip()=='failed'


@pytest.mark.parametrize('scheduler,result',[
    ('lsf',(1,'PEND')),('lsf',(0,'unrecognized')),('sge',(0,'')),('sge',(0,'job_number: 6\n'))])
def test_failed_or_ambiguous_native_query_is_never_running(monkeypatch,scheduler,result):
    fake_run(monkeypatch,result)
    with pytest.raises(RuntimeError):cluster.job_status(scheduler,'5')


@pytest.mark.parametrize('results,expected',[
    ([(0,'5|RUNNING\n')],'running'),
    ([(0,''),(0,'5|COMPLETED|0:0\n5.batch|COMPLETED|0:0\n')],'success'),
    ([(0,''),(0,'5.batch|FAILED|1:0\n5|COMPLETED|0:0\n')],'failed'),
    ([(0,''),(0,'5|COMPLETED|1:0\n')],'failed')])
def test_slurm_status_uses_identified_live_and_accounted_records(monkeypatch,results,expected):
    calls=fake_run(monkeypatch,*results)
    assert cluster.job_status('slurm','5')==expected
    assert calls[0]==['squeue','-h','-j','5','-o','%i|%T']
    if len(calls)>1:assert calls[1]==['sacct','-j','5','--format=JobIDRaw,State,ExitCode','--noheader','--parsable2']


@pytest.mark.parametrize('results',[
    [(0,'6|RUNNING\n')],[(0,'5|UNKNOWN\n')],[(0,''),(0,'')],
    [(0,''),(0,'5.batch|COMPLETED|0:0\n')],[(0,''),(0,'6|COMPLETED|0:0\n')],
    [(0,''),(0,'5|COMPLETED|unknown\n')]])
def test_slurm_unknown_identity_state_or_accounting_raises(monkeypatch,results):
    fake_run(monkeypatch,*results)
    with pytest.raises(RuntimeError):cluster.job_status('slurm','5')


def test_sge_explicit_unknown_live_state_raises(monkeypatch):
    fake_run(monkeypatch,(0,'job_number: 5\njob_state: UNKNOWN\n'))
    with pytest.raises(RuntimeError,match='Unknown SGE live state'):cluster.job_status('sge','5')


def native_tracking(monkeypatch,logs):
    monkeypatch.setenv('FUNGEN_CONTROLLER_ID','100')
    monkeypatch.setenv('FUNGEN_SUBMISSIONS',str(logs/'submissions.jsonl'))
    monkeypatch.setenv('JOB_ID','100');monkeypatch.setenv('SLURM_JOB_ID','100');monkeypatch.setenv('LSB_JOBID','100')


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
def test_native_intent_is_durable_before_scheduler_submission(tmp_path,monkeypatch,scheduler):
    logs=tmp_path/'logs';native_tracking(monkeypatch,logs)
    calls=[]
    def submit(cmd,**kw):
        records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
        assert len(records)==1 and records[0]['event']=='intent'
        assert records[0]['kind']=='wrapper' and records[0]['snakemake_job_id']=='4'
        assert 'wrapper-start' in Path(cmd[-1]).read_text()
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd,0,'Job <101> is submitted to queue <premium>.\n' if scheduler=='lsf' else '101\n','')
    from pathlib import Path
    monkeypatch.setattr(cluster.subprocess,'run',submit)
    cluster.main(['submit','--scheduler',scheduler,'--logs',str(logs),jobscript(tmp_path)])
    records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
    assert [r['event'] for r in records]==['intent','receipt'] and records[1]['job_id']=='101'
    assert len(calls)==1


def test_failed_native_submission_keeps_unresolved_intent(tmp_path,monkeypatch):
    logs=tmp_path/'logs';native_tracking(monkeypatch,logs)
    def failed(cmd,**kw):raise subprocess.CalledProcessError(1,cmd,stderr='native scheduler failure')
    monkeypatch.setattr(cluster.subprocess,'run',failed)
    with pytest.raises(subprocess.CalledProcessError):cluster.main(['submit','--scheduler','slurm','--logs',str(logs),jobscript(tmp_path)])
    records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
    assert len(records)==1 and records[0]['event']=='intent'


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
@pytest.mark.parametrize('body,expected',[('exec /bin/true',0),('exec /bin/false',1)])
def test_native_rule_completion_survives_exec_in_job_body(tmp_path,monkeypatch,body,expected,scheduler):
    from pathlib import Path
    import os
    logs=tmp_path/'logs';native_tracking(monkeypatch,logs)
    monkeypatch.setenv({'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler],'101')
    script=tmp_path/'tracked.sh'
    script.write_text(cluster.tracked_rule('#!/bin/bash\n'+body+'\n',scheduler,logs,'100',logs/'submissions.jsonl'))
    result=subprocess.run(['bash',str(script)],env=dict(os.environ),capture_output=True,text=True)
    assert result.returncode==expected,result.stderr
    records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
    assert [row['event'] for row in records]==['begin','end']
    assert records[-1]['exit_code']==expected


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm'])
def test_task_intent_precedes_native_submit_and_receipt(tmp_path,monkeypatch,capsys,scheduler):
    logs=tmp_path/'logs';native_tracking(monkeypatch,logs)
    monkeypatch.setenv({'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler],'101')
    script=tmp_path/'tabcdef.sh';script.write_text('#!/bin/bash\n#BSUB -n 4\ntrue\n')
    def submit(cmd,**kwargs):
        records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
        assert len(records)==1 and records[0]['event']=='intent'
        assert records[0]['kind']=='child' and records[0]['parent']=='101' and records[0]['task_id']=='tabcdef'
        if scheduler=='lsf':
            assert cmd==['bsub'] and kwargs['stdin'].read()==script.read_text()
        else:assert cmd==(['qsub','-terse',str(script)] if scheduler=='sge' else ['sbatch','--parsable',str(script)])
        return subprocess.CompletedProcess(cmd,0,'Job <102> is submitted to queue <premium>.\n' if scheduler=='lsf' else '102\n','')
    monkeypatch.setattr(cluster.subprocess,'run',submit)
    cluster.main(['submit-task','--scheduler',scheduler,'--logs',str(logs),str(script)])
    records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
    assert [r['event'] for r in records]==['intent','receipt']
    assert records[1]['job_id']=='102' and records[1]['attempt']==records[0]['attempt']
    assert capsys.readouterr().out=='102\n'



def test_native_group_submission_retains_group_and_internal_identity(tmp_path,monkeypatch):
    from pathlib import Path
    logs=tmp_path/'logs';native_tracking(monkeypatch,logs)
    props={'type':'group','groupid':'native_group','jobid':'group-uuid','threads':2,'resources':{'mem_mb':4000,'runtime':1}}
    script=tmp_path/'group.sh';script.write_text('#!/bin/bash\n# properties = '+json.dumps(props)+'\ntrue\n')
    fake_run(monkeypatch,(0,'101\n'))
    cluster.main(['submit','--scheduler','sge','--logs',str(logs),str(script)])
    records=cluster.journal_records(logs/'submissions.jsonl',{'100'})
    assert records[0]['rule']=='native_group' and records[0]['snakemake_job_id']=='group-uuid'
    assert records[1]['job_id']=='101'
