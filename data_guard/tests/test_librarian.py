import os
import json
import subprocess
from pathlib import Path

import pytest

LIBRARIAN = Path(__file__).resolve().parents[1] / "librarian"

STUB = """#!/bin/sh
if [ -n "$STUB_AVAILABLE_MODEL" ]; then
    selected=${CODEX_OLLAMA_MODEL:-${MINERVA_OLLAMA_DEFAULT_MODEL:-}}
    prev=
    for arg do
        [ "$prev" = --model ] && selected=$arg
        prev=$arg
    done
    [ "$selected" = "$STUB_AVAILABLE_MODEL" ] || { echo 'Pull failed: pull model manifest: file does not exist'; exit 1; }
fi
echo "NOISY tool output: secret-row-42"
echo "NOISY stderr" >&2
[ -z "$STUB_NO_COMMAND" ] && echo '{"type":"item.completed","item":{"type":"command_execution","exit_code":0}}'
[ -n "$STUB_LOG_ERROR" ] && echo "$STUB_LOG_ERROR"
[ -n "$STUB_SLIP_TIMES" ] && echo '{"type":"thread.started","thread_id":"stub-thread"}'
[ -n "$STUB_SLIP_TIMES" ] && echo x >> "$STUB_SLIP_COUNT" && [ "$(wc -l < "$STUB_SLIP_COUNT")" -le "$STUB_SLIP_TIMES" ] && echo 'ERROR codex_core::tools::router: error=unsupported call: read'
[ -n "$STUB_LOCK" ] && flock -n "$LIBRARIAN_HOME/librarian.lock" -c true && exit 7
[ -n "$STUB_ARGS" ] && printf '%s\\n' "$@" > "$STUB_ARGS"
while [ $# -gt 0 ]; do
    [ "$1" = -C ] && rd=$2
    [ "$1" = -o ] && out=$2
    shift
done
[ -n "$STUB_CALLS" ] && printf '%s\\n' "$rd" >> "$STUB_CALLS"
[ -n "$STUB_TABLE" ] && printf 'key\\tvalue\\na\\t1\\n' > "$rd/result.tsv"
[ -n "$STUB_FAIL" ] && exit 3
printf '%s\\n' "${STUB_ANSWER:-FAKE ANSWER}" > "$out"
"""


def run(tmp_path, *args, fail=False, **extra):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "codex-oss"
    stub.write_text(STUB)
    stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", LIBRARIAN_HOME=str(tmp_path / "home"))
    for k in ("STUB_FAIL", "JUPYTER_PORT", "JUPYTER_SERVER_ROOT", "LIBRARIAN_JUPYTER_BASE_URL"):
        env.pop(k, None)
    if fail:
        env["STUB_FAIL"] = "1"
    env.update(extra)
    return subprocess.run([str(LIBRARIAN), *args], env=env, capture_output=True, text=True)


def runs(tmp_path):
    return sorted((tmp_path / "home" / "runs").iterdir())


def test_network_override_is_an_exec_argument(tmp_path):
    trace = tmp_path / 'args.txt'
    p = run(tmp_path, 'synthetic task', LIBRARIAN_NETWORK='off', STUB_ARGS=str(trace))
    assert p.returncode == 0
    args = trace.read_text().splitlines()
    # The host launcher injects additional -c flags after exec. The pinned CLI
    # uses that subcommand override list, so a global-only network flag is lost.
    setting = args.index('sandbox_workspace_write.network_access=false')
    assert setting > args.index('exec') and args[setting - 1] == '-c'


@pytest.mark.parametrize('slips', [0, 1])
def test_me_pins_installed_main_model_despite_inherited_defaults(tmp_path, slips):
    # The deployed main store has only Qwen; the old state and scribe model are absent.
    installed = "qwen3.8-flash-next:125b-a6b-q4_K_M"
    trace = tmp_path / 'args.txt'
    p = run(tmp_path, '--me', 'synthetic task', STUB_AVAILABLE_MODEL=installed,
            MINERVA_OLLAMA_DEFAULT_MODEL='laguna-s-2.1:q8_0-256k-t2',
            CODEX_OLLAMA_MODEL='laguna-xs-2.1:q4_K_M-256k-t2',
            STUB_ARGS=str(trace), STUB_SLIP_TIMES=str(slips),
            STUB_SLIP_COUNT=str(tmp_path / 'slips'))
    assert p.returncode == 0 and p.stdout.startswith('Done')
    args = trace.read_text().splitlines()
    assert args[args.index('--model') + 1] == installed
    assert ('resume' in args) == bool(slips)
    if not slips:
        assert f"The caller's working directory is {Path.cwd()}." in args[-1]
        assert 'Resolve relative input paths against that directory.' in args[-1]
    policy = json.loads(LIBRARIAN.with_name('standin_policy.json').read_text())
    assert policy['review_model'] == installed


