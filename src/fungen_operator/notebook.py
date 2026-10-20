"""Notebook is the recipe and history; no separate execution ledger."""

from __future__ import annotations

import copy
import fcntl
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import nbformat

from .actions import VERSION, render


def now():
    return datetime.now(timezone.utc).isoformat()


def active(nb):
    return [c for c in nb.cells if c.cell_type == "code" and "superseded" not in c.metadata.get("tags", [])]


def verify(nb):
    seen = set()
    for cell in active(nb):
        meta = cell.metadata.get("fungen", {})
        if meta.get("template_version") != VERSION:
            raise ValueError(f"unknown template version in cell {cell.id}")
        if cell.source != render(meta["action"], meta["slots"]):
            raise ValueError(f"cell {cell.id} does not re-render exactly")
        key = recipe_key(meta)
        if key in seen:
            raise ValueError(f"duplicate active recipe position: {key}")
        seen.add(key)


def recipe_key(meta):
    action = meta["action"]
    if action == "control_run":
        from .live_control import approval_fingerprint
        return action + ":" + approval_fingerprint(meta["slots"]["arguments"], meta["slots"]["bindings"])
    if action == "check_readiness":
        return action + ":" + meta["slots"]["arguments"]["phase"]
    return action


ORDER = {"prepare_config": 0, "check_readiness:before_run": 1,
         "initiate_run": 2, "check_readiness:conclusion": 3}


class Notebook:
    def __init__(self, path: str):
        self.path = Path(path)

    def read(self):
        if self.path.exists():
            nb = nbformat.read(self.path, as_version=4)
            verify(nb)
            return nb
        return nbformat.v4.new_notebook(metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "fungen": {"format_version": 1},
        }, cells=[nbformat.v4.new_markdown_cell(
            "# Fungen Operator\n\nActive cells below form the current recipe. "
            "Use `fungen-operator replay` to execute them in order. "
            "Superseded attempts retain their original outputs in the history section."
        )])

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Lock is coordination only, not a second execution ledger.
        with open(str(self.path) + ".lock", "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def save(self, nb):
        verify(nb)
        nbformat.validate(nb)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".notebook-")
        try:
            with os.fdopen(fd, "w") as stream:
                nbformat.write(nb, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def append(self, nb, action, slots, identity, cell_id, approval=None):
        meta = {"action": action, "template_version": VERSION, "slots": copy.deepcopy(slots),
                "identity": identity, "created": now(), "status": "prepared",
                "approval": approval, "sequence": 1 + max(
                    (c.metadata.get("fungen", {}).get("sequence", 0) for c in nb.cells), default=0)}
        superseded = []
        key = recipe_key(meta)
        for prior in active(nb):
            p = prior.metadata.fungen
            if (action == "prepare_config" or recipe_key(p) == key
                    or (action == "initiate_run" and recipe_key(p) == "check_readiness:conclusion")
                    or (key == "check_readiness:before_run" and recipe_key(p) in
                        {"initiate_run", "check_readiness:conclusion"})):
                prior.metadata.setdefault("tags", []).append("superseded")
                p["superseded_by"] = cell_id
                superseded.append(prior.id)
        meta["supersedes"] = superseded
        cell = nbformat.v4.new_code_cell(render(action, slots), metadata={
            "tags": ["fungen-action"], "fungen": meta}, id=cell_id)
        nb.cells.append(cell)
        intro = [c for c in nb.cells if c.cell_type != "code" and not c.metadata.get("fungen_history_heading")]
        current = sorted(active(nb), key=lambda c: ORDER.get(recipe_key(c.metadata.fungen), 2.5))
        history = sorted([c for c in nb.cells if c.cell_type == "code" and c not in current],
                         key=lambda c: c.metadata.fungen.sequence)
        heading = nbformat.v4.new_markdown_cell("## Superseded attempts\n\nRetained history; excluded from replay.",
                                               metadata={"fungen_history_heading": True})
        nb.cells = intro + current + ([heading] + history if history else [])
        self.save(nb)
        return cell
