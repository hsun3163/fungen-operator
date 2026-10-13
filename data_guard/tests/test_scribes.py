"""Synthetic checks only: no scheduler, GPU, real Codex, or protected data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / 'tests/fixtures/scribe_gpu_lsf.json').read_text())
spec = importlib.util.spec_from_file_location('scribe_support', ROOT / 'scribe_support.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_normalize_order_rounding_na_and_duplicates(tmp_path):
    a, b = tmp_path / 'a.tsv', tmp_path / 'b.tsv'
    a.write_text('key\tvalue\tmissing\nb\t1.23456740\tNA\na\t-0.0000000\tnull\n')
    b.write_text('missing\tvalue\tkey\nNaN\t0\ta\n\t1.23456749\tb\n')
    assert helper.comparison(a, b) == 'match'
    b.write_text(b.read_text() + '\t0\ta\n')
    assert helper.comparison(a, b) == 'mismatch'
    assert helper.comparison(a, tmp_path / 'absent') == 'no-table'
    b.write_text('a\ta\n1\t2\n')
    assert helper.comparison(a, b) == 'invalid-table'


def test_normalize_scientific_numbers_and_text_identity(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_text('x\n1E25\nWord\n')
    b.write_text('x\n10000000000000000000000000\nWord\n')
    assert helper.comparison(a, b) == 'match'
    b.write_text(b.read_text().replace('Word', 'word'))
    assert helper.comparison(a, b) == 'mismatch'


@pytest.mark.parametrize('error', ["bwrap: Can't mkdir /example: Read-only file system",
    'Creating new namespace failed: No space left on device',
    'Failed to create unified exec process', 'sandbox failed to execute'])
def test_log_rejects_errors_even_with_answer_and_success(tmp_path, error):
    log = tmp_path / 'log'
    log.write_text(json.dumps(dict(type='item.completed', item=dict(type='command_execution', exit_code=0, aggregated_output=error))))
    assert helper.log_failure(log) == 'sandbox execution error'


@pytest.mark.parametrize('error', [
    'ERROR codex_core::tools::router: error=`justification` requires an explicit `sandbox_permissions`; use `sandbox_permissions: "require_escalated"` for unsandboxed execution, or omit `justification`.',
    'ERROR codex_core::tools::router: error=unsupported call: read',
])
def test_recovered_tool_argument_errors_are_not_sandbox_failures(tmp_path, error):
    ok = json.dumps(dict(type='item.completed', item=dict(type='command_execution', exit_code=0, aggregated_output='ok')))
    log = tmp_path / 'log'
    # A mistake followed by a successful command is recovered: the session stands, with a note.
    log.write_text(error + '\n' + ok)
    assert helper.log_failure(log) is None
    assert helper.log_notes(log) == 'tool x1'
    # A mistake with no successful command anywhere has no evidence behind it.
    log.write_text(error)
    assert helper.log_failure(log) == 'invalid tool call or arguments'
    # Ending on a mistake asks for a guided retry and names the correction.
    log.write_text(ok + '\n' + error)
    assert helper.log_failure(log) == 'ended on a failed tool call'
    assert 'exec_command' in helper.log_guidance(log)
    # An environment failure that is never followed by a success still blocks.
    with log.open('a') as f:
        f.write('\nbwrap: Creating new namespace failed: No space left on device')
    assert helper.log_failure(log) == 'sandbox execution error'
    with log.open('a') as f:
        f.write('\n' + ok)
    assert helper.log_failure(log) is None


def test_missing_working_directory_is_a_recoverable_mistake(tmp_path):
    ok = json.dumps(dict(type='item.completed', item=dict(type='command_execution', exit_code=0, aggregated_output='ok')))
    slip = 'Rejected("Failed to create unified exec process: No such file or directory (os error 2)")'
    log = tmp_path / 'log'
    log.write_text(ok + '\n' + slip)
    assert helper.log_failure(log) == 'ended on a failed tool call'
    assert 'working directory' in helper.log_guidance(log)
    log.write_text(ok + '\n' + slip + '\n' + ok)
    assert helper.log_failure(log) is None and helper.log_notes(log) == 'exec x1'
    log.write_text(slip)
    assert helper.log_failure(log) == 'sandbox execution error'


def test_log_requires_success_and_accepts_text_and_json(tmp_path):
    log = tmp_path / 'log'
    log.write_text('plausible answer, no tool calls')
    assert helper.log_failure(log) == 'no command succeeded'
    log.write_text('command succeeded in 2ms:\n')
    assert helper.log_failure(log) is None
    log.write_text(json.dumps(dict(type='item.completed', item=dict(type='command_execution', exit_code=0, aggregated_output='ok'))))
    assert helper.log_failure(log) is None
    # A diagnostic question mentioning bwrap is not itself a failure event.
    log.write_text(log.read_text() + '\n' + json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='Explain bwrap sandbox failures'))))
    assert helper.log_failure(log) is None


def state(path, ident=1):
    path.write_text(f"MINERVA_OLLAMA_JOB_NAME='codex-ollama-scribe-{ident}'\nMINERVA_OLLAMA_REMOTE_PORT='{8890+ident}'\nMINERVA_OLLAMA_LOCAL_PORT='{11440+ident}'\nMINERVA_OLLAMA_DEFAULT_MODEL='invented:27b'\n")


def test_state_identity_never_accepts_librarian(tmp_path):
    path = tmp_path / 'scribe.env'
    state(path)
    assert helper.state_model(path, 1) == 'invented:27b'
    for old, bad in [('codex-ollama-scribe-1', 'codex-ollama-flash-next'), ('8891', '8889'), ('11441', '11435')]:
        state(path)
        path.write_text(path.read_text().replace(old, bad))
        with pytest.raises(ValueError):
            helper.state_model(path, 1)
    path.write_text("MINERVA_OLLAMA_DEFAULT_MODEL=$(touch should-not-exist)\n")
    with pytest.raises(ValueError):
        helper.state_model(path, 1)
    assert not (tmp_path / 'should-not-exist').exists()


def lifecycle_env(tmp_path):
    bindir = tmp_path / 'bin'; bindir.mkdir()
    trace = tmp_path / 'trace'
    scripts = {
        'bjobs': 'if [ -f "$HOME/submitted" ]; then printf "%s\\n" "$FAKE_AFTER_SUBMIT"; else printf "%s\\n" "$FAKE_JOBS"; fi\n',
        'bsub': 'cat >/dev/null\nprintf "parallel=%s\\n" "$SCRIBE_PARALLEL" >> "$TRACE"\ntouch "$HOME/submitted"\necho "Job <123> is submitted to queue <gpuexpress>."\n',
        'bkill': '',
        'bqueues': 'printf "%s\\n" "$FAKE_QUEUES"\n',
        'bmgroup': 'printf "%s\\n" "$FAKE_GROUPS"\n',
        'bhosts': 'if [[ "$*" == *-gpu* ]]; then printf "%s\\n" "$FAKE_ALLOCATION"; else printf "%s\\n" "$FAKE_SLOTS"; fi\n',
        'lsload': 'printf "%s\\n" "$FAKE_LOAD"\n',
    }
    for name, body in scripts.items():
        script = bindir / name
        script.write_text('#!/bin/bash\nprintf "%s\\n" "$0 $*" >> "$TRACE"\n' + body)
        script.chmod(0o755)
    env = dict(os.environ, PATH=f'{bindir}:{os.environ["PATH"]}', HOME=str(tmp_path),
               LIBRARIAN_HOME=str(tmp_path / 'private'), TRACE=str(trace), FAKE_JOBS='',
               FAKE_AFTER_SUBMIT='123 RUN codex-ollama-scribe-1 2*lg02e01 0',
               FAKE_QUEUES=FIXTURE['queues'], FAKE_GROUPS=FIXTURE['groups'],
               FAKE_ALLOCATION=FIXTURE['bhosts_gpu'], FAKE_LOAD=FIXTURE['lsload_gpuload'],
               FAKE_SLOTS=FIXTURE['bhosts_slots'])
    for key in ('SCRIBE_GPU_MODEL', 'SCRIBE_PARALLEL', 'SCRIBE_WALLTIME', 'SCRIBE_MAX_PENDING'):
        env.pop(key, None)
    return env, trace


@pytest.mark.parametrize('args', [('down', 'codex-ollama-flash-next'), ('down', '0'), ('up', 'codex-ollama-flash-next')])
def test_refuses_librarian_and_invalid_id_without_scheduler(tmp_path, args):
    env, trace = lifecycle_env(tmp_path)
    p = subprocess.run([str(ROOT / 'scribes'), *args], env=env, capture_output=True)
    assert p.returncode != 0
    assert not trace.exists()


def test_down_crosschecks_exact_live_names(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env['FAKE_JOBS'] = '271767293 RUN codex-ollama-flash-next 8*node'
    p = subprocess.run([str(ROOT / 'scribes'), 'down', '1'], env=env, capture_output=True)
    assert p.returncode != 0 and 'bkill' not in trace.read_text()
    env['FAKE_JOBS'] = '123 RUN codex-ollama-scribe-1 8*node'
    p = subprocess.run([str(ROOT / 'scribes'), 'down', '1'], env=env, capture_output=True)
    assert p.returncode == 0 and 'bkill 123' in trace.read_text()


def available_allocation(text=FIXTURE['bhosts_gpu'], host='lg02e01', count=1):
    rows = helper.lsf_table(text, ('HOST_NAME', 'GPU_ID'), True)
    header = text.splitlines()[0].split()
    for row in rows:
        if row['HOST_NAME'] == host and int(row['GPU_ID']) < count:
            for key in ('NJOBS', 'RUN', 'SUSP', 'RSV'):
                row[key] = '0'
    return ' '.join(header) + '\n' + '\n'.join(' '.join(row[k] for k in header) for row in rows) + '\n'


def test_up_idempotent_and_parameterized(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_JOBS='123 RUN codex-ollama-scribe-1 2*node 0', SCRIBE_PARALLEL='2',
               SCRIBE_WALLTIME='02:30', SCRIBE_MAX_PENDING='2', SCRIBE_GPU_MODEL='NVIDIAA100_SXM4_80GB')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'bsub' not in trace.read_text() and 'bhosts' not in trace.read_text()
    env.update(FAKE_JOBS='', FAKE_ALLOCATION=available_allocation(host='lg07c09'))
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert '-J codex-ollama-scribe-1 -q gpuexpress -m lg07c09 -W 02:30 -ptl 2 -gpu num=1:gmem=32G:mode=exclusive_process:j_exclusive=yes:gmodel=NVIDIAA100_SXM4_80GB' in trace.read_text()
    assert 'parallel=2' in trace.read_text()


def test_recorded_free_gpu_parser_ignores_memory_use_and_reservations():
    assert helper.free_gpu_slots(FIXTURE['bhosts_gpu'], FIXTURE['lsload_gpuload'], FIXTURE['bhosts_slots']) == []
    alloc = available_allocation()
    assert helper.free_gpu_slots(alloc, FIXTURE['lsload_gpuload'], FIXTURE['bhosts_slots']) == [('lg02e01', 'NVIDIAH10080GBHBM3')]
    alloc = alloc.replace('lg02e01 0 NVIDIAH10080GBH 76.2G 0M 0 0 0 0', 'lg02e01 0 NVIDIAH10080GBH 76.2G 0M 0 0 0 1')
    assert helper.free_gpu_slots(alloc, FIXTURE['lsload_gpuload'], FIXTURE['bhosts_slots']) == []


@pytest.mark.parametrize('host,model', [('lg07c01', 'NVIDIAA100_PCIE_40GB'), ('lg07c09', 'NVIDIAA100_SXM4_80GB'),
    ('lg02e17', 'NVIDIAL40S'), ('lg05g29', 'NVIDIAH100PCIe'), ('lg01e01', 'NVIDIAB200')])
def test_accepts_any_qualifying_gpu_model(host, model):
    rows = helper.lsf_table(FIXTURE['bhosts_slots'], ('HOST_NAME', 'STATUS', 'MAX', 'NJOBS'))
    header = FIXTURE['bhosts_slots'].splitlines()[0].split()
    for row in rows:
        if row['HOST_NAME'] == host:
            row.update(STATUS='ok', NJOBS=str(int(row['MAX']) - 2))
    slots = ' '.join(header) + '\n' + '\n'.join(' '.join(row[k] for k in header) for row in rows)
    found = helper.free_gpu_slots(available_allocation(host=host), FIXTURE['lsload_gpuload'], slots)
    assert found == [(host, model)]


def test_parser_rejects_small_cards_full_cores_and_bad_schema():
    # The recorded unallocated V100 16G is too small.
    assert not any(host == 'lg03a01' for host, _ in helper.free_gpu_slots(FIXTURE['bhosts_gpu'], FIXTURE['lsload_gpuload'], FIXTURE['bhosts_slots']))
    slots = FIXTURE['bhosts_slots'].replace('96     64     64', '96     95     95')
    assert helper.free_gpu_slots(available_allocation(), FIXTURE['lsload_gpuload'], slots) == []
    with pytest.raises(ValueError):
        helper.free_gpu_slots('unexpected output', FIXTURE['lsload_gpuload'], slots)


def test_up_with_no_free_gpu_queues_the_scribes_and_lets_them_wait(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '3'], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    lines = [line for line in trace.read_text().splitlines() if '/bsub ' in line]
    assert len(lines) == 3 and all(' -q gpu -W 24:00 -ptl 10080 ' in line and ' -m ' not in line for line in lines)
    assert 'bkill' not in trace.read_text()


def test_up_caps_submissions_and_uses_small_defaults(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env['FAKE_ALLOCATION'] = available_allocation()
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '3'], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    lines = trace.read_text().splitlines()
    assert len([line for line in lines if '/bsub ' in line]) == 3
    assert '-W 24:00 -ptl 10080 -gpu num=1:gmem=32G:mode=exclusive_process:j_exclusive=yes' in trace.read_text()
    assert 'parallel=1' in trace.read_text()
    server = (ROOT / 'scribe_server.lsf').read_text()
    assert '#BSUB -n 2' in server and 'rusage[mem=32G]' in server and '#BSUB -ptl' not in server


def test_a_pending_scribe_is_left_waiting_in_the_queue(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_ALLOCATION=available_allocation(), FAKE_AFTER_SUBMIT='123 PEND codex-ollama-scribe-1 - 1')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'waiting in the queue' in p.stdout
    assert 'bkill' not in trace.read_text()


def test_up_never_touches_a_job_with_another_name(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_ALLOCATION=available_allocation(), FAKE_AFTER_SUBMIT='123 PEND codex-ollama-flash-next - 1')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'bkill' not in trace.read_text()


def test_status_shows_pending_age(tmp_path):
    env, _ = lifecycle_env(tmp_path)
    env['FAKE_JOBS'] = '123 PEND codex-ollama-scribe-1 - 67'
    p = subprocess.run([str(ROOT / 'scribes'), 'status'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'PENDING_SECONDS' in p.stdout
    assert p.stdout.splitlines()[1].endswith('\t67')


@pytest.mark.parametrize('status', ['match', 'mismatch', 'no-table'])
def test_route_independent_sessions_and_reviewer(tmp_path, monkeypatch, status):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('LIBRARIAN_HOME', str(tmp_path / 'private'))
    monkeypatch.delenv('LIBRARIAN_SCRIBE_ID', raising=False)
    (tmp_path / '.codex').mkdir()
    state(tmp_path / '.codex/ollama-scribe-1.env')
    run = tmp_path / 'run'; run.mkdir()
    sessions = []
    def fake(args, **kwargs):
        if args[1] == 'endpoint':
            return subprocess.CompletedProcess(args, 0, json.dumps(dict(id=1, model='invented:27b', host='http://127.0.0.1:11441')), '')
        env = kwargs['env']; rd = Path(env['LIBRARIAN_RUN_DIR']); rd.mkdir()
        sessions.append(rd.name)
        assert env['MINERVA_OLLAMA_STATE_FILE'].endswith('ollama-scribe-1.env')
        assert env['MINERVA_OLLAMA_JOB_NAME'] == 'codex-ollama-scribe-1'
        assert env['MINERVA_OLLAMA_REMOTE_PORT'] == '8891'
        assert env['MINERVA_OLLAMA_LOCAL_PORT'] == '11441'
        assert env['MINERVA_OLLAMA_DEFAULT_MODEL'] == 'invented:27b'
        assert env['CODEX_OSS_BASE_URL'] == 'http://127.0.0.1:11441/v1'
        (rd / 'answer.md').write_text('invented final ' + rd.name)
        if status != 'no-table':
            (rd / 'result.tsv').write_text('key\tvalue\na\t' + ('2' if status == 'mismatch' and rd.name == 'B' else '1') + '\n')
        return subprocess.CompletedProcess(args, 0, '', '')
    monkeypatch.setattr(helper.subprocess, 'run', fake)
    helper.route(run, 'Synthetic exact input task', True, 'me')
    assert {'A', 'B'} <= set(sessions)
    assert json.loads((run / 'comparison.json').read_text())['status'] == status
    assert ('reviewer' in sessions) == (status != 'match')
    assert (run / 'answer.md').is_file()


def test_normalization_preserves_tiny_scientific_values(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_text('p\n4.46E-8\n')
    b.write_text('p\n4.47E-8\n')
    assert helper.comparison(a, b) == 'mismatch'


def test_server_health_publishes_only_own_state_and_cleans_exit(tmp_path):
    bindir = tmp_path / 'bin'; bindir.mkdir()
    home = tmp_path / 'home'; (home / '.codex').mkdir(parents=True)
    librarian = home / '.codex/ollama-flash-next.env'
    librarian.write_text('LIBRARIAN SENTINEL\n')
    trace = tmp_path / 'trace'
    stubs = {
        'ollama': '#!/bin/bash\nprintf "%s\\n" "$*" >> "$TRACE"\nsleep 2\n',
        'ss': '#!/bin/bash\nexit 0\n',
        'nvidia-smi': '#!/bin/bash\necho "invented GPU, 1 MiB, 80000 MiB"\n',
        'curl': '''#!/bin/bash
printf '%s\n' "$*" >> "$TRACE"
case "$*" in
*/api/tags*) echo '{"models":[{"name":"invented:27b"}]}' ;;
*/api/generate*) echo '{"done":true,"eval_count":2,"eval_duration":1000000000}' ;;
*/api/ps*) echo '{"models":[{"name":"invented:27b","size_vram":18000000000,"context_length":262144}]}' ;;
esac
''',
    }
    for name, content in stubs.items():
        p=bindir / name; p.write_text(content); p.chmod(0o755)
    env=dict(os.environ, HOME=str(home), PATH=f'{bindir}:{os.environ["PATH"]}', TRACE=str(trace),
             SCRIBE_ID='1', SCRIBE_MODEL='invented:27b', SCRIBE_PARALLEL='3',
             SCRIBE_OLLAMA_BIN=str(bindir / 'ollama'), LSB_JOBNAME='codex-ollama-scribe-1', LSB_JOBID='123')
    p=subprocess.run(['bash',str(ROOT / 'scribe_server.lsf')],env=env,capture_output=True,text=True)
    assert p.returncode == 0 and 'scribe 1 ready' in p.stdout
    assert not (home / '.codex/ollama-scribe-1.env').exists()
    assert librarian.read_text() == 'LIBRARIAN SENTINEL\n'
    assert '/api/generate' in trace.read_text() and 'pull' not in trace.read_text()


def test_lifecycle_scheduler_failure_does_not_submit(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    jobstub = tmp_path / 'bin/bjobs'
    jobstub.write_text('#!/bin/bash\necho "scheduler unavailable" >&2\nexit 1\n')
    p=subprocess.run([str(ROOT / 'scribes'), 'up', '1'],env=env,capture_output=True)
    assert p.returncode != 0 and not trace.exists()


def test_state_rejects_source_side_effects_and_redirects(tmp_path):
    path=tmp_path / 'state'
    for extra in ["MINERVA_OLLAMA_LAST_NODE='$(touch injected)'", "MINERVA_OLLAMA_STATE_FILE='/example/ollama-flash-next.env'"]:
        state(path)
        path.write_text(path.read_text() + extra + '\n')
        with pytest.raises(ValueError):
            helper.state_model(path, 1)


@pytest.mark.parametrize('check,status', [(False, 'match'), (True, 'match'), (True, 'mismatch')])
def test_no_healthy_scribe_falls_back_sequentially(tmp_path, monkeypatch, check, status):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('LIBRARIAN_SCRIBE_ID', '1')
    monkeypatch.setenv('LIBRARIAN_SCRIBE_SESSION', '1')
    monkeypatch.setenv('OLLAMA_HOST', 'http://127.0.0.1:11441')
    monkeypatch.setenv('CODEX_OSS_BASE_URL', 'http://127.0.0.1:11441/v1')
    monkeypatch.setenv('MINERVA_OLLAMA_DEFAULT_MODEL', 'invented:scribe')
    run = tmp_path / 'run'; run.mkdir()
    sessions = []
    def fake(args, **kwargs):
        if args[1] == 'endpoint':
            return subprocess.CompletedProcess(args, 1, '', '')
        env = kwargs['env']; rd = Path(env['LIBRARIAN_RUN_DIR']); rd.mkdir()
        sessions.append(rd.name)
        assert 'LIBRARIAN_SCRIBE_SESSION' not in env  # ordinary wrapper must take its lock
        assert 'OLLAMA_HOST' not in env and 'CODEX_OSS_BASE_URL' not in env
        assert 'MINERVA_OLLAMA_DEFAULT_MODEL' not in env
        assert env['MINERVA_OLLAMA_JOB_NAME'] == 'codex-ollama-flash-next'
        assert env['MINERVA_OLLAMA_STATE_FILE'].endswith('ollama-flash-next.env')
        assert env['MINERVA_OLLAMA_REMOTE_PORT'] == '8889' and env['MINERVA_OLLAMA_LOCAL_PORT'] == '11435'
        (rd / 'answer.md').write_text('invented answer')
        (rd / 'result.tsv').write_text('key\tvalue\na\t' + ('2' if status == 'mismatch' and rd.name == 'B' else '1') + '\n')
        return subprocess.CompletedProcess(args, 0, '', '')
    class ForbiddenPool:
        def __init__(self, *args, **kwargs):
            pytest.fail('main librarian fallback must run sequentially')
    monkeypatch.setattr(helper.subprocess, 'run', fake)
    monkeypatch.setattr(helper, 'ThreadPoolExecutor', ForbiddenPool)
    helper.route(run, 'invented task', check, 'me')
    assert sessions == (['A', 'B', 'reviewer'] if status == 'mismatch' else ['A', 'B'] if check else ['A'])
    assert (run / 'backend').read_text() == 'librarian\n'
    assert (run / 'answer.md').is_file()


@pytest.mark.parametrize('command', ['bqueues', 'bmgroup', 'bhosts', 'lsload'])
def test_failed_free_gpu_query_never_submits(tmp_path, command):
    env, trace = lifecycle_env(tmp_path)
    (tmp_path / 'bin' / command).write_text('#!/bin/bash\necho "query unavailable" >&2\nexit 1\n')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode != 0 and 'bsub' not in trace.read_text()


def test_candidate_count_is_capped_by_free_cores():
    alloc = available_allocation(count=4)
    slots = FIXTURE['bhosts_slots'].replace('96     64     64', '96     93     93')
    assert helper.free_gpu_slots(alloc, FIXTURE['lsload_gpuload'], slots) == [('lg02e01', 'NVIDIAH10080GBHBM3')]


def test_closed_hosts_never_admit_scribes():
    assert helper.free_gpu_slots(available_allocation(host='lg05g29'), FIXTURE['lsload_gpuload'], FIXTURE['bhosts_slots']) == []


def test_up_adds_a_job_on_a_free_node_for_a_waiting_scribe_and_removes_nothing(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_ALLOCATION=available_allocation(), FAKE_JOBS='122 PEND codex-ollama-scribe-1 - 600')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    lines = [line for line in trace.read_text().splitlines() if '/bsub ' in line]
    assert len(lines) == 1 and ' -m ' in lines[0] and 'adding one on free node' in p.stdout
    assert 'bkill' not in trace.read_text()


def test_up_leaves_a_waiting_scribe_alone_when_no_gpu_is_free_or_two_jobs_already_wait(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_JOBS='122 PEND codex-ollama-scribe-1 - 600')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'no free GPU now' in p.stdout and (not trace.exists() or 'bsub' not in trace.read_text())
    env.update(FAKE_ALLOCATION=available_allocation(), FAKE_JOBS='122 PEND codex-ollama-scribe-1 - 600\n123 PEND codex-ollama-scribe-1 - 5')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True, text=True)
    assert p.returncode == 0 and 'none added' in p.stdout and (not trace.exists() or 'bsub' not in trace.read_text())


def test_running_server_removes_waiting_twins_only_after_it_is_up():
    server = (ROOT / 'scribe_server.lsf').read_text()
    ready = server.index("kill -0 \"$server\" || { echo 'Server exited during warmup'; exit 1; }")
    twin = server.index('removed waiting twin job')
    state = server.index('mv "$state.${LSB_JOBID}.tmp" "$state"')
    assert ready < twin < state and 'this job steps aside' in server
