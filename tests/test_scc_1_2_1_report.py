"""Regressions for the 1.2.1 BU SCC report (scc-219, A100, Exclusive_Process)."""
import json
import subprocess
from types import SimpleNamespace

import pytest
from fungen_operator import bootstrap as b, cluster
from native_scheduler import fake_sge_clients


def config(tmp_path, **updates):
    return dict(install=str(tmp_path), scheduler='sge', account='science', gpus=1,
                runtime='apptainer', models='/project/models', image='/project/fungen.sif',
                model='laguna-xs-2.1:q4_K_M', port=11434, context=32768, backend='local', **updates)


# 1. Ollama's bootstrap and verify runners both open the GPU; in Exclusive_Process
#    the second open fails as busy. The SGE job asks SCC for Default (shared) mode.
def test_sge_job_requests_shared_compute_mode(tmp_path, monkeypatch):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    script = b.render_serve(config(tmp_path))
    directives = [line for line in script.splitlines() if line.startswith('#$')]
    assert '#$ -v COMPUTE_MODE=Default' in directives
    assert '#$ -l h_rt=12:00:00,mem_per_core=8G,gpu=1,gpu_memory=24G' in directives
    assert '#$ -pe omp 8' in directives
    # One CUDA library is still pinned, so only one verify runner starts.
    assert 'export OLLAMA_LLM_LIBRARY="$library"' in script
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)


def test_sge_library_override_keeps_shared_compute_mode(tmp_path, monkeypatch):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    c = config(tmp_path)
    (tmp_path/'serve.sge.sh').write_text(b.render_serve(c))
    monkeypatch.setattr(b, 'write_config', lambda _: None)
    monkeypatch.setattr(b, 'configure_sge', lambda *a, **k: None)
    run = SimpleNamespace(calls=[])
    monkeypatch.setattr(b, 'run', lambda cmd, **kw: run.calls.append(cmd) or SimpleNamespace(stdout='42\n'))
    b.serve(c, 'cuda_v13')
    assert run.calls[-1][:4] == ['qsub', '-terse', '-v', 'OLLAMA_LLM_LIBRARY=cuda_v13,COMPUTE_MODE=Default']


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
