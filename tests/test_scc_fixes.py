"""Regressions for the 1.2.0 BU SCC Exclusive_Process report."""
import io
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fungen_operator import bootstrap as b, bundle, gpu_diagnostics as d
from native_scheduler import fake_sge_clients


@pytest.mark.parametrize('driver,env_library,flag,expected', [
    ('579.99', None, None, 'cuda_v12'),
    ('580.00', None, None, 'cuda_v13'),
    ('610.57.04', 'cuda_v12', None, 'cuda_v12'),
    ('579.99', 'cuda_v12', 'cuda_v13', 'cuda_v13'),
])
def test_serve_pins_one_library_and_preserves_allocated_gpu(tmp_path, monkeypatch, driver, env_library, flag, expected):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', 'GPU-allocated')
    monkeypatch.delenv('OLLAMA_LLM_LIBRARY', raising=False)
    monkeypatch.delenv('FUNGEN_OLLAMA_LLM_LIBRARY', raising=False)
    if env_library:
        monkeypatch.setenv('OLLAMA_LLM_LIBRARY', env_library)
    monkeypatch.setattr(d.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=driver+'\n'))
    monkeypatch.setattr(b, 'gpu_memory', lambda: [80])
    monkeypatch.setattr(b, 'available_port', lambda _: 11434)
    monkeypatch.setattr(b, 'runtime_requirements', lambda: None)
    process = MagicMock(pid=12345, stdout=io.StringIO('inference compute id=GPU-allocated library=CUDA\n'))
    process.poll.return_value = None
    process.wait.return_value = 0
    launch = MagicMock(return_value=process)
    monkeypatch.setattr(b.subprocess, 'Popen', launch)
    def api(url, path='/api/tags', *args, **kw):
        return {'response': 'READY'} if path == '/api/generate' else {'models': [{'name': 'm:tag', 'size_vram': 10}]}
    monkeypatch.setattr(b, 'api', api)
    b.inside_serve(SimpleNamespace(port=11434, models_dir=str(tmp_path), model='m:tag', context=32768, state=str(tmp_path/'state.json'), ollama_llm_library=flag))
    env = launch.call_args.kwargs['env']
    assert env['OLLAMA_LLM_LIBRARY'] == expected
    assert env['CUDA_VISIBLE_DEVICES'] == 'GPU-allocated'
    assert json.loads((tmp_path/'state.json').read_text())['ready']


@pytest.mark.parametrize('line,warn', [('inference compute id=cpu library=cpu\n', True),
    ('inference compute id="cpu" library=cpu\n', True), ('inference compute id=GPU-1 library=CUDA\n', False)])
def test_cpu_fallback_warns_at_discovery(line, warn, capsys):
    log = d.DiscoveryLog(io.StringIO(line)); log.thread.join()
    assert ('WARNING: Ollama selected CPU although a GPU was visible' in capsys.readouterr().out) is warn


def config(tmp_path):
    return dict(install=str(tmp_path), scheduler='sge', account='science', gpus=1,
                runtime='apptainer', models='/project/models', image='/project/fungen.sif',
                model='laguna-xs-2.1:q4_K_M', port=11434, context=32768)


@pytest.mark.parametrize('pe,memory,slots', [(None, None, 8), ('site_omp', 4, 16), ('smp', 16, 4)])
def test_sge_render_preserves_total_ram_and_gpu_requests(tmp_path, monkeypatch, pe, memory, slots):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    c=config(tmp_path)
    if pe: c['sge_parallel_environment']=pe
    if memory: c['sge_memory_per_slot_gb']=memory
    script=b.render_serve(c)
    assert f'#$ -pe {pe or "omp"} {slots}\n' in script
    assert f'#$ -l h_rt=12:00:00,mem_per_core={memory or 8}G,gpu=1,gpu_memory=24G\n' in script
    assert slots*(memory or 8) >= b.serve_memory(c)[1]
    subprocess.run(['bash', '-n'], input=script, text=True, check=True)


@pytest.mark.parametrize('driver,expected', [
    ('580\n610.57.04\n', 'cuda_v13'), ('580\n579.99\n', 'cuda_v12'),
    ('N/A\n', 'cuda_v12'), ('', 'cuda_v12'),
])
def test_driver_detection_uses_a_conservative_cuda12_default(monkeypatch, driver, expected):
    monkeypatch.setattr(d.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=driver))
    assert d.ollama_library() == expected


