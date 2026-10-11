"""Local orchestration and deterministic checks; never prints private result tables."""
import csv
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

HERE = Path(__file__).resolve().parent


def lsf_table(text, required, continuation=False):
    """Parse native wide tables; continuation GPU rows inherit HOST_NAME."""
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if not lines or not set(required) <= set(lines[0]):
        raise ValueError('unrecognized LSF table header')
    header, rows, host = lines[0], [], None
    for cells in lines[1:]:
        if continuation and len(cells) == len(header) - 1 and host:
            cells.insert(0, host)
        if len(cells) != len(header):
            raise ValueError('unrecognized LSF table row')
        row = dict(zip(header, cells))
        host = row['HOST_NAME']
        rows.append(row)
    return rows


def memory_gb(value):
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)([KMGT])(?:B)?', value, re.I)
    if not match:
        raise ValueError('unknown GPU memory capacity')
    return float(match[1]) * {'K': 1 / 1024**2, 'M': 1 / 1024, 'G': 1, 'T': 1024}[match[2].upper()]


def free_gpu_slots(allocation, load, slots, model=''):
    """One host/model entry per unallocated >=32G GPU, capped by free CPU slots."""
    alloc = lsf_table(allocation, ('HOST_NAME', 'GPU_ID', 'NJOBS', 'RUN', 'SUSP', 'RSV'), True)
    capacities = {(r['HOST_NAME'], r['gpuid']): r for r in
                  lsf_table(load, ('HOST_NAME', 'gpuid', 'gpu_model', 'gpu_mtotal', 'gpu_status'), True)}
    # NJOBS already includes suspended and reserved slots: do not subtract RSV twice.
    cores = {r['HOST_NAME']: max(0, int(r['MAX']) - int(r['NJOBS'])) // 2
             for r in lsf_table(slots, ('HOST_NAME', 'STATUS', 'MAX', 'NJOBS'))
             if r['STATUS'] == 'ok' and r['MAX'].isdigit()}
    result, seen = [], set()
    for row in alloc:
        key = row['HOST_NAME'], row['GPU_ID']
        if key in seen:
            raise ValueError('duplicate GPU allocation row')
        seen.add(key)
        info = capacities.get(key)
        if (not info or cores.get(key[0], 0) < 1 or
                any(int(row[k]) != 0 for k in ('NJOBS', 'RUN', 'SUSP', 'RSV')) or
                info['gpu_status'] != 'ok' or memory_gb(info['gpu_mtotal']) < 32 or
                (model and info['gpu_model'] != model)):
            continue
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', key[0]):
            raise ValueError('invalid scheduler host name')
        result.append((key[0], info['gpu_model']))
        cores[key[0]] -= 1
    return result


def native_output(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f'scheduler query failed: {shlex.join(args)}: {proc.stderr.strip()}')
    return proc.stdout


def free_gpus(model='', wall='04:00'):
    # Resolve queue HOSTS instead of treating every GPU host as available to these queues.
    queues = native_output(['bqueues', '-l', 'gpu', 'gpuexpress'])
    memberships = {}
    for block in queues.split('QUEUE: ')[1:]:
        queue = block.split()[0]
        status = re.search(r'^\s*\d+\s+\d+\s+Open:Active\b', block, re.M)
        hosts = re.search(r'^HOSTS:\s*(.*)$', block, re.M)
        if not hosts:
            raise ValueError('queue HOSTS missing')
        if not status:
            continue
        members = set()
        for token in hosts[1].split():
            if token.endswith('/'):
                # bmgroup has a variable-width HOSTS field; -r expands nested groups.
                lines = native_output(['bmgroup', '-w', '-r', token[:-1]]).splitlines()
                if not lines or lines[0].split() != ['GROUP_NAME', 'HOSTS']:
                    raise ValueError('unrecognized host group header')
                for line in lines[1:]:
                    cells = line.split()
                    if cells and cells[0] == token[:-1]:
                        members.update(cells[1:])
            elif re.fullmatch(r'[A-Za-z0-9_.-]+', token) and token not in {'all', 'none'}:
                members.add(token)
            else:
                raise ValueError('unsupported queue host membership')
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', host) for host in members):
            raise ValueError('unexpanded queue host membership')
        memberships[queue] = members
    hosts = sorted(set().union(*memberships.values())) if memberships else []
    if not hosts:
        return []
    allocation = native_output(['bhosts', '-gpu', *hosts])
    load = native_output(['lsload', '-gpuload', '-w', *hosts])
    slots = native_output(['bhosts', '-w', *hosts])
    hours, minutes = map(int, wall.split(':'))
    candidates = []
    for host, gpu_model in free_gpu_slots(allocation, load, slots, model):
        # gpuexpress accepts up to 15 hours on Minerva; gpu supports longer overrides.
        queue = 'gpuexpress' if host in memberships.get('gpuexpress', ()) and hours * 60 + minutes <= 900 else 'gpu'
        if host in memberships.get(queue, ()):
            candidates.append((host, queue, gpu_model))
    return candidates


