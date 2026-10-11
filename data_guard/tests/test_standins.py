"""Invented data exercises the real dictionary, release path and linked command."""
import json
import re
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
import broker as b
import masking as m
import standins as s

BAD = r"\b(?:not|no|never|cannot|can't|don't|won't|unable|refuse|reject|deny|withheld|forbidden|prohibited|secret|cheat|infer|guess|narrow|work around|threshold)\b"

@pytest.fixture
def case(tmp_path,monkeypatch):
 import google_docs
 monkeypatch.setattr(google_docs,'send_result',lambda *a:dict(status='retained'))
 raw=b'gene\tINTACT_PP\tbeta\tnote\nGENE_A\t0.91\t-0.32\tstaff-id\nGENE_B\t0.97\t0.11\tstaff-other\nGENE_A\t0.91\t-0.32\tstaff-id\n'
 d=m.empty_dictionary();name='run-'+'a'*32
 m.mask_table(d,name,raw,'',genes=['GENE_A','GENE_B'])
 rules=m.table_rules(d,name,genes=['GENE_A','GENE_B'],gene_columns=['gene'],protected_columns=['INTACT_PP','beta'])
 choices={t:'keep masked' for t,ps in d['documents'][name]['positions'].items() if any(i>0 and j==3 for i,j in ps)}
 released,allowed,decisions=m.release_table(d,name,choices,rules)
 policy=s.configure_policy(dict(scribes=[4,4],private_root=str(tmp_path/'private'),gene_columns=['gene'],protected_columns=['INTACT_PP','beta'],max_input_bytes=1024**2))
 source=Path(policy['private_root'])/name;source.mkdir(parents=True);source.parent.chmod(0o700)
 m.save_dictionary(source/'dict.json.zst',d)
 b.save(source/'rules.json',rules);b.save(source/'release.json',dict(allowed=allowed,decisions=decisions,reviewed={}))
 b.save(source/'bindings.json',dict(inputs={'table':'toy'},parameters={}))
 (source/'snapshot/inputs').mkdir(parents=True);(source/'snapshot/inputs/toy').write_bytes(raw)
 tokens={c:[d['documents'][name]['table'][i][j] for i in (1,2)] for j,c in enumerate(d['documents'][name]['columns'])}
 return policy,source,d,name,released,decisions,tokens


def test_reply_is_single_positive_frame_and_uses_output(case):
 p,_,d,n,raw,decisions,_=case
 out,reply,meta=s.decorate(raw,d,n,decisions,p)
 assert not re.search(BAD,reply,re.I)
 assert len(reply.splitlines())==4
 assert 'row count, rank, group, or match with another placeholder' in reply
 assert 'rank, or comparison with another placeholder' in reply
 assert 'row count, group, or match with another placeholder' in reply
 assert 'INTACT PP (2 items)' in reply
 assert '(bin, percentile)' in reply
 assert '(direction, percentile, absolute value percentile)' in reply
 assert all(line.count('Use the placeholder in your work;')==1 for line in reply.splitlines())
 assert 'INTACT_PP_bin' in out.decode() and 'beta_absolute_percentile' in out.decode()


def test_single_item_reply_reads_attached_facts(case):
 p,_,d,n,raw,decisions,tokens=case
 # Keep just one decimal item masked; facts must come from generated output.
 decisions=[x for x in decisions if x['item']==tokens['INTACT_PP'][0]]
 out,reply,_=s.decorate(raw,d,n,decisions,p)
 assert 'bin 0.80 to below 0.95, percentile 67' in reply
 assert '{{VALUE-' in reply
 assert not re.search(BAD,reply,re.I)

