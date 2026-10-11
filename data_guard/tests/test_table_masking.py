"""Synthetic release controls through the real masking/broker path."""
import base64
import json
import re
from pathlib import Path
import sys
import copy

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import broker as b
import masking as m
import google_docs as g
from test_broker import case, SCRIPT


def test_gzip_snapshot_preserves_private_controls(case, monkeypatch):
    import gzip
    rp, _, request, policy = case
    raw=b'gene\tscore\nSYNGENE1\t0.654321\n'
    source=Path(policy['inputs']['toy']);source.write_bytes(gzip.compress(raw))
    policy.update(gene_columns=['gene'],protected_columns=['score'])
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained'))
    def execute(policy,request,snapshot,selected,rd):
        assert (snapshot/'inputs/toy').read_bytes()==raw
        return b'count\n654321\n',[['count'],['654321']]
    result=b.mask_run(rp,policy,Staff(),execute)
    assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    assert '654321' in (rd/'answer.md').read_text()
    assert all(v['allowed'] for v in json.loads((rd/'rules.json').read_text()).values())


def test_gzip_expansion_is_bounded(tmp_path):
    import gzip
    source=tmp_path/'large.gz';source.write_bytes(gzip.compress(b'A'*100000))
    with pytest.raises(b.Rejected,match='input-expanded-limit'):
        b.table_content(source,1024)


def test_probe_has_schema_without_private_values(case, monkeypatch):
    rp, _, _, policy=case
    rp.write_text(json.dumps(dict(action='probe',inputs={'table':'toy'})))
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained'))
    def execute(policy,request,snapshot,selected,rd):
        script=(snapshot/'analysis').read_text()
        assert 'row_count' in script and 'writerows' not in script
        assert selected['inputs']=={'table':'toy'}
        return b'input_role\tcolumn\trow_count\ntable\tgroup\t3\ntable\tvalue\t3\n',[]
    result=b.mask_run(rp,policy,Staff(),execute)
    assert result['status']=='completed'
    outgoing=(Path(policy['private_root'])/result['run_id']/'answer.md').read_text()
    assert '0.654321' not in outgoing and '0.876543' not in outgoing


def table(raw,script="cols=['category','count','rank','score','odd']"):
    d=m.empty_dictionary();m.mask_table(d,'run',raw,script)
    return d,m.table_rules(d,'run',genes=['SYNGENE1','BIN1'],protected=['0.654321','PRIVATE_CANARY_TEST'])


@pytest.mark.parametrize('value',['0.654321','65.4321%','6.54321E-1'])
def test_seeded_controls_cannot_be_unmasked_even_labelled_counts(value):
    raw=m.table_bytes([['count'],[value]])
    d,r=table(raw,"cols=['count']")
    choices={t:'unmask' for t in r}
    output,allowed,audit=m.release_table(d,'run',choices,r)
    assert value.encode() not in output
    assert any(a['reason']=='decimal value' for a in audit)
    assert m.restore_table(d,'run')==raw


@pytest.mark.parametrize('gene',['SYNGENE1','BIN1','ENSG00000123456','ENSG00000123456.8','tag_ENSG00000123456','ENSMUSG00000123456'])
def test_gene_in_unexpected_column(gene):
    d,r=table(m.table_bytes([['odd'],[gene]]),"cols=['odd']")
    output,allowed,_=m.release_table(d,'run',{t:'unmask' for t in r},r)
    assert gene.encode() not in output


def test_generated_header_empty_cells_repeated_values_and_exact_bytes(tmp_path):
    raw=b'private-derived\tcategory\r\nSYNGENE1\t""\r\nSYNGENE1\t""\r\n'
    d,r=table(raw,"cols=['category']")
    masked=d['documents']['run']['table']
    assert masked[1]==masked[2]
    assert masked[0][0].startswith('{{TEXT-')
    path=tmp_path/'dict.json.zst';m.save_dictionary(path,d)
    assert m.restore_table(m.load_dictionary(path),'run')==raw
    output,allowed,audit=m.release_table(d,'run',{t:'unmask' for t in r},r)
    assert b'private-derived' in output


@pytest.mark.parametrize('value',['1.1','1E-3'])
def test_numeric_value_refused(value):
    d,r=table(m.table_bytes([['score'],[value]]),"cols=['score']")
    assert any(not rule['allowed'] for rule in r.values())


def test_zero_count_dense_rank_and_decimal_column():
    d,r=table(b'count\trank\tcategory\n7\t1\tSTARNET\n9\t1\tMiGA\n0\t2\tyes\n',"cols=['count','rank','category']")
    output,allowed,_=m.release_table(d,'run',{t:'unmask' for t in r},r)
    assert output==m.restore_table(d,'run') and all(v['allowed'] for v in r.values())
    d,r=table(b'score\n0\n0.1\n',"cols=['score']")
    assert any(not v['allowed'] for v in r.values())
    output,_,_=m.release_table(d,'run',{},r)
    assert output.splitlines()[1]==b'0'


