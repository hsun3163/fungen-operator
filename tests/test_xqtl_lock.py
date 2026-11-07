from types import SimpleNamespace

import pytest
import yaml

from fungen_operator import lock


def test_yaml_channel_order_overrides_condarc_and_specs_remain_argv(tmp_path, monkeypatch):
    spec=tmp_path/'spec with spaces.yaml'
    channels=['dnachun','conda-forge','bioconda']
    packages=['r-pecotmr=0.9.5','r-susier>=0.16.4','literal$(touch bad)']
    spec.write_text(yaml.safe_dump(dict(channels=channels,dependencies=packages)))
    calls=[]
    explicit='@EXPLICIT\nhttps://example.org/package.conda#abc\n'
    def run(cmd,**kw):
        calls.append((cmd,kw));return SimpleNamespace(stdout=explicit)
    monkeypatch.setattr(lock.subprocess,'run',run)
    output=tmp_path/'output.lock'
    lock.generate('/mamba with spaces',tmp_path/'solve prefix',output,spec)
    assert calls[0][0]==['/mamba with spaces','create','-y','-p',str(tmp_path/'solve prefix'),
                         '--override-channels','-c','dnachun','-c','conda-forge','-c','bioconda']+packages
    assert calls[1][0][-2:]==['--explicit','--md5']
    assert all(kw['check'] for _,kw in calls)
    assert output.read_text()==explicit


def test_failed_solve_preserves_previous_lock(tmp_path,monkeypatch):
    output=tmp_path/'old.lock';output.write_text('reviewed lock')
    def fail(*a,**kw):raise lock.subprocess.CalledProcessError(1,a[0])
    monkeypatch.setattr(lock.subprocess,'run',fail)
    with pytest.raises(lock.subprocess.CalledProcessError):
        lock.generate('mamba',tmp_path/'prefix',output)
    assert output.read_text()=='reviewed lock'
