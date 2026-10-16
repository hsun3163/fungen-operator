"""Code-generated librarian stand-ins, linked requests and resident main review.

Operation metadata owns the advertised vocabulary; the single reply frame owns prose.
Private values stay in the existing run dictionary.
"""
import csv
import fcntl
import io
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import time
from urllib.request import Request, build_opener, ProxyHandler

DEFAULTS = json.loads(Path(__file__).with_name('standin_policy.json').read_text())
FRAME = '{subject} stands for a {kind}{facts}. Use the placeholder in your work; you can ask for its {options}.'
OPERATIONS = {
    'count': dict(kinds=('gene identifier', 'withheld by staff'), phrase='row count'),
    'rank': dict(kinds=('gene identifier', 'decimal value'), phrase='rank'),
    'group': dict(kinds=('gene identifier', 'withheld by staff'), phrase='group'),
    'match': dict(kinds=('gene identifier', 'withheld by staff'), phrase='match with another placeholder'),
    'compare': dict(kinds=('decimal value',), phrase='comparison with another placeholder'),
    'percentile': dict(kinds=('decimal value',), phrase='percentile'),
    'absolute_percentile': dict(kinds=('decimal value',), phrase='absolute value percentile'),
    'bin': dict(kinds=('decimal value',), phrase='bin'),
    'direction': dict(kinds=('decimal value',), phrase='direction sign'),
    'threshold': dict(kinds=('decimal value',), phrase=None),
}
DEFAULT_EDGES = DEFAULTS['probability_bins']['edges']
DEFAULT_LABELS = DEFAULTS['probability_bins']['labels']
POLICY_FIELDS = ('column_labels', 'column_kinds', 'bins', 'threshold_cap', 'review_model', 'main_state', 'main_lock', 'reason_labels')


def configure_policy(policy):
    """Install editable operator definitions; explicit definitions take precedence."""
    policy.setdefault('threshold_cap', DEFAULTS['threshold_cap'])
    policy.setdefault('reason_labels', DEFAULTS['reason_labels'].copy())
    policy.setdefault('review_model', DEFAULTS['review_model'])
    policy.setdefault('column_labels', {})
    policy.setdefault('column_kinds', {})
    bins = policy.setdefault('bins', {})
    for col in policy.get('protected_columns', []):
        if any(x in col.lower() for x in ('intact_pp', 'posterior', 'regional_pp', 'pph4', 'probability')):
            bins.setdefault(col, dict(edges=DEFAULT_EDGES[:], labels=DEFAULT_LABELS[:]))
            policy['column_labels'].setdefault(col, 'INTACT PP' if 'intact' in col.lower() else col)
    return policy


def validate_policy(policy):
    if type(policy.get('threshold_cap', 3)) is not int or not 0 <= policy.get('threshold_cap', 3) <= 100:
        raise ValueError('stand-in-cap')
    if policy.get('review_backend', 4) != 'main' and (type(policy.get('review_backend',4)) is not int or not 1 <= policy.get('review_backend',4) <= 100):
        raise ValueError('review-backend')
    for col, spec in policy.get('bins', {}).items():
        edges, labels = spec['edges'], spec['labels']
        if (not edges or any(type(v) not in (int, float) or not math.isfinite(v) for v in edges)
                or sorted(set(edges)) != edges or len(labels) != len(edges) + 1
                or any(type(v) is not str or not v or '\n' in v or '\t' in v for v in labels)):
            raise ValueError('stand-in-bins')
    return policy


def rows(raw):
    return list(csv.reader(io.StringIO(raw.decode()), delimiter='\t'))


def encode(table):
    out = io.StringIO(); csv.writer(out, delimiter='\t', lineterminator='\n').writerows(table)
    return out.getvalue().encode()


def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def percentile(value, reference, absolute=False):
    values = [numeric(v) for v in reference]
    values = [abs(v) if absolute else v for v in values if v is not None]
    if not values:
        raise ValueError('stand-in-empty-reference')
    value = abs(value) if absolute else value
    # Empirical CDF, inclusive ties, nearest whole percentile; endpoints 0..100.
    return str(int(math.floor(100 * sum(v <= value for v in values) / len(values) + 0.5)))


