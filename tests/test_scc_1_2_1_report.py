"""Regressions for the 1.2.1 BU SCC report (scc-219, A100, Exclusive_Process)."""
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fungen_operator import bootstrap as b, cluster
from native_scheduler import fake_sge_clients


def config(tmp_path, **updates):
    return dict(install=str(tmp_path), scheduler='sge', account='science', gpus=1,
                runtime='apptainer', models='/project/models', image='/project/fungen.sif',
                model='laguna-xs-2.1:q4_K_M', port=11434, context=32768, backend='local', **updates)


# 1. Ollama checks a GPU with CUDA_VISIBLE_DEVICES set to the GPU's position among
#    the job's GPUs. On a node where the job sees every GPU (BU SCC), position 0 is
#    physical GPU 0, often another job's GPU in Exclusive_Process. The image's
#    llama-server wrapper turns the position back into the job's own GPU.
WRAPPER = Path(__file__).parents[1]/'container/llama-server.sh'


def llama_server(tmp_path, **env):
    wrapper = tmp_path/'llama-server'
    shutil.copy(WRAPPER, wrapper)
    (tmp_path/'llama-server.ollama').write_text('#!/bin/sh\necho "$CUDA_VISIBLE_DEVICES $*"\n')
    for path in (wrapper, tmp_path/'llama-server.ollama'):
        path.chmod(0o755)
    env = {'PATH': '/usr/bin:/bin', **env}
    return subprocess.run([str(wrapper), '--list-devices'], env=env, capture_output=True, text=True, check=True).stdout


@pytest.mark.parametrize('job,position,gpu', [('3', '0', '3'), ('1,2', '1', '2'), ('GPU-a,GPU-b', '0', 'GPU-a')])
def test_gpu_check_opens_the_jobs_gpu(tmp_path, job, position, gpu):
    out = llama_server(tmp_path, GGML_CUDA_INIT='1', CUDA_VISIBLE_DEVICES=position, FUNGEN_JOB_CUDA_VISIBLE_DEVICES=job)
    assert out == gpu+' --list-devices\n'


@pytest.mark.parametrize('env', [
    dict(CUDA_VISIBLE_DEVICES='3', FUNGEN_JOB_CUDA_VISIBLE_DEVICES='3'),          # discovery and model runner
    dict(GGML_CUDA_INIT='1', CUDA_VISIBLE_DEVICES='0'),                          # no job list (cgroup-isolated sites)
    dict(GGML_CUDA_INIT='1', CUDA_VISIBLE_DEVICES='5', FUNGEN_JOB_CUDA_VISIBLE_DEVICES='3')])
def test_other_runs_keep_their_devices(tmp_path, env):
    assert llama_server(tmp_path, **env) == env['CUDA_VISIBLE_DEVICES']+' --list-devices\n'


def test_image_installs_the_wrapper_where_ollama_looks():
    install = (WRAPPER.parent/'install.sh').read_text()
    assert 'mv /usr/lib/ollama/llama-server /usr/lib/ollama/llama-server.ollama' in install
    assert 'install -m 755 /opt/fungen-operator/container/llama-server.sh /usr/lib/ollama/llama-server' in install


def test_sge_job_keeps_site_compute_mode(tmp_path, monkeypatch):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    script = b.render_serve(config(tmp_path))
    assert 'COMPUTE_MODE' not in script
    assert 'export OLLAMA_LLM_LIBRARY="$library"' in script
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)


# 2. A project-space install folder is identified by the mount the path shows.
def test_stacked_automount_uses_the_visible_mount(tmp_path, monkeypatch):
    info = tmp_path/'mountinfo'
    info.write_text('1 0 0:1 / / rw - overlay overlay ro\n'
                    '2 1 0:2 / /restricted/projectnb rw - autofs /etc/auto.projectnb rw\n'
                    '3 2 0:3 /lab /restricted/projectnb rw - nfs4 fs:/projectnb rw\n')
    real = b.Path
    monkeypatch.setattr(b, 'Path', lambda p, *a: real(info) if p == '/proc/self/mountinfo' else real(p, *a))
    assert b.mount_type('/restricted/projectnb/lab/fungen') == 'nfs4'
    assert b.host_visible('/restricted/projectnb/lab/fungen')


