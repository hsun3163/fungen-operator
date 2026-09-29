import os
import subprocess
from pathlib import Path

LIBRARIAN = Path(__file__).resolve().parents[1] / "librarian"

STUB = """#!/bin/sh
echo "NOISY tool output: secret-row-42"
echo "NOISY stderr" >&2
[ -n "$STUB_ARGS" ] && printf '%s\\n' "$@" > "$STUB_ARGS"
while [ $# -gt 0 ]; do
    [ "$1" = -o ] && out=$2
    shift
done
[ -n "$STUB_FAIL" ] && exit 3
printf '%s\\n' "${STUB_ANSWER:-FAKE ANSWER}" > "$out"
"""


def run(tmp_path, *args, fail=False, **extra):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "codex"
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


def test_default_mode_prints_only_answer(tmp_path):
    p = run(tmp_path, "task")
    assert p.returncode == 0
    assert p.stdout == "FAKE ANSWER\n"
    assert p.stderr == ""
    (rd,) = runs(tmp_path)
    assert "-agent-" in rd.name
    assert "NOISY tool output" in (rd / "log").read_text()
    assert (rd / "task").read_text() == "task\n"


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