def bin_value(value, spec):
    return spec['labels'][sum(value >= edge for edge in spec['edges'])]


def attach(raw, dictionary, document, decisions, policy):
    """Attach permitted columns to the return, with a named returned-column reference."""
    table = rows(raw); record = dictionary['documents'][document]
    reasons = {d['item']: d['reason'] for d in decisions if d['decision'] == 'keep masked'}
    original = rows(__import__('masking').restore_table(dictionary, document))
    metadata = {}; additions = []
    for j, col in enumerate(record['columns']):
        tokens = {record['table'][i][j] for i in range(1, len(table))}
        protected = [t for t in tokens if reasons.get(t) == 'decimal value']
        if not protected:
            continue
        reference = [r[j] for r in original[1:]]
        operations = ['percentile']
        if col in policy.get('bins', {}): operations.insert(0, 'bin')
        else: operations = ['direction', 'percentile', 'absolute_percentile']
        for operation in operations:
            heading = table[0][j] + '_' + operation
            if heading in table[0]: raise ValueError('stand-in-column-collision')
            additions.append((j, col, operation, heading, reference))
    for j, col, operation, heading, reference in additions:
        table[0].append(heading)
        for i in range(1, len(table)):
            token = record['table'][i][j]; value = numeric(original[i][j])
            fact = ''
            if reasons.get(token) == 'decimal value' and value is not None:
                if operation == 'bin': fact = bin_value(value, policy['bins'][col])
                elif operation == 'direction': fact = '+' if value > 0 else '-' if value < 0 else '0'
                else: fact = percentile(value, reference, operation == 'absolute_percentile')
                metadata.setdefault(token, {})[operation] = dict(column=heading, row=i, reference='returned table column ' + col)
            table[i].append(fact)
    return encode(table), metadata


