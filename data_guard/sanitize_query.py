#!/usr/bin/python3
"""Broker for reading protected result data. Everything it prints passes the egress filter.

  sanitize-query run  [--timeout S] SCRIPT_OR_COMMAND [ARGS...]
  sanitize-query ask  [--rows N] "QUESTION" FILE [FILE...]
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
POLICY_PATH = os.environ.get("SANITIZE_POLICY", os.path.join(HOME, ".config/sanitize-layer/policy.json"))
STATE = os.environ.get("SANITIZE_STATE", os.path.join(HOME, ".sanitize-layer"))

ENTITY = re.compile(r"\b(?:ENS[A-Z]*G\d{6,}|rs\d{3,}|chr(?:[0-9]{1,2}|X|Y|M)[:_]\d+)", re.I)
DECIMAL = re.compile(r"(?<![\w.])[-+]?(?:\d+\.\d+(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+|\.\d+)(?![\w.])")
NUMBER = re.compile(r"(?<![\w.])[-+]?(?:\d+\.\d+(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+|\.\d+|\d+)(?![\w.])")
ROW_INDEX = re.compile(r"^\s*\d+:")
WORD = re.compile(r"\b[A-Za-z][A-Za-z0-9\-.]{1,19}\b")
SYMBOL_STOPLIST = {"ALL", "AND", "NOT", "MAX", "MIN", "SET", "END", "TOP", "LOW", "MAP", "CAT", "ACE", "SUN",
                   "TAG", "GAS", "CAR", "PIP", "REST", "IMPACT", "SHE", "ARC", "NET", "SPR", "MET", "FAT", "HR",
                   "TRUE", "FALSE", "DONE", "PASS", "FAIL"}


def redact_entity_line(line):
    """On a line naming a gene/variant: redact decimals and small integers; keep positions, IDs, row indexes."""
    idx = ROW_INDEX.match(line)
    keep_upto = idx.end() if idx else 0
    n = 0

    def sub(m):
        nonlocal n
        tok = m.group(0)
        if m.start() < keep_upto:
            return tok
        if re.fullmatch(r"[-+]?\d+", tok) and abs(int(tok)) >= 1000:
            return tok
        n += 1
        return "<R>"

    return NUMBER.sub(sub, line), n


def load_policy():
    with open(POLICY_PATH) as f:
        return json.load(f)


def load_symbols(eg):
    syms = set()
    col = eg.get("symbol_column", "gene_name")
    for f in eg.get("symbol_files", []):
        try:
            with open(os.path.expanduser(f)) as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    s = (row.get(col) or "").strip()
                    if len(s) >= 3 and s.upper() not in SYMBOL_STOPLIST:
                        syms.add(s)
        except OSError:
            pass
    return syms


def egress(text, policy):
    eg = policy.get("egress", {})
    syms = load_symbols(eg)
    max_lines = eg.get("max_lines", 400)
    max_chars = eg.get("max_chars", 40000)
    max_anon = eg.get("max_anonymous_numeric_lines", 50)
    out, redacted, anon, truncated = [], 0, 0, 0
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if len(out) >= max_lines:
            truncated = len(lines) - i
            break
        has_entity = bool(ENTITY.search(line)) or any(w in syms for w in WORD.findall(line))
        decimals = DECIMAL.findall(line)
        if has_entity:
            line, n = redact_entity_line(line)
            redacted += n
        elif decimals and anon >= max_anon:
            line, n = DECIMAL.subn("<R>", line)
            redacted += n
        elif decimals:
            anon += 1
        out.append(line)
    body = "\n".join(out)
    if len(body) > max_chars:
        truncated += body[max_chars:].count("\n") + 1
        body = body[:max_chars]
    footer = f"[sanitize-query: {len(out)} lines released, {redacted} entity-linked values redacted"
    footer += f", {truncated} lines truncated]" if truncated else "]"
    return body, footer, redacted, truncated


def audit(record, released):
    os.makedirs(STATE, exist_ok=True)
    record["released_sha256"] = hashlib.sha256(released.encode()).hexdigest()
    record["released"] = released
    with open(os.path.join(STATE, "audit.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")


def release(text, policy, record, exit_code=0):
    body, footer, red, trunc = egress(text, policy)
    record.update({"redacted": red, "truncated": trunc})
    audit(record, body)
    if body:
        print(body)
    print(footer, file=sys.stderr)
    sys.exit(exit_code)


def interpreter_for(path):
    ext = os.path.splitext(path)[1].lower()
    return {".r": ["Rscript"], ".py": ["python3"], ".sh": ["bash"]}.get(ext)


def cmd_run(a, policy):
    work = os.path.join(STATE, "work", time.strftime("%Y%m%d_%H%M%S") + f"_{os.getpid()}")
    os.makedirs(os.path.join(work, "tmp"), exist_ok=True)
    first = a.target[0]
    interp = interpreter_for(first) if os.path.isfile(first) else None
    if interp:
        script = os.path.join(work, os.path.basename(first))
        shutil.copyfile(first, script)
        inner = interp + [script] + a.target[1:]
    else:
        inner = ["/bin/bash", "-c", " ".join(a.target)]
    bw = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
          "--bind", work, work, "--unshare-net",
          "--chdir", os.getcwd(), "--setenv", "TMPDIR", os.path.join(work, "tmp"),
          "--setenv", "SANITIZE_WORK", work, "--"]
    env = dict(os.environ)
    env["BASH_ENV"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bash_env.sh")
    t0 = time.time()
    try:
        p = subprocess.run(bw + inner, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=a.timeout or policy.get("run", {}).get("timeout_sec", 3600), env=env)
        text, code = p.stdout.decode("utf-8", "replace"), p.returncode
    except subprocess.TimeoutExpired as e:
        text, code = (e.stdout or b"").decode("utf-8", "replace") + "\n[timed out]", 124
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": "run", "cwd": os.getcwd(),
           "target": a.target, "exit": code, "seconds": round(time.time() - t0, 1), "work": work}
    release(text + (f"\n[exit status {code}]" if code else ""), policy, rec, code)


def open_text(path):
    return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace") \
        if path.endswith(".gz") else open(path, encoding="utf-8", errors="replace")


def describe(path, rows):
    """Local-only context for the model: schema, sample rows, exact per-column summaries."""
    with open_text(path) as fh:
        head = fh.readline()
        if "\t" not in head and "," not in head:
            text = head + "".join(line for _, line in zip(range(rows), fh))
            return f"### {path} (text, first {rows} lines)\n{text}"
        sep = "\t" if "\t" in head else ","
        cols = head.rstrip("\n").split(sep)
        stats = {c: [0, 0, math.inf, -math.inf, 0.0] for c in cols}  # n_num, n_na, min, max, sum
        text_counts = {c: {} for c in cols}
        sample, n = [], 0
        for line in fh:
            n += 1
            vals = line.rstrip("\n").split(sep)
            if len(sample) < rows:
                sample.append(line.rstrip("\n"))
            for c, v in zip(cols, vals):
                s = stats[c]
                try:
                    x = float(v)
                    if math.isfinite(x):
                        s[0] += 1; s[2] = min(s[2], x); s[3] = max(s[3], x); s[4] += x
                    else:
                        s[1] += 1
                except ValueError:
                    if v in ("", "NA", "NaN", "nan", "null"):
                        s[1] += 1
                    else:
                        tc = text_counts[c]
                        if v in tc or len(tc) < 2_000_000:
                            tc[v] = tc.get(v, 0) + 1
    summ = "\n".join(f"{c}\tn={s[0]}\tNA={s[1]}\tmin={s[2]:.6g}\tmax={s[3]:.6g}\tmean={s[4] / s[0]:.6g}"
                     for c, s in stats.items() if s[0])
    tsumm = "\n".join(
        f"{c}\tn_nonmissing={sum(tc.values())}\tn_distinct={len(tc)}\ttop10="
        + ", ".join(f"{k}:{v}" for k, v in sorted(tc.items(), key=lambda kv: -kv[1])[:10])
        for c, tc in text_counts.items() if tc)
    return (f"### {path}\nrows={n}\ncolumns={cols}\nnumeric column summary:\n{summ}\n"
            f"text column summary (exact, whole file):\n{tsumm}\n"
            f"first {len(sample)} rows:\n{head}" + "\n".join(sample))


def cmd_ask(a, policy):
    ol = policy["ollama"]
    ctx = "\n\n".join(describe(f, a.rows) for f in a.files)
    system = ("You are a local data analyst with private access to the data below. Answer the question "
              "accurately and concisely. You may name gene IDs, gene symbols, variant IDs and alleles. "
              "Report counts and aggregate statistics; do not list per-row numeric result values. "
              "If the excerpt is insufficient to answer exactly, say so and say what script would answer it.")
    body = json.dumps({"model": a.model or ol["model"], "stream": False, "think": False,
                       "options": {"num_ctx": ol.get("num_ctx", 65536)},
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": f"{ctx}\n\nQUESTION: {a.question}"}]}).encode()
    req = urllib.request.Request(ol["url"].rstrip("/") + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    t0 = time.time()
    with opener.open(req, timeout=ol.get("timeout_sec", 900)) as r:
        answer = json.load(r)["message"]["content"]
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": "ask", "cwd": os.getcwd(),
           "question": a.question, "files": a.files, "model": a.model or ol["model"],
           "seconds": round(time.time() - t0, 1)}
    release(answer, policy, rec)


def main():
    ap = argparse.ArgumentParser(prog="sanitize-query")
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("run", help="run a script or command against protected data")
    r.add_argument("--timeout", type=int)
    r.add_argument("target", nargs=argparse.REMAINDER)
    q = sub.add_parser("ask", help="ask the local model about protected tables")
    q.add_argument("--rows", type=int, default=200)
    q.add_argument("--model")
    q.add_argument("question")
    q.add_argument("files", nargs="+")
    a = ap.parse_args()
    policy = load_policy()
    if a.mode == "run":
        if not a.target:
            ap.error("run needs a script or command")
        cmd_run(a, policy)
    else:
        cmd_ask(a, policy)


if __name__ == "__main__":
    main()
