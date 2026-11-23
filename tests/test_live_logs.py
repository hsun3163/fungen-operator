from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from fungen_operator.execution import Executor
from fungen_operator.cluster import profile_logs


def test_live_lsf_spool_requires_host_approval_and_exact_id(tmp_path,monkeypatch):
    d=SimpleNamespace(backend='lsf',run_root=str(tmp_path))
    called=[]
    def run(argv,**kw):
        called.append(argv)
        return subprocess.CompletedProcess(argv,0,stdout='Running native task\n',stderr='')
    monkeypatch.setattr('fungen_operator.execution.subprocess.run',run)
    stem=str(tmp_path/'controller')
    assert Executor(d).live_logs(stem,'123')=={} and called==[]
    executor=Executor(d,host_approved=True)
    assert executor.live_logs(stem,'123')['live_stdout']=='Running native task\n'
    assert called==[['bpeek','123']]
    with pytest.raises(ValueError): executor.live_logs(stem,'123;other')


def test_saved_streams_remain_authoritative_and_spool_errors_are_diagnostic(tmp_path,monkeypatch):
    d=SimpleNamespace(backend='lsf',run_root=str(tmp_path))
    executor=Executor(d,host_approved=True);stem=str(tmp_path/'controller')
    (tmp_path/'controller.123.out').write_text('Saved native log\n')
    def run(argv,**kw): return subprocess.CompletedProcess(argv,1,stdout='',stderr='Spool unavailable')
    monkeypatch.setattr('fungen_operator.execution.subprocess.run',run)
    assert executor.live_logs(stem,'123')=={'stdout':'Saved native log\n'}
    assert executor.live_logs(stem,'124')=={'live_diagnostic':'Spool unavailable'}


def test_executor_profile_reports_missing_journal_without_claiming_coverage(tmp_path):
    (tmp_path/'config.yaml').write_text('executor: lsf\njobs: 2000\n')
    with pytest.raises(ValueError,match='no tracked submission journal'):
        profile_logs(tmp_path,'lsf')


def test_lsf_inspection_includes_terminal_jobs():
    from fungen_operator.cluster import job_status
    calls=[]
    def run(argv,**kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv,0,stdout='DONE\n',stderr='')
    assert job_status('lsf','123',runner=run)=='success'
    assert calls==[['bjobs','-a','-noheader','-o','stat','123']]


def test_verified_synchronous_readiness_survives_scheduler_purge():
    from fungen_operator.run_jobs import retained_readiness_state
    meta={'action':'check_readiness','status':'ready','result':{'status':'ready','job_id':'123',
          'scheduler':{'job_id':'123','status':'DONE','exit_code':''},
          'logs':{'stdout':'This was a dry-run (flag -n).\n'}}}
    result=retained_readiness_state(meta,'123')
    assert result['status']=='DONE' and result['source']=='retained_readiness_receipt'
    import copy
    for location,key,value in [('scheduler','job_id','124'),('scheduler','status','RUN'),('scheduler','exit_code',1),('result','logs',{}),('meta','action','initiate_run')]:
        bad=copy.deepcopy(meta)
        target=bad if location=='meta' else bad['result'] if location=='result' else bad['result']['scheduler']
        target[key]=value
        assert retained_readiness_state(bad,'123') is None
