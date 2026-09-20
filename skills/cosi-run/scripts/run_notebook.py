#!/usr/bin/env python3
"""Create and update a small, auditable COSI Snakemake run notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path_text: str | None) -> str:
    if not path_text:
        return "not supplied"
    path = Path(path_text).expanduser()
    if not path.is_file():
        return "missing"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_run_path(path_text: str, cwd: Path) -> str:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return str(path.resolve())


def git_value(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return result.stdout.strip() or "clean"
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def bullet_lines(values: list[str], empty: str = "not specified") -> str:
    return "\n".join(f"- `{value}`" for value in values) if values else f"- {empty}"


def write_notebook(path: Path, notebook: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(notebook, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_notebook(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        notebook = json.load(handle)
    if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
        raise ValueError(f"Not a supported v4 notebook: {path}")
    return notebook


def set_display_status(notebook: dict, status: str) -> None:
    """Keep the visible notebook status aligned with machine-readable metadata."""
    cells = notebook.get("cells", [])
    if cells and cells[0].get("cell_type") == "markdown":
        source = "".join(cells[0].get("source", []))
        lines = source.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("**Run status:**"):
                ending = "\n" if line.endswith("\n") else ""
                lines[index] = f"**Run status:** {status.upper()}  {ending}"
                cells[0]["source"] = lines
                break


def init_notebook(args: argparse.Namespace) -> None:
    output = Path(args.output).expanduser()
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite existing notebook: {output}")

    cwd = Path(args.cwd).expanduser().resolve()
    config = resolve_run_path(args.config, cwd)
    snakefile = resolve_run_path(args.snakefile, cwd)
    source_config = resolve_run_path(args.source_config, cwd) if args.source_config else "same as run config"
    dirty = git_value(cwd, "status", "--short", "--untracked-files=no")
    cells = [
        markdown(f"# {args.title}\n\n**Run status:** PREPARED  \n**Created:** {now()}\n"),
        markdown(
            "## Run contract\n\n"
            f"**Objective:** {args.objective or 'Complete the declared COSI Snakemake targets.'}\n\n"
            "**Targets**\n\n"
            f"{bullet_lines(args.target)}\n\n"
            "**Expected outputs / checks**\n\n"
            f"{bullet_lines(args.expected_output)}\n"
        ),
        markdown(
            "## Provenance\n\n"
            f"- Working directory: `{cwd}`\n"
            f"- Git commit: `{git_value(cwd, 'rev-parse', 'HEAD')}`\n"
            f"- Tracked dirty state: `{dirty}`\n"
            f"- Source config: `{source_config}`\n"
            f"- Run config: `{config}`\n"
            f"- Run config SHA256: `{sha256(config)}`\n"
            f"- Snakefile: `{snakefile}`\n"
            f"- Snakefile SHA256: `{sha256(snakefile)}`\n"
            f"- Snakemake driver log: `{args.driver_log or 'not supplied'}`\n"
        ),
        markdown(
            "## Exact commands\n\n"
            "### Dry-run\n\n"
            f"```bash\n{args.dry_run_command}\n```\n\n"
            "### Submission\n\n"
            f"```bash\n{args.submit_command}\n```\n"
        ),
        markdown(
            "## Execution ledger\n\n"
            "Append submission, scheduler, recovery, and completion evidence below.\n"
        ),
    ]
    if args.notes:
        cells.append(markdown(f"## Preparation notes\n\n{args.notes}\n"))

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "R", "language": "R", "name": "ir"},
            "language_info": {"name": "R"},
            "cosi_run": {"status": "prepared", "created": now()},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    write_notebook(output, notebook)


def append_entry(args: argparse.Namespace) -> None:
    path = Path(args.notebook).expanduser()
    notebook = read_notebook(path)
    notebook["cells"].append(markdown(f"## {args.heading}\n\n**Recorded:** {now()}\n\n{args.body}\n"))
    metadata = notebook.setdefault("metadata", {}).setdefault("cosi_run", {})
    metadata["updated"] = now()
    if args.status:
        metadata["status"] = args.status
        set_display_status(notebook, args.status)
    write_notebook(path, notebook)


def finalize_notebook(args: argparse.Namespace) -> None:
    path = Path(args.notebook).expanduser()
    notebook = read_notebook(path)
    evidence = bullet_lines(args.evidence, empty="No evidence supplied")
    notebook["cells"].append(
        markdown(
            "## Final outcome\n\n"
            f"**Outcome:** {args.outcome.upper()}  \n"
            f"**Recorded:** {now()}\n\n"
            f"{args.summary}\n\n"
            "**Evidence**\n\n"
            f"{evidence}\n"
        )
    )
    metadata = notebook.setdefault("metadata", {}).setdefault("cosi_run", {})
    metadata["status"] = args.outcome
    metadata["updated"] = now()
    set_display_status(notebook, args.outcome)
    write_notebook(path, notebook)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a run ledger notebook")
    init.add_argument("--output", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--cwd", required=True)
    init.add_argument("--config", required=True)
    init.add_argument("--source-config")
    init.add_argument("--snakefile", required=True)
    init.add_argument("--dry-run-command", required=True)
    init.add_argument("--submit-command", required=True)
    init.add_argument("--driver-log", "--controller-log", dest="driver_log")
    init.add_argument("--objective")
    init.add_argument("--target", action="append", default=[])
    init.add_argument("--expected-output", action="append", default=[])
    init.add_argument("--notes")
    init.add_argument("--overwrite", action="store_true")
    init.set_defaults(function=init_notebook)

    append = subparsers.add_parser("append", help="Append a timestamped ledger entry")
    append.add_argument("--notebook", required=True)
    append.add_argument("--heading", required=True)
    append.add_argument("--body", required=True)
    append.add_argument(
        "--status",
        choices=("prepared", "submitted", "running", "recovering"),
        help="Also update the visible and machine-readable run status",
    )
    append.set_defaults(function=append_entry)

    finalize = subparsers.add_parser("finalize", help="Record the terminal run outcome")
    finalize.add_argument("--notebook", required=True)
    finalize.add_argument("--outcome", required=True, choices=("completed", "failed", "blocked"))
    finalize.add_argument("--summary", required=True)
    finalize.add_argument("--evidence", action="append", default=[])
    finalize.set_defaults(function=finalize_notebook)

    return root


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