@pytest.mark.parametrize('operation,column,kwargs,expected',[
 ('count','gene',{},'2'),('rank','gene',{},'1'),('group','gene',{},'group-1'),
 ('match','gene',{'other_column':'gene','other_index':0},'true'),
 ('match','gene',{'other_column':'gene','other_index':1},'false'),
 ('compare','INTACT_PP',{'other_column':'INTACT_PP','other_index':1},'smaller'),
 ('compare','INTACT_PP',{'other_column':'INTACT_PP','other_index':0},'equal'),
 ('rank','INTACT_PP',{},'2'),('rank','INTACT_PP',{'order':'ascending'},'1'),
 ('direction','beta',{},'-'),('percentile','beta',{},'67'),
 ('absolute_percentile','beta',{},'100'),('bin','INTACT_PP',{},'0.80 to below 0.95'),
 ('threshold','INTACT_PP',{'threshold':0.95},'false'),
 ('percentile','INTACT_PP',{'reference':{'kind':'source','column':'INTACT_PP','input':'toy'}},'67'),
])
def test_linked_forms_preserve_review_state(case,tmp_path,operation,column,kwargs,expected):
 p,source,d,n,raw,decisions,tokens=case
 spec=dict(operation=operation,item=tokens[column][0])
 kwargs=dict(kwargs)
 if 'other_column' in kwargs:spec['other']=tokens[kwargs.pop('other_column')][kwargs.pop('other_index')]
 spec.update(kwargs)
 prior=b.read_json(source/'release.json')['reviewed']
 rd=b.directory(tmp_path/'request')
 receipt=s.linked(dict(action='rephrase',run=n,operations=[spec]),p,rd,'the coding agent')
 assert s.rows((rd/'answer.md').read_bytes())==[['operation','result'],[operation,expected]]
 assert receipt['linked_run']==n and receipt['service']=='librarian'
 assert b.read_json(rd/'audit.json')['linked_run']==n
 assert b.read_json(source/'release.json')['reviewed']==prior

@pytest.mark.parametrize('unit,expected',[('rows','2'),('genes','1')])
def test_condition_counts(case,tmp_path,unit,expected):
 p,_,_,n,_,_,_=case
 spec=dict(operation='count',unit=unit,condition=dict(column='INTACT_PP',operator='<',value=0.95))
 rd=b.directory(tmp_path/'request')
 s.linked(dict(action='rephrase',run=n,operations=[spec]),p,rd,'the coding agent')
 assert s.rows((rd/'answer.md').read_bytes())[1][1]==expected


def test_cap_shared_across_requests_and_bin_edges(case,tmp_path):
 p,source,_,n,_,_,tokens=case
 op=dict(operation='threshold',item=tokens['INTACT_PP'][0],threshold=0.8)
 for i in range(3):s.linked(dict(action='rephrase',run=n,operations=[op]),p,b.directory(tmp_path/f'call{i}'),'the coding agent')
 with pytest.raises(b.Rejected,match='stand-in-threshold-cap'):
  s.linked(dict(action='rephrase',run=n,operations=[op]),p,b.directory(tmp_path/'four'),'the coding agent')
 assert b.read_json(source/'release.json')['threshold_questions'][tokens['INTACT_PP'][0]]==3
 with pytest.raises(b.Rejected,match='stand-in-threshold-edge'):
  s.linked(dict(action='rephrase',run=n,operations=[dict(op,threshold=0.8123)]),p,b.directory(tmp_path/'edge'),'the coding agent')

@pytest.mark.parametrize('value,expected',[(0.49,'below 0.50'),(0.5,'0.50 to below 0.70'),(0.7,'0.70 to below 0.80'),(0.8,'0.80 to below 0.95'),(0.95,'0.95 and above')])
def test_bins_are_policy_owned(value,expected):
 assert s.bin_value(value,dict(edges=s.DEFAULT_EDGES,labels=s.DEFAULT_LABELS))==expected
 assert s.bin_value(value,dict(edges=[0.5],labels=['low','high'])) in ('low','high')

@pytest.mark.parametrize('value,expected',[(0,'0'),(1,'100'),(0.5,'50')])
def test_percentile_endpoints(value,expected):assert s.percentile(value,[0.25,0.75])==expected