def state_model(path, ident):
    ident = int(ident)
    if not 1 <= ident <= 100:
        raise ValueError('invalid scribe id')
    # Parse, never execute, state. Require precisely the isolated identity.
    state = {}
    allowed = {'MINERVA_OLLAMA_JOB_NAME', 'MINERVA_OLLAMA_JOB_ID', 'MINERVA_OLLAMA_REMOTE_PORT',
               'MINERVA_OLLAMA_LOCAL_PORT', 'MINERVA_OLLAMA_DEFAULT_MODEL', 'MINERVA_OLLAMA_LAST_NODE'}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, value = line.split('=', 1)
        tokens = shlex.split(value)
        if key not in allowed or len(tokens) != 1 or not re.fullmatch(r'[A-Za-z0-9_.:/-]+', tokens[0]):
            raise ValueError('invalid state file')
        state[key] = tokens[0]
    expected = dict(MINERVA_OLLAMA_JOB_NAME=f'codex-ollama-scribe-{ident}',
                    MINERVA_OLLAMA_REMOTE_PORT=str(8890 + ident),
                    MINERVA_OLLAMA_LOCAL_PORT=str(11440 + ident))
    if any(state.get(k) != v for k, v in expected.items()):
        raise ValueError('scribe state identity mismatch; librarian endpoint forbidden')
    model = state['MINERVA_OLLAMA_DEFAULT_MODEL']
    if not re.fullmatch(r'[A-Za-z0-9_.:/-]+', model):
        raise ValueError('invalid model name')
    return model


def log_failure(path, require_command=True):
    text = Path(path).read_text(errors='replace')
    succeeded = False
    outputs = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            outputs.append(line)
            if re.search(r'\bsucceeded in\b', line):
                succeeded = True
            continue
        item = event.get('item', {})
        if item.get('type') == 'error':
            outputs.append(item.get('message', ''))
        if item.get('type') == 'command_execution':
            outputs.append(item.get('aggregated_output', ''))
            if event.get('type') == 'item.completed' and item.get('exit_code') == 0:
                succeeded = True
        if event.get('type') in ('error', 'turn.failed'):
            error = event.get('error', {})
            outputs.append(event.get('message', '') + ' ' + (error.get('message', '') if isinstance(error, dict) else str(error)))
    errors = '\n'.join(outputs)
    if re.search(r'bwrap[^\n]*(?:fail|error|can.t|namespace)|\bsandbox\b[^\n]*(?:fail|error)|(?:fail|error)[^\n]*\bsandbox\b|Failed to create unified exec process|Creating new namespace failed', errors, re.I):
        return 'sandbox execution error'
    if re.search(r'error=`justification` requires an explicit `sandbox_permissions`|error=unsupported call:', errors):
        return 'invalid tool call or arguments'
    if require_command and not succeeded:
        return 'no command succeeded'
    return None


def session_id(path):
    for line in Path(path).read_text(errors='replace').splitlines():
        if line.startswith('session id: '):
            return line.removeprefix('session id: ')
        try:
            event = json.loads(line)
            if event.get('type') == 'thread.started':
                return event['thread_id']
        except (ValueError, KeyError):
            pass
    return ''


