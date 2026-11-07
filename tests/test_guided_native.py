"""Full guided caller against synthetic native scheduler executables on PATH."""
import json
import os
from pathlib import Path
import subprocess
import sys

import yaml
import pytest

from fungen_operator import onboarding
from fungen_operator.actions import Deployment
from fungen_operator.notebook import Notebook


@pytest.mark.parametrize('scheduler,clients',[
    ('lsf',('bsub','bjobs','bacct')),('sge',('qsub','qstat','qacct')),('slurm',('sbatch','squeue','sacct'))])
def test_actual_guided_test_native_lifecycle(tmp_path,scheduler,clients):
    prepared=os.environ.get('FUNGEN_TEST_XQTL_ROOT')
    if not prepared:
        pytest.fail('Guided native integration requires the pinned host xQTL environment and checkout. '
                    'Run fungen xqtl --root NEW_ROOT through fixture, then export FUNGEN_TEST_XQTL_ROOT=NEW_ROOT and rerun the host suite.')
    prepared=Path(prepared).resolve()
    settings=onboarding.settings(prepared)
    root=tmp_path/'guide';root.mkdir()
    c=dict(settings,scheduler=scheduler,account='science',queue='premium' if scheduler=='lsf' else '')
    (root/'setup.json').write_text(json.dumps(c))
    # Reuse only installed tools and the actual pinned/patched upstream source.
    # Reference, profiles, 500-person inputs and every native product are fresh.
    subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(prepared/'workflow'),str(root/'workflow')],check=True,capture_output=True,text=True)
    subprocess.run(['git','-C',str(root/'workflow'),'checkout','--detach',onboarding.COMMIT],check=True,capture_output=True,text=True)
    assert not (root/'workflow').is_symlink() and (root/'workflow').resolve().is_relative_to(root.resolve())
    binpath=tmp_path/'clients';binpath.mkdir()
    executable=binpath/'scheduler.py'
    executable.write_text((Path(__file__).with_name('native_scheduler.py')).read_text())
    for name in (*clients,'bkill','qdel','scancel'):
        path=binpath/name
        path.write_text('#!'+sys.executable+'\nexec(compile(open('+repr(str(executable))+').read(),'+repr(str(executable))+',"exec"))\n')
        path.chmod(0o755)
    env={k:v for k,v in os.environ.items() if not k.startswith('FUNGEN_') and k not in ('JOB_ID','SLURM_JOB_ID','LSB_JOBID')}
    env['PATH']=str(binpath)+':'+str(Path(c['software'])/'bin')+':'+env['PATH']
    env['PYTHONPATH']=str(Path(onboarding.__file__).resolve().parents[1])
    # This is the public guide, including its real predecessor checks and grade.
    code='from fungen_operator.onboarding import main; '+ '; '.join(
        'main('+repr(['--root',str(root),'--step',step])+')' for step in ('workflow','reference','scheduler','fixture','test','handoff'))
    result=subprocess.run([sys.executable,'-c',code],env=env,input='yes\n'*6,text=True,capture_output=True,timeout=2400)
    runtime=onboarding.guided_run(root);work=runtime/'work'
    diagnostics=result.stdout+result.stderr
    if result.returncode:
        for path in sorted((work/'logs').rglob('*.err')):
            diagnostics+='\n'+str(path)+'\n'+path.read_text()[-6000:]
        diagnostics+='\n'+(work/'logs/test.log').read_text()[-10000:] if (work/'logs/test.log').is_file() else ''
    assert result.returncode==0,diagnostics
    acceptance=json.loads((runtime/'acceptance.json').read_text())
    assert acceptance['passed'] is True
    submissions=[json.loads(line) for line in (binpath/'state/submissions.jsonl').read_text().splitlines()]
    controllers=[s for s in submissions if s['kind']=='controller']
    assert len(controllers)==1
    controller=controllers[0]
    calls=[json.loads(line) for line in (binpath/'state/calls.jsonl').read_text().splitlines()]
    submit_calls=[c for c in calls if c['client']==clients[0]]
    assert submit_calls[0]['controller'] is None and submit_calls[0]['journal'] is None
    assert all(c['controller']==controller['job_id'] and c['journal']==str(work/'logs/rules/submissions.jsonl') for c in submit_calls[1:])
    assert {s['kind'] for s in submissions}=={'controller','wrapper','task'}
    # Inspect exactly the deployment and executed receipt notebook the guide
    # emitted, using the public CLI with the production cloned topology.
    d=Deployment.load(root/'deployment.json');d.validate_layout()
    inspection=runtime/'operator.ipynb'
    d.validate_write_path(str(inspection))
    book=Notebook(str(inspection),d.registry).read()
    emitted=[cell for cell in book.cells if cell.cell_type=='code' and cell.metadata.fungen.action=='guided_test']
    assert len(emitted)==1 and emitted[0].metadata.fungen.result.job_id==controller['job_id']
    native=emitted[0].metadata.fungen
    assert native.status=='completed'
    for path in (inspection,Path(native.slots.arguments.workdir),Path(native.slots.bindings.log_stem),
                 work/'logs/rules/submissions.jsonl',Path(yaml.safe_load((runtime/'config.yaml').read_text())['runtime_home'])):
        assert path.resolve().is_relative_to(Path(d.run_root).resolve())
    assert not Path(d.repository).resolve().is_relative_to(Path(d.run_root).resolve())
    assert not Path(d.run_root).resolve().is_relative_to(Path(d.repository).resolve())
    inspected=subprocess.run([sys.executable,'-m','fungen_operator','inspect','--deployment',str(root/'deployment.json'),
                              '--notebook',str(inspection)],env=env,capture_output=True,text=True,timeout=120)
    assert inspected.returncode==0,inspected.stdout+inspected.stderr
    report=json.loads(inspected.stdout)
    assert report['scheduler_ok'] is True and report['discovery_coverage']['verified'] is True
    assert report['discovery_coverage']['controllers']==1 and report['discovery_coverage']['wrappers']>0 and report['discovery_coverage']['tasks']>0
    assert report['dead_child_count']==0 and all(job['status']=='DONE' for job in report['jobs'].values())
    assert set(report['jobs'])=={record['job_id'] for record in submissions}
    calls=[json.loads(line) for line in (binpath/'state/calls.jsonl').read_text().splitlines()]
    assert set(clients)<={call['client'] for call in calls}