def test_registry_updates_reply(case,monkeypatch):
 p,_,d,n,raw,decisions,_=case
 monkeypatch.setitem(s.OPERATIONS,'added',dict(kinds=('gene identifier',),phrase='added operation'))
 assert 'added operation' in s.decorate(raw,d,n,decisions,p)[1]


def test_rephrase_dispatch_uses_same_native_broker(case,tmp_path):
 p,source,_,n,_,_,tokens=case
 p.update(scribes=[4,4])
 path=tmp_path/'request.json';path.write_text(json.dumps(dict(action='rephrase',run=n,operations=[dict(operation='rank',item=tokens['gene'][0])])))
 result=b.mask_run(path,p)
 assert result['status']=='completed' and result['linked_run']==n


def test_main_model_pin_stops_before_inference(tmp_path):
 import threading
 state=tmp_path/'main.env';state.write_text('MINERVA_OLLAMA_DEFAULT_MODEL=other-model\n')
 agents=b.DirectAgents(dict(main_state=str(state),agent_timeout_seconds=1))
 with pytest.raises(b.Rejected,match='main-model-pin'):
  s.main_call(agents,'unmask-review','x',tmp_path,dict(type='object'))
 assert not agents.metrics

@pytest.mark.parametrize('resident_ok',[False,True])
def test_main_resident_pin_lock_and_constrained_payload(tmp_path,resident_ok):
 import fcntl,threading
 from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
 pin='laguna-s-2.1:q8_0-256k-t2';lock=tmp_path/'librarian.lock';lock.touch();payloads=[]
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   body=json.dumps(dict(models=[dict(name=pin if resident_ok else 'different')])).encode()
   self.send_response(200);self.end_headers();self.wfile.write(body)
  def do_POST(self):
   payloads.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
   with lock.open('a') as f:
    with pytest.raises(BlockingIOError):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   body=json.dumps(dict(message=dict(content='{"status":"reviewed"}'),total_duration=1000000000)).encode()
   self.send_response(200);self.end_headers();self.wfile.write(body)
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
 state=tmp_path/'state';state.write_text(f'MINERVA_OLLAMA_DEFAULT_MODEL={pin}\nMINERVA_OLLAMA_LOCAL_PORT={server.server_port}\n')
 agents=b.DirectAgents(dict(main_state=str(state),main_lock=str(lock),agent_timeout_seconds=5))
 try:
  schema=b.object_schema(dict(status=dict(type='string',enum=['reviewed'])))
  if resident_ok:
   assert s.main_call(agents,'unmask-review','Review the staff text.',tmp_path,schema)==dict(status='reviewed')
   assert set(payloads[0])=={'model','stream','format','messages'}
   assert payloads[0]['model']==pin and agents.metrics[0]['backend']=='main'
   assert agents.metrics[0]['model_seconds']==1
  else:
   with pytest.raises(b.Rejected,match='main-resident-model-mismatch'):s.main_call(agents,'unmask-review','x',tmp_path,schema)
   assert payloads==[] and agents.metrics==[]
 finally:server.shutdown();thread.join();server.server_close()


def test_review_refusal_uses_template_and_retains_one_review(case,tmp_path):
 p,source,_,n,_,_,tokens=case
 (source/'snapshot/analysis').write_text('print("private")')
 class Staff:
  metrics=[]
  count=0
  def call(self,role,prompt,rd,backend,schema):
   self.count+=1
   return {tokens['note'][0]:dict(decision='keep masked',reason='identifier concern')}
 staff=Staff();request=dict(action='unmask',run=n,items=[tokens['note'][0]],reason='Use the staff entry')
 first=b.unmask_request(request,p,staff,b.directory(tmp_path/'review1'),'the coding agent')
 second=b.unmask_request(request,p,staff,b.directory(tmp_path/'review2'),'the coding agent')
 assert staff.count==1
 assert first['rephrase_request']==second['rephrase_request']
 assert 'entry set aside by staff' in first['rephrase_request']
 assert not re.search(BAD,first['rephrase_request'],re.I)
 assert tokens['note'][1] not in b.read_json(source/'release.json')['reviewed']


