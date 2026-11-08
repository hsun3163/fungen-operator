import json
from pathlib import Path
from types import SimpleNamespace
import os
import shutil
import subprocess
import pytest
from fungen_operator import bootstrap as b
from ollama_inventory import inventory_model


def launch(tmp_path,monkeypatch,backend,args,**extra):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setattr(b,'state',lambda c:{'endpoint':'http://gpu:11435'})
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    if backend=='local':
        (tmp_path/'codex').mkdir(exist_ok=True)
        (tmp_path/'codex/models.json').write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
        monkeypatch.setattr(b,'run',lambda *a,**k:SimpleNamespace(stdout='codex-cli 0.155.1\n'))
        model=extra.get('serve_model','laguna-xs-2.1:q4_K_M');context=extra.get('context',32768)
        row,show=inventory_model(model,context,tmp_path/'models')
        monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                            {'models':[row]} if path in ('/api/tags','/api/ps') else show)
    config={'install':str(tmp_path),'backend':backend,'codex':'/host/codex','model':'laguna-xs-2.1:q4_K_M','context':32768,'runtime_models':str(tmp_path/'models'),**extra}
    b.codex(config,SimpleNamespace(backend=None,args=args,wait=0,deployment=None))
    file,cmd,env=captured[0]
    assert file==cmd[0]=='/host/codex'
    return cmd,env


def developer(tmp_path):
    return ['-c','developer_instructions='+json.dumps('Read '+str(tmp_path/'skills/fungen-operator/SKILL.md')
            +' before workflow operation. Ask before each setup notebook step. Operator and scheduler run on the host.')]


def local_root(context):
    return ['-c','model_provider="ollama"','-c','model_context_window='+str(context),
            '-c','model_auto_compact_token_limit='+str(int(context*.75))]


def test_local_interactive_selects_ollama_provider_in_root_config(tmp_path,monkeypatch):
    cmd,env=launch(tmp_path,monkeypatch,'local',[])
    assert cmd==['/host/codex']+local_root(32768)+catalog_arg(tmp_path)+developer(tmp_path)+['--oss','--local-provider','ollama','--model','laguna-xs-2.1:q4_K_M']
    assert env['CODEX_HOME']==str(tmp_path/'codex')
    assert env['CODEX_OSS_BASE_URL']=='http://gpu:11435/v1'
    assert env['CODEX_OLLAMA_MODEL']=='laguna-xs-2.1:q4_K_M'


def test_local_exec_keeps_root_overrides_before_exec(tmp_path,monkeypatch):
    cmd,env=launch(tmp_path,monkeypatch,'local',['--','exec','hello'],context=262144,serve_model='laguna-xs-2.1:q4_K_M-256k')
    assert cmd==(['/host/codex']+local_root(262144)+catalog_arg(tmp_path)+developer(tmp_path)
                 +['exec','--oss','--local-provider','ollama','--model','laguna-xs-2.1:q4_K_M-256k','hello'])
    assert env['CODEX_OSS_BASE_URL']=='http://gpu:11435/v1'
    assert env['CODEX_OLLAMA_MODEL']=='laguna-xs-2.1:q4_K_M-256k'


def test_openai_uses_host_codex_home_and_default_login(tmp_path,monkeypatch):
    monkeypatch.setenv('CODEX_HOME','/home/user/.codex')
    cmd,env=launch(tmp_path,monkeypatch,'openai',[])
    assert cmd==['/host/codex']+developer(tmp_path)
    assert env['CODEX_HOME']=='/home/user/.codex'
    assert 'CODEX_OSS_BASE_URL' not in env


