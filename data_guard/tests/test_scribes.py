"""Synthetic checks only: no scheduler, GPU, real Codex, or protected data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
    for name in ('bjobs', 'bsub', 'bkill'):
        script = bindir / name
        script.write_text('#!/bin/bash\nprintf "%s\\n" "$0 $*" >> "$TRACE"\n' +
                          ('printf "%s\\n" "$FAKE_JOBS"\n' if name == 'bjobs' else 'cat >/dev/null\n' if name == 'bsub' else ''))
        script.chmod(0o755)
    env = dict(os.environ, PATH=f'{bindir}:{os.environ["PATH"]}', HOME=str(tmp_path),
               LIBRARIAN_HOME=str(tmp_path / 'private'), TRACE=str(trace), FAKE_JOBS='')
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


def test_up_idempotent_and_parameterized(tmp_path):
    env, trace = lifecycle_env(tmp_path)
    env.update(FAKE_JOBS='123 RUN codex-ollama-scribe-1 8*node', SCRIBE_PARALLEL='3', SCRIBE_WALLTIME='02:30', SCRIBE_GPU_MODEL='NVIDIAA100_SXM4_80GB')
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True)
    assert p.returncode == 0 and 'bsub' not in trace.read_text()
    env['FAKE_JOBS'] = ''
    p = subprocess.run([str(ROOT / 'scribes'), 'up', '1'], env=env, capture_output=True)
    assert p.returncode == 0
    assert '-J codex-ollama-scribe-1 -W 02:30 -gpu num=1:gmodel=NVIDIAA100_SXM4_80GB' in trace.read_text()


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
