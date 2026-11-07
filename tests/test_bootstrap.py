"""Host/image separation and installer storage/scheduler contracts."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,Mock
import pytest
from fungen_operator import bootstrap as b

@pytest.mark.parametrize('memory,model', [([], 'laguna-xs-2.1:q4_K_M'),([24],'laguna-xs-2.1:q4_K_M'),([80],'laguna-xs-2.1:q8_0'),([80,80],'laguna-s-2.1:q8_0'),([141],'laguna-s-2.1:q8_0')])
def test_model_default(memory,model):
    assert b.model_default(memory)==model

@pytest.mark.parametrize('scheduler',['lsf','slurm','sge','local'])
def test_serve_scripts(tmp_path,scheduler):
    c=dict(install=str(tmp_path),scheduler=scheduler,account='acc_LOAD',gpu_queue='gpuexpress',gpus=2,
           runtime='apptainer',models='/models with spaces',image='/some image.sif',model='laguna-s-2.1:q4_K_M',port=11434,context=32768)
    script=tmp_path/'serve.sh';script.write_text(b.render_serve(c))
    b.run(['bash','-n',script])
    text=script.read_text()
    assert '--nv' in text and '--home' in text and ' serve ' in text
    assert 'codex' not in text
    if scheduler=='lsf': assert 'num=2' in text
    if scheduler=='sge': assert 'gpu=2' in text and '#$ -pe smp 4' in text and 'serve.$JOB_ID.log' in text

@pytest.mark.parametrize('tools,env,expected',[({'bsub','sbatch','qsub'},{},'lsf'),({'sbatch'},{},'slurm'),
    ({'qsub'},{'SGE_ROOT':'/opt/sge'},'sge'),({'qsub','qconf'},{},'sge'),({'qsub'},{},'local')])
def test_scheduler_detection(monkeypatch,tools,env,expected):
    for key in ('LSF_BINDIR','SGE_ROOT'): monkeypatch.delenv(key,raising=False)
    for key,value in env.items(): monkeypatch.setenv(key,value)
    monkeypatch.setattr(b.shutil,'which',lambda name: '/bin/'+name if name in tools else None)
    assert b.scheduler()==expected


def test_read_only_store_never_written(tmp_path,monkeypatch):
    monkeypatch.setattr(b.tempfile,'TemporaryFile',Mock(side_effect=AssertionError('write')))
    assert b.check_folder(tmp_path,False,96)==str(tmp_path)


def test_advanced_read_only_store_stops_before_ollama(monkeypatch):
    monkeypatch.setattr(b.os,'statvfs',lambda _:SimpleNamespace(f_flag=b.os.ST_RDONLY))
    monkeypatch.setattr(b,'inside_download',Mock(side_effect=AssertionError('read-only model mutation')))
    with pytest.raises(ValueError,match='writable model blobs'):
        b.context_variant({'models':'/existing/read-only'})


def test_space_gate(tmp_path,monkeypatch):
    monkeypatch.setattr(b.shutil,'disk_usage',lambda _:SimpleNamespace(free=1))
    with pytest.raises(ValueError,match='Insufficient'):
        b.check_folder(tmp_path,True,20)


def test_complete_blob_required(tmp_path):
    m='laguna-xs-2.1:q4_K_M';p=b.manifest(tmp_path,m);p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'config':{'digest':'sha256:abc','size':4},'layers':[]}))
    assert not b.model_present(tmp_path,m)
    (tmp_path/'blobs').mkdir();(tmp_path/'blobs/sha256-abc').write_bytes(b'abcd')
    assert b.model_present(tmp_path,m)


def test_config_atomic_and_idempotent(tmp_path,monkeypatch):
    p=tmp_path/'config.toml';monkeypatch.setattr(b,'config_path',lambda:p)
    c={'backend':'local','port':11434,'models':'/models with spaces'}
    b.write_config(c);stamp=p.stat().st_mtime_ns
    b.write_config(c)
    assert p.stat().st_mtime_ns==stamp and b.read_config()==c


def test_codex_host_config_untouched(tmp_path,monkeypatch):
    (tmp_path/'codex').mkdir()
    (tmp_path/'codex/models.json').write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout='codex-cli 0.155.1\n'))
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11435'})
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        {'models':[{'name':'laguna-xs-2.1:q4_K_M','context_length':32768}]} if path in ('/api/tags','/api/ps') else
                        {'details':{'quantization_level':'Q4_K_M'},'parameters':'num_ctx 32768',
                         'model_info':{'general.architecture':'laguna','laguna.context_length':262144}})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    c={'install':str(tmp_path),'backend':'local','codex':'/host/codex','model':'laguna-xs-2.1:q4_K_M'}
    b.codex(c,SimpleNamespace(backend=None,args=['exec','hello'],wait=0,deployment='/run/deployment.json'))
    _,cmd,env=captured[0]
    assert cmd[0]=='/host/codex' and cmd[cmd.index('exec')+1]=='--oss'
    assert cmd.index('mcp_servers.fungen.command='+json.dumps(str(tmp_path/'bin/fungen-operator')))<cmd.index('exec')
    assert env['CODEX_OSS_BASE_URL']=='http://gpu:11435/v1'
    assert env['CODEX_HOME']==str(tmp_path/'codex')
    assert 'mcp_servers.fungen.command='+json.dumps(str(tmp_path/'bin/fungen-operator')) in cmd
    assert 'mcp_servers.fungen.required=true' in cmd
    assert not (tmp_path/'config.toml').exists()


def test_no_gpu_fails_with_exact_fix(monkeypatch):
    monkeypatch.setattr(b,'gpu_memory',lambda:[])
    with pytest.raises(ValueError,match='--nv'):
        b.inside_serve(SimpleNamespace())


def test_busy_port():
    import socket
    with socket.socket() as s:
        s.bind(('0.0.0.0',0));port=s.getsockname()[1]
        assert b.available_port(port)!=port

@pytest.mark.parametrize('version,expected',[('codex-cli 0.154.0',False),('codex-cli 0.155.1',True),('codex-cli 0.162.1',True)])
def test_codex_version(version,expected,monkeypatch):
    monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout=version))
    assert b.recent_codex('/host/codex')==expected


def test_advanced_context_preserves_source_store(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();(source/'blobs').mkdir()
    blob=source/'blobs/sha256-abc';blob.write_bytes(b'abcd')
    model='laguna-xs-2.1:q4_K_M';m=b.manifest(source,model);m.parent.mkdir(parents=True)
    m.write_text(json.dumps({'config':{'digest':'sha256:abc','size':4},'layers':[]}))
    before=(blob.read_bytes(),m.read_bytes(),blob.stat().st_mtime_ns)
    install=tmp_path/'install';install.mkdir()
    calls=[];monkeypatch.setattr(b,'inside_download',lambda a:calls.append(a))
    c={'install':str(install),'models':str(source),'model':model}
    b.context_variant(c)
    assert (blob.read_bytes(),m.read_bytes(),blob.stat().st_mtime_ns)==before
    assert (install/'server-models/blobs/sha256-abc').is_symlink()
    assert calls[0].skip_pull and calls[0].context==262144
    assert c['serve_model']==model+'-256k'


def test_xqtl_cli_forwards_options_without_double_dash(monkeypatch,tmp_path):
    from fungen_operator import onboarding
    monkeypatch.setattr(b,"BUNDLE",tmp_path/"absent-image-bundle")
    seen=[];monkeypatch.setattr(onboarding,'main',lambda args:seen.append(args))
    b.main(['xqtl','--root','/scratch/test'])
    assert seen==[['--root','/scratch/test']]


def test_gpu_probe_respects_allocated_devices(monkeypatch):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','GPU-test-uuid')
    calls=[]
    def probe(cmd,**kwargs):
        calls.append(cmd);return SimpleNamespace(stdout='81920\n')
    monkeypatch.setattr(b,'run',probe)
    assert b.gpu_memory()==[80]
    assert '--id=GPU-test-uuid' in calls[0]


def test_quota_failure_is_actionable(tmp_path,monkeypatch):
    monkeypatch.setattr(b.shutil,'disk_usage',lambda _:SimpleNamespace(free=1E15))
    monkeypatch.setattr(b.os,'posix_fallocate',Mock(side_effect=OSError(122,'Disk quota exceeded')))
    with pytest.raises(ValueError,match='quota/reservation'):
        b.check_folder(tmp_path,True,20)


def test_api_key_stays_in_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','unit-test-placeholder')
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    b.codex({'install':str(tmp_path),'backend':'openai','codex':'/host/codex'},SimpleNamespace(backend=None,args=[],deployment=None))
    _,cmd,env=captured[0]
    assert env['OPENAI_API_KEY']=='unit-test-placeholder'
    assert not any('unit-test-placeholder' in arg for arg in cmd)
    assert not list(tmp_path.iterdir())


def test_advanced_context_is_served_as_variant(tmp_path):
    assert b.gpu_count('laguna-xs-2.1:q4_K_M',[24,24],262144)==2
    c=dict(install=str(tmp_path),scheduler='lsf',account='a',gpu_queue='gpu',gpus=2,runtime='apptainer',
           models='/overlay',source_models='/source',image='/image.sif',model='laguna-xs-2.1:q4_K_M',
           serve_model='laguna-xs-2.1:q4_K_M-256k',port=11434,context=262144)
    text=b.render_serve(c)
    assert '--model laguna-xs-2.1:q4_K_M-256k' in text
    assert '/source:/source:ro' in text


def test_path_edit_requires_confirmation_and_is_idempotent(tmp_path,monkeypatch):
    home=tmp_path/'home';home.mkdir();profile=home/'.bashrc';profile.write_text('# user shell settings\n')
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'.config/fungen/config.toml')
    monkeypatch.setattr(b,'install_host',lambda p:'/host/codex')
    monkeypatch.setattr(b,'check',lambda *a,**k:True)
    args=['setup','--non-interactive','--backend','openai','--scheduler','local','--install',str(home/'.fungen')]
    b.main(args+['--add-path','no'])
    assert profile.read_text()=='# user shell settings\n'
    b.main(args+['--add-path','yes']);first=profile.read_text()
    b.main(args+['--add-path','yes'])
    assert profile.read_text()==first and first.count('export PATH=')==1


def test_runtime_store_allows_migration_without_writing_source(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'blobs').mkdir()
    blob=source/'blobs/sha256-data';blob.write_bytes(b'data')
    manifest=source/'manifests/registry.ollama.ai/library/model/tag';manifest.parent.mkdir(parents=True)
    manifest.write_text('original manifest')
    c={'install':str(tmp_path/'install'),'models':str(source),'runtime':'apptainer','image':'/image.sif'}
    b.prepare_runtime_store(c)
    overlay=Path(c['runtime_models'])
    assert (overlay/'blobs/sha256-data').is_symlink()
    (overlay/'manifests-v2').mkdir();(overlay/'manifests-v2/index').write_text('migration')
    assert not (source/'manifests-v2').exists() and manifest.read_text()=='original manifest'
    cmd=b.runtime(c,True)
    assert str(source)+':'+str(source)+':ro' in cmd
    assert str(overlay)+':/models' in cmd


def test_codex_explicit_root_override_precedes_exec(tmp_path,monkeypatch):
    (tmp_path/'codex').mkdir()
    (tmp_path/'codex/models.json').write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout='codex-cli 0.155.1\n'))
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11434'})
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        {'models':[{'name':'laguna-xs-2.1:q4_K_M','context_length':32768}]} if path in ('/api/tags','/api/ps') else
                        {'details':{'quantization_level':'Q4_K_M'},'parameters':'num_ctx 32768',
                         'model_info':{'general.architecture':'laguna','laguna.context_length':262144}})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    override='mcp_servers.fungen.tools.initiate_run.approval_mode="approve"'
    b.codex({'install':str(tmp_path),'backend':'local','codex':'codex','model':'laguna-xs-2.1:q4_K_M'},
            SimpleNamespace(backend=None,args=['-c',override,'exec','hello'],wait=0,deployment=None))
    command=captured[0][1]
    assert command.index(override)<command.index('exec')<command.index('--oss')


def test_host_kernel_uses_installed_python_and_is_idempotent(tmp_path,monkeypatch):
    monkeypatch.setenv('JUPYTER_DATA_DIR',str(tmp_path/'jupyter'))
    install=tmp_path/'custom install'
    path=b.install_kernel(install)
    data=json.loads(path.read_text())
    assert data['argv']==[str(install/'venv/bin/python'),'-m','ipykernel_launcher','-f','{connection_file}']
    assert data['env']['PYTHONPATH']==''
    stamp=path.stat().st_mtime_ns
    b.install_kernel(install)
    assert path.stat().st_mtime_ns==stamp


def test_interrupted_pull_repairs_only_invalid_part_records(tmp_path):
    blobs=tmp_path/'blobs';blobs.mkdir();digest='sha256-'+'a'*64
    model=blobs/(digest+'-partial');model.write_bytes(b'partial model bytes')
    with model.open('r+b') as stream:stream.truncate(1600000000)
    empty=blobs/(digest+'-partial-7');empty.write_bytes(b'')
    truncated=blobs/(digest+'-partial-8');truncated.write_text('{"Completed":')
    valid=blobs/(digest+'-partial-9');valid.write_text('{"N":9,"Offset":900000000,"Size":100000000,"Completed":5}')
    unrelated=blobs/'another-file';unrelated.write_bytes(b'')
    repaired=b.repair_pull_progress(tmp_path)
    assert len(repaired)==15
    assert sorted(p.read_bytes() for p in (tmp_path/'.fungen-download-recovery').iterdir())==[b'',b'{"Completed":']
    with model.open('rb') as stream:assert stream.read(19)==b'partial model bytes'
    assert json.loads(valid.read_text())['Completed']==5 and unrelated.exists()
    records=[json.loads((blobs/(digest+'-partial-'+str(i))).read_text()) for i in range(16)]
    assert [r['N'] for r in records]==list(range(16))
    assert sum(r['Size'] for r in records)==model.stat().st_size
    assert json.loads(empty.read_text())=={'N':7,'Offset':700000000,'Size':100000000,'Completed':0}
    assert b.repair_pull_progress(tmp_path)==[]


def test_missing_pull_records_preserve_valid_completed_chunks(tmp_path):
    blobs=tmp_path/'blobs';blobs.mkdir();model=blobs/('sha256-'+'b'*64+'-partial')
    with model.open('wb') as stream:stream.truncate(300000000)
    for i in (0,2):
        model.with_name(model.name+'-'+str(i)).write_text(json.dumps({'N':i,'Offset':i*100000000,'Size':100000000,'Completed':100000000}))
    repaired=b.repair_pull_progress(tmp_path)
    assert len(repaired)==1 and repaired[0].name.endswith('-1')
    assert json.loads(repaired[0].read_text())['Completed']==0
    assert json.loads(model.with_name(model.name+'-2').read_text())['Completed']==100000000


def test_atomic_install_keeps_live_mappings_and_identical_files(tmp_path):
    import mmap
    source=tmp_path/'source';target=tmp_path/'codex'
    old=b'O'*4096;new=b'N'*4096
    source.write_bytes(new);source.chmod(0o755);target.write_bytes(old)
    with target.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as mapped:
        b.atomic_copy(source,target)
        assert mapped[:]==old
        assert target.read_bytes()==new
    stamp=target.stat()
    b.atomic_copy(source,target)
    assert target.stat().st_ino==stamp.st_ino and target.stat().st_mtime_ns==stamp.st_mtime_ns
    assert target.stat().st_mode&0o777==0o755


def test_complete_read_only_reuse_never_repairs_download_state(monkeypatch):
    monkeypatch.setattr(b,'gpu_memory',lambda:[])
    monkeypatch.setattr(b,'repair_pull_progress',Mock(side_effect=AssertionError('read-only state mutation')))
    with pytest.raises(ValueError,match='GPU unavailable'):b.inside_serve(SimpleNamespace())


@pytest.mark.parametrize('command',['codex','xqtl','check','backend'])
def test_image_cannot_run_host_agent_or_workflow(tmp_path,monkeypatch,capsys,command):
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    monkeypatch.setattr(b,'read_config',lambda:{'install':str(tmp_path/'host install')})
    monkeypatch.setattr(b,'codex',Mock(side_effect=AssertionError('agent started in image')))
    assert b.main([command])==1
    assert 'run on the host' in capsys.readouterr().err


def backend_config(tmp_path,monkeypatch,backend='openai',local=True):
    monkeypatch.setattr(b,'config_path',lambda:tmp_path/'config.toml')
    monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout='codex-cli 0.155.1\n'))
    c={'install':str(tmp_path),'scheduler':'lsf','backend':backend,'image':'/some image.sif','runtime':'apptainer','codex':'/host/codex'}
    if local:
        c.update(model='laguna-xs-2.1:q4_K_M',models=str(tmp_path/'models'),gpus=1,context=32768,port=11434,runtime_models=str(tmp_path/'models'),account='acc_LOAD',gpu_queue='gpu')
        folder=Path(c['models']);(folder/'blobs').mkdir(parents=True);(folder/'blobs/sha256-abc').write_bytes(b'data')
        m=b.manifest(folder,c['model']);m.parent.mkdir(parents=True);m.write_text(json.dumps({'config':{'digest':'sha256:abc','size':4},'layers':[]}))
        (tmp_path/'codex').mkdir();(tmp_path/'codex/models.json').write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
        (tmp_path/'serve.lsf.sh').write_text(b.render_serve(c))
    b.write_config(c)
    return c


@pytest.mark.parametrize('local',[False,True])
def test_backend_local_requires_local_setup(tmp_path,monkeypatch,capsys,local):
    c=backend_config(tmp_path,monkeypatch,local=local)
    if local: (tmp_path/'serve.lsf.sh').unlink()
    else: c.update(model='laguna-xs-2.1:q4_K_M');b.write_config(c)
    assert b.main(['backend','local'])==1
    assert "Local backend is not configured. Run: apptainer run '/some image.sif' setup --backend local" in capsys.readouterr().err
    assert b.read_config()['backend']=='openai'


def test_backend_switch_persists_and_keeps_local_keys(tmp_path,monkeypatch,capsys):
    backend_config(tmp_path,monkeypatch)
    assert b.main(['backend','local'])==0
    assert b.read_config()['backend']=='local'
    assert capsys.readouterr().out=='Backend: local\nNext: fungen serve, then fungen codex\n'
    assert b.main(['backend','openai'])==0
    saved=b.read_config()
    assert saved['backend']=='openai' and saved['model']=='laguna-xs-2.1:q4_K_M' and saved['runtime_models']==str(tmp_path/'models')
    assert capsys.readouterr().out=='Backend: openai\nNext: fungen codex (no server needed)\n'
    stamp=b.config_path().stat().st_mtime_ns
    assert b.main(['backend','openai'])==0 and b.config_path().stat().st_mtime_ns==stamp
    assert capsys.readouterr().out.startswith('Backend: openai\n')


@pytest.mark.parametrize('local',[False,True])
def test_backend_status(tmp_path,monkeypatch,capsys,local):
    backend_config(tmp_path,monkeypatch,local=local)
    assert b.main(['backend'])==0
    out=capsys.readouterr().out.splitlines()
    assert out[0]=='Active backend: openai'
    assert out[1]==(f'local: assets configured (laguna-xs-2.1:q4_K_M, {tmp_path}/models, serve.lsf.sh); runtime unverified: fungen serve, then fungen check' if local else
                    "local: not configured — Local backend is not configured. Run: apptainer run '/some image.sif' setup --backend local")
    assert out[2]=='openai: authentication unverified (check with fungen check; sign in with /host/codex login --device-auth or OPENAI_API_KEY)'


@pytest.mark.parametrize('saved,override',[('openai','local'),('local','openai')])
def test_codex_backend_override_is_one_session(tmp_path,monkeypatch,saved,override):
    monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout='codex-cli 0.155.1\n'))
    backend_config(tmp_path,monkeypatch,backend=saved);before=b.config_path().read_bytes()
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11434'})
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        {'models':[{'name':'laguna-xs-2.1:q4_K_M','context_length':32768}]} if path in ('/api/tags','/api/ps') else
                        {'details':{'quantization_level':'Q4_K_M'},'parameters':'num_ctx 32768',
                         'model_info':{'general.architecture':'laguna','laguna.context_length':262144}})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    b.main(['codex','--backend',override,'exec','hello'])
    assert ('--oss' in captured[0][1])==(override=='local')
    assert b.config_path().read_bytes()==before


def test_codex_local_override_requires_local_setup(tmp_path,monkeypatch,capsys):
    backend_config(tmp_path,monkeypatch,local=False)
    monkeypatch.setattr(b.os,'execvpe',Mock(side_effect=AssertionError('codex started')))
    assert b.main(['codex','--backend','local'])==1
    assert 'setup --backend local' in capsys.readouterr().err


def test_openai_setup_keeps_previous_local_keys(tmp_path,monkeypatch):
    home=tmp_path/'home';home.mkdir()
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'.config/fungen/config.toml')
    monkeypatch.setattr(b,'install_host',lambda p:'/host/codex')
    monkeypatch.setattr(b,'check',lambda *a,**k:True)
    local=dict(model='laguna-s-2.1:q8_0',models='/models',gpus=2,context=262144,port=11500,
               source_models='/models',runtime_models='/install/server-models',serve_model='laguna-s-2.1:q8_0-256k')
    b.write_config({'backend':'local','download':'yes',**local})
    b.main(['setup','--non-interactive','--backend','openai','--scheduler','local','--install',str(home/'.fungen'),'--add-path','no'])
    saved=b.read_config()
    assert saved['backend']=='openai' and {k:saved[k] for k in local}==local and 'download' not in saved


MOUNTS=('1 0 0:1 / / rw - overlay overlay ro\n'
        '2 1 0:2 / /home/jenny\\040x rw - {home} server:/home rw\n'
        '3 1 0:3 / /scratch rw - gpfs scratch rw\n')


@pytest.mark.parametrize('fstype,visible',[('nfs4',True),('tmpfs',False)])
def test_mount_type_finds_deepest_mount(tmp_path,monkeypatch,fstype,visible):
    info=tmp_path/'mountinfo';info.write_text(MOUNTS.format(home=fstype))
    real=b.Path;monkeypatch.setattr(b,'Path',lambda p,*a:real(info) if p=='/proc/self/mountinfo' else real(p,*a))
    assert b.mount_type('/home/jenny x/.config')==fstype and b.host_visible('/home/jenny x')==visible
    assert b.mount_type('/home/jennyx')=='overlay' and not b.host_visible('/opt/fungen') and b.host_visible('/scratch/a')


def test_setup_stops_when_home_is_container_only(tmp_path,monkeypatch,capsys):
    home=tmp_path/'home';home.mkdir()
    monkeypatch.setattr(b,'BUNDLE',tmp_path);monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'.config/fungen/config.toml')
    monkeypatch.setattr(b,'mount_info',lambda p:dict(point=str(home),root='/',fstype='tmpfs',source='tmpfs'))
    monkeypatch.setattr(b,'install_host',Mock(side_effect=AssertionError('installed into container home')))
    monkeypatch.delenv('APPTAINER_CONTAINER',raising=False);monkeypatch.setenv('SINGULARITY_CONTAINER','/proj/fungen.sif')
    assert b.main(['setup','--non-interactive'])==1
    assert capsys.readouterr().err==f'fungen: Host home/config mount identity is unknown or private. Run: singularity run --home {home}:{home} /proj/fungen.sif\n'
    assert not list(home.iterdir())


def local_setup(tmp_path,monkeypatch,detected,previous=None,answers=None,args=()):
    (tmp_path/'home/.fungen').mkdir(parents=True,exist_ok=True);home=tmp_path/'home';models=tmp_path/'models';models.mkdir(exist_ok=True)
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'.config/fungen/config.toml')
    monkeypatch.setattr(b,'scheduler',lambda:detected)
    for name,value in [('install_host',lambda p:'/host/codex'),('check',lambda *a,**k:True),('gpu_memory',lambda:[]),
                       ('gpu_driver',lambda:detected=='local'),('model_present',lambda *a:True),('prepare_runtime_store',lambda c:None)]:
        monkeypatch.setattr(b,name,value)
    if previous: b.write_config(previous)
    prompts=[];answers=dict(answers or {})
    monkeypatch.setattr('builtins.input',lambda p:prompts.append(p) or answers.get(p.split(' [')[0],''))
    b.main(['setup','--install',str(home/'.fungen'),'--backend','local','--model','laguna-xs-2.1:q4_K_M','--download','no',
            '--models-dir',str(models),'--context','32768','--add-path','no','--image','/img.sif','--runtime','apptainer',*args])
    return prompts,b.read_config()


@pytest.mark.parametrize('detected,previous,expected',[('sge','local','sge'),('lsf','slurm','lsf'),('local','sge','sge'),('local',None,'local')])
def test_scheduler_default_prefers_fresh_detection(tmp_path,monkeypatch,detected,previous,expected):
    prompts,saved=local_setup(tmp_path,monkeypatch,detected,{'scheduler':previous} if previous else None,args=['--account',''])
    assert 'Scheduler (lsf/slurm/sge/local) ['+expected+']: ' in prompts and saved['scheduler']==expected


def test_sge_project_prompt_is_saved_and_rendered(tmp_path,monkeypatch,capsys):
    prompts,saved=local_setup(tmp_path,monkeypatch,'sge',{'scheduler':'local','account':'acc_LOAD'},{'SGE project (-P)':'xqtl'})
    assert 'SGE project (-P) []: ' in prompts and saved['account']=='xqtl'
    assert '#$ -P xqtl\n' in (tmp_path/'home/.fungen/serve.sge.sh').read_text()
    assert 'GPU offload remains unverified until fungen serve starts' in capsys.readouterr().out
    prompts,saved=local_setup(tmp_path,monkeypatch,'sge')
    assert 'SGE project (-P) [xqtl]: ' in prompts and saved['account']=='xqtl'


@pytest.mark.parametrize('detected,previous,expected',[('lsf',None,'acc_LOAD'),('lsf',{'scheduler':'lsf','account':'acc_X'},'acc_X'),
    ('slurm',{'scheduler':'lsf','account':'acc_LOAD'},''),('sge',{'scheduler':'lsf','account':'acc_LOAD'},''),('local',None,'')])
def test_account_default_follows_scheduler(tmp_path,monkeypatch,detected,previous,expected):
    prompts,saved=local_setup(tmp_path,monkeypatch,detected,previous,{'Scheduler (lsf/slurm/sge/local)':detected})
    assert saved['account']==expected and ('SGE project (-P) []: ' in prompts)==(detected=='sge')
    assert not any(p.startswith('SGE') for p in prompts if detected!='sge')


@pytest.mark.parametrize('account,directive',[('xqtl','#$ -P xqtl\n'),('',None)])
def test_sge_project_directive(tmp_path,account,directive):
    c=dict(install=str(tmp_path),scheduler='sge',account=account,gpus=1,runtime='apptainer',models='/m',image='/i.sif',
           model='laguna-xs-2.1:q4_K_M',port=11434,context=32768)
    text=b.render_serve(c)
    assert (directive in text) if directive else '#$ -P' not in text


def serving(monkeypatch,ps):
    proc=Mock();proc.poll.return_value=None;proc.pid=7
    monkeypatch.setattr(b,'gpu_memory',lambda:[80]);monkeypatch.setattr(b,'available_port',lambda p:p)
    monkeypatch.setattr(b.subprocess,'Popen',lambda *a,**k:proc)
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,timeout=5:{'response':'READY'} if path=='/api/generate' else {'models':ps} if path=='/api/ps' else {'models':[]})
    return proc


def test_cpu_only_load_refuses_to_serve(tmp_path,monkeypatch,capsys):
    proc=serving(monkeypatch,[{'name':'m','size':10,'size_vram':0}])
    args=['serve','--model','laguna-xs-2.1:q4_K_M','--state',str(tmp_path/'server.json')]
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    assert b.main(args)==1
    err=capsys.readouterr().err
    assert err.startswith('fungen: GPU offload unavailable') and 'GPU job' in err and '--nv' in err
    assert proc.terminate.called and not (tmp_path/'server.json').exists()


def check_config(tmp_path,monkeypatch):
    monkeypatch.setattr(b,'recent_codex',lambda p:True);monkeypatch.setattr(b,'model_present',lambda *a:True)
    monkeypatch.setattr(b.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0))
    monkeypatch.setattr(b.urllib.request,'urlopen',MagicMock())
    monkeypatch.setenv('PATH',str(tmp_path/'bin'));monkeypatch.setattr(b.Path,'home',lambda:tmp_path)
    skill=tmp_path/'.agents/skills/fungen-operator/SKILL.md';skill.parent.mkdir(parents=True);skill.write_text('skill')
    c=backend_config(tmp_path,monkeypatch,backend='local');c['scheduler']='sge'
    (tmp_path/'serve.sge.sh').write_text(b.render_serve(c))
    return c


@pytest.mark.parametrize('scenario,server,gpu,ok',[
    ('fresh','PENDING','PENDING',False),('ready','PASS','PASS',True),
    ('cpu','PASS','FAIL',False),('empty','PASS','FAIL',False),('wrong_model','PASS','FAIL',False),
    ('ps_error','PASS','FAIL',False),('tags_error','FAIL','PENDING',False),
    ('failed_job','FAIL','PENDING',False),('status_error','FAIL','PENDING',False),
    ('pending','PENDING','PENDING',False)])
def test_check_requires_runtime_evidence(tmp_path,monkeypatch,capsys,scenario,server,gpu,ok):
    from fungen_operator import cluster
    c=check_config(tmp_path,monkeypatch)
    if scenario not in ('fresh','pending'):
        (tmp_path/'server.json').write_text(json.dumps(dict(model=c['model'],ready=True,endpoint='http://gpu:1',job_id='5')))
    if scenario in ('failed_job','status_error','pending'):
        (tmp_path/'server-request.json').write_text(json.dumps(dict(scheduler='sge',job_id='5')))
    def status(*a):
        if scenario=='status_error':raise RuntimeError('qacct unavailable')
        return 'failed' if scenario=='failed_job' else 'running'
    monkeypatch.setattr(cluster,'job_status',status)
    def api(url,path='/api/tags'):
        if scenario=='tags_error' or path=='/api/ps' and scenario=='ps_error':raise OSError('native connection failed')
        if path=='/api/tags':return {'models':[{'name':c['model']}]}
        return {'models':[] if scenario=='empty' else [{'name':'other' if scenario=='wrong_model' else c['model'],'size_vram':0 if scenario=='cpu' else 5}]}
    monkeypatch.setattr(b,'api',api)
    # Unrelated logs, including an old fungen error, never determine health.
    (tmp_path/'serve.123.log').write_text('fungen: old failure\nCUDA driver failure\n')
    assert b.check(c) is ok
    out=capsys.readouterr().out.splitlines()
    assert all(x.startswith('PASS') for x in out[:10])
    assert out[10].startswith(server+' server reachable') and out[11].startswith(gpu+' GPU offload')
    assert out[-1]==('VERIFIED' if ok else 'NOT VERIFIED: runtime verification is pending. Run fungen serve, then fungen check.' if scenario in ('fresh','pending') else 'NOT VERIFIED: correct failed checks; for local runtime run fungen serve, then fungen check.')
    if not ok:assert 'fungen serve, then fungen check' in out[-1]
    if scenario=='ps_error':assert 'GPU status retrieval failed: native connection failed' in out[11]


@pytest.mark.parametrize('content',[None,'invalid mountinfo','1 0 0:1 / / rw - overlay overlay rw\n'])
def test_unknown_mount_never_proves_host_visibility(tmp_path,monkeypatch,content):
    info=tmp_path/'mountinfo'
    if content is not None:info.write_text(content)
    real=b.Path;monkeypatch.setattr(b,'Path',lambda p,*a:real(info) if p=='/proc/self/mountinfo' else real(p,*a))
    assert b.host_visible('/home/jenny') is False


@pytest.mark.parametrize('fstype,source,root,visible',[
    ('ext4','/dev/loop0','/',False),('ext4','/dev/sda1','/',False),
    ('ext4','/dev/sda1','/home/jenny',False),('tmpfs','tmpfs','/jenny',False)])
def test_mount_identity_requires_host_bind_or_shared_storage(monkeypatch,fstype,source,root,visible):
    monkeypatch.setattr(b,'mount_info',lambda p:dict(point='/home/jenny',root=root,fstype=fstype,source=source))
    assert b.host_visible('/home/jenny') is visible


@pytest.mark.parametrize('asset',['model','script','catalog'])
def test_local_switch_validates_assets(tmp_path,monkeypatch,asset):
    c=backend_config(tmp_path,monkeypatch)
    if asset=='model':(Path(c['models'])/'blobs/sha256-abc').write_bytes(b'broken')
    elif asset=='script':(tmp_path/'serve.lsf.sh').write_text('#!/bin/bash\n# stale script\n')
    else:(tmp_path/'codex/models.json').write_text('{}')
    with pytest.raises(ValueError,match='[Rr]erun setup'):b.backend(c,'local')
    assert b.read_config()['backend']=='openai'


def test_saved_scheduler_fallback_is_visible(tmp_path,monkeypatch,capsys):
    local_setup(tmp_path,monkeypatch,'local',{'scheduler':'sge'},args=['--account',''])
    assert 'No scheduler client detected; using saved scheduler sge. Select explicitly with --scheduler' in capsys.readouterr().out


def test_explicit_local_scheduler_beats_saved_cluster(tmp_path,monkeypatch):
    _,saved=local_setup(tmp_path,monkeypatch,'local',{'scheduler':'sge'},args=['--scheduler','local','--account',''])
    assert saved['scheduler']=='local'


@pytest.mark.parametrize('sched',['lsf','slurm','sge'])
def test_explicit_empty_account_clears_saved_project(tmp_path,monkeypatch,sched):
    _,saved=local_setup(tmp_path,monkeypatch,sched,{'scheduler':sched,'account':'old'},args=['--account',''])
    assert saved['account']==''


def test_interactive_sge_project_can_be_cleared(tmp_path,monkeypatch):
    _,saved=local_setup(tmp_path,monkeypatch,'sge',{'scheduler':'sge','account':'old'},{'SGE project (-P)':'-'})
    assert saved['account']==''


def test_check_cli_returns_nonzero_for_pending_runtime(tmp_path,monkeypatch,capsys):
    config=check_config(tmp_path,monkeypatch)
    monkeypatch.setattr(b,'read_config',lambda:config)
    assert b.main(['check'])==1
    assert 'NOT VERIFIED' in capsys.readouterr().out


def test_unknown_external_config_mount_gives_its_exact_bind(tmp_path,monkeypatch,capsys):
    home=tmp_path/'home';home.mkdir();external=tmp_path/'external config'
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:external/'fungen/config.toml')
    monkeypatch.setattr(b,'host_visible',lambda p:p==home)
    monkeypatch.setattr(b,'install_host',lambda *a:pytest.fail('wrote before mount check'))
    assert b.main(['setup','--runtime','apptainer','--image','/image.sif','--non-interactive'])==1
    assert '--bind '+b.shlex.quote(str(external/'fungen')+':'+str(external/'fungen')) in capsys.readouterr().err
    assert not external.exists()


@pytest.mark.parametrize('kernel,device,mode,verified',[
    ('/sys/devices/pci0000/block/sda/sda1','8:1',b.stat.S_IFBLK,True),
    ('/sys/devices/virtual/block/loop0','8:1',b.stat.S_IFBLK,False),
    ('/sys/devices/virtual/block/dm-0','8:1',b.stat.S_IFBLK,False),
    ('/sys/devices/pci0000/block/sda/sda1','8:2',b.stat.S_IFBLK,False),
    ('/sys/devices/pci0000/block/sda/sda1','8:1',b.stat.S_IFREG,False)])
def test_host_disk_source_requires_positive_kernel_identity(monkeypatch,kernel,device,mode,verified):
    disk=SimpleNamespace(stat=lambda:SimpleNamespace(st_mode=mode,st_rdev=b.os.makedev(8,1)))
    sysfs=MagicMock();sysfs.__truediv__.return_value=SimpleNamespace(exists=lambda:True,resolve=lambda:kernel)
    monkeypatch.setattr(b,'Path',lambda path:disk if path=='/dev/sda1' else sysfs)
    assert b.host_disk_source(dict(source='/dev/sda1',device=device)) is verified


def test_private_subdirectory_tmpfs_stops_before_installation(tmp_path,monkeypatch,capsys):
    home=tmp_path/'home';home.mkdir()
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'mount_info',lambda path:dict(point=str(home),root='/private/home',fstype='tmpfs',source='tmpfs'))
    monkeypatch.setattr(b,'install_host',lambda *a:pytest.fail('installation wrote into private tmpfs'))
    assert b.main(['setup','--non-interactive','--runtime','apptainer','--image','/fungen.sif'])==1
    assert 'mount identity is unknown or private' in capsys.readouterr().err
    assert not list(home.iterdir())