def test_default_mode_prints_only_answer(tmp_path):
    p = run(tmp_path, "task")
    assert p.returncode == 0
    assert p.stdout == "FAKE ANSWER\n"
    assert p.stderr == ""
    (rd,) = runs(tmp_path)
    assert "-agent-" in rd.name
    assert "NOISY tool output" in (rd / "log").read_text()
    assert (rd / "task").read_text() == "task\n"


def receipt(**extra):
    return {'slots': {'{{VALUE-ABCD}}': 'resolved'}, 'doc_verified': True,
            'mask_verified': True, 'dictionary_synced': True, 'preserved': True, **extra}


def test_receipt_mode_filters_private_values_locally(tmp_path):
    allowed = receipt(blockers={'{{VALUE-ABCD}}': 'source-mismatch'})
    answer = {**allowed, 'invented_qc_bound': 0.123456, 'invented_genes': ['FABLE1']}
    p = run(tmp_path, '--receipt', 'synthetic operation', STUB_ANSWER=json.dumps(answer))
    assert p.returncode == 0 and json.loads(p.stdout) == allowed and p.stderr == ''
    assert '0.123456' not in p.stdout and 'FABLE1' not in p.stdout and 'NOISY' not in p.stdout
    (rd,) = runs(tmp_path)
    assert '-receipt-' in rd.name and 'FABLE1' in (rd / 'answer.md').read_text()
    assert not (tmp_path / 'home/latest.md').exists()


@pytest.mark.parametrize('answer', [
    'Invented value 0.123456',
    '[]',
    json.dumps(receipt(doc_verified=1)),
    json.dumps(receipt(slots={'{{VALUE-ABCD}}': {'value': '0.123456'}})),
    json.dumps(receipt(slots={'FABLE1': 'resolved'})),
    json.dumps(receipt(slots={'{{VALUE-ABCD}}': '0.123456'})),
    json.dumps(receipt(blockers={'{{VALUE-ABCD}}': 'Invented value 0.123456'})),
])
def test_invalid_receipt_fails_without_leaking_answer(tmp_path, answer):
    p = run(tmp_path, '--receipt', 'synthetic operation', STUB_ANSWER=answer)
    assert p.returncode == 1
    assert p.stdout == 'Librarian failed: invalid status receipt; private answer retained.\n'
    assert p.stderr == '' and '0.123456' not in p.stdout and 'FABLE1' not in p.stdout


def test_receipt_mode_cannot_be_overridden_by_option_like_task(tmp_path):
    p = run(tmp_path, '--receipt', '--slots', STUB_ANSWER='{"value":"FABLE1"}')
    assert p.returncode == 1
    assert p.stdout == 'Librarian failed: invalid status receipt; private answer retained.\n'
    assert 'FABLE1' not in p.stdout + p.stderr
    assert '-receipt-' in runs(tmp_path)[0].name


def test_me_mode_writes_latest_and_prints_done(tmp_path):
    latest = tmp_path / "home" / "latest.md"
    run(tmp_path, "--me", "first")
    p = run(tmp_path, "--me", "second")
    assert p.returncode == 0
    assert p.stdout.startswith("Done") and len(p.stdout.splitlines()) == 1
    assert "FAKE ANSWER" not in p.stdout
    text = latest.read_text()
    assert "FAKE ANSWER" in text and "> second" in text and "> first" not in text
    assert all("-me-" in r.name for r in runs(tmp_path))


def test_failure_is_one_line_with_log_path(tmp_path):
    p = run(tmp_path, "task", fail=True)
    assert p.returncode != 0
    (rd,) = runs(tmp_path)
    assert p.stdout.splitlines() == [p.stdout.strip()]
    assert str(rd / "log") in p.stdout
    assert "NOISY" not in p.stdout + p.stderr


