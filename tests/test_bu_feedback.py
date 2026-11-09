"""BU field regressions: real host bootstrap with explicitly fake SGE clients."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest
from fungen_operator import bootstrap as b
from native_scheduler import fake_sge_clients, SGE_SCC_COMPLEXES


def config(tmp_path, **updates):
    return dict(install=str(tmp_path), scheduler='sge', account='science', gpus=1,
                runtime='apptainer', models='/project/models', image='/project/fungen.sif',
                model='laguna-xs-2.1:q4_K_M', port=11434, context=32768, backend='local', **updates)


@pytest.mark.parametrize('model',list(b.MODELS))
@pytest.mark.parametrize('context',[32768,262144])
@pytest.mark.parametrize('gpus',[1,2])
def test_shared_gpu_requirement_all_schedulers(tmp_path,monkeypatch,model,context,gpus):
    fake_sge_clients(tmp_path/'clients',monkeypatch)
    c=config(tmp_path);c.update(model=model,context=context,gpus=gpus,gpu_queue='gpu')
    expected=(b.MODELS[model]+(24 if context==262144 else 4)+gpus-1)//gpus
    sge=b.render_serve(c)
    assert f'gpu_memory={expected}G' in sge
    assert 'mem_per_core=' in sge and 'h_vmem=' not in sge
    assert '#$ -pe smp 4' in sge and '#$ -P science' in sge
    c['scheduler']='lsf';lsf=b.render_serve(c)
    assert f'gmem={expected}G:mode=shared:j_exclusive=yes' in lsf
    assert 'rusage[mem=32000] span[hosts=1]' in lsf and '#BSUB -M 64000' in lsf
    c['scheduler']='slurm';slurm=b.render_serve(c)
    assert f'Per-GPU VRAM required: {expected}G' in slurm
    assert 'Slurm has no standard VRAM request' in slurm
    assert '--mem-per-gpu' not in slurm and f'--gres=gpu:{gpus}' in slurm
    for script in (sge,lsf,slurm):subprocess.run(['bash','-n'],input=script,text=True,check=True)


def test_scc_memory_budget_and_larger_model_scale(tmp_path,monkeypatch):
    fake_sge_clients(tmp_path/'clients',monkeypatch)
    c=config(tmp_path)
    assert 'mem_per_core=16G,gpu=1,gpu_memory=24G' in b.render_serve(c)
    c.update(model='laguna-s-2.1:q8_0',context=262144,gpus=2)
    assert 'mem_per_core=42G,gpu=2,gpu_memory=76G' in b.render_serve(c)
    c['scheduler']='slurm'
    assert '--mem=168G' in b.render_serve(c)


def test_site_without_gpu_complex_requires_explicit_answer(tmp_path,monkeypatch,capsys):
    complexes='mem_per_core mpc MEMORY <= YES NO 0 0\n'
    fake_sge_clients(tmp_path/'clients',monkeypatch,complexes)
    c=config(tmp_path)
    monkeypatch.setattr(b,'config_path',lambda:tmp_path/'config.toml')
    with pytest.raises(ValueError,match='NAME or none explicitly'):b.render_serve(c)
    prompts=[]
    monkeypatch.setattr('builtins.input',lambda p:prompts.append(p) or ('none' if 'GPU-memory' in p else ''))
    b.configure_sge(c,interactive=True,announce=True)
    assert any('or explicit none' in p for p in prompts)
    assert c['sge_gpu_memory_complex']=='none'
    b.write_config(c);assert b.read_config()['sge_gpu_memory_complex']=='none'
    script=b.render_serve(c)
    assert 'gpu_memory=' not in script and 'mem_per_core=16G' in script
    assert 'explicitly disabled (none)' in capsys.readouterr().out


def test_custom_complex_name_is_validated_and_saved(tmp_path,monkeypatch):
    fake_sge_clients(tmp_path/'clients',monkeypatch,
                     'accelerator_capacity ac MEMORY <= YES NO 0 0\nram_slot rs MEMORY <= YES YES 0 0\n')
    c=config(tmp_path)
    b.configure_sge(c,gpu_complex='accelerator_capacity',memory_complex='ram_slot')
    assert 'ram_slot=16G,gpu=1,accelerator_capacity=24G' in b.render_serve(c)
    c['sge_gpu_memory_complex']='invented'
    with pytest.raises(ValueError,match='not a requestable MEMORY complex'):b.render_serve(c)


def test_site_with_no_memory_complex_refuses(tmp_path,monkeypatch):
    fake_sge_clients(tmp_path/'clients',monkeypatch,'gpu gpu INT <= YES YES 0 0\n')
    c=config(tmp_path);c['sge_gpu_memory_complex']='none'
    with pytest.raises(ValueError,match='sge-memory-complex'):b.render_serve(c)


def test_virtual_only_site_has_explained_cuda_headroom(tmp_path,monkeypatch,capsys):
    fake_sge_clients(tmp_path/'clients',monkeypatch,'h_vmem h_vmem MEMORY <= YES YES 0 0\ngpu_memory gm MEMORY <= YES NO 0 0\n')
    assert 'h_vmem=64G' in b.render_serve(config(tmp_path),announce=True)
    assert 'minimum 256G aggregate' in capsys.readouterr().out
    c=config(tmp_path);c.update(model='laguna-s-2.1:q8_0',context=262144)
    assert 'h_vmem=168G' in b.render_serve(c)


@pytest.mark.parametrize('listing',[
    'gpu_memory gm MEMORY <= NO NO 0 0\nmem_per_core mpc MEMORY <= YES NO 0 0\n',
    'gpu_memory gm INT <= YES NO 0 0\nmem_per_core mpc MEMORY <= YES NO 0 0\n',
    'gpu_memory gm MEMORY <= YES YES 0 0\nmem_per_core mpc MEMORY <= YES NO 0 0\n',
    'malformed listing\n'])
def test_unusable_complex_definitions_refuse(tmp_path,monkeypatch,listing):
    fake_sge_clients(tmp_path/'clients',monkeypatch,listing)
    with pytest.raises(ValueError):b.render_serve(config(tmp_path))


def test_discovery_failure_is_visible_and_blocks_submission(tmp_path,monkeypatch):
    clients=fake_sge_clients(tmp_path/'clients',monkeypatch)
    (clients/'complexes.txt').rename(clients/'unreadable-listing')
    monkeypatch.setattr(b,'runtime_observation',lambda c:b.RuntimeObservation(False,{},'',None))
    with pytest.raises(ValueError,match='qconf -sc must succeed on the host'):b.serve(config(tmp_path))
    calls=[json.loads(x) for x in (clients/'state/calls.jsonl').read_text().splitlines()]
    assert [c['client'] for c in calls]==['qconf']


def test_serve_rediscovers_and_submits_updated_script_on_host(tmp_path,monkeypatch):
    clients=fake_sge_clients(tmp_path/'clients',monkeypatch)
    # The submit client records the real script and returns a receipt. It does
    # not allocate resources or start the image on this test host.
    (clients/'qsub').unlink()
    (clients/'qsub').write_text('#!'+sys.executable+"\nimport sys\nfrom pathlib import Path\np=Path(sys.argv[-1]); (p.parent/'submitted.sh').write_text(p.read_text()); print('42')\n")
    (clients/'qsub').chmod(0o755)
    c=config(tmp_path)
    (tmp_path/'serve.sge.sh').write_text('# old round-five script\n')
    monkeypatch.setattr(b,'config_path',lambda:tmp_path/'config.toml')
    b.serve(c)
    script=(tmp_path/'submitted.sh').read_text()
    assert 'gpu_memory=24G' in script and 'mem_per_core=16G' in script and 'h_vmem=' not in script
    assert b.read_config()['sge_gpu_memory_complex']=='gpu_memory'
    assert json.loads((tmp_path/'server-request.json').read_text())==dict(scheduler='sge',job_id='42')
    calls=[json.loads(x) for x in (clients/'state/calls.jsonl').read_text().splitlines()]
    assert [r['argv'] for r in calls]==[['-sc']]
    (clients/'complexes.txt').write_text('h_vmem h_vmem MEMORY <= YES YES 0 0\n')
    with pytest.raises(ValueError,match='not a requestable MEMORY complex'):b.render_serve(c)


@pytest.mark.parametrize('env,expected',[
    ({'SGE_ROOT':'/opt/sge'},'sge'),({'SGE_CELL':'default'},'sge'),
    ({'LSF_ENVDIR':'/opt/lsf/conf'},'lsf'),({'LSF_BINDIR':'/opt/lsf/bin'},'lsf'),
    ({'SLURM_CONF':'/etc/slurm.conf'},'slurm'),({},'local')])
def test_container_environment_is_scheduler_evidence(monkeypatch,env,expected):
    for key in ('LSF_BINDIR','LSF_ENVDIR','SGE_ROOT','SGE_CELL','SLURM_CONF'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(b.shutil,'which',lambda name:None)
    for key,value in env.items():monkeypatch.setenv(key,value)
    assert b.scheduler()==expected


def test_host_sge_detection_with_real_fake_clients(tmp_path,monkeypatch):
    clients=fake_sge_clients(tmp_path/'clients',monkeypatch)
    for key in ('LSF_BINDIR','LSF_ENVDIR','SGE_ROOT','SGE_CELL','SLURM_CONF'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setenv('PATH',str(clients))
    assert b.scheduler()=='sge'


def offline_bundle(root):
    for name in ('python/bin','venv/bin','wheels','skills/fungen-operator','bin'):(root/name).mkdir(parents=True,exist_ok=True)
    for name in ('python/bin/python3','venv/bin/python'):(root/name).symlink_to(sys.executable)
    (root/'wheels/operator.whl').write_bytes(b'wheel')
    (root/'skills/fungen-operator/SKILL.md').write_text('skill')
    (root/'bundle.sha256').write_text(hashlib.sha256(b'wheelskill').hexdigest())
    for name in ('fungen','fungen-operator'):(root/'venv/bin'/name).write_text('host entrypoint')
    (root/'bin/uv').write_text('uv')
    (root/'bin/codex').write_text('#!/bin/sh\necho codex-cli 0.155.1\n');(root/'bin/codex').chmod(0o755)


@pytest.mark.parametrize('kind',['dangling','older','directory','foreign'])
@pytest.mark.parametrize('family',['.codex','.agents'])
def test_upgrade_skill_links_through_host_install(tmp_path,monkeypatch,kind,family):
    home=tmp_path/'home';home.mkdir();install=home/'new-install';offline_bundle(install)
    dest=home/family/'skills/fungen-operator';dest.parent.mkdir(parents=True)
    if kind=='dangling':dest.symlink_to(home/'gone/skills/fungen-operator')
    elif kind=='older':
        old=home/'older-install';offline_bundle(old);dest.symlink_to(old/'skills/fungen-operator')
    elif kind=='directory':dest.mkdir();(dest/'mine').write_text('keep')
    else:
        foreign=home/'foreign/skills/fungen-operator';foreign.mkdir(parents=True);(foreign/'mine').write_text('keep');dest.symlink_to(foreign)
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'BUNDLE',tmp_path/'no-image')
    monkeypatch.setattr(b,'host_codex',lambda:None)
    monkeypatch.setenv('JUPYTER_DATA_DIR',str(home/'jupyter'))
    if kind in ('dangling','older'):
        b.install_host(install)
        assert dest.resolve()==install/'skills/fungen-operator'
        b.install_host(install);assert dest.resolve()==install/'skills/fungen-operator'
    else:
        with pytest.raises(ValueError,match='move it aside explicitly') as exc:b.install_host(install)
        assert shlex.join(['mv',str(dest),str(dest)+'.before-fungen']) in str(exc.value)
        assert (dest/'mine').read_text()=='keep'


def test_image_copies_only_then_host_detects(tmp_path,monkeypatch,capsys):
    home=tmp_path/'home';home.mkdir();bundle=tmp_path/'image-bundle';offline_bundle(bundle)
    install=home/'install with spaces'
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'config.toml')
    monkeypatch.setattr(b,'BUNDLE',bundle)
    monkeypatch.setattr(b,'host_visible',lambda p:True)
    for name in ('scheduler','install_host','check','gpu_memory'):
        monkeypatch.setattr(b,name,lambda *a,**k:pytest.fail('host work attempted inside image'))
    assert b.main(['setup','--install',str(install),'--image','/project/image with spaces.sif','--runtime','apptainer','--non-interactive','--scheduler','sge']) is None
    assert (install/'wheels/operator.whl').read_bytes()==b'wheel'
    assert not (home/'config.toml').exists()
    command=shlex.split(capsys.readouterr().out.split('host:\n  ')[1].strip())
    assert command[:4]==[str(install/'python/bin/python3'),'-m','fungen_operator.bootstrap','setup']
    assert command[command.index('--image')+1]=='/project/image with spaces.sif'
    assert '--non-interactive' in command and command[-2:]==['--scheduler','sge']


@pytest.mark.parametrize('feature,accepted',[('vram_48gb',True),('missing',False),('vram_48gb|other',False)])
def test_slurm_site_capacity_feature_uses_host_discovery(tmp_path,monkeypatch,feature,accepted):
    clients=tmp_path/'slurm-bin';clients.mkdir()
    sinfo=clients/'sinfo'
    sinfo.write_text('#!/bin/sh\n[ "$1" = "--noheader" ] && [ "$2" = "--format=%f" ] || exit 2\nprintf "vram_48gb,avx2\\n(null)\\n"\n')
    sinfo.chmod(0o755)
    monkeypatch.setenv('PATH',str(clients)+':'+os.environ['PATH'])
    c=config(tmp_path);c.update(scheduler='slurm',slurm_gpu_constraint=feature,slurm_gpu_memory_gb=48)
    if accepted:assert '#SBATCH --constraint=vram_48gb' in b.render_serve(c)
    else:
        with pytest.raises(ValueError):b.render_serve(c)


@pytest.mark.parametrize('sched',['lsf','sge','slurm'])
def test_native_acceptance_configures_on_host_after_image_copy(tmp_path,monkeypatch,sched):
    import importlib.util
    spec=importlib.util.spec_from_file_location('fungen_acceptance',Path(__file__).parents[1]/'container/acceptance.py')
    acceptance=importlib.util.module_from_spec(spec);spec.loader.exec_module(acceptance)
    calls=[]
    monkeypatch.setattr(acceptance,'drive',lambda command,answers,*a,**k:calls.append((command,answers)))
    home,work,env=acceptance.setup(tmp_path,'/images/fungen.sif','/models','laguna-xs-2.1:q4_K_M',sched=sched)
    assert len(calls)==2
    assert calls[0][0][0] in ('singularity','apptainer')
    assert [prompt for prompt,answer in calls[0][1]]==['Install folder']
    assert str(calls[1][0][0])==str(home/'.fungen/python/bin/python3')
    assert calls[1][0][1:4]==['-m','fungen_operator.bootstrap','setup']
    assert calls[1][1][0]==('Scheduler',sched) and env['HOME']==str(home)
    prompts=[prompt for prompt,answer in calls[1][1]]
    if sched=='sge':
        assert prompts.index('SGE project (-P)') < prompts.index('Model backend')
        assert prompts.index('Context') < prompts.index('SGE GPU-memory complex') < prompts.index('SGE host-memory complex') < prompts.index('Add the install bin')
    if sched=='slurm':assert prompts.index('Context') < prompts.index('Slurm GPU capacity Feature') < prompts.index('Add the install bin')


def test_container_sge_evidence_is_the_setup_prompt_default(tmp_path,monkeypatch):
    from test_bootstrap import local_setup
    for key in ('LSF_BINDIR','LSF_ENVDIR','SGE_CELL','SLURM_CONF'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setenv('SGE_ROOT','/site/sge')
    monkeypatch.setattr(b.shutil,'which',lambda name:None)
    detected=b.scheduler()
    prompts,saved=local_setup(tmp_path,monkeypatch,detected,args=['--account',''])
    assert 'Scheduler (lsf/slurm/sge/local) [sge]: ' in prompts
    assert saved['scheduler']=='sge' and saved['sge_gpu_memory_complex']=='gpu_memory'


def test_host_setup_records_explicit_no_gpu_complex(tmp_path,monkeypatch,capsys):
    from test_bootstrap import local_setup
    # Run the real host setup; supply the site's listing through its native client.
    from native_scheduler import fake_sge_clients as install_clients
    import test_bootstrap
    def no_gpu(root,patch):
        return install_clients(root,patch,'mem_per_core mpc MEMORY <= YES NO 0 0\n')
    monkeypatch.setattr(test_bootstrap,'fake_sge_clients',no_gpu)
    prompts,saved=local_setup(tmp_path,monkeypatch,'sge',answers={
        'SGE GPU-memory complex (name from qconf -sc, or explicit none)':'none'},args=['--account',''])
    assert saved['sge_gpu_memory_complex']=='none'
    assert any('or explicit none' in p for p in prompts)
    assert 'explicitly disabled (none)' in capsys.readouterr().out
    assert '# GPU-memory complex: explicit none' in (Path(saved['install'])/'serve.sge.sh').read_text()


@pytest.mark.parametrize('capacity',[None,12])
def test_slurm_capacity_feature_must_meet_shared_requirement(tmp_path,capacity):
    c=config(tmp_path);c.update(scheduler='slurm',slurm_gpu_constraint='vram_12gb')
    if capacity is not None:c['slurm_gpu_memory_gb']=capacity
    with pytest.raises(ValueError,match='at least 24G per GPU'):b.render_serve(c)


def test_host_advanced_context_creation_runs_image_download(tmp_path,monkeypatch):
    source=tmp_path/'source with spaces';(source/'blobs').mkdir(parents=True)
    (source/'blobs/sha256-abc').write_bytes(b'abcd')
    model='laguna-xs-2.1:q4_K_M'
    manifest=b.manifest(source,model);manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'config':{'digest':'sha256:abc','size':4},'layers':[]}))
    install=tmp_path/'install';install.mkdir()
    runtime=tmp_path/'apptainer'
    runtime.write_text('#!'+sys.executable+"\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ['FUNGEN_TEST_DOWNLOAD_ARGS']).write_text(json.dumps(sys.argv[1:]))\n")
    runtime.chmod(0o755)
    captured=tmp_path/'download-args.json';monkeypatch.setenv('FUNGEN_TEST_DOWNLOAD_ARGS',str(captured))
    monkeypatch.setattr(b,'inside_download',lambda *a:pytest.fail('Ollama download ran on host'))
    c=dict(install=str(install),models=str(source),model=model,runtime=str(runtime),image='/images/image with spaces.sif')
    b.context_variant(c)
    args=json.loads(captured.read_text())
    assert args[0]=='run' and '--skip-pull' in args
    assert args[args.index('--context')+1]=='262144'
    assert str(source)+':'+str(source) in args
    assert str(install/'server-models')+':/models' in args
    assert '/images/image with spaces.sif' in args and 'download' in args
    assert '--nv' not in args and c['models']==str(source)
    assert (install/'server-models/blobs/sha256-abc').is_symlink()


def test_host_download_cli_refuses_direct_ollama(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(b,'BUNDLE',tmp_path/'absent-image')
    monkeypatch.setattr(b,'inside_download',lambda *a:pytest.fail('host download started Ollama'))
    assert b.main(['download'])==1
    message=capsys.readouterr().err
    assert 'downloads run in the image' in message and 'fungen setup --download yes' in message