def test_openai_api_key_selects_responses_provider(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','unit-test-placeholder')
    captured=[];monkeypatch.setattr(b.os,'execvpe',lambda *a:captured.append(a))
    b.codex({'install':str(tmp_path),'backend':'openai','codex':'/host/codex'},SimpleNamespace(backend=None,args=['exec','hi'],deployment=None))
    _,cmd,env=captured[0]
    assert cmd==['/host/codex','-c','model_provider="fungen_openai"','-c','model_providers.fungen_openai.name="OpenAI API"',
                 '-c','model_providers.fungen_openai.base_url="https://api.openai.com/v1"',
                 '-c','model_providers.fungen_openai.env_key="OPENAI_API_KEY"',
                 '-c','model_providers.fungen_openai.wire_api="responses"']+developer(tmp_path)+['exec','hi']
    assert env['OPENAI_API_KEY']=='unit-test-placeholder'


def catalog_arg(tmp_path):
    catalogs=list((tmp_path/'codex/served').glob('*.json'))
    assert len(catalogs)==1
    return ['-c','model_catalog_json='+json.dumps(str(catalogs[0]))]


def test_local_passes_installed_model_catalog(tmp_path,monkeypatch):
    cmd,_=launch(tmp_path,monkeypatch,'local',['exec','hello'])
    assert cmd==(['/host/codex']+local_root(32768)+catalog_arg(tmp_path)+developer(tmp_path)
                 +['exec','--oss','--local-provider','ollama','--model','laguna-xs-2.1:q4_K_M','hello'])
    catalog=json.loads(next((tmp_path/'codex/served').glob('*.json')).read_text())
    assert [m['slug'] for m in catalog['models'] if m['visibility']=='list']==['laguna-xs-2.1:q4_K_M']


@pytest.mark.parametrize('fault',['missing_selected','wrong_quantization','wrong_context','missing_context','excess_context','bad_inventory','api_failure'])
def test_local_override_catalog_requires_positive_endpoint_evidence(tmp_path,monkeypatch,fault):
    catalog=tmp_path/'models.json';catalog.write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    selected='laguna-xs-2.1:q4_K_M'
    def api(url,path='/api/tags',data=None,**kwargs):
        if fault=='api_failure':raise RuntimeError('status retrieval failed')
        if path=='/api/tags':return {'models':[] if fault=='missing_selected' else {} if fault=='bad_inventory' else [inventory_model(selected)[0]]}
        if path=='/api/ps':return {'models':[]}
        return {'modelfile':inventory_model(selected)[1]['modelfile'],
                'details':{'quantization_level':'BF16' if fault=='wrong_quantization' else 'Q4_K_M'},
                'parameters':'' if fault=='missing_context' else 'num_ctx '+('262144' if fault in ('wrong_context','excess_context') else '32768'),
                'model_info':{'general.architecture':'laguna','laguna.context_length':32768 if fault=='excess_context' else 262144}}
    monkeypatch.setattr(b,'api',api)
    with pytest.raises(RuntimeError,match='Cannot verify local model override choices.*Run fungen serve, then fungen check'):
        b.served_catalog({'model':selected,'context':32768},'http://fixture',catalog)
    assert not (tmp_path/'served').exists()


@pytest.mark.parametrize('parameters',[None,''])
def test_local_base_model_requires_loaded_context_when_parameter_absent(tmp_path,monkeypatch,parameters):
    catalog=tmp_path/'models.json';catalog.write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    selected='laguna-xs-2.1:q4_K_M'
    def api(url,path='/api/tags',data=None,**kwargs):
        if path in ('/api/tags','/api/ps'):return {'models':[inventory_model(selected)[0]]}
        show={'modelfile':inventory_model(selected)[1]['modelfile'],
              'details':{'quantization_level':'Q4_K_M'},
              'model_info':{'general.architecture':'laguna','laguna.context_length':262144}}
        if parameters is not None:show['parameters']=parameters
        return show
    monkeypatch.setattr(b,'api',api)
    c={'model':selected,'context':32768}
    def unloaded(url,path='/api/tags',data=None,**kwargs):
        return {'models':[]} if path=='/api/ps' else api(url,path,data,**kwargs)
    monkeypatch.setattr(b,'api',unloaded)
    with pytest.raises(RuntimeError,match='Cannot verify local model override choices'):
        b.served_catalog(c,'http://fixture',catalog)
    assert not (tmp_path/'served').exists()
    monkeypatch.setattr(b,'api',api)
    path=b.served_catalog(c,'http://fixture',catalog);stamp=path.stat().st_mtime_ns
    assert b.served_catalog(c,'http://fixture',catalog)==path and path.stat().st_mtime_ns==stamp
    visible=[m for m in json.loads(path.read_text())['models'] if m['visibility']=='list']
    assert len(visible)==1 and visible[0]['slug']==selected
    assert visible[0]['context_window']==visible[0]['max_context_window']==32768
    path.write_text('{}')
    with pytest.raises(RuntimeError,match='Generated local model catalog is invalid; rerun setup'):
        b.served_catalog(c,'http://fixture',catalog)


def test_openai_ignores_installed_model_catalog(tmp_path,monkeypatch):
    (tmp_path/'codex').mkdir();(tmp_path/'codex/models.json').write_text('{}')
    cmd,_=launch(tmp_path,monkeypatch,'openai',[])
    assert cmd==['/host/codex']+developer(tmp_path)


def test_packaged_catalog_covers_every_laguna_tag():
    catalog=json.loads((Path(b.__file__).with_name('resources')/'codex-models.json').read_text())
    slugs=[m['slug'] for m in catalog['models'] if m['visibility']=='none']
    assert slugs==['laguna-xs-2.1','laguna-s-2.1']
    for tag in b.MODELS:
        assert sum((tag+'-256k').startswith(s) and tag.startswith(s) for s in slugs)==1
    visible={m['slug']:m for m in catalog['models'] if m['visibility']=='list'}
    assert set(visible)=={tag+suffix for tag in b.MODELS for suffix in ('','-256k')}
    for tag,model in visible.items():
        context=262144 if tag.endswith('-256k') else 32768
        assert model['context_window']==model['max_context_window']==context
        assert tag.split(':')[1].split('-')[0].upper() in model['description']
    for model in catalog['models']:
        assert model['model_messages']['instructions_template'].startswith('You are a coding agent running in the Codex CLI')
        assert '`update_plan`' not in model['model_messages']['instructions_template']


def test_local_setup_installs_model_catalog(tmp_path,monkeypatch):
    home=tmp_path/'home';install=home/'.fungen';models=tmp_path/'models';models.mkdir();install.mkdir(parents=True)
    monkeypatch.setattr(b.Path,'home',lambda:home)
    monkeypatch.setattr(b,'config_path',lambda:home/'.config/fungen/config.toml')
    for name,value in [('install_host',lambda p:'/host/codex'),('check',lambda *a,**k:True),('gpu_memory',lambda:[]),('scheduler',lambda:'lsf'),
                       ('model_present',lambda *a:True),('prepare_runtime_store',lambda c:None)]:
        monkeypatch.setattr(b,name,value)
    args=['setup','--non-interactive','--install',str(install),'--backend','local','--model','laguna-xs-2.1:q4_K_M','--download','no',
          '--models-dir',str(models),'--context','32768','--add-path','no','--image','/img.sif','--runtime','apptainer']
    b.main(args)
    installed=install/'codex/models.json'
    assert installed.read_bytes()==(Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes()
    stamp=installed.stat().st_mtime_ns
    b.main(args)
    assert installed.stat().st_mtime_ns==stamp


@pytest.mark.parametrize('content',[None,'{}','{broken'])
def test_local_missing_or_invalid_catalog_blocks_exec(tmp_path,monkeypatch,content):
    if content is not None:
        (tmp_path/'codex').mkdir();(tmp_path/'codex/models.json').write_text(content)
    monkeypatch.setattr(b.os,'execvpe',lambda *a:pytest.fail('launched without required catalog'))
    c=dict(install=str(tmp_path),backend='local',codex='/host/codex',runtime='apptainer',image='/fungen.sif')
    with pytest.raises(ValueError,match='catalog missing or invalid.*Rerun setup'):
        b.codex(c,SimpleNamespace(backend=None,args=[],wait=0,deployment=None))


def test_catalog_loads_in_pinned_host_client(tmp_path):
    client=os.environ.get('FUNGEN_TEST_CODEX') or shutil.which('codex')
    assert client, 'Set FUNGEN_TEST_CODEX to host Codex 0.155.1 to validate the shipped catalog'
    version=subprocess.run([client,'--version'],text=True,capture_output=True,check=True).stdout.strip()
    assert version=='codex-cli 0.155.1', 'Set FUNGEN_TEST_CODEX to the bundled host Codex 0.155.1'
    home=tmp_path/'codex';home.mkdir()
    catalog=Path(b.__file__).with_name('resources')/'codex-models.json'
    result=subprocess.run([client,'-c','model_catalog_json='+json.dumps(str(catalog)),
                           'debug','models'],env=dict(os.environ,CODEX_HOME=str(home)),
                          capture_output=True,text=True,check=True,timeout=30)
    loaded=json.loads(result.stdout)
    assert loaded['models']==json.loads(catalog.read_text())['models']


def capture_pinned_request(client,folder,catalog=None,model="laguna-xs-2.1:q4_K_M",context=32768,inventory=None):
    """Run the actual pinned host client against a model-free loopback endpoint."""
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    import threading
    bodies=[]
    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            ids=[tag+('-256k' if context==262144 else '') for tag in b.MODELS]
            if inventory is not None:ids=[row['id'] for row in inventory['models']]
            models=[inventory_model(name,context,folder/'models')[0] for name in ids]
            if inventory is not None and self.path.endswith('/ps'):models=inventory['loaded']
            body=json.dumps({'models':models,'data':[]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if self.path.endswith('/show'):
                name=body['model'];quant='Q8_0' if ':q8_0' in name else 'Q4_K_M'
                show=inventory_model(name,context,folder/'models')[1]
                if inventory is not None:show=next(row for row in inventory['models'] if row['id']==name)
                data=json.dumps(show).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data);return
            bodies.append(body)
            response={'id':'resp_fixture','object':'response','status':'completed','output':[{'id':'msg_fixture','type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'READY','annotations':[]}]}]}
            events=[{'type':'response.created','response':{'id':'resp_fixture','status':'in_progress','output':[]}},
                    {'type':'response.output_item.added','output_index':0,'item':response['output'][0]},
                    {'type':'response.output_item.done','output_index':0,'item':response['output'][0]},
                    {'type':'response.completed','response':response}]
            data=''.join('data: '+json.dumps(event)+'\n\n' for event in events).encode()
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers();self.wfile.write(data)
    home=folder/'home';home.mkdir(exist_ok=True);codex_home=home/'.codex';codex_home.mkdir(exist_ok=True)
    skill=home/'.agents/skills/instruction-probe/SKILL.md';skill.parent.mkdir(parents=True,exist_ok=True)
    skill.write_text('---\nname: instruction-probe\ndescription: Exact skill delivery test marker FUNGENGUIDANCE123.\n---\nPreserve FUNGENGUIDANCE123 instructions.\n')
    (folder/'AGENTS.md').write_text('Host operator instructions: FUNGENGUIDANCE456.\n')
    server=ThreadingHTTPServer(('127.0.0.1',0),Endpoint);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    endpoint='http://127.0.0.1:'+str(server.server_address[1])
    env=dict(os.environ,HOME=str(home),CODEX_HOME=str(codex_home),CODEX_OSS_BASE_URL=endpoint+'/v1')
    env.pop('OPENAI_API_KEY',None);env.pop('CODEX_THREAD_ID',None)
    args=[client,'-c','model_provider="ollama"',
          '-c','developer_instructions="FUNGENGUIDANCE789: read the installed operator skill before work."',
          '-c','model_context_window='+str(context),'-c','model_auto_compact_token_limit='+str(int(context*.75))]
    if catalog:
        installed=folder/'models.json';installed.write_bytes(catalog.read_bytes())
        catalog=b.served_catalog({'model':model,'context':context,'runtime_models':str(folder/'models')},endpoint,installed)
        args+=['-c','model_catalog_json='+json.dumps(str(catalog))]
    args+=['exec','--oss','--local-provider','ollama','--model',model,'--skip-git-repo-check','--ephemeral','--sandbox','read-only','--json','Reply exactly READY.']
    try:result=subprocess.run(args,cwd=folder,env=env,capture_output=True,text=True,timeout=45)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    assert result.returncode==0,result.stderr
    assert bodies, 'Pinned client sent no model request'
    return bodies[-1]


def assert_full_request_parity(baseline,supplied,model,context,expected=None):
    """Only the local picker list and fresh per-invocation identity may differ."""
    import copy
    import uuid
    left,right=copy.deepcopy(baseline),copy.deepcopy(supplied)
    def spawn(body):
        matches=[tool for namespace in body['tools'] for tool in namespace.get('tools',[])
                 if tool.get('name')=='spawn_agent']
        assert len(matches)==1
        return matches[0]
    old,new=spawn(left),spawn(right)
    # The catalog intentionally replaces OpenAI override choices with exact local
    # IDs. Everything after this generated list, and every other tool byte, stays.
    marker='Spawn a sub-agent'
    assert old['description'].split(marker,1)[1]==new['description'].split(marker,1)[1]
    picker=new['description'].split(marker,1)[0]
    if expected is None:expected={tag+('-256k' if context==262144 else '') for tag in b.MODELS}
    import re
    assert set(re.findall(r'^- `([^`]+)`:',picker,re.M))==expected
    assert 'No picker-visible model overrides' not in picker
    for tag in expected:
        assert tag in picker and str(context) in picker
        assert ('Q8_0' if ':q8_0' in tag else 'Q4_K_M') in picker
    assert model in expected
    assert old['description']!=new['description']
    old['description']=new['description']
    assert left['tools']==right['tools']  # Entire definitions, including schemas.
    for body in (left,right):
        # These are independently generated request IDs, not catalog behavior.
        for item in body['input']:
            if 'id' in item:
                assert item['id'].startswith('msg_');uuid.UUID(item['id'][4:])
                item['id']='msg_<fresh>'
        meta=body['client_metadata'];session=meta['session_id'];turn=meta['turn_id']
        uuid.UUID(session);uuid.UUID(turn)
        assert body['prompt_cache_key']==meta['thread_id']==session
        assert meta['root_turn_id']==turn
        assert meta['x-codex-window-id']==session+':0'
        nested=json.loads(meta['x-codex-turn-metadata'])
        assert nested['session_id']==nested['thread_id']==session
        assert nested['turn_id']==nested['root_turn_id']==turn
        assert nested['window_id']==session+':0'
        uuid.UUID(nested['context_window_id'])
        assert type(nested['turn_started_at_unix_ms']) is int and nested['turn_started_at_unix_ms']>0
        for key in ('session_id','thread_id','turn_id','root_turn_id','window_id','context_window_id','turn_started_at_unix_ms'):
            nested[key]='<fresh invocation>'
        for key in ('session_id','thread_id','turn_id','root_turn_id','x-codex-window-id'):
            meta[key]='<fresh invocation>'
        meta['x-codex-turn-metadata']=nested
        body['prompt_cache_key']='<fresh invocation>'
    assert left==right  # All remaining request fields, with no broad exclusions.


@pytest.mark.parametrize('model,context',[('laguna-xs-2.1:q4_K_M',32768),('laguna-s-2.1:q8_0',32768),('laguna-xs-2.1:q8_0-256k',262144),('laguna-s-2.1:q4_K_M-256k',262144)])
def test_pinned_catalog_preserves_effective_instruction_delivery(tmp_path,model,context):
    client=os.environ['FUNGEN_TEST_CODEX']
    assert subprocess.run([client,'--version'],capture_output=True,text=True,check=True).stdout.strip()=='codex-cli 0.155.1'
    catalog=Path(b.__file__).with_name('resources')/'codex-models.json'
    baseline=capture_pinned_request(client,tmp_path,model=model,context=context)
    supplied=capture_pinned_request(client,tmp_path,catalog,model=model,context=context)
    (tmp_path/'baseline-request.json').write_text(json.dumps(baseline,indent=2))
    (tmp_path/'catalog-request.json').write_text(json.dumps(supplied,indent=2))
    assert supplied['instructions']==baseline['instructions']
    for marker in ('FUNGENGUIDANCE123','FUNGENGUIDANCE456','FUNGENGUIDANCE789'):
        assert marker in json.dumps(baseline['input'])
        assert marker in json.dumps(supplied['input'])
    def delivered(body):
        return [(item.get('role'),item.get('content')) for item in body['input'] if item.get('role') in ('system','developer','user')]
    assert delivered(supplied)==delivered(baseline)
    assert_full_request_parity(baseline,supplied,model,context)
    if os.environ.get('FUNGEN_PROMPT_EVIDENCE'):
        import hashlib
        evidence={'client':'codex-cli 0.155.1','model':model,'context':context,'instructions_equal':True,'delivered_input_equal':True,
                  'full_request_parity':True,'intentional_difference':'Exact served Laguna picker IDs replace OpenAI overrides; fresh request/session/message IDs and turn timestamp are validated separately.',
                  'instructions_sha256':hashlib.sha256(supplied['instructions'].encode()).hexdigest(),
                  'baseline_request':baseline,'catalog_request':supplied}
        path=Path(os.environ['FUNGEN_PROMPT_EVIDENCE'])
        previous=json.loads(path.read_text()) if path.exists() else {}
        cases=previous.get('cases',{});cases[model+'/'+str(context)]=evidence
        path.write_text(json.dumps({'client':'codex-cli 0.155.1','cases':cases},indent=2)+'\n')


@pytest.mark.parametrize('tag',list(b.MODELS))
@pytest.mark.parametrize('context',[32768,262144])
def test_official_payload_identity_and_context(tmp_path,monkeypatch,tag,context):
    """All pins, including the mixed-header S Q4 and create variants, launch."""
    name=tag+('-256k' if context==262144 else '')
    row,show=inventory_model(name,context,tmp_path/'store')
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        show if path=='/api/show' else {'models':[row]})
    source=Path(b.__file__).with_name('resources')/'codex-models.json'
    catalog=tmp_path/'models.json';catalog.write_bytes(source.read_bytes())
    generated=b.served_catalog({'model':name,'context':context,'runtime_models':str(tmp_path/'store')},'http://fixture',catalog)
    visible=[m for m in json.loads(generated.read_text())['models'] if m['visibility']=='list']
    assert len(visible)==1 and visible[0]['slug']==name
    assert visible[0]['context_window']==visible[0]['max_context_window']==context
    if tag=='laguna-s-2.1:q4_K_M':
        assert show['details']['quantization_level']=='Q8_0'
        assert 'Q4_K_M (mixed Q4_K/Q8_0)' in visible[0]['description']


@pytest.mark.parametrize('fault,message',[
    ('wrong_layer','model-layer digest mismatch'),
    ('missing_layer','must expose one exact model-layer SHA-256'),
    ('unknown_tag','unsupported local model tag'),
    ('unknown_digest','unknown or mismatched manifest digest'),
    ('missing_digest','manifest digest is missing or invalid'),
    ('wrong_size','served manifest digest/size mismatch'),
    ('string_size','served manifest digest/size mismatch')])
def test_identity_refuses_wrong_unknown_or_incomplete_evidence(tmp_path,monkeypatch,fault,message):
    name='laguna-s-2.1:q4_K_M';row,show=inventory_model(name)
    if fault=='wrong_layer':show['modelfile']='FROM /models/blobs/sha256-'+('f'*64)+'\n'
    if fault=='missing_layer':show.pop('modelfile')
    if fault=='unknown_tag':name=row['name']='laguna-s-2.1:q4_K_M-unverified'
    if fault=='unknown_digest':row['digest']='f'*64
    if fault=='missing_digest':row.pop('digest')
    if fault=='wrong_size':row['size']+=1
    if fault=='string_size':row['size']=str(row['size'])
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        show if path=='/api/show' else {'models':[row]})
    catalog=tmp_path/'models.json';catalog.write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    with pytest.raises(RuntimeError,match=message):b.served_catalog({'model':name},'http://fixture',catalog)
    assert not (tmp_path/'served').exists()


@pytest.mark.parametrize('fault,message',[
    ('unknown_manifest','manifest is unreadable'),
    ('corrupt_manifest','manifest digest mismatch'),
    ('wrong_layer_size','model-layer digest/size mismatch')])
def test_context_variant_requires_exact_manifest_and_layer_size(tmp_path,monkeypatch,fault,message):
    import hashlib
    name='laguna-s-2.1:q4_K_M-256k';store=tmp_path/'store'
    row,show=inventory_model(name,262144,store)
    path=store/'blobs'/('sha256-'+row['digest'])
    if fault=='unknown_manifest':row['digest']='f'*64
    if fault=='corrupt_manifest':path.write_bytes(b'corrupt')
    if fault=='wrong_layer_size':
        doc=json.loads(path.read_text());doc['layers'][0]['size']+=1
        raw=json.dumps(doc).encode();row['digest']=hashlib.sha256(raw).hexdigest();row['size']+=1
        (store/'blobs'/('sha256-'+row['digest'])).write_bytes(raw)
    monkeypatch.setattr(b,'api',lambda url,path='/api/tags',data=None,**kw:
                        show if path=='/api/show' else {'models':[row]})
    catalog=tmp_path/'models.json';catalog.write_bytes((Path(b.__file__).with_name('resources')/'codex-models.json').read_bytes())
    with pytest.raises(RuntimeError,match=message):
        b.served_catalog({'model':name,'context':262144,'runtime_models':str(store)},'http://fixture',catalog)
    assert not (tmp_path/'served').exists()


def test_registry_pins_bind_recorded_provenance():
    import hashlib
    doc=json.loads((Path(b.__file__).with_name('resources')/'ollama-models.json').read_text())
    assert set(doc['models'])==set(b.MODELS)
    for name,pin in doc['models'].items():
        assert pin['url']=='https://registry.ollama.ai/v2/library/'+name.replace(':','/manifests/')
        assert pin['manifest_digest']=='sha256:'+hashlib.sha256(pin['raw_manifest'].encode()).hexdigest()
        assert pin['manifest']==json.loads(pin['raw_manifest'])
        assert pin['model_layer'] in pin['manifest']['layers']
        assert pin['api_size']==pin['manifest']['config']['size']+sum(layer['size'] for layer in pin['manifest']['layers'])
        assert pin['retrieved_utc']
