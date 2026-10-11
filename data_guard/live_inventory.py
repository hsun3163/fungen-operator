"""Rebuild only live table filenames, sizes and headers; fail on unclassified schema drift."""
import argparse, csv, gzip, hashlib, json, re, sys
from pathlib import Path

PRODUCTION = Path('/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/3_Production')
PAPER = PRODUCTION / 'COSI_paper'
PACKET = PRODUCTION / 'COSI_side_analyses/gene_annotation_8080'

def table_paths(root):
    """Paper exports and merged annotation outputs, excluding raw inputs/staging."""
    import os
    if root == PAPER / 'data':
        yield from root.glob('*')
        return
    for directory, children, files in os.walk(root):
        children[:] = sorted(d for d in children if d not in
                             {'raw','stage','stages','batches','logs','sources','.ipynb_checkpoints'})
        for name in sorted(files):
            yield Path(directory) / name

def inventory():
    roots = [PAPER / 'data', *sorted((PAPER / 'analysis').glob('*/results')),
             *sorted((PAPER / 'figures').glob('*/source_data')),
             *[PACKET / name for name in ('01_gene_list_loci','31_judge','41_role_atlas','42_interactome','43_sensor_machinery')]]
    paths = sorted({p for root in roots for p in table_paths(root)
                    if p.is_file() and p.name.endswith(('.tsv', '.tsv.gz', '.csv', '.csv.gz'))})
    rows = []
    for path in paths:
        op = gzip.open if path.suffix == '.gz' else open
        with op(path, 'rt') as stream:
            header = next(csv.reader([stream.readline()], delimiter=',' if '.csv' in path.suffixes else '\t'))
        relative = path.relative_to(PRODUCTION).as_posix()
        ident = 'live_' + hashlib.sha256(relative.encode()).hexdigest()[:16]
        rows.append(dict(input_id=ident, path=str(path.resolve(strict=True)), bytes=path.stat().st_size,
                         format='csv' if '.csv' in path.suffixes else 'tsv', columns=header))
    return rows

def check(rows, policy):
    genes, protected, shown = (set(policy.get(k, [])) for k in ('gene_columns','protected_columns','shown_headings'))
    bad = []
    for row in rows:
        if policy['inputs'].get(row['input_id']) != row['path']:
            bad.append(dict(input_id=row['input_id'], problem='new-or-changed-input'))
        for column in row['columns']:
            classes = sum(column in group for group in (genes, protected, shown))
            if classes != 1:
                bad.append(dict(input_id=row['input_id'], column=column, problem='unclassified' if classes == 0 else 'multiple-classes'))
        if row['format'] != 'tsv':
            bad.append(dict(input_id=row['input_id'], problem='broker-requires-tsv'))
    current = {r['input_id'] for r in rows}
    bad.extend(dict(input_id=i, problem='missing-input') for i in policy['inputs'] if i not in current)
    return bad

def request_policy(policy, request):
    """Select only operator-owned candidate inputs; preserve every release setting."""
    action = request.get('action')
    if action in ('rephrase', 'unmask'):
        run = request.get('run', '')
        if not re.fullmatch(r'run-[a-f0-9]{32}', run):
            raise ValueError('invalid-run')
        # This retained config contains paths and settings, rather than result values.
        original = json.loads((Path(policy['private_root']) / run / 'policy.json').read_text())
        ids = set(original['inputs'])
    else:
        ids = {ident for value in request.get('inputs', {}).values()
               for ident in (value if isinstance(value, list) else [value])}
    if not ids or not ids <= policy['inputs'].keys():
        raise ValueError('unknown-input')
    return dict(policy, inputs={i: policy['inputs'][i] for i in sorted(ids)})

def structure_probe(policy, request, answer):
    """Fixed structural calculation: header and logical row count, with no cell release."""
    import io, uuid, time
    from broker import directory, save
    if set(request) != {'action','inputs'} or request['action'] != 'probe':
        raise ValueError('probe-request')
    rd=directory(Path(policy['private_root']) / ('run-' + uuid.uuid4().hex))
    started=time.monotonic(); stream=io.StringIO()
    writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
    writer.writerow(['input_role','column','row_count'])
    for role, ident in request['inputs'].items():
        path=Path(policy['inputs'][ident])
        if path.stat().st_size > policy['max_input_bytes']:
            raise ValueError('probe-input-limit')
        op=gzip.open if path.suffix == '.gz' else open
        with op(path,'rt') as source:
            reader=csv.reader(source,delimiter='\t')
            header=next(reader); count=sum(1 for _ in reader)
        for column in header: writer.writerow([role,column,count])
    raw=stream.getvalue().encode()
    save(rd/'policy.json',policy);save(rd/'answer.md',raw);save(answer,raw)
    receipt=dict(service='librarian',status='completed',run_id=rd.name,
                 structure_only=True,google=dict(status='structure-only'))
    save(rd/'receipt.json',receipt)
    save(rd/'audit.json',dict(receipt=receipt,model_calls=0,calls=[],events=[],seconds=time.monotonic()-started))
    return receipt