class Staff:
    def __init__(self):self.metrics=[];self.calls=[]
    def call(self,role,prompt,rd,scribe_id=None,schema=None):
        self.calls.append(role)
        def choose(spec,key=''):
            if 'const' in spec:return spec['const']
            if spec['type']=='object':return {k:choose(v,k) for k,v in spec['properties'].items()}
            if key=='status':return spec['enum'][0]
            if key=='action':return 'run'
            if key=='reason':return 'ready'
            if 'enum' in spec:return 'unmask' if 'unmask' in spec['enum'] else spec['enum'][0]
            return 'A'
        return b.validate_constrained(choose(schema),schema)


def test_native_mask_flow_and_cached_numeric_review(case,monkeypatch):
    rp,_,request,policy=case
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained',reason='synthetic-auth-failure'))
    staff=Staff()
    def executor(policy,request,snapshot,selected,rd):
        rd.mkdir();(rd/'execution.log').write_text('PRIVATE_CANARY_TEST "SYNGENE1" 0.654321')
        return b'count\tscore\n2\t0.654321\n',[['count','score'],['2','0.654321']]
    script=Path(request['script']['path']);script.write_text(SCRIPT.decode()+"\ncols=['count','score']\n")
    request['script']['sha256']=b.digest(script.read_bytes());request['output']['columns']=['count','score'];rp.write_text(json.dumps(request))
    result=b.mask_run(rp,policy,staff,executor)
    assert result['status']=='completed' and result['google']['status']=='local-retained'
    rd=Path(policy['private_root'])/result['run_id']
    assert (rd/'human.tsv').read_bytes()==b'count\tscore\n2\t0.654321\n'
    outgoing=(rd/'answer.md').read_text()+json.dumps(result)
    assert '0.654321' not in outgoing and 'PRIVATE_CANARY_TEST' not in outgoing and 'SYNGENE1' not in outgoing
    assert staff.calls==['binding','binding','run-action','first-unmask']
    q={'action':'unmask','run':rd.name,'items':['score'],'reason':'Show the number'}
    for n in range(2):
        target=rd.parent/f'review-{n}';target.mkdir()
        receipt=b.unmask_request(q,policy,staff,target,'the coding agent')
        assert all(item['decision']=='keep masked' for item in receipt['decisions'])
        assert '0.654321' not in (target/'answer.md').read_text()+json.dumps(receipt)
    assert staff.calls.count('unmask-review')==0


@pytest.mark.parametrize('error',[ValueError('0.654321 "SYNGENE1"'),RuntimeError('PRIVATE_CANARY_TEST')])
def test_error_messages_do_not_leave(case,monkeypatch,error):
    rp,_,_,policy=case
    def failed(*a):raise error
    result=b.mask_run(rp,policy,Staff(),failed)
    rd=Path(policy['private_root'])/result['run_id']
    public=json.dumps(result)+(rd/'error.json').read_text()
    assert all(v not in public for v in ['0.654321','SYNGENE1','PRIVATE_CANARY_TEST'])


def test_schema_rejects_unknown_keys_and_invalid_choices():
    schema=b.unmask_schema(['{{VALUE-ABCD}}'])
    with pytest.raises(b.Rejected):b.validate_constrained({'extra':'unmask'},schema)
    with pytest.raises(b.Rejected):b.validate_constrained({'{{VALUE-ABCD}}':'reveal'},schema)


def test_google_result_failure_keeps_local_human_table(tmp_path,monkeypatch):
    path=tmp_path/'human.tsv';path.write_bytes(b'count\n3\n')
    monkeypatch.setattr(g,'result_settings',lambda p: (_ for _ in ()).throw(m.MaskError('google-authentication')))
    result=g.send_result({},tmp_path,path.read_bytes())
    assert result=={'status':'local-retained','reason':'google-authentication'}
    assert path.read_bytes()==b'count\n3\n'


@pytest.mark.parametrize('audience',['the coding agent','research committee caller','the coding agent through a strict local status filter','the user'])
def test_real_sandbox_mask_flow_across_audiences(case,monkeypatch,audience):
    import os,subprocess,shutil
    if os.environ.get('BROKER_TEST_SANDBOX')!='1':pytest.skip('native sandbox integration requires BROKER_TEST_SANDBOX=1')
    rp,_,request,policy=case
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='sent',document='synthetic-doc'))
    result=b.mask_run(rp,policy,Staff(),audience=audience)
    assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    assert (rd/'human.tsv').read_bytes()==b'count\n2\n'
    outgoing=(rd/'answer.md').read_text()+json.dumps(result)
    assert '0.654321' not in outgoing and 'PRIVATE_STDOUT' not in outgoing
    assert (rd/'execution/execution.json').is_file()


def test_real_sandbox_blocks_values_moved_into_column_names(case,monkeypatch):
    import os
    if os.environ.get('BROKER_TEST_SANDBOX')!='1':pytest.skip('native sandbox integration requires BROKER_TEST_SANDBOX=1')
    rp,_,request,policy=case
    policy.update(gene_columns=['label'])
    source=Path(policy['inputs']['toy']);source.write_text('group\tlabel\nA\tSYNGENE1\n')
    script=Path(request['script']['path']);script.write_text("import csv,json,sys\np=json.load(open(sys.argv[1]))\nrows=list(csv.DictReader(open(p['inputs']['table']),delimiter='\\t'))\nwith open(sys.argv[2],'w') as f:\n w=csv.writer(f,delimiter='\\t');w.writerow([rows[0]['label']]);w.writerow([len(rows)])\n")
    request['script']['sha256']=b.digest(script.read_bytes());request['output']['columns']=['SYNGENE1'];rp.write_text(json.dumps(request))
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained',reason='synthetic-offline'))
    result=b.mask_run(rp,policy,Staff());assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    assert 'SYNGENE1' not in (rd/'answer.md').read_text()+json.dumps(result)
    rules=json.loads((rd/'rules.json').read_text());assert any(v['rule']=='gene-identifier' for v in rules.values())


