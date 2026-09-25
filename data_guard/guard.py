#!/usr/bin/python3
"""PreToolUse guard shared by Claude Code and Codex.

Shell commands are rewritten to run under `sbx` (protected paths hidden).
File tools touching protected paths are denied. Any internal error denies.
"""
import json
import os
import re
import shlex
import sys

HOME = os.path.expanduser("~")
POLICY_PATH = os.environ.get("SANITIZE_POLICY", os.path.join(HOME, ".config/sanitize-layer/policy.json"))
HERE = os.path.dirname(os.path.realpath(__file__))
SBX = os.path.join(HERE, "sbx")
DISABLED = os.path.join(os.path.dirname(POLICY_PATH), "DISABLED")
SHELL_OPS = {";", "&&", "||", "|", "&", "|&", ">", ">>", "<", "<<", "<<<", ">|", "&>", "(", ")"}
SHELL_TOOLS = {"Bash", "Monitor", "shell", "local_shell", "exec_command", "unified_exec", "container.exec"}
PATH_TOOLS = {"Read", "NotebookRead", "Edit", "MultiEdit", "Write", "NotebookEdit"}


def emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.exit(0)


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": "[sanitize-layer] " + reason}})


def rewrite(tool_input, decision):
    out = {"hookEventName": "PreToolUse", "updatedInput": tool_input}
    if decision:
        out["permissionDecision"] = decision
    emit({"hookSpecificOutput": out})


def load_policy():
    with open(POLICY_PATH) as f:
        return json.load(f)


def roots_of(paths):
    out = []
    for r in paths:
        r = os.path.expanduser(r)
        for c in (os.path.abspath(r), os.path.realpath(r)):
            if c not in out:
                out.append(c.rstrip("/"))
    return out


def under(path, roots):
    if not path:
        return False
    cands = {os.path.abspath(path), os.path.realpath(path)}
    return any(c == r or c.startswith(r + "/") for c in cands for r in roots)


def contains_root(path, roots):
    p = os.path.realpath(path).rstrip("/")
    return any(r == p or r.startswith(p + "/") for r in roots)


def resolve(p, cwd):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(cwd or os.getcwd(), p)


def strings_in(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings_in(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings_in(v)


SQ_CALL = re.compile(r"(?:^|[\s;&|(`$])(?:\S*/)?sanitize-query\s+(?:run|ask)\b")
PATHISH = re.compile(r"(?:~|\.{1,2})?/[^\s'\"`;|&<>()]+|[\w.\-]+/[^\s'\"`;|&<>()]*")


def mentions_root(text, roots, cwd):
    for m in PATHISH.finditer(text):
        tok = m.group(0)
        if under(resolve(tok, cwd), roots):
            return tok
    return None


def tokens(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def is_standalone(cmd, prog):
    if "$(" in cmd or "`" in cmd or "\n" in cmd.strip():
        return False
    try:
        toks = tokens(cmd)
    except ValueError:
        return False
    return bool(toks) and os.path.basename(toks[0]) == prog and not any(t in SHELL_OPS for t in toks)


def shell_command(tool_input):
    for key in ("command", "cmd"):
        if key in tool_input:
            return key, tool_input[key]
    return None, None


def wrap_string(cmd):
    return f"{SBX} -c {shlex.quote(cmd)}"


def handle_shell(tool, tool_input, cwd, policy, agent):
    key, cmd = shell_command(tool_input)
    if cmd is None:
        deny(f"unrecognised shell input for tool {tool}")
    text = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
    self_roots = roots_of(policy.get("self_paths", []))
    if "SANITIZE_BROKER" in text or mentions_root(text, self_roots, cwd) and not text.lstrip().startswith(SBX):
        if not is_standalone(text, "sanitize-query"):
            deny("commands may not modify or reference the sanitize-layer configuration; ask the user to change it")
    if isinstance(cmd, str):
        if is_standalone(cmd, "sanitize-query"):
            sys.exit(0)
        if SQ_CALL.search(cmd):
            deny("run sanitize-query as a standalone command, not inside a pipeline or compound command")
        if cmd.lstrip().startswith(SBX + " "):
            sys.exit(0)
        new = wrap_string(cmd)
    else:
        argv = [str(a) for a in cmd]
        if argv and os.path.basename(argv[0]) == "sanitize-query":
            sys.exit(0)
        if argv and argv[0] == SBX:
            sys.exit(0)
        if len(argv) >= 3 and os.path.basename(argv[0]) in ("bash", "sh", "zsh") and argv[1] in ("-c", "-lc"):
            if is_standalone(argv[2], "sanitize-query"):
                sys.exit(0)
            if SQ_CALL.search(argv[2]):
                deny("run sanitize-query as a standalone command, not inside a pipeline or compound command")
            new = argv[:2] + [wrap_string(argv[2])] + argv[3:]
        else:
            new = [SBX, "--"] + argv
    mode = policy.get("agent_mode", {}).get(agent, "rewrite")
    if mode == "require-prefix":
        deny(f"prefix shell commands with the sandbox wrapper, e.g. {SBX} -c '<command>'")
    updated = dict(tool_input)
    updated[key] = new
    rewrite(updated, policy.get("rewrite_decision", {}).get(agent))


def handle_path_tool(tool, tool_input, cwd, roots, self_roots):
    p = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
    if not p:
        sys.exit(0)
    full = resolve(p, cwd)
    if under(full, roots):
        deny(f"{p} is protected result data; use `sanitize-query run <script>` or `sanitize-query ask '<question>' <files>`")
    if tool not in ("Read", "NotebookRead") and under(full, self_roots):
        deny("the sanitize-layer configuration can only be changed by the user")
    sys.exit(0)


def handle_grep(tool_input, cwd, roots):
    p = resolve(tool_input.get("path") or cwd or ".", cwd)
    if under(p, roots) or contains_root(p, roots):
        deny("this search would read protected result data; narrow the path to exclude protected directories, "
             "use shell grep (protected directories appear empty), or use sanitize-query")
    sys.exit(0)


def main():
    if os.path.exists(DISABLED) or os.environ.get("SANITIZE_BROKER") == "1":
        sys.exit(0)
    data = json.load(sys.stdin)
    policy = load_policy()
    roots = roots_of(policy.get("protected", []))
    self_roots = roots_of(policy.get("self_paths", []))
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    agent = "codex" if "turn_id" in data else "claude"

    if not isinstance(tool_input, dict):
        tool_input = {"input": tool_input}
    if tool in SHELL_TOOLS or ("command" in tool_input or "cmd" in tool_input) and tool not in PATH_TOOLS:
        handle_shell(tool, tool_input, cwd, policy, agent)
    if tool in PATH_TOOLS:
        handle_path_tool(tool, tool_input, cwd, roots, self_roots)
    if tool == "Grep":
        handle_grep(tool_input, cwd, roots)
    if tool in ("Glob", "LS"):
        sys.exit(0)
    for s in strings_in(tool_input):
        hit = mentions_root(s, roots, cwd)
        if hit:
            deny(f"{tool} input references protected result data ({hit}); use sanitize-query")
        if tool == "apply_patch" and mentions_root(s, self_roots, cwd):
            deny("the sanitize-layer configuration can only be changed by the user")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        deny(f"guard error, blocking for safety: {type(e).__name__}: {e}")