def test_driver_detection_handles_missing_nvidia_smi(monkeypatch):
    def unavailable(*args, **kwargs):
        raise FileNotFoundError('nvidia-smi')
    monkeypatch.setattr(d.subprocess, 'run', unavailable)
    assert d.ollama_library() == 'cuda_v12'


@pytest.mark.parametrize('saved,host_env,expected', [
    (None, {}, 'cuda_v13'),
    ('cuda_v12', {}, 'cuda_v12'),
    ('cuda_v12', {'FUNGEN_OLLAMA_LLM_LIBRARY': 'cuda_v13'}, 'cuda_v13'),
    ('cuda_v13', {'FUNGEN_OLLAMA_LLM_LIBRARY': 'cuda_v13', 'OLLAMA_LLM_LIBRARY': 'cuda_v12'}, 'cuda_v12'),
])
def test_generated_script_passes_library_through_both_container_runtimes(tmp_path, monkeypatch, saved, host_env, expected):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    c = config(tmp_path)
    if saved:
        c['ollama_llm_library'] = saved
    # Execute the rendered shell with stand-ins for preflight and the runtime.
    python = tmp_path/'venv/bin/python'
    python.parent.mkdir(parents=True)
    python.write_text('#!/bin/bash\nprintf "%s\\n" "${!#:-cuda_v13}"\n')
    python.chmod(0o755)
    runtime = tmp_path/'runtime'
    runtime.write_text('#!/bin/bash\nprintf "%s|%s|%s" "$OLLAMA_LLM_LIBRARY" "$APPTAINERENV_OLLAMA_LLM_LIBRARY" "$SINGULARITYENV_OLLAMA_LLM_LIBRARY"\n')
    runtime.chmod(0o755)
    c['runtime'] = str(runtime)
    env = dict(os.environ)
    for key in ('OLLAMA_LLM_LIBRARY', 'FUNGEN_OLLAMA_LLM_LIBRARY'):
        env.pop(key, None)
    env.update(host_env)
    result = subprocess.run(['bash'], input=b.render_serve(c), env=env, capture_output=True, text=True, check=True)
    assert result.stdout == '|'.join([expected]*3)


def test_host_serve_flag_precedes_environment_and_reaches_sge(tmp_path, monkeypatch):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    c = dict(config(tmp_path), backend='local', ollama_llm_library='cuda_v12')
    (tmp_path/'serve.sge.sh').write_text(b.render_serve(c))
    monkeypatch.setattr(b, 'write_config', lambda _: None)
    monkeypatch.setenv('OLLAMA_LLM_LIBRARY', 'cuda_v12')
    run = MagicMock(return_value=SimpleNamespace(stdout='42\n'))
    monkeypatch.setattr(b, 'run', run)
    monkeypatch.setattr(b, 'configure_sge', lambda *a, **k: None)
    b.serve(c, 'cuda_v13')
    assert run.call_args.args[0] == ['qsub', '-terse', '-v', 'OLLAMA_LLM_LIBRARY=cuda_v13', tmp_path/'serve.sge.sh']
    assert run.call_args.kwargs['env']['OLLAMA_LLM_LIBRARY'] == 'cuda_v13'
    assert c['ollama_llm_library'] == 'cuda_v12'


@pytest.mark.parametrize('key,value', [('sge_parallel_environment','omp\n#$ -q other'), ('sge_memory_per_slot_gb',0), ('sge_memory_per_slot_gb',True)])
def test_invalid_sge_parameters_are_rejected(tmp_path, monkeypatch, key, value):
    fake_sge_clients(tmp_path/'clients',monkeypatch); c=config(tmp_path);c[key]=value
    with pytest.raises(ValueError): b.render_serve(c)


def test_every_exact_host_pin_requires_a_compatible_wheel(tmp_path):
    pins=[line.split('==') for line in bundle.LOCK.read_text().splitlines() if line and not line.startswith('#')]
    assert ['debugpy','1.8.16'] in pins and ['cryptography','50.0.2'] in pins
    for name,version in pins:
        (tmp_path/f'{name.replace("-","_")}-{version}-cp312-abi3-manylinux_2_28_x86_64.whl').touch()
    assert bundle.audit_locked_wheels(tmp_path)==len(pins)
    wheel=tmp_path/'debugpy-1.8.16-cp312-abi3-manylinux_2_28_x86_64.whl'
    wheel.rename(tmp_path/'omitted-debugpy.whl.backup')
    with pytest.raises(ValueError,match='missing locked wheel: debugpy==1.8.16'):bundle.audit_locked_wheels(tmp_path)