def test_operator_backend_assignment_adds_capacity_without_code(tmp_path):
    policy={'scribe_backends':[4,9,7],'lock_root':str(tmp_path),'scribes':[4,4]}
    assert [b.assign_staff(policy)['scribes'] for _ in range(3)]==[[4,9],[9,7],[7,4]]


@pytest.mark.parametrize('value',['0.654321','65.4321%','6.54321E-1'])
def test_native_seeded_table_logs_and_receipt_never_release_controls(case,monkeypatch,value):
    import os
    if os.environ.get('BROKER_TEST_SANDBOX')!='1':pytest.skip('native sandbox integration requires BROKER_TEST_SANDBOX=1')
    rp,_,request,policy=case
    source=Path(policy['inputs']['toy']);source.write_text('group\tvalue\tprivate_token\nA\t0.654321\tPRIVATE_CANARY_TEST\n')
    script=Path(request['script']['path']);script.write_text("import sys\nvalue="+repr(value)+"\nprint(value, 'quoted \\\"SYNGENE1\\\"')\nprint(value,file=sys.stderr)\nwith open(sys.argv[2],'w') as f:f.write('count\\n'+value+'\\n')\n")
    request['script']['sha256']=b.digest(script.read_bytes());rp.write_text(json.dumps(request))
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='sent',document='synthetic-doc'))
    result=b.mask_run(rp,policy,Staff());assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    public=(rd/'answer.md').read_text()+json.dumps(result)
    assert value not in public and 'SYNGENE1' not in public
    assert value in (rd/'execution/execution.log').read_text()


def test_literal_gene_header_and_embedded_decimal_stay_masked():
    d=m.empty_dictionary()
    raw=b'BIN1\tcategory\nplain\tscore: 0.654321\n'
    m.mask_table(d,'run',raw,"cols=['BIN1','category']",genes={'BIN1'})
    rules=m.table_rules(d,'run',genes={'BIN1'},protected=['0.654321'])
    output,_,_=m.release_table(d,'run',{t:'unmask' for t in rules},rules)
    assert b'BIN1' not in output and b'0.654321' not in output


def test_direct_call_has_no_tools_or_reload_options(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import urllib.request
    import io
    seen=[]
    monkeypatch.setattr(b.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=json.dumps(dict(id=4,model='synthetic-model',host='http://127.0.0.1:11444')).encode()))
    class Opener:
        def open(self,request,timeout):
            payload=json.loads(request.data);seen.append(payload)
            reply=dict(code="d={'quoted':\"text\"}",status='ok')
            return io.BytesIO(json.dumps(dict(message=dict(content=json.dumps(reply)),total_duration=1000000000)).encode())
    monkeypatch.setattr(urllib.request,'build_opener',lambda *a:Opener())
    policy=dict(lock_root=str(tmp_path/'locks'),agent_timeout_seconds=10)
    agents=b.DirectAgents(policy)
    schema=b.object_schema(dict(code=dict(type='string'),status=dict(type='string',enum=['ok','unresolved'])))
    reply=agents.call('librarian','Synthetic code integrity',tmp_path/'call',4,schema)
    assert reply['code']=="d={'quoted':\"text\"}" and 'tools' not in seen[0]
    # Only word-choice options are sent; nothing that would make the server reload the model.
    assert seen[0]['options']==dict(temperature=0.2,seed=11,num_predict=6000)
    assert agents.metrics[0]['model_seconds']==1


@pytest.mark.parametrize('value',['with SYNGENE1 support','with BIN1 support','xENSG00000123456'])
def test_embedded_gene_and_scaled_numeric_controls(value):
    d,r=table(m.table_bytes([['category'],[value]]), "cols=['category']")
    output,allowed,_=m.release_table(d,'run',{t:'unmask' for t in r},r)
    assert value.encode() not in output


def test_empty_manuscript_value_stays_invalid():
    with pytest.raises(m.MaskError):m.validate_runs('',[{'text':''}])
    m.validate_runs('',[{'text':''}],allow_empty=True)


def test_failed_review_is_consumed_once(case,monkeypatch):
    rp,_,request,policy=case
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained',reason='synthetic-auth-failure'))
    staff=Staff()
    result=b.mask_run(rp,policy,staff,lambda *a:(b'count\n2\n',[['count'],['2']]))
    rd=Path(policy['private_root'])/result['run_id']
    calls=[]
    class Failed:
        metrics=[]
        def call(self,*args):calls.append(args[0]);raise TimeoutError('private error')
    for i in range(2):
        review=rd.parent/f'failed-review-{i}';review.mkdir()
        receipt=b.unmask_request(dict(action='unmask',run=rd.name,items=['count'],reason='synthetic review'),policy,Failed(),review,'the coding agent')
        assert receipt['status']=='completed'
    assert calls==[]


