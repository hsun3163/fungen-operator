"""The guided notebook records consent boundaries and native execution profiles."""
from pathlib import Path
import json
import nbformat
import pytest
import yaml
from fungen_operator import onboarding as o


def test_notebook_retains_every_confirmed_step(tmp_path):
    p=o.notebook(tmp_path); nb=nbformat.read(p,as_version=4)
    cells=[c for c in nb.cells if c.cell_type=='code']
    assert [c.metadata.fungen_setup.step for c in cells]==list(o.STEPS)
    assert all('perform(' in c.source and not c.outputs for c in cells)
    stamp=p.stat().st_mtime_ns
    assert o.notebook(tmp_path)==p and p.stat().st_mtime_ns==stamp


def test_refusing_a_step_prevents_execution(tmp_path,monkeypatch):
    (tmp_path/'setup.json').write_text('{}')
    monkeypatch.setattr(o,'ask',lambda *a:'no')
    monkeypatch.setattr(o,'run',lambda *a,**k:pytest.fail('execution after refusal'))
    with pytest.raises(RuntimeError,match='prepared'):
        o.perform(tmp_path,'workflow')
    assert not (tmp_path/'workflow').exists()


def test_profiles_keep_native_scheduler_parallelism(tmp_path):
    o.profiles(tmp_path,{'account':'a','queue':'q','software':'/software'})
    hosts=yaml.safe_load((tmp_path/'sos.yaml').read_text())['hosts']
    assert hosts['q']['max_running_jobs']==2000
    assert 'bsub' in hosts['q']['submit_cmd']
    for sched in ['lsf','slurm','local']:
        p=yaml.safe_load((tmp_path/'profiles'/sched/'config.yaml').read_text())
        assert p['jobs']==(4 if sched=='local' else 2000)
        if sched!='local':
            assert 'cluster.py submit' in p['cluster'] and '--scheduler '+sched in p['cluster']
            assert 'cluster.py status' in p['cluster-status']


def test_scientific_commands_use_pinned_native_snakefile(tmp_path):
    c={'software':'/software folder','scheduler':'lsf'}
    cmd=o.scientific_command(tmp_path,c,True)
    assert cmd[0]=='/software folder/bin/snakemake'
    assert str(tmp_path/'workflow/code/snakemake/Snakefile') in cmd
    assert cmd[-1]=='xqtl_core' and '--dry-run' in cmd
    assert cmd[cmd.index('--jobs')+1]=='2000'


def test_frozen_recovery_is_declared_before_any_fit():
    from fungen_operator.synthetic import RECOVERY, SEED
    assert SEED==20261020 and RECOVERY['planted_required']==24
    assert RECOVERY['nominal_p']==5E-8 and RECOVERY['credible_set_coverage']==.95
    assert RECOVERY['null_max']==1


def test_miniforge_hash_is_checked_before_execution(tmp_path,monkeypatch):
    installer=tmp_path/'Miniforge3-26.7.2-0-Linux-x86_64.sh';installer.write_text('invalid installer')
    monkeypatch.setattr(o,'run',lambda *a,**k:pytest.fail('unverified installer executed'))
    with pytest.raises(ValueError,match='hash differs'):
        o.acquire_mamba(tmp_path)