def test_me_mode_publishes_answer_to_repo(tmp_path):
    bare = tmp_path / "answers.git"
    git = lambda *a, cwd=None: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
    git("init", "-q", "--bare", "-b", "main", str(bare))
    kb = tmp_path / "home" / "repo"
    git("clone", "-q", str(bare), str(kb))
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init", cwd=kb)
    git("push", "-q", "origin", "HEAD:main", cwd=kb)
    git("config", "user.name", "t", cwd=kb)
    git("config", "user.email", "t@t", cwd=kb)
    p = run(tmp_path, "--me", "task")
    assert p.returncode == 0 and len(p.stdout.splitlines()) == 1 and "failed" not in p.stdout
    show = lambda path: subprocess.run(["git", "--git-dir", str(bare), "show", f"main:{path}"],
                                       capture_output=True, text=True, check=True).stdout
    latest = (tmp_path / "home" / "latest.md").read_text()
    (rd,) = runs(tmp_path)
    assert show("README.md") == latest and show(f"answers/{rd.name}.md") == latest


def test_me_mode_writes_paths_under_home(tmp_path):
    home = tmp_path / "userhome"
    real = tmp_path / "scratch" / "project"
    real.mkdir(parents=True)
    home.mkdir()
    (home / "proj").symlink_to(real)
    answer = f"Notebook: {real}/run/analysis.ipynb and {home}/notes.md"
    p = run(tmp_path, "--me", "task", HOME=str(home), STUB_ANSWER=answer)
    assert p.returncode == 0
    text = (tmp_path / "home" / "latest.md").read_text()
    assert "Notebook: ~/proj/run/analysis.ipynb and ~/notes.md" in text


def test_me_mode_links_paths_to_jupyterlab(tmp_path):
    answer = "Notebook: `~/proj/analysis.ipynb`\n```\ncat ~/proj/x.tsv\n```"
    p = run(tmp_path, "--me", "task", STUB_ANSWER=answer, JUPYTER_PORT="8548")
    assert p.returncode == 0
    text = (tmp_path / "home" / "latest.md").read_text()
    assert "[`~/proj/analysis.ipynb`](http://127.0.0.1:8548/lab/tree/proj/analysis.ipynb)" in text
    assert "cat ~/proj/x.tsv" in text