def test_dynamic_private_header_executes_and_masks(case,monkeypatch):
    import os
    if os.environ.get('BROKER_TEST_SANDBOX')!='1':pytest.skip('native sandbox required')
    rp,_,request,policy=case
    policy=dict(policy,execution_mode='mask')
    Path(policy['inputs']['toy']).write_text('gene\tgroup\tvalue\nSYNGENE1\tA\t0.654321\nSYNGENE2\tB\t0.876543\n')
    script=Path(request['script']['path'])
    script.write_text("import csv,json,sys\np=json.load(open(sys.argv[1]))\nrows=list(csv.DictReader(open(p['inputs']['table']),delimiter=chr(9)))\nw=csv.writer(open(sys.argv[2],'w'),delimiter=chr(9),lineterminator=chr(10))\nw.writerow(['count',rows[0]['gene']])\nw.writerow([len(rows),rows[0]['gene']])\n")
    request['script']['sha256']=b.digest(script.read_bytes());request['output']['columns']=[];rp.write_text(json.dumps(request))
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained',reason='synthetic-auth-failure'))
    result=b.mask_run(rp,policy,Staff())
    assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    assert (rd/'answer.md').read_text().splitlines()[0].split('\t')[1].startswith('{{TEXT-')



def test_large_google_table_uses_private_file_link(tmp_path,monkeypatch):
    from types import SimpleNamespace
    raw=b'category\n'+b'synthetic\n'*5000
    (tmp_path/'human.tsv').write_bytes(raw)
    monkeypatch.setattr(g,'result_settings',lambda p:dict(rclone_remote='toy'))
    monkeypatch.setattr(g,'ensure_folder',lambda *a:'private-folder')
    monkeypatch.setattr(g,'ensure_file',lambda *a:'scratch-document')
    commands=[];drive=[];entries=[]
    def process(command,**kwargs):commands.append(command);return SimpleNamespace(returncode=0,stdout='')
    def drive_api(config,method,**kwargs):drive.append(method);return dict(files=[dict(id='private-file')])
    def api(config,method,identifier,params=None,body=None):
        if method=='POST':entries.append(body['requests'][0]['insertText']['text']);return {}
        if params:return dict(revisionId='revision',body=dict(content=[dict(endIndex=2)]))
        return dict(body=dict(content=[dict(paragraph=dict(elements=[dict(textRun=dict(content=''.join(entries)))]))]))
    monkeypatch.setattr(g.subprocess,'run',process);monkeypatch.setattr(g,'drive_api',drive_api);monkeypatch.setattr(g,'api',api)
    result=g.send_result(dict(google_config=str(tmp_path/'codex/config.toml')),tmp_path,raw)
    assert result['status']=='sent'
    assert commands==[['rclone','copyto',str(tmp_path/'human.tsv'),'toy:Librarian/results/'+tmp_path.name+'.tsv','--retries','1']]
    assert drive==['GET'] and 'https://drive.google.com/file/d/private-file/view' in entries[0]


@pytest.mark.parametrize('value',['score0.123456789','prefix1.23E-6','fraction1.23%'])
def test_noninteger_numeric_text_cannot_be_relabelled_category(value):
    d,r=table(m.table_bytes([['category'],[value]]), "cols=['category']")
    output,_,_=m.release_table(d,'run',{},r)
    assert value.encode() not in output
    d=m.empty_dictionary();masked=m.mask_table(d,'run',m.table_bytes([[value],['text']]),'header='+repr(value))
    assert value.encode() not in masked



def test_native_local_agent_unresolved_retries_then_escalates(case,tmp_path):
    import os
    if os.environ.get('BROKER_TEST_SANDBOX')!='1':pytest.skip('native sandbox required')
    _,_,_,policy=case;policy=dict(policy,max_attempts=2,review_backend=9)
    code="import csv,json,sys\np=json.load(open(sys.argv[1]))\nrows=list(csv.DictReader(open(p['inputs']['table']),delimiter=chr(9)))\nw=csv.writer(open(sys.argv[2],'w'),delimiter=chr(9),lineterminator=chr(10))\nw.writerow(['count'])\nw.writerow([len(rows)])\n"
    calls=[]
    class Staff:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append((role,backend))
            action='run_python' if len(calls) in (1,4) else 'unresolved' if len(calls)<4 else 'answer'
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code=code if action=='run_python' else ''),schema)
    rd=tmp_path/'agent';rd.mkdir()
    request=b.local_question(dict(action='question',question='Count all data rows',inputs={'table':'toy'}),policy,Staff(),rd)
    assert request['output']['columns']==['count']
    assert (rd/'agent-execution-0/out/result.tsv').read_bytes()==b'count\n3\n'
    assert len(calls)==5 and calls[-1]==('local-agent-escalation',9)


def test_local_agent_incomplete_contract_escalates_without_private_retry(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=2,review_backend=9,pushback=dict(attempts=99,tries=1))
    calls=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append((role,backend,prompt))
            action='run_python' if len(calls)<4 else 'answer'
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code='pass' if action=='run_python' else ''),schema)
    def execute(policy,request,snapshot,selected,rd,dynamic_columns=False):
        return (b'item\tanswer\nQ1\tPRIVATE_CANARY_TEST\n' if len(calls)<3 else b'item\tanswer\nQ1\tyes\nQ2\tno\n'),[]
    monkeypatch.setattr(b,'execute',execute)
    rd=tmp_path/'agent';rd.mkdir()
    request=b.local_question(dict(action='question',question='Return items Q1 through Q2 in order',inputs={'table':'toy'}),policy,Agent(),rd)
    assert request['output']['columns']==['item','answer']
    assert [backend for _,backend,_ in calls]==[4,4,9,9]
    assert all('PRIVATE_CANARY_TEST' not in prompt for _,_,prompt in calls)


