"""Host/image separation and installer storage/scheduler contracts."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fungen_operator import bootstrap as b

@pytest.mark.parametrize('memory,model', [([], 'laguna-xs-2.1:q4_K_M'),([24],'laguna-xs-2.1:q4_K_M'),([80],'laguna-xs-2.1:q8_0'),([80,80],'laguna-s-2.1:q8_0'),([141],'laguna-s-2.1:q8_0')])
def test_model_default(memory,model):
    assert b.model_default(memory)==model

@pytest.mark.parametrize('scheduler',['lsf','slurm','local'])
def test_serve_scripts(tmp_path,scheduler):
    c=dict(install=str(tmp_path),scheduler=scheduler,account='acc_LOAD',gpu_queue='gpuexpress',gpus=2,
           runtime='apptainer',models='/models with spaces',image='/some image.sif',model='laguna-s-2.1:q4_K_M',port=11434,context=32768)
    script=tmp_path/'serve.sh';script.write_text(b.render_serve(c))
    b.run(['bash','-n',script])
    text=script.read_text()
    assert '--nv' in text and '--home' in text and ' serve ' in text
    assert 'codex' not in text
    if scheduler=='lsf': assert 'num=2' in text


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
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11435'})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    c={'install':str(tmp_path),'backend':'local','codex':'/host/codex','model':'laguna-xs-2.1:q4_K_M'}
    b.codex(c,SimpleNamespace(args=['exec','hello'],wait=0,deployment='/run/deployment.json'))
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


def test_xqtl_cli_forwards_options_without_double_dash(monkeypatch):
    from fungen_operator import onboarding
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
    b.codex({'install':str(tmp_path),'backend':'openai','codex':'/host/codex'},SimpleNamespace(args=[],deployment=None))
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
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11434'})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    override='mcp_servers.fungen.tools.initiate_run.approval_mode="approve"'
    b.codex({'install':str(tmp_path),'backend':'local','codex':'codex','model':'laguna-xs-2.1:q4_K_M'},
            SimpleNamespace(args=['-c',override,'exec','hello'],wait=0,deployment=None))
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


@pytest.mark.parametrize('command',['codex','xqtl'])
def test_image_cannot_run_host_agent_or_workflow(tmp_path,monkeypatch,capsys,command):
    monkeypatch.setattr(b,'BUNDLE',tmp_path)
    monkeypatch.setattr(b,'read_config',lambda:{'install':str(tmp_path/'host install')})
    monkeypatch.setattr(b,'codex',Mock(side_effect=AssertionError('agent started in image')))
    assert b.main([command])==1
    assert 'run on the host' in capsys.readouterr().err