def validate_probes(policy_path, output):
    """One installed --broker probe per catalog input; keep one safe raw log/report."""
    import subprocess, tempfile, os, concurrent.futures, threading
    policy=json.loads(policy_path.read_text()); lock=threading.Lock(); records=[]
    output.mkdir(parents=True,exist_ok=True)
    log=output/'probes.log';log.write_text('')
    def one(ident):
        with tempfile.TemporaryDirectory(prefix='librarian-structure-',dir=Path(policy['private_root']).parent) as folder:
            work=Path(folder);request=work/'request.json'
            request.write_text(json.dumps(dict(action='probe',inputs={'table':ident})))
            env=dict(os.environ,LIBRARIAN_BROKER_POLICY=str(policy_path),LIBRARIAN_RUN_DIR=str(work/'wrapper'))
            result=subprocess.run(['librarian','--broker',str(request)],env=env,capture_output=True,text=True)
            rows=list(csv.reader(result.stdout.splitlines(),delimiter='\t'))
            expected=next(r['columns'] for r in inventory_rows if r['input_id']==ident)
            passed=(result.returncode==0 and rows and rows[0]==['input_role','column','row_count']
                    and [r[1] for r in rows[1:]]==expected and all(len(r)==3 and r[2].isdigit() for r in rows[1:]))
            receipt_path=work/'wrapper/broker-receipt.json'
            receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            record=dict(input_id=ident,passed=bool(passed),run_id=receipt.get('run_id',''),
                        columns=len(rows)-1,row_count=int(rows[1][2]) if passed and len(rows)>1 else None)
            with lock:
                with log.open('a') as stream:stream.write(ident+'\n'+result.stdout+result.stderr+'\n')
                records.append(record)
                print(json.dumps(dict(checked=len(records),total=len(policy['inputs']),failed=sum(not r['passed'] for r in records))),flush=True)
    inventory_rows=inventory()
    problems=check(inventory_rows,policy)
    if problems:
        print(json.dumps(dict(problems=problems)))
        return 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one,policy['inputs']))
    with (output/'probes.tsv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['input_id','passed','run_id','columns','row_count'],delimiter='\t',lineterminator='\n')
        writer.writeheader();writer.writerows(sorted(records,key=lambda r:r['input_id']))
    return int(any(not r['passed'] for r in records))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--request',type=Path)
    parser.add_argument('--probe-answer',type=Path)
    parser.add_argument('--validate-probes',action='store_true')
    parser.add_argument('--policy',type=Path)
    args=parser.parse_args()
    if args.validate_probes:
        return validate_probes(args.policy,args.output)
    if args.request:
        if not args.policy: parser.error('--request requires --policy')
        policy=request_policy(json.loads(args.policy.read_text()),json.loads(args.request.read_text()))
        args.output.write_text(json.dumps(policy,separators=(',',':'))+'\n')
        from broker import policy_file
        policy_file(str(args.output))
        if args.probe_answer and json.loads(args.request.read_text()).get('action') == 'probe':
            receipt=structure_probe(policy,json.loads(args.request.read_text()),args.probe_answer)
            args.output.with_name('broker-receipt.json').write_text(json.dumps(receipt)+'\n')
            print('probe')
        else:
            print('analysis')
        return 0
    rows=inventory()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['input_id','path','bytes','format','columns'],delimiter='\t',lineterminator='\n')
        writer.writeheader()
        writer.writerows(dict(r,columns=json.dumps(r['columns'])) for r in rows)
    bad=check(rows,json.loads(args.policy.read_text())) if args.policy else []
    print(json.dumps(dict(inputs=len(rows),columns=len({c for r in rows for c in r['columns']}),problems=bad)))
    return int(bool(bad))

if __name__ == '__main__':
    sys.exit(main())