def test_local_agent_can_repair_table_after_final_unresolved(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=2,review_backend=9,pushback=dict(attempts=99,tries=1))
    calls=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append(prompt)
            action=['run_python','unresolved','run_python','answer'][len(calls)-1]
            code='#'+('x'*5000) if action=='run_python' else ''
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code=code),schema)
    monkeypatch.setattr(b,'execute',lambda *a,**kw:(b'count\n3\n',[]))
    rd=tmp_path/'agent';rd.mkdir()
    request=b.local_question(dict(action='question',question='Count rows',inputs={'table':'toy'}),policy,Agent(),rd)
    assert len(calls)==4 and 'Repair the computed script' in calls[2]
    assert request['script']['path'].endswith('agent-script-2.py')


def test_local_execution_errors_escalate_with_public_type_only(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=2,review_backend=9,pushback=dict(attempts=99,tries=1))
    calls=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append((backend,prompt))
            action='run_python' if len(calls)<4 else 'answer'
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code='pass' if action=='run_python' else ''),schema)
    def execute(*args,**kw):
        if len(calls)<3:raise ValueError('PRIVATE_CANARY_TEST 0.654321')
        return b'count\n3\n',[]
    monkeypatch.setattr(b,'execute',execute)
    rd=tmp_path/'agent';rd.mkdir()
    b.local_question(dict(action='question',question='Count rows',inputs={'table':'toy'}),policy,Agent(),rd)
    assert [backend for backend,_ in calls]==[4,4,9,9]
    assert all('PRIVATE_CANARY_TEST' not in prompt and '0.654321' not in prompt for _,prompt in calls)



def test_empty_table_still_has_mandatory_staff_first_pass(case,monkeypatch):
    rp,_,_,policy=case
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained',reason='synthetic-auth-failure'))
    staff=Staff()
    result=b.mask_run(rp,policy,staff,lambda *a:(b'count\n',[['count']]))
    assert result['status']=='completed'
    rd=Path(policy['private_root'])/result['run_id']
    assert staff.calls==['binding','binding','run-action','first-unmask']
    assert json.loads((rd/'audit.json').read_text())['first_unmask_status']=='reviewed'
    assert (rd/'human.tsv').read_bytes()==b'count\n'


@pytest.mark.parametrize('value',['-2','0','1','987654321','654321','1.0','-2.00','1E3','0%','95%','6,543,210'])
def test_every_whole_number_releases_even_when_staff_withholds(value):
    raw=m.table_bytes([['score'],[value]])
    d=m.empty_dictionary();m.mask_table(d,'run',raw,'')
    rules=m.table_rules(d,'run',genes={value},protected={value},gene_columns=['score'],protected_columns=['score'])
    out,allowed,_=m.release_table(d,'run',{t:'keep masked' for t in rules},rules)
    assert m.whole_number(value).encode() in out and any(r['rule']=='allowed-integer' for r in rules.values())


@pytest.mark.parametrize('text',['SET','MAX','REST','CAT','PROXY','INTACT_PP','LIBRARIAN_BROKER_POLICY','MAX_VALUE','category_SET'])
def test_ambiguous_words_and_technical_components_are_not_genes(text):
    assert not m.contains_gene(text,{'SET','MAX','REST','CAT','PROXY','PP'})


def test_gene_columns_override_ambiguous_stop_list_and_long_text_masks_in_place():
    d=m.empty_dictionary();m.mask_table(d,'run',b'gene\tnote\nSET\tSupport BIN1 in peripheral tissue at 0.8123\n','')
    rules=m.table_rules(d,'run',genes={'SET','BIN1'},gene_columns=['gene'])
    out,_,_=m.release_table(d,'run',{},rules)
    import re
    assert re.search(rb'Support \{\{TEXT-[A-Z0-9]+\}\} \[gene identifier\] in peripheral tissue at \{\{VALUE-[A-Z0-9]+\}\} \[decimal value\]',out)
    assert b'SET' not in out and b'BIN1' not in out and b'0.8123' not in out


def test_staff_can_withhold_text_with_reason_and_review_cannot_touch_absolute_cells(case,monkeypatch):
    rp,_,_,policy=case
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='local-retained'))
    class Safety(Staff):
        def call(self,role,prompt,rd,scribe_id=None,schema=None):
            value=super().call(role,prompt,rd,scribe_id,schema)
            if role=='first-unmask':
                return {k:dict(decision='keep masked',reason='variant identifier missed by vocabulary') for k in value}
            return value
    staff=Safety();r=b.mask_run(rp,policy,staff,lambda *a:(b'count\tlabel\tscore\n654321\trs123456\t0.8123\n',[]))
    source=Path(policy['private_root'])/r['run_id'];raw=(source/'answer.md').read_text()
    assert '654321' in raw and '[withheld by staff]' in raw and '[decimal value]' in raw
    review=source.parent/'review';review.mkdir()
    receipt=b.unmask_request(dict(action='unmask',run=source.name,items=['label','score'],reason='review staff withholding'),dict(policy,review_backend=4),Staff(),review,'the coding agent')
    assert receipt['review_backend']==4 and 'backend 9' in receipt['review_note']
    assert 'rs123456' in (review/'answer.md').read_text() and '0.8123' not in (review/'answer.md').read_text()



