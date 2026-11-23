"""Offline ABI and cross-node model storage regressions."""
import io
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from fungen_operator import bootstrap as b, bundle, gpu_diagnostics as d


@pytest.mark.parametrize('tag,ok', [('manylinux_2_28_x86_64',True),('manylinux_2_34_x86_64',False),
    ('manylinux2014_x86_64',True),('manylinux_2_17_x86_64.manylinux_2_34_x86_64',True),
    ('linux_x86_64',False),('manylinux_2_28_aarch64',False),('any',True)])
def test_wheel_abi(tmp_path,tag,ok):
    (tmp_path/f'p-1-cp312-cp312-{tag}.whl').touch()
    if ok: assert bundle.audit_wheels(tmp_path)==1
    else:
        with pytest.raises(ValueError,match='no platform compatible'):bundle.audit_wheels(tmp_path)


@pytest.mark.parametrize('version,ok',[('glibc 2.17',False),('glibc 2.28',True),('glibc 2.34',True)])
def test_preflight_glibc(monkeypatch,version,ok):
    monkeypatch.setattr(bundle.os,'confstr',lambda _:version)
    if ok:bundle.host_preflight()
    else:
        with pytest.raises(ValueError,match='older.*2.28'):bundle.host_preflight()


def test_platform_resolution_not_build_host(tmp_path,monkeypatch):
    calls=[]
    def run(cmd,**kw):
        calls.append(cmd)
        if 'wheel' in cmd:(tmp_path/'fungen_operator-1-py3-none-any.whl').touch()
    monkeypatch.setattr(bundle.subprocess,'run',run)
    monkeypatch.setattr(bundle,'audit_locked_wheels',lambda _:1)
    bundle.build('/source',tmp_path)
    download=calls[1]
    assert '--only-binary=:all:' in download
    assert download[download.index('--python-version')+1]=='3.12'
    assert 'manylinux_2_28_x86_64' in download and 'manylinux2014_x86_64' in download
    assert 'manylinux_2_34_x86_64' not in download


@pytest.mark.parametrize('fs,source,shared', [('nfs','server:/p',True),('gpfs','gpfs',True),('lustre','host:/p',True),
    ('ext4','/dev/sda8',False),('xfs','/dev/sda1',False),('tmpfs','tmpfs',False),('unknown','unknown',False)])
def test_storage_probes(tmp_path,monkeypatch,fs,source,shared):
    tmp_path=Path('/shared/project/models')
    monkeypatch.setattr(b,'mount_info',lambda p:dict(fstype=fs,source=source))
    assert b.model_storage(tmp_path)[2] is shared
    if shared:assert b.validate_model_storage(tmp_path,interactive=False)==(str(tmp_path),False)
    else:
        with pytest.raises(ValueError,match='Refusing unverified'):b.validate_model_storage(tmp_path,interactive=False)
        assert b.validate_model_storage(tmp_path,interactive=False,confirmation='SHARED')==(str(tmp_path),True)


def test_storage_no_local_default_or_blank(tmp_path,monkeypatch):
    monkeypatch.setattr(b,'mount_info',lambda p:dict(fstype='ext4',source='/dev/sda8'))
    assert b.model_folder(tmp_path,'sge')==''
    with pytest.raises(ValueError,match='required'):b.validate_model_storage('',interactive=False)
    monkeypatch.setattr(b,'mount_info',lambda p:dict(fstype='nfs',source='host:/p'))
    assert not b.model_storage('/scratch/user/models')[2]


def test_serve_preflight_missing_model(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(b,'host_diagnostics',lambda:None)
    with pytest.raises(ValueError,match='missing/incomplete on host.*folder=.*model='):
        b.serve_preflight(SimpleNamespace(models_dir=str(tmp_path),runtime_models=str(tmp_path),model='model:tag'))


def test_host_diagnostics_retains_scheduler_selection(monkeypatch,capsys):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','3');monkeypatch.setenv('CUDA_VISIBLE_DEVICES_ORIG','7');commands=[]
    monkeypatch.setattr(d,'probe',lambda c:commands.append(c))
    d.host_diagnostics()
    assert ['-i','3']==commands[1][1:3]
    text=capsys.readouterr().out
    assert 'CUDA_VISIBLE_DEVICES=3' in text and 'CUDA_VISIBLE_DEVICES_ORIG=7' in text
    assert d.os.environ['CUDA_VISIBLE_DEVICES']=='3'


def test_discovery_error_reprinted(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(d,'probe',lambda c:print('driver=580.1'))
    log=d.DiscoveryLog(io.StringIO('CUDA error: invalid device ordinal\ninference compute id=cpu\n'))
    log.thread.join();log.failure()
    text=capsys.readouterr().out
    assert 'FUNGEN_GPU_DISCOVERY CUDA error: invalid device ordinal' in text
    assert 'driver=580.1' in text and 'FUNGEN_GPU_FAILURE_END' in text


def test_preflight_distinguishes_context_variant_source(tmp_path,monkeypatch):
    seen=[]
    monkeypatch.setattr(b,'host_diagnostics',lambda:None)
    monkeypatch.setattr(b,'model_present',lambda folder,model:seen.append((str(folder),model)) or True)
    b.serve_preflight(SimpleNamespace(models_dir=str(tmp_path),runtime_models=str(tmp_path),model='m:tag-256k',source_model='m:tag'))
    assert seen==[(str(tmp_path),'m:tag'),(str(tmp_path),'m:tag-256k')]


def test_setup_preflight_stops_before_package_install(tmp_path,monkeypatch):
    for name in ('python/bin/python3','wheels/a-1-py3-none-any.whl','skills/fungen-operator/SKILL.md','bin/uv'):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    monkeypatch.setattr(bundle.os,'confstr',lambda _:'glibc 2.17')
    monkeypatch.setattr(b,'run',lambda *a,**kw:pytest.fail('package installation before preflight'))
    with pytest.raises(ValueError,match='older.*2.28'):b.install_host(tmp_path/'install')