def conjunction(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ', or ' + items[-1]


def reply(raw, dictionary, document, decisions, policy, metadata):
    table = rows(raw); record = dictionary['documents'][document]
    groups = {}
    for decision in decisions:
        token = decision['item']
        if decision['decision'] != 'keep masked' or token not in record['positions']: continue
        positions = record['positions'][token]
        # Only placeholders still present in this actual output receive a sentence.
        if not any(token in table[i][j] for i, j in positions): continue
        column = record['columns'][positions[0][1]]
        reason = decision['reason']; groups.setdefault((reason, column), []).append(token)
    lines = []
    for (reason, column), tokens in groups.items():
        label = policy.get('column_labels', {}).get(column, column)
        heading = table[0][record['columns'].index(column)]
        if '{{' in heading: label = heading.split(' [')[0]+' column'
        label = re.sub(r"\b(?:not|no|never|cannot|can't|don't|won't|unable|refuse|reject|deny|withheld|forbidden|prohibited|secret|cheat|infer|guess|narrow|work around|threshold)\b",'column',label,flags=re.I)
        kind = policy.get('column_kinds', {}).get(column, policy.get('reason_labels',DEFAULTS['reason_labels']).get(reason,reason))
        # Display naming is metadata, separate from the single sentence frame.
        kind = kind.format(label=label)
        shown = set.intersection(*(set(metadata.get(t, {})) for t in tokens)) if tokens else set()
        facts = []
        for op in metadata.get(tokens[0], {}):
            if op not in shown: continue
            if len(tokens) == 1:
                location = metadata[tokens[0]][op]
                value = table[location['row']][table[0].index(location['column'])]
                facts.append(OPERATIONS[op]['phrase'].replace(' sign', '') + ' ' + value)
            else: facts.append(OPERATIONS[op]['phrase'].replace(' sign', ''))
        options = [v['phrase'] for k,v in OPERATIONS.items() if reason in v['kinds'] and v['phrase'] and k not in shown
                   and (k != 'bin' or column in policy.get('bins', {}))
                   and (k != 'absolute_percentile' or column not in policy.get('bins', {}))
                   and (k != 'direction' or column not in policy.get('bins', {}))]
        subject = tokens[0] if len(tokens) == 1 else f'{label} ({len(tokens)} items)'
        lines.append(FRAME.format(subject=subject, kind=kind, facts=' ('+', '.join(facts)+')' if facts else '', options=conjunction(options)))
    return '\n'.join(lines)


def decorate(raw, dictionary, document, decisions, policy):
    enriched, metadata = attach(raw, dictionary, document, decisions, policy)
    return enriched, reply(enriched, dictionary, document, decisions, policy, metadata), metadata


def linked(request, policy, rd, audience):
    """New ordinary librarian action, audited link, no model/release reconsideration."""
    import broker as b
    import masking as m
    b.exact(request, ('action', 'run', 'operations') + (('question',) if 'question' in request else ()), 'rephrase-request')
    b.require('question' not in request or (type(request['question']) is str and 0 < len(request['question']) <= 4096), 'rephrase-question')
    b.require(re.fullmatch(r'run-[0-9a-f]{32}', request['run']) is not None, 'rephrase-run')
    b.require(type(request['operations']) is list and 0 < len(request['operations']) <= 128, 'rephrase-operations')
    source = Path(policy['private_root']) / request['run']
    with (source/'review.lock').open('a') as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        dictionary = m.load_dictionary(source/'dict.json.zst'); record = dictionary['documents'][source.name]
        original = rows(m.restore_table(dictionary, source.name)); state = b.read_json(source/'release.json',16*1024**2)
        rules = b.read_json(source/'rules.json',16*1024**2)
        counters = state.setdefault('threshold_questions', {}); output = [['operation','result']]; events = []
        for spec in request['operations']:
            b.require(type(spec) is dict and set(spec) <= {'operation','item','other','column','condition','reference','absolute','order','threshold','operator','unit'}, 'stand-in-fields')
            op = spec.get('operation'); b.require(op in OPERATIONS, 'stand-in-operation')
            token = spec.get('item'); value = None; col = spec.get('column')
            if token is not None:
                b.require(token in record['positions'], 'stand-in-item')
                i,j = record['positions'][token][0]; col = record['columns'][j]
                value = dictionary['entries'][token]['value']
            if op == 'count':
                b.require(col in record['columns'] or col is None,'stand-in-column')
                selected = original[1:]
                condition = spec.get('condition')
                if condition:
                    b.exact(condition, ('column','operator','value'), 'stand-in-condition')
                    b.require(condition['column'] in record['columns'], 'stand-in-column')
                    cj = record['columns'].index(condition['column'])
                    def accepts(row):
                        v = row[cj]; target = condition['value']; cmp = condition['operator']
                        if cmp in ('>','>=','<','<='): return compare(numeric(v), numeric(target), cmp)
                        b.require(cmp in ('==','!='),'stand-in-condition-operator')
                        return (v == str(target)) if cmp == '==' else (v != str(target))
                    selected = [r for r in selected if accepts(r)]
                if token is not None: selected = [r for r in selected if r[record['columns'].index(col)] == value]
                unit = spec.get('unit','rows'); b.require(unit in ('rows','genes'),'stand-in-unit')
                if unit == 'genes':
                    gc = col if col in policy.get('gene_columns',[]) else next((c for c in record['columns'] if c in policy.get('gene_columns',[])),None)
                    b.require(gc is not None,'stand-in-gene-column')
                    result = len({r[record['columns'].index(gc)] for r in selected})
                else: result = len(selected)
            else:
                b.require(token is not None,'stand-in-item')
                reason = next((d['reason'] for d in state['decisions'] if d['item']==token and d['decision']=='keep masked'),None)
                b.require(reason in OPERATIONS[op]['kinds'],'stand-in-kind')
                reference = spec.get('reference',dict(kind='returned',column=col))
                b.require(type(reference) is dict and reference.get('column') is not None,'stand-in-reference')
                if reference.get('kind') == 'returned':
                    b.require(reference['column'] in record['columns'],'stand-in-column')
                    refvalues = [r[record['columns'].index(reference['column'])] for r in original[1:]]
                elif reference.get('kind') == 'source':
                    ident = reference.get('input'); bindings = b.read_json(source/'bindings.json')
                    b.require(ident in bindings['inputs'].values(),'stand-in-reference-input')
                    rr = rows(b.table_content(source/'snapshot/inputs'/ident,policy['max_input_bytes']))
                    b.require(reference['column'] in rr[0],'stand-in-column'); refvalues = [r[rr[0].index(reference['column'])] for r in rr[1:]]
                else: raise b.Rejected('stand-in-reference-kind')
                if op == 'rank':
                    if numeric(value) is None: result = next(i for i,v in enumerate(refvalues,1) if v == value)
                    else:
                        b.require(spec.get('order','descending') in ('descending','ascending'),'stand-in-order')
                        result = 1 + sum((numeric(v)>numeric(value) if spec.get('order','descending')=='descending' else numeric(v)<numeric(value)) for v in refvalues if numeric(v) is not None)
                elif op == 'group': result = 'group-' + str(sorted(set(refvalues)).index(value)+1)
                elif op in ('match','compare'):
                    other = spec.get('other'); b.require(other in record['positions'],'stand-in-other')
                    ov = dictionary['entries'][other]['value']
                    other_reason = next((d['reason'] for d in state['decisions'] if d['item']==other and d['decision']=='keep masked'),None)
                    b.require(other_reason in OPERATIONS[op]['kinds'],'stand-in-other-kind')
                    result = str(value==ov).lower() if op=='match' else 'larger' if numeric(value)>numeric(ov) else 'smaller' if numeric(value)<numeric(ov) else 'equal'
                elif op in ('percentile','absolute_percentile'): result = percentile(numeric(value),refvalues,op=='absolute_percentile' or spec.get('absolute',False))
                elif op == 'direction': result = '+' if numeric(value)>0 else '-' if numeric(value)<0 else '0'
                elif op == 'bin':
                    b.require(col in policy.get('bins',{}),'stand-in-bin'); result = bin_value(numeric(value),policy['bins'][col])
                elif op == 'threshold':
                    threshold = spec.get('threshold'); cmp = spec.get('operator','>=')
                    edges = policy.get('bins',{}).get(col,{}).get('edges',[])
                    b.require(type(threshold) in (int,float) and math.isfinite(threshold) and (threshold in edges or (abs(threshold*10-round(threshold*10))<1E-9)), 'stand-in-threshold-edge')
                    b.require(cmp in ('>','>=','<','<=','=='),'stand-in-threshold-operator')
                    b.require(counters.get(token,0)<policy.get('threshold_cap',3),'stand-in-threshold-cap')
                    counters[token] = counters.get(token,0)+1
                    m.atomic_write(source/'release.json',(json.dumps(state)+'\n').encode())
                    result = str(compare(numeric(value),threshold,cmp)).lower()
            output.append([op,str(result)]); events.append(dict(spec,result=str(result)))
        m.atomic_write(source/'release.json',(json.dumps(state)+'\n').encode())
    raw = encode(output); b.save(rd/'request.json',request); b.save(rd/'answer.md',raw); b.save(rd/'human.tsv',raw)
    from google_docs import send_result
    delivery = send_result(policy,rd,raw)
    receipt = dict(status='completed',run_id=rd.name,service='librarian',linked_run=source.name,google=delivery)
    b.save(rd/'audit.json',dict(service='librarian',linked_run=source.name,question=request.get('question'),events=events,calls=[],model_calls=0))
    b.save(rd/'receipt.json',receipt)
    return receipt


def compare(a,b,op):
    if a is None or b is None: return False
    return {'>':lambda:a>b,'>=':lambda:a>=b,'<':lambda:a<b,'<=':lambda:a<=b,'==':lambda:a==b}[op]()


@__import__('contextlib').contextmanager
def resident_main(policy, rd):
    """Share Hao's lock, validate the resident model, close only an owned tunnel."""
    import broker as b
    rd = Path(rd); rd.mkdir(parents=True,exist_ok=True)
    state = {}
    statepath = Path(policy.get('main_state',Path.home()/'.codex/ollama-flash-next.env'))
    for line in statepath.read_text().splitlines():
        line = line.removeprefix('export ')
        if '=' in line and not line.startswith('#'):
            key,value = line.split('=',1)
            if key.startswith('MINERVA_OLLAMA_'): state[key] = shlex.split(value)[0] if shlex.split(value) else ''
    pinned = policy.get('review_model', DEFAULTS['review_model'])
    b.require(state.get('MINERVA_OLLAMA_DEFAULT_MODEL') == pinned,'main-model-pin')
    b.require(state.get('MINERVA_OLLAMA_JOB_NAME','codex-ollama-flash-next')=='codex-ollama-flash-next','main-job-identity')
    queued = time.monotonic()
    lockpath = Path(policy.get('main_lock',Path.home()/'sunh14/librarian_agent/librarian.lock'))
    with lockpath.open('a') as fd:
        fcntl.flock(fd,fcntl.LOCK_EX); started = time.monotonic(); owned = None
        host = 'http://127.0.0.1:'+state.get('MINERVA_OLLAMA_LOCAL_PORT','11435')
        opener = build_opener(ProxyHandler({}))
        try:
            try:
                with opener.open(host+'/api/ps',timeout=5) as response: resident = json.load(response)
            except OSError:
                query = subprocess.run(['bjobs','-J','codex-ollama-flash-next','-o','stat exec_host','-noheader'],capture_output=True,text=True,timeout=30)
                nodes = [line.split()[1].split('*')[-1] for line in query.stdout.splitlines() if line.split() and line.split()[0]=='RUN']
                b.require(query.returncode==0 and len(nodes)==1,'main-endpoint-unavailable')
                socket = '/tmp/librarian-main-'+__import__('hashlib').sha256(str(rd).encode()).hexdigest()[:20]+'.sock'
                node = nodes[0]
                command = ['ssh','-M','-S',socket,'-fNT','-o','ExitOnForwardFailure=yes','-L',host.rsplit(':',1)[1]+':127.0.0.1:'+state.get('MINERVA_OLLAMA_REMOTE_PORT','8889'),node]
                opened = subprocess.run(command,capture_output=True,timeout=30)
                b.require(opened.returncode==0,'main-tunnel-unavailable'); owned = (socket,node)
                with opener.open(host+'/api/ps',timeout=10) as response: resident = json.load(response)
            b.require(any(m.get('name',m.get('model'))==pinned for m in resident.get('models',[])), 'main-resident-model-mismatch')
            yield host,pinned,opener,started,queued
        finally:
            if owned:
                closed = subprocess.run(['ssh','-S',owned[0],'-O','exit',owned[1]],capture_output=True,timeout=30)
                b.save(rd/'main-cleanup.json',dict(exit_code=closed.returncode,owned_tunnel=True))
                b.require(closed.returncode==0,'main-tunnel-close')


def verify_main(policy, rd):
    """Preflight the resident main service without an inference call."""
    import broker as b
    with resident_main(policy,rd) as (_,pinned,_,_,_):
        b.save(Path(rd)/'resident.json',dict(service='librarian',resident_model=pinned,inference_calls=0))


def main_call(agents, role, prompt, rd, schema):
    """Direct constrained decisions from the already resident pinned main model."""
    import broker as b
    b.require(role in ('unmask-review','local-agent-escalation','binding-escalation'), 'main-role')
    with resident_main(agents.policy,rd) as (host,pinned,opener,started,queued):
        payload = dict(model=pinned,stream=False,format=schema,messages=[dict(role='system',content='You are the librarian. Return schema-constrained decisions. The code releases values.'),dict(role='user',content=prompt)],options=b.sampling(agents.policy))
        b.save(Path(rd)/'request.json',payload)
        request = Request(host+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        result = None
        try:
            with opener.open(request,timeout=agents.policy['agent_timeout_seconds']) as response: result = json.load(response)
            b.save(Path(rd)/'response.json',result)
            value = b.decode(result['message']['content']); b.validate_constrained(value,schema)
            return value
        finally:
            metric = dict(service='librarian',role=role,backend='main',seconds=time.monotonic()-started,queue_seconds=started-queued,model_seconds=result.get('total_duration',0)/1E9 if result else None,turns=1,status='completed' if result else 'failed')
            with agents.lock: agents.metrics.append(metric)
            b.save(Path(rd)/'call.json',metric); agents.last_review_backend = 'main'