def test_unavailable_large_review_backend_uses_existing_scribe_only(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import urllib.request,io
    commands=[];payloads=[]
    def process(command,**kwargs):
        commands.append(command)
        if command[0]=='bjobs':return SimpleNamespace(returncode=0,stdout='EXIT\n')
        assert command[-1]=='4'
        return SimpleNamespace(returncode=0,stdout=json.dumps(dict(id=4,model='synthetic-model',host='http://127.0.0.1:11444')).encode())
    class Opener:
        def open(self,request,timeout):
            payloads.append(json.loads(request.data))
            return io.BytesIO(json.dumps(dict(message=dict(content=json.dumps(dict(status='reviewed'))),total_duration=1000000000)).encode())
    monkeypatch.setattr(b.subprocess,'run',process);monkeypatch.setattr(urllib.request,'build_opener',lambda *a:Opener())
    agents=b.DirectAgents(dict(lock_root=str(tmp_path/'locks'),agent_timeout_seconds=10,scribes=[4,4]))
    agents.call('unmask-review','invented request',tmp_path/'call',9,b.object_schema(dict(status=dict(type='string',enum=['reviewed']))))
    assert agents.last_review_backend==4 and agents.metrics[0]['backend']==4
    assert len(payloads)==1 and all('273831252' not in str(command) for command in commands)


@pytest.mark.parametrize('value',['NaN','Infinity','-inf'])
def test_nonfinite_words_are_permitted_text(value):
    d,r=table(m.table_bytes([['category'],[value]]))
    out,_,_=m.release_table(d,'run',{},r)
    assert value.encode() in out



def test_local_loop_requires_computation_and_repairs_all_ordered_parts(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,pushback=dict(attempts=99,tries=1));calls=[];outputs=iter([b'metric\tcount\nfirst\t2\n',b'metric\tcount\nfirst\t2\nsecond\t3\n'])
    monkeypatch.setattr(b,'execute',lambda *a,**k:(next(outputs),[]))
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append(prompt)
            is_final='answer' in schema['properties']['action']['enum']
            assert 'Parts checklist' in prompt
            return b.validate_constrained(dict(action='answer' if is_final else 'run_python',input_id='toy',column='',n=1,code='' if is_final else 'pass'),schema)
    rd=tmp_path/'parts';rd.mkdir()
    result=b.local_question(dict(action='question',question='Return columns metric,count in this order: first, second.',inputs={'table':'toy'}),policy,Agent(),rd)
    assert len(calls)==3 and result['output']['columns']==['metric','count']
    assert 'requested-labels-incomplete' in calls[1]


def test_local_final_prompt_marks_large_preview_truncated(case,tmp_path,monkeypatch):
    _,_,_,policy=case;prompts=[]
    monkeypatch.setattr(b,'execute',lambda *a,**k:(b'category\n'+b'ordinary category\n'*1000,[]))
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            prompts.append(prompt);is_final='answer' in schema['properties']['action']['enum']
            return b.validate_constrained(dict(action='answer' if is_final else 'run_python',input_id='toy',column='',n=1,code='' if is_final else 'pass'),schema)
    rd=tmp_path/'preview';rd.mkdir()
    b.local_question(dict(action='question',question='Return all category rows.',inputs={'table':'toy'}),policy,Agent(),rd)
    assert 'PREVIEW TRUNCATED' in prompts[-1] and '1000 data rows' in prompts[-1]


@pytest.mark.parametrize("error,expected",[("KeyError", "KeyError"),("SyntaxError", "SyntaxError"),("PRIVATE_GENE_Error", "ExecutionError")])
def test_execution_feedback_contains_builtin_type_and_script_line_only(tmp_path,error,expected):
    log=tmp_path/'execution.log'
    log.write_text('Traceback (most recent call last):\n  File "/job/analysis", line 17, in <module>\n    PRIVATE_GENE 0.654321\n'+error+': PRIVATE_GENE 0.654321\n')
    result=b.execution_diagnostic(log)
    assert result==dict(exception=expected,script_line=17)
    assert 'PRIVATE_GENE' not in json.dumps(result) and '0.654321' not in json.dumps(result)


def test_local_last_unresolved_has_reserved_main_execution_and_answer_turns(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=3,review_backend='main',pushback=dict(attempts=99,tries=1))
    calls=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            calls.append((role,backend))
            action='run_python' if len(calls)%2 else ('answer' if len(calls)==8 else 'unresolved')
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code='pass' if action=='run_python' else ''),schema)
    monkeypatch.setattr(b,'execute',lambda *a,**kw:(b'count\n3\n',[]))
    rd=tmp_path/'agent';rd.mkdir()
    result=b.local_question(dict(action='question',question='Count rows',inputs={'table':'toy'}),policy,Agent(),rd)
    assert result['script']['path'].endswith('agent-script-6.py')
    assert calls[-2:]==[('local-agent-escalation','main'),('local-agent-escalation','main')]