def normalize(path):
    """TSV: order-independent columns/rows; numeric half-even rounding to 7 significant digits."""
    with Path(path).open(newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        cols = next(reader)
        if not cols or any(not c.strip() for c in cols) or len(set(cols)) != len(cols):
            raise ValueError('invalid table header')
        order = sorted(range(len(cols)), key=lambda i: cols[i])
        rows = []
        for row in reader:
            if len(row) != len(cols):
                raise ValueError('ragged table')
            normalized = []
            for value in row:
                value = value.strip()
                if value.casefold() in {'', 'na', 'nan', 'null', 'none', 'n/a'}:
                    normalized.append(('na', ''))
                    continue
                try:
                    number = Decimal(value)
                    if not number.is_finite():
                        raise ValueError('nonfinite numeric value')
                    # Decimal context must accommodate large scientific values.
                    from decimal import localcontext
                    with localcontext() as ctx:
                        ctx.prec = max(32, len(number.as_tuple().digits) + abs(number.adjusted()) + 12)
                        quantum = Decimal(1).scaleb(number.adjusted() - 6) if number else Decimal(1)
                        rounded = number.quantize(quantum, rounding=ROUND_HALF_EVEN)
                    normalized.append(('number', str(rounded.copy_abs() if rounded == 0 else rounded)))
                except InvalidOperation:
                    normalized.append(('text', value))
            rows.append(tuple(normalized[i] for i in order))
    return tuple(cols[i] for i in order), tuple(sorted(rows))


def comparison(a, b):
    if not Path(a).is_file() or not Path(b).is_file():
        return 'no-table'
    try:
        return 'match' if normalize(a) == normalize(b) else 'mismatch'
    except (ValueError, StopIteration, OSError):
        return 'invalid-table'


def route(run, task, check, audience):
    run = Path(run)
    wanted = os.environ.get('LIBRARIAN_SCRIBE_ID')
    if wanted and (not wanted.isdigit() or not 1 <= int(wanted) <= 100):
        raise RuntimeError('invalid scribe id; librarian endpoint forbidden')
    states = [Path.home() / f'.codex/ollama-scribe-{wanted}.env'] if wanted else sorted((Path.home() / '.codex').glob('ollama-scribe-*.env'))
    endpoints = []
    for state in states:
        match = re.fullmatch(r'ollama-scribe-([1-9][0-9]*)\.env', state.name)
        if not match:
            continue
        probe = subprocess.run([str(HERE / 'scribes'), 'endpoint', match[1]], capture_output=True, text=True)
        if probe.returncode == 0:
            endpoints.append(json.loads(probe.stdout))
    fallback = not endpoints
    (run / 'backend').write_text('librarian\n' if fallback else 'scribe\n')

    def call(label, prompt, endpoint):
        rd = run / label
        env = dict(os.environ, LIBRARIAN_RUN_DIR=str(rd), LIBRARIAN_NO_PUBLISH='1')
        if endpoint is None:
            # Restore the fixed main identity; each child takes librarian.lock as usual.
            for key in ('OLLAMA_HOST', 'CODEX_OSS_BASE_URL', 'CODEX_OSS_PORT', 'CODEX_OLLAMA_MODEL',
                        'LIBRARIAN_SCRIBE_SESSION', 'MINERVA_OLLAMA_DEFAULT_MODEL'):
                env.pop(key, None)
            env.update(MINERVA_OLLAMA_STATE_FILE=str(Path.home() / '.codex/ollama-flash-next.env'),
                       MINERVA_OLLAMA_JOB_NAME='codex-ollama-flash-next',
                       MINERVA_OLLAMA_REMOTE_PORT='8889', MINERVA_OLLAMA_LOCAL_PORT='11435')
        else:
            env.update(MINERVA_OLLAMA_STATE_FILE=str(Path.home() / f'.codex/ollama-scribe-{endpoint["id"]}.env'),
                       MINERVA_OLLAMA_JOB_NAME=f'codex-ollama-scribe-{endpoint["id"]}',
                       MINERVA_OLLAMA_REMOTE_PORT=str(8890 + endpoint['id']),
                       MINERVA_OLLAMA_LOCAL_PORT=str(11440 + endpoint['id']),
                       MINERVA_OLLAMA_DEFAULT_MODEL=endpoint['model'],
                       CODEX_OLLAMA_MODEL=endpoint['model'], OLLAMA_HOST=endpoint['host'],
                       CODEX_OSS_BASE_URL=endpoint['host'] + '/v1', LIBRARIAN_SCRIBE_SESSION='1')
            env.pop('CODEX_OSS_PORT', None)
        # No shared conversation or child-session history; separate Codex processes and cwd.
        write_args = json.loads(os.environ.get('LIBRARIAN_SCRIBE_ADD_DIRS', '[]'))
        option = '--me' if audience == 'me' else '--receipt' if audience == 'receipt' else '--slots' if audience == 'slots' else '--internal'
        proc = subprocess.run([str(HERE / 'librarian'), *write_args, option, *([] if audience == 'slots' else [prompt])],
                              input=prompt if audience == 'slots' else None, env=env, capture_output=True, text=True)
        with (run / 'log').open('a') as f:
            f.write(f'{label}: backend={"librarian" if endpoint is None else "scribe=" + str(endpoint["id"])} rc={proc.returncode} log={rd / "log"}\n')
        if proc.returncode:
            with (run / 'log').open('a') as f:
                f.write(proc.stdout + proc.stderr)
            raise RuntimeError(f'{label} failed; see {rd / "log"}')
        return rd

    instructions = (' Save any defined result table as result.tsv in your own run directory, with a header and tab delimiters, all requested rows and columns. Retain the script used to compute it. If the task defines no table, do not invent one. ')
    if check:
        if fallback:
            a, b = [call(label, task + instructions, None) for label in ('A', 'B')]
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(call, label, task + instructions, endpoints[i % len(endpoints)]) for i, label in enumerate(('A', 'B'))]
                a, b = [f.result() for f in futures]
        status = comparison(a / 'result.tsv', b / 'result.tsv')
        (run / 'comparison.json').write_text(json.dumps(dict(status=status, rounding_significant_digits=7, A=str(a), B=str(b))) + '\n')
        if status == 'match':
            final = (a / 'answer.md').read_text()
            if audience not in ('receipt', 'slots'):
                final += '\n\nIndependent A/B result tables match after normalization.\n'
        else:
            scripts = [str(p) for rd in (a, b) for p in sorted(rd.iterdir()) if p.is_file() and p.suffix.lower() in {'.py', '.r', '.sh', '.ipynb'}]
            tables = [str(p) for p in (a / 'result.tsv', b / 'result.tsv') if p.is_file()]
            review = call('reviewer', f'Original task: {task}\nComparison status: {status}. Independently review BOTH answers {a / "answer.md"} and {b / "answer.md"}, these exact retained script paths {scripts} and table paths {tables}, and the original named inputs only. If scripts are missing say so and verify the computation directly from the original inputs. Use commands to inspect the evidence. Resolve disagreements and write the final answer for the original audience. Do not assume either answer is correct. If unresolved say so explicitly.', None if fallback else endpoints[0])
            final = (review / 'answer.md').read_text()
    else:
        a = call('A', task + instructions, None if fallback else endpoints[0])
        final = (a / 'answer.md').read_text()
    (run / 'answer.md').write_text(final)


if __name__ == '__main__':
    try:
        cmd, *args = sys.argv[1:]
        if cmd == 'free-gpus':
            for host, queue, model in free_gpus(*args):
                print(f'{host}\t{queue}\t{model}')
        elif cmd == 'state':
            print(state_model(*args))
        elif cmd == 'health':
            models = json.load(sys.stdin)['models']
            model = next(m for m in models if m['name'] == args[0])
            print(f'{model["size_vram"] / 1e9:.1f}')
        elif cmd == 'log':
            error = log_failure(args[0], len(args) == 1)
            if error:
                print(error); sys.exit(1)
        elif cmd == 'session':
            print(session_id(args[0]))
        elif cmd == 'compare':
            print(comparison(*args))
        elif cmd == 'route':
            route(args[0], Path(args[0], 'task').read_text(), args[1] == '1', args[2])
        else:
            raise ValueError('unknown operation')
    except Exception as e:
        # Endpoint/state errors are operational; no table content escapes here.
        print(f'{type(e).__name__}: scribe operation failed' if cmd in ('state', 'health') else str(e), file=sys.stderr)
        sys.exit(1)
