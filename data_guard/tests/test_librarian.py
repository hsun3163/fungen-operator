import os
import subprocess
from pathlib import Path

LIBRARIAN = Path(__file__).resolve().parents[1] / "librarian"

STUB = """#!/bin/sh
echo "NOISY tool output: secret-row-42"
echo "NOISY stderr" >&2
while [ $# -gt 0 ]; do
    [ "$1" = -o ] && out=$2
    shift
done
[ -n "$STUB_FAIL" ] && exit 3
printf 'FAKE ANSWER\\n' > "$out"
"""


def run(tmp_path, *args, fail=False):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "codex"
    stub.write_text(STUB)
    stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", LIBRARIAN_HOME=str(tmp_path / "home"))
    env.pop("STUB_FAIL", None)
    if fail:
        env["STUB_FAIL"] = "1"
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