def test_result_delivery_settings_do_not_require_a_manuscript_dictionary(tmp_path,monkeypatch):
    home=tmp_path/'repository';(home/'.git').mkdir(parents=True);(home/'.git/HEAD').write_text('ref: refs/heads/main')
    config=home/'codex/config.toml';config.parent.mkdir()
    config.write_text('[masking]\ndictionary="../dict.json.zst"\nrclone_remote="test_drive"\nresults_title="Scratch"\n')
    with pytest.raises(m.MaskError,match='dictionary-in-repository'):m.settings(config)
    entries=[]
    monkeypatch.setattr(g,'ensure_folder',lambda *a:'folder')
    monkeypatch.setattr(g,'ensure_file',lambda *a:'document')
    def api(settings,method,identifier,params=None,body=None):
        assert settings['rclone_remote']=='test_drive'
        if method=='POST':entries.append(body['requests'][0]['insertText']['text']);return {}
        if params:return dict(revisionId='rev',body=dict(content=[dict(endIndex=2)]))
        return dict(body=dict(content=[dict(paragraph=dict(elements=[dict(textRun=dict(content=''.join(entries)))]))]))
    monkeypatch.setattr(g,'api',api)
    run=home/'run-test';run.mkdir()
    result=g.send_result(dict(google_config=str(config)),run,b'count\n3\n')
    assert result['status']=='sent' and 'run-test' in ''.join(entries)


@pytest.mark.parametrize('heading,shown',[('gene_id',True),('ENSG00000123456',False),('0.32',False)])
def test_operator_column_labels_release_but_identifier_and_decimal_headings_stay_masked(case,monkeypatch,heading,shown):
    rp,_,_,policy=case;policy.update(gene_columns=[heading,'gene_symbol'])
    raw=(heading+'\tgene_symbol\trank\nGENE_A\tGENE_A\t1\n').encode()
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='retained'))
    class StaffNet(Staff):
        def call(self,role,prompt,rd,scribe_id=None,schema=None):
            if role=='first-unmask':
                return {token:dict(decision='keep masked',reason='identifier column heading') for token in schema['properties']}
            return super().call(role,prompt,rd,scribe_id,schema)
    receipt=b.mask_run(rp,policy,StaffNet(),lambda *a:(raw,[]));assert receipt['status']=='completed'
    out=(Path(policy['private_root'])/receipt['run_id']/'answer.md').read_text()
    header=out.splitlines()[0].split('\t')
    assert (header[0]==heading)==shown
    assert header[1]=='gene_symbol'
    assert 'GENE_A' not in out and out.splitlines()[1].split('\t')[-1]=='1'


@pytest.mark.parametrize('heading,policy_list,shown',[('gene_name',None,True),('locus_label',['locus_label'],True),('locus_label',None,False),('GENE_A',None,False)])
def test_whitelisted_headings_show_while_gene_values_stay_masked(case,monkeypatch,heading,policy_list,shown):
    rp,_,_,policy=case;policy.update(gene_columns=['gene_symbol'])
    if policy_list is not None:policy.update(shown_headings=policy_list)
    raw=(heading+'\tgene_symbol\trank\nGENE_A\tGENE_A\t1\n').encode()
    monkeypatch.setattr(g,'send_result',lambda *a:dict(status='retained'))
    class StaffNet(Staff):
        def call(self,role,prompt,rd,scribe_id=None,schema=None):
            if role=='first-unmask':
                return {token:dict(decision='keep masked',reason='identifier column heading') for token in schema['properties']}
            return super().call(role,prompt,rd,scribe_id,schema)
    receipt=b.mask_run(rp,policy,StaffNet(),lambda *a:(raw,[]));assert receipt['status']=='completed'
    out=(Path(policy['private_root'])/receipt['run_id']/'answer.md').read_text()
    header=out.splitlines()[0].split('\t')
    assert (header[0]==heading)==shown
    assert header[1]=='gene_symbol'
    assert 'GENE_A' not in out and out.splitlines()[1].split('\t')[-1]=='1'


def test_local_agent_helpers_catch_misnamed_columns_and_headers():
    assert b.unknown_columns("x=[r for r in reader if r.get('scheme_label')=='a']\nd={'k':1}\nd.get('k');p.get('inputs');r.get('gene_id')",{'gene_id'})==['scheme_label']
    assert b.unknown_columns("def broken(:",{'gene_id'})==[]
    assert b.requested_header('Report counts: columns panel_key,count (count copies genes).')==['panel_key','count']
    assert b.requested_header('Return input,header_present,rectangular,data_present using yes/no.')==['input','header_present','rectangular','data_present']
    assert b.requested_header('Use gene_id, source_eqtl and source_gwas as identity columns.') is None


def test_local_agent_retries_on_renamed_header_and_unknown_column(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=3,review_backend=9,pushback=dict(attempts=3,tries=1))
    codes=iter(["r.get('not_a_column')","pass","pass"]);tables=iter([b'gene\tn\nA\t3\n',b'gene\tcount\nA\t3\n']);prompts=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            prompts.append(prompt)
            action='answer' if 'enum' in schema['properties']['action'] and schema['properties']['action']['enum']==['answer','unresolved'] else 'run_python'
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code=next(codes) if action=='run_python' else ''),schema)
    monkeypatch.setattr(b,'execute',lambda *a,**k:(next(tables),[]))
    rd=tmp_path/'agent';rd.mkdir()
    b.local_question(dict(action='question',question='Count rows per gene. Return columns gene,count.',inputs={'table':'toy'}),policy,Agent(),rd)
    assert 'unknown-input-columns' in prompts[1] and 'requested-header-mismatch' in prompts[2]