def test_linked_question_is_audited(case,tmp_path):
 p,_,_,n,_,_,tokens=case
 rd=b.directory(tmp_path/'linked')
 s.linked(dict(action='rephrase',run=n,question='What is the position of this placeholder?',operations=[dict(operation='rank',item=tokens['gene'][0])]),p,rd,'the coding agent')
 assert b.read_json(rd/'audit.json')['question']=='What is the position of this placeholder?'


def test_signed_round_tenth_threshold(case,tmp_path):
 p,_,_,n,_,_,tokens=case
 rd=b.directory(tmp_path/'signed')
 s.linked(dict(action='rephrase',run=n,operations=[dict(operation='threshold',item=tokens['beta'][0],threshold=-0.1)]),p,rd,'the coding agent')
 assert s.rows((rd/'answer.md').read_bytes())[1][1]=='false'


def test_inline_items_have_real_placeholders_and_generated_replies():
 raw=b'note\nSupport GENE_A at 0.8123\n'
 d=m.empty_dictionary();m.mask_table(d,'inline',raw,'',genes=['GENE_A'])
 rules=m.table_rules(d,'inline',genes=['GENE_A'])
 out,_,decisions=m.release_table(d,'inline',{},rules)
 _,reply,_=s.decorate(out,d,'inline',decisions,s.configure_policy({}))
 assert len(reply.splitlines())==2
 assert '{{TEXT-' in reply and '{{VALUE-' in reply
 assert not re.search(BAD,reply,re.I)
 assert 'GENE_A' not in out.decode() and '0.8123' not in out.decode()


def test_masked_header_and_positive_label_keep_reply_safe():
 raw=b'GENE_A\tthreshold\nGENE_A\t0.8123\n'
 d=m.empty_dictionary();m.mask_table(d,'header',raw,'',genes=['GENE_A'])
 rules=m.table_rules(d,'header',genes=['GENE_A'])
 out,_,decisions=m.release_table(d,'header',{},rules)
 _,reply,_=s.decorate(out,d,'header',decisions,s.configure_policy({}))
 assert 'GENE_A' not in reply and not re.search(BAD,reply,re.I)


@pytest.mark.parametrize('text,expected',[('range 1.0;3.0','range 1;3'),('sum 1E2 and -2.0','sum 100 and -2'),('GENE_A 1.0 and 0.32',None)])
def test_whole_number_fragments_release_and_fractional_fragments_keep_real_tokens(text,expected):
    raw=('note\n'+text+'\n').encode();d=m.empty_dictionary();m.mask_table(d,'toy',raw,'')
    rules=m.table_rules(d,'toy',genes=['GENE_A']);out,_,decisions=m.release_table(d,'toy',{},rules)
    assert m.restore_table(d,'toy')==raw
    if expected is not None:
        assert out==('note\n'+expected+'\n').encode()
    else:
        assert b' 1 and ' in out and b'0.32' not in out and b'GENE_A' not in out
        assert out.count(b'{{TEXT-')==1 and out.count(b'{{VALUE-')==1
        _,reply,_=s.decorate(out,d,'toy',decisions,s.configure_policy({}))
        assert len(reply.splitlines())==2 and not re.search(BAD,reply,re.I)


@pytest.mark.parametrize('column',['coloc_abf_PPH4','susie_PPH4','both_PPH4','posterior_probability','probability'])
def test_every_named_posterior_probability_receives_operator_default_bins(column):
    p=s.configure_policy(dict(protected_columns=[column,'beta','best_P']))
    assert p['bins'][column]['edges']==[0.50,0.70,0.80,0.95]
    assert 'beta' not in p['bins'] and 'best_P' not in p['bins']