def test_slots_mode_is_private_machine_response(tmp_path):
    # Bootstrap the existing stub without contacting a real model.
    run(tmp_path, 'bootstrap')
    env = dict(os.environ, PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
               LIBRARIAN_HOME=str(tmp_path / 'home'), STUB_ANSWER='{"{{TEXT-ABCD}}":{"value":"17"}}')
    p = subprocess.run([str(LIBRARIAN), '--slots'], input='Synthetic retrieval request',
                       env=env, capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout == '{"{{TEXT-ABCD}}":{"value":"17"}}\n'
    assert not (tmp_path / 'home/latest.md').exists()
    assert any('-slots-' in path.name for path in runs(tmp_path))


def test_mask_entrypoint_uses_separate_config_without_starting_codex(tmp_path):
    home=tmp_path / 'mask-home'
    (home / 'codex').mkdir(parents=True)
    (home / 'codex/config.toml').write_text('[masking]\ndictionary="../dict.json.zst"\n')
    source=tmp_path / 'invented-human.md'
    source.write_text('Invented **12** genes.\n')
    masked=tmp_path / 'invented-masked.md'
    p=subprocess.run([str(LIBRARIAN),'mask','export','--document','synthetic','--markdown',str(source),'--masked',str(masked)],
                     env=dict(os.environ,LIBRARIAN_HOME=str(home)),capture_output=True,text=True)
    assert p.returncode==0 and p.stdout=='OK\n'
    assert '12' not in masked.read_text()
    assert not (home / 'runs').exists()


def test_explicit_write_roots_preserve_shell_metacharacters(tmp_path):
    root = tmp_path / 'room with $dollars and `backticks`'
    root.mkdir()
    args = tmp_path / 'args.txt'
    p = run(tmp_path, '--add-dir', str(root), '--add-dir', str(tmp_path), 'synthetic sync', STUB_ARGS=str(args))
    assert p.returncode == 0
    assert args.read_text().splitlines()[:4] == ['--add-dir', str(root), '--add-dir', str(tmp_path)]


@pytest.mark.parametrize('error', ['Failed to create unified exec process', "bwrap: Can't mkdir /synthetic", 'sandbox failed'])
def test_failed_commands_never_print_done_even_with_answer(tmp_path, error):
    p = run(tmp_path, '--me', 'synthetic task', STUB_LOG_ERROR=error)
    assert p.returncode != 0 and p.stdout.startswith('Librarian failed:')
    assert 'Done' not in p.stdout
    assert not (tmp_path / 'home/latest.md').exists()


@pytest.mark.parametrize('slips,done', [(1, True), (2, True), (3, False)])
def test_last_failed_tool_call_gets_guided_retries_then_stands_or_fails(tmp_path, slips, done):
    count = tmp_path / 'slips'
    trace = tmp_path / 'args.txt'
    p = run(tmp_path, '--me', 'synthetic task', STUB_SLIP_TIMES=str(slips), STUB_SLIP_COUNT=str(count), STUB_ARGS=str(trace))
    assert len(count.read_text().splitlines()) == min(slips, 2) + 1
    if done:
        assert p.returncode == 0 and p.stdout.startswith('Done')
        assert (tmp_path / 'home/latest.md').exists()
        # The retry is a resume of the same session that names the correction.
        args = trace.read_text()
        assert 'resume' in args and 'stub-thread' in args and 'exec_command' in args
        (rd,) = runs(tmp_path)
        assert f'guided retries: {slips}' in (rd / 'session-notes.txt').read_text()
    else:
        assert p.returncode != 0 and 'ended on a failed tool call' in p.stdout
        assert not (tmp_path / 'home/latest.md').exists()


def test_no_command_never_releases_plausible_answer(tmp_path):
    p=run(tmp_path, '--me', 'synthetic task', STUB_NO_COMMAND='1')
    assert p.returncode != 0 and 'no command succeeded' in p.stdout
    assert not (tmp_path / 'home/latest.md').exists()


@pytest.mark.parametrize('check', [False, True])
def test_scribe_fallback_cli_preserves_main_lock_and_sequential_runs(tmp_path, check):
    home = tmp_path / 'userhome'; home.mkdir()
    calls = tmp_path / 'calls'
    p = run(tmp_path, '--scribe', *(['--check'] if check else []), 'invented task',
            HOME=str(home), STUB_CALLS=str(calls), STUB_TABLE='1', STUB_LOCK='1')
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stderr.splitlines() == ['No healthy scribe; running A and B sequentially on the main librarian.' if check
                                   else 'No healthy scribe; falling back to the main librarian.']
    assert [Path(line).name for line in calls.read_text().splitlines()] == (['A', 'B'] if check else ['A'])
    assert 'FAKE ANSWER' in p.stdout and 'NOISY' not in p.stdout + p.stderr


def test_scribe_fallback_receipt_remains_json_only(tmp_path):
    home = tmp_path / 'userhome'; home.mkdir()
    answer = {**receipt(), 'invented_private_value': 123}
    p = run(tmp_path, '--scribe', '--receipt', 'invented task', HOME=str(home), STUB_ANSWER=json.dumps(answer))
    assert p.returncode == 0 and json.loads(p.stdout) == receipt()
    assert '123' not in p.stdout + p.stderr
    assert p.stderr == 'No healthy scribe; falling back to the main librarian.\n'


def test_scribe_fallback_me_keeps_answer_private(tmp_path):
    home = tmp_path / 'userhome'; home.mkdir()
    p = run(tmp_path, '--scribe', '--me', 'invented task', HOME=str(home))
    assert p.returncode == 0 and p.stdout.startswith('Done')
    assert 'FAKE ANSWER' not in p.stdout + p.stderr
    assert 'FAKE ANSWER' in (tmp_path / 'home/latest.md').read_text()


@pytest.mark.parametrize('error,note', [
    ('error=unsupported call: read', 'invalid tool call or arguments'),
    ('Failed to create unified exec process', 'sandbox execution error'),
    ('', 'no command succeeded'),
])
def test_private_final_reply_retains_session_errors_as_notes(tmp_path, error, note):
    trace = tmp_path / 'args.txt'
    p = run(tmp_path, '--private', 'Return a binding from the inlined facts.',
            STUB_LOG_ERROR=error, STUB_NO_COMMAND='1', STUB_ANSWER='input.table=current', STUB_ARGS=str(trace))
    assert p.returncode == 0 and p.stdout == ''
    rd = runs(tmp_path)[0]
    assert (rd / 'answer.md').read_text() == 'input.table=current\n'
    assert json.loads((rd / 'session-audit.json').read_text()) == {'exit_code': 0, 'note': note}
    assert 'Before answering, execute pwd' not in trace.read_text()
    assert not (tmp_path / 'home/latest.md').exists()