@pytest.mark.parametrize('fstype', sorted(b.SHARED_FILESYSTEMS))
def test_every_shared_filesystem_is_host_visible(monkeypatch, fstype):
    monkeypatch.setattr(b, 'mount_info', lambda p: dict(point='/restricted/projectnb', root='/', fstype=fstype, source='fs:/p'))
    assert b.host_visible('/restricted/projectnb/lab')


# 3. qconf exiting 0 without a complex table means SGE is unreachable.
@pytest.mark.parametrize('stdout,stderr', [
    ('', 'error: commlib error: got select error (Connection refused)\n'),
    ('error: commlib error: got select error (Connection refused)\n'
     'unable to send message to qmaster using port 6444 on host "qmaster"\n', '')])
def test_unreachable_qmaster_is_named(tmp_path, monkeypatch, stdout, stderr):
    monkeypatch.setattr(b, 'run', lambda cmd, **kw: SimpleNamespace(stdout=stdout, stderr=stderr))
    c = config(tmp_path, sge_gpu_memory_complex='gpu_memory', sge_memory_complex='mem_per_core')
    with pytest.raises(ValueError, match='SGE unreachable') as exc:
        b.configure_sge(c)
    assert 'commlib error' in str(exc.value) and 'requestable MEMORY' not in str(exc.value)


# 4. Declining the PATH prompt is a choice, not a failed check.
def test_install_off_path_is_a_note(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('PATH', '/usr/bin')
    monkeypatch.setattr(b, 'recent_codex', lambda p: True)
    monkeypatch.setattr(b.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0))
    monkeypatch.setattr(b.Path, 'home', lambda: tmp_path)
    b.check(dict(install=str(tmp_path), backend='openai', codex='codex'), online=False)
    out = capsys.readouterr().out
    assert 'NOTE install not on PATH (optional)' in out and 'install on PATH' not in out


# 5. After serve refuses, check reports the refusal instead of PENDING.
def test_check_reports_serve_refusal(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('JOB_ID', '5')
    monkeypatch.setattr(b, 'gpu_memory', lambda: [])
    (tmp_path/'server-request.json').write_text(json.dumps(dict(scheduler='sge', job_id='5')))
    with pytest.raises(ValueError):
        b.inside_serve(SimpleNamespace(state=str(tmp_path/'server.json')))
    monkeypatch.setattr(cluster, 'job_status', lambda *a: 'failed')
    c = config(tmp_path)
    observed = b.runtime_observation(c)
    assert observed.ready is False and 'not running (failed): GPU unavailable: refusing CPU-only inference' in observed.detail
    monkeypatch.setattr(b, 'require_local', lambda c: None)
    monkeypatch.setattr(b, 'model_present', lambda *a: True)
    monkeypatch.setattr(b, 'recent_codex', lambda p: True)
    monkeypatch.setattr(b.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0))
    monkeypatch.setattr(b.Path, 'home', lambda: tmp_path)
    c.update(models=str(tmp_path), codex='codex', local_codex='codex')
    b.check(c, online=False)
    gpu = next(line for line in capsys.readouterr().out.splitlines() if 'GPU offload' in line)
    assert gpu.startswith('FAIL') and 'refusing CPU-only inference' in gpu


def test_refusal_from_an_earlier_job_is_not_reported(tmp_path, monkeypatch):
    (tmp_path/'server.json').write_text(json.dumps(dict(ready=False, error='old refusal', job_id='4')))
    (tmp_path/'server-request.json').write_text(json.dumps(dict(scheduler='sge', job_id='5')))
    monkeypatch.setattr(cluster, 'job_status', lambda *a: 'failed')
    assert 'old refusal' not in b.runtime_observation(config(tmp_path)).detail
