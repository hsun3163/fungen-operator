"""Tests for the data guard. Run: python3 -m pytest data_guard/tests"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

DG = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
GUARD = os.path.join(DG, "guard.py")
SBX = os.path.join(DG, "sbx")
SQ = os.path.join(DG, "sanitize_query.py")
HAVE_BWRAP = shutil.which("bwrap") is not None and subprocess.run(
    ["bwrap", "--dev-bind", "/", "/", "true"], capture_output=True).returncode == 0


@pytest.fixture()
def env(tmp_path):
    proj = tmp_path / "proj"
    (proj / "results").mkdir(parents=True)
    (proj / "results" / "table.tsv").write_text("gene\tpp\nENSG00000136717\t0.97\n")
    (proj / "code").mkdir()
    (proj / "code" / "a.r").write_text("x\n")
    (proj / "inputs").mkdir()
    (proj / "inputs" / "sumstats.tsv").write_text("id\tbeta\nrs429358\t0.1\n")
    conf = tmp_path / "conf"
    conf.mkdir()
    state = tmp_path / "state"
    policy = {"protected": [str(proj / "results"), str(state)],
              "self_paths": [str(conf), DG],
              "egress": {"max_lines": 50, "max_anonymous_numeric_lines": 5}}
    (conf / "policy.json").write_text(json.dumps(policy))
    e = dict(os.environ, SANITIZE_POLICY=str(conf / "policy.json"), SANITIZE_STATE=str(state))
    e.pop("SANITIZE_BROKER", None)
    return {"proj": proj, "conf": conf, "state": state, "env": e}


def call(env, tool, tool_input, codex=False, cwd=None, extra=None):
    payload = {"session_id": "t", "transcript_path": None, "cwd": str(cwd or env["proj"]),
               "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
               "tool_use_id": "x", "permission_mode": "default"}
    if codex:
        payload.update({"turn_id": "t1", "model": "m"})
    p = subprocess.run([sys.executable, GUARD], input=json.dumps(payload).encode(),
                       capture_output=True, env=dict(env["env"], **(extra or {})))
    out = json.loads(p.stdout) if p.stdout.strip() else {}
    hso = out.get("hookSpecificOutput", {})
    if hso.get("permissionDecision") == "deny":
        return "deny", hso.get("permissionDecisionReason")
    if "updatedInput" in hso:
        return "rewrite", hso["updatedInput"]
    return "pass", None


@pytest.mark.parametrize("tool,inp,codex,want", [
    ("Bash", {"command": "cat results/table.tsv"}, False, "rewrite"),
    ("Bash", {"command": "D=results; cat $D/*"}, False, "rewrite"),
    ("Bash", {"command": "sanitize-query run check.R"}, False, "pass"),
    ("Bash", {"command": "sanitize-query run x.R | cat"}, False, "deny"),
    ("Bash", {"command": "echo $(sanitize-query run x.R)"}, False, "deny"),
    ("Bash", {"command": "cd x && ~/.local/bin/sanitize-query ask 'q' f"}, False, "deny"),
    ("Bash", {"command": "git commit -m 'document sanitize-query, its run/ask modes' && git log -1"}, False, "rewrite"),
    ("Bash", {"command": "SANITIZE_BROKER=1 cat x"}, False, "deny"),
    ("Monitor", {"command": "tail -f log"}, False, "rewrite"),
    ("Read", {"file_path": "results/table.tsv"}, False, "deny"),
    ("Read", {"file_path": "inputs/sumstats.tsv"}, False, "pass"),
    ("Read", {"file_path": "code/a.r"}, False, "pass"),
    ("Write", {"file_path": "results/new.tsv", "content": "x"}, False, "deny"),
    ("Grep", {"pattern": "x"}, False, "deny"),
    ("Grep", {"pattern": "x", "path": "code"}, False, "pass"),
    ("Glob", {"pattern": "**/*.tsv"}, False, "pass"),
    ("mcp__x__read", {"uri": "results/table.tsv"}, False, "deny"),
    ("exec_command", {"cmd": "cat results/table.tsv"}, True, "rewrite"),
    ("shell", {"command": ["bash", "-lc", "cat results/table.tsv"]}, True, "rewrite"),
    ("shell", {"command": ["cat", "results/table.tsv"]}, True, "rewrite"),
    ("shell", {"command": ["bash", "-lc", "sanitize-query run a.R"]}, True, "pass"),
    ("apply_patch", {"input": "*** Begin Patch\n*** Update File: results/table.tsv\n"}, True, "deny"),
    ("apply_patch", {"input": "*** Begin Patch\n*** Update File: code/a.r\n"}, True, "pass"),
])
def test_guard_decisions(env, tool, inp, codex, want):
    assert call(env, tool, inp, codex)[0] == want


def test_rewrite_shapes(env):
    _, v = call(env, "Bash", {"command": "ls"})
    assert v["command"].startswith(SBX + " -c ")
    _, v = call(env, "shell", {"command": ["bash", "-lc", "ls"]}, codex=True)
    assert v["command"][:2] == ["bash", "-lc"] and v["command"][2].startswith(SBX)
    _, v = call(env, "shell", {"command": ["ls", "-l"]}, codex=True)
    assert v["command"][:2] == [SBX, "--"]


def test_config_is_self_protected(env):
    assert call(env, "Write", {"file_path": str(env["conf"] / "policy.json"), "content": "{}"})[0] == "deny"
    assert call(env, "Bash", {"command": f"touch {env['conf']}/DISABLED"})[0] == "deny"
    assert call(env, "Read", {"file_path": str(env["conf"] / "policy.json")})[0] == "pass"


def test_kill_switch_and_fail_closed(env):
    (env["conf"] / "DISABLED").write_text("")
    assert call(env, "Read", {"file_path": "results/table.tsv"})[0] == "pass"
    (env["conf"] / "DISABLED").unlink()
    assert call(env, "Read", {"file_path": "/etc/hosts"}, extra={"SANITIZE_POLICY": "/nonexistent.json"})[0] == "deny"


def load_sq(env):
    os.environ["SANITIZE_STATE"] = str(env["state"])
    spec = importlib.util.spec_from_file_location("sanitize_query", SQ)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("line,expect", [
    ("chr19:44905791 A/G beta 0.12 n=3", "chr19:44905791 A/G beta <R> n=<R>"),
    ("ENSG00000136717 5465 snps z=5 p=1e-8", "ENSG00000136717 5465 snps z=<R> p=<R>"),
    ("rs429358 T C 0.15", "rs429358 T C <R>"),
    ("1: ENSG00000136717 BIN1 0.97 1", "1: ENSG00000136717 BIN1 <R> <R>"),
    ("genes passing 814 mean 0.43", "genes passing 814 mean 0.43"),
])
def test_egress_entity_lines(env, line, expect):
    sq = load_sq(env)
    assert sq.egress(line, {"egress": {}})[0] == expect


def test_egress_anonymous_numeric_cap_and_truncation(env):
    sq = load_sq(env)
    text = "\n".join(f"value {i}.5" for i in range(10))
    body, _, red, _ = sq.egress(text, {"egress": {"max_anonymous_numeric_lines": 5}})
    assert red == 5 and body.splitlines()[-1] == "value <R>"
    body, footer, _, trunc = sq.egress("\n".join(["x"] * 30), {"egress": {"max_lines": 10}})
    assert trunc == 20 and "truncated" in footer


@pytest.mark.skipif(not HAVE_BWRAP, reason="bubblewrap unavailable")
def test_sbx_hides_protected(env):
    p = subprocess.run([SBX, "-c", "ls results | wc -l; cat inputs/sumstats.tsv | wc -l; exit 3"],
                       cwd=env["proj"], env=env["env"], capture_output=True, text=True)
    assert p.stdout.split() == ["0", "2"] and p.returncode == 3


@pytest.mark.skipif(not HAVE_BWRAP, reason="bubblewrap unavailable")
def test_run_mode_filters_and_isolates(env):
    script = env["proj"] / "code" / "q.sh"
    script.write_text(
        "cat results/table.tsv\n"
        "echo leak > code/leak.txt 2>/dev/null && echo WRITE-OK || echo write-blocked\n"
        "echo ok > \"$SANITIZE_WORK/out.txt\" && echo work-ok\n")
    p = subprocess.run([sys.executable, SQ, "run", str(script)], cwd=env["proj"], env=env["env"],
                       capture_output=True, text=True)
    assert "ENSG00000136717\t<R>" in p.stdout
    assert "write-blocked" in p.stdout and "work-ok" in p.stdout
    assert not (env["proj"] / "code" / "leak.txt").exists()
    log = (env["state"] / "audit.jsonl").read_text().splitlines()
    assert json.loads(log[-1])["redacted"] == 1
