#!/usr/bin/python3
"""Install the data guard for Claude Code and Codex.

  install.py            create policy if missing, link sanitize-query, register the PreToolUse hook
  install.py --dry-run  show what would change
  install.py --remove   unregister the hook (policy and state are left in place)

Existing hook configs are backed up next to the original before being modified.
"""
import argparse
import json
import os
import shutil
import time

HERE = os.path.dirname(os.path.realpath(__file__))
GUARD = os.path.join(HERE, "guard.py")
HOME = os.path.expanduser("~")
POLICY = os.path.join(HOME, ".config/sanitize-layer/policy.json")
LINK = os.path.join(HOME, ".local/bin/sanitize-query")
TARGETS = [os.path.join(HOME, ".claude/settings.json"), os.path.join(HOME, ".codex/hooks.json")]


def is_guard(h):
    return os.path.basename(h.get("command", "")) == "guard.py" and "sanitize" in h.get("command", "") \
        or h.get("command") == GUARD


def update(path, remove, dry):
    d = json.load(open(path)) if os.path.exists(path) else {}
    pre = d.setdefault("hooks", {}).setdefault("PreToolUse", [])
    kept = [e for e in pre if not any(is_guard(h) for h in e.get("hooks", []))]
    if not remove:
        kept.append({"matcher": "", "hooks": [{"type": "command", "command": GUARD, "timeout": 30}]})
    if kept == pre:
        print(f"unchanged  {path}")
        return
    d["hooks"]["PreToolUse"] = kept
    print(f"{'would update' if dry else 'updated'}  {path}")
    if dry:
        return
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak_data_guard_{time.strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    if not a.remove:
        if os.path.exists(POLICY):
            print(f"kept       {POLICY}")
        else:
            print(f"{'would create' if a.dry_run else 'created'}  {POLICY} (edit its protected paths)")
            if not a.dry_run:
                os.makedirs(os.path.dirname(POLICY), exist_ok=True)
                shutil.copy2(os.path.join(HERE, "policy.example.json"), POLICY)
        if not a.dry_run:
            os.makedirs(os.path.dirname(LINK), exist_ok=True)
            if os.path.islink(LINK) or os.path.exists(LINK):
                os.remove(LINK)
            os.symlink(os.path.join(HERE, "sanitize_query.py"), LINK)
        print(f"{'would link' if a.dry_run else 'linked'}     {LINK} -> {os.path.join(HERE, 'sanitize_query.py')}")
    for t in TARGETS:
        update(t, a.remove, a.dry_run)
    if not a.remove:
        print("Codex runs a new hook only after you approve it; start Codex and approve the PreToolUse hook.")


if __name__ == "__main__":
    main()