def test_bundle_build_validates_dependency_closure_without_index(tmp_path, monkeypatch):
    calls=[]
    def run(command,**kwargs):
        calls.append(command)
        if 'wheel' in command: (tmp_path/'fungen_operator-1-py3-none-any.whl').touch()
    monkeypatch.setattr(bundle.subprocess,'run',run)
    monkeypatch.setattr(bundle,'audit_locked_wheels',lambda _:1)
    bundle.build('/source',tmp_path)
    download,offline=calls[1:]
    for command in (download,offline):
        assert str(bundle.LOCK) in command and 'manylinux_2_28_x86_64' in command
    assert '--no-index' in offline and '--ignore-installed' in offline and '--dry-run' in offline


@pytest.mark.parametrize('override', ['flag', 'env'])
def test_setup_model_override_is_saved_and_bound(tmp_path, monkeypatch, override):
    models=tmp_path/'project space/models'; models.mkdir(parents=True)
    monkeypatch.setattr(b,'BUNDLE',tmp_path/'absent-bundle')
    (tmp_path/'install').mkdir()
    monkeypatch.setattr(b,'config_path',lambda:tmp_path/'config.toml')
    monkeypatch.setattr(b,'mount_info',lambda _:dict(fstype='nfs',source='project:/shared'))
    monkeypatch.setattr(b,'gpu_memory',lambda:[])
    monkeypatch.setattr(b,'gpu_driver',lambda:False)
    monkeypatch.setattr(b,'model_present',lambda *a:True)
    monkeypatch.setattr(b,'install_host',lambda *a:'/host/codex')
    monkeypatch.setattr(b,'prepare_runtime_store',lambda *a:None)
    monkeypatch.setattr(b,'check',lambda *a,**kw:True)
    args=['setup','--non-interactive','--scheduler','lsf','--backend','local','--install',str(tmp_path/'install'), '--download','no','--ollama-llm-library','cuda_v13','--models-shared-confirmation','SHARED','--model','laguna-xs-2.1:q4_K_M']
    if override=='flag':args+=['--models-dir',str(models)]
    else:monkeypatch.setenv('FUNGEN_MODELS_DIR',str(models))
    assert b.main(args) is None
    saved=b.read_config()
    assert saved['models']==str(models.resolve())
    assert saved['ollama_llm_library']=='cuda_v13'
    assert str(models.resolve())+':/models' in b.runtime(saved,True)


def test_saved_library_survives_sge_submission_environment(tmp_path, monkeypatch):
    fake_sge_clients(tmp_path/'clients', monkeypatch)
    c=config(tmp_path); c['ollama_llm_library']='cuda_v13'
    script=b.render_serve(c)
    assert '${OLLAMA_LLM_LIBRARY:-${FUNGEN_OLLAMA_LLM_LIBRARY:-cuda_v13}}' in script
    c['ollama_llm_library']='cuda_v13\nother-command'
    with pytest.raises(ValueError,match='backend directory'): b.render_serve(c)


def test_copy_installer_preserves_old_wheels_outside_resolver(tmp_path, monkeypatch):
    image = tmp_path/'image'
    for name in ('python/bin/python3', 'wheels/debugpy-1.8.16-py3-none-any.whl',
                 'skills/fungen-operator/SKILL.md', 'bin/uv'):
        path = image/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    monkeypatch.setattr(b, 'BUNDLE', image)
    install = tmp_path/'install'
    wheels = install/'wheels'
    wheels.mkdir(parents=True)
    old = 'debugpy-1.8.22-cp312-cp312-manylinux_2_34_x86_64.whl'
    (wheels/old).write_text('old wheel')
    b.copy_host_installer(install, SimpleNamespace(), 'fungen.sif', 'singularity')
    assert sorted(p.name for p in wheels.glob('*.whl')) == ['debugpy-1.8.16-py3-none-any.whl']
    assert next(install.glob('previous-wheels-*/'+old)).read_text() == 'old wheel'