BAD_WORDS=r"\b(not|no|never|cannot|can't|don't|won't|unable|refuse|reject|deny|withheld|forbidden|prohibited|complex|too)\b"


def test_request_size_counts_words_and_clause_marks():
    assert b.request_size('Count rows.')==(2,1)
    assert b.request_size('Return a,b; then (c): done. Next?')==(6,6)


def test_large_request_is_handed_back_before_any_model_call(case,tmp_path):
    _,_,_,policy=case
    class Agent:
        metrics=[]
        def call(self,*a,**k):raise AssertionError('model called')
    question=' '.join(['Count rows,']*60)
    rd=tmp_path/'agent';rd.mkdir()
    with pytest.raises(b.Pushback) as info:b.local_question(dict(action='question',question=question,inputs={'table':'toy'}),policy,Agent(),rd)
    text=str(info.value)
    assert text=='This request has 60 clauses in 120 words and names 1 table. Send it as a script, or ask one part at a time.'
    assert not re.search(BAD_WORDS,text,re.I)


def test_two_failed_attempts_hand_the_request_back_as_a_completed_reply(case,monkeypatch):
    rp,_,_,policy=case;policy=dict(policy,max_attempts=5,review_backend=9)
    request=Path(rp).parent/'question.json'
    request.write_text(json.dumps(dict(action='question',question='Count rows per gene. Return columns gene,count.',inputs={'table':'toy'})))
    backends=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema):
            backends.append(backend)
            return b.validate_constrained(dict(action='run_python',input_id='toy',column='',n=1,code='pass'),schema)
    monkeypatch.setattr(b,'execute',lambda *a,**k:(b'gene\tn\nA\t3\n',[]))
    receipt=b.mask_run(str(request),policy,Agent())
    out=(Path(policy['private_root'])/receipt['run_id']/'answer.md').read_text()
    assert receipt['status']=='completed' and receipt['pushback'] is True and 'google' not in receipt
    assert out=='2 attempts at this request ended with an incomplete table. Send it as a script, or ask one part at a time.\n'
    assert not re.search(BAD_WORDS,out,re.I) and 9 not in backends and 'main' not in backends


def test_two_local_tries_must_agree_or_the_request_goes_back(case,tmp_path,monkeypatch):
    _,_,_,policy=case;policy=dict(policy,max_attempts=3,review_backend=9)
    seen=[]
    class Agent:
        metrics=[]
        def call(self,role,prompt,rd,backend,schema,seed=None):
            seen.append(seed)
            action='answer' if schema['properties']['action']['enum']==['answer','unresolved'] else 'run_python'
            return b.validate_constrained(dict(action=action,input_id='toy',column='',n=1,code='pass' if action=='run_python' else ''),schema)
    question=dict(action='question',question='Count rows per gene. Return columns gene,count.',inputs={'table':'toy'})
    tables=iter([b'gene\tcount\nA\t3\nB\t1\n',b'gene\tcount\nB\t1\nA\t3\n'])
    monkeypatch.setattr(b,'execute',lambda *a,**k:(next(tables),[]))
    rd=tmp_path/'same';rd.mkdir()
    b.local_question(question,policy,Agent(),rd)
    assert seen==[11,11,23,23]
    tables=iter([b'gene\tcount\nA\t3\n',b'gene\tcount\nA\t0\n'])
    rd=tmp_path/'differ';rd.mkdir()
    with pytest.raises(b.Pushback) as info:b.local_question(question,policy,Agent(),rd)
    assert str(info.value)=='2 independent tries at this request produced different tables. Send it as a script, or ask one part at a time.'
    assert not re.search(BAD_WORDS,str(info.value),re.I)


def test_cut_off_or_empty_reply_is_asked_again_with_the_next_seed(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import urllib.request, io
    seen=[]
    monkeypatch.setattr(b.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=json.dumps(dict(id=4,model='synthetic-model',host='http://127.0.0.1:11444')).encode()))
    replies=iter([dict(message=dict(content=''),done_reason='length'),dict(message=dict(content='not json'),done_reason='stop'),
                  dict(message=dict(content=json.dumps(dict(status='ok'))),done_reason='stop',total_duration=1000000000)])
    class Opener:
        def open(self,request,timeout):
            seen.append(json.loads(request.data)['options']['seed']);return io.BytesIO(json.dumps(next(replies)).encode())
    monkeypatch.setattr(urllib.request,'build_opener',lambda *a:Opener())
    agents=b.DirectAgents(dict(lock_root=str(tmp_path/'locks'),agent_timeout_seconds=10))
    reply=agents.call('librarian','Synthetic',tmp_path/'call',4,b.object_schema(dict(status=dict(type='string',enum=['ok','unresolved']))))
    assert reply=={'status':'ok'} and seen==[11,12,14] and len(agents.metrics[0]['repeats'])==2
