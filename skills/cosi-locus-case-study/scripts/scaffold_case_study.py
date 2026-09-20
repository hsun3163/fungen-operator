#!/usr/bin/env python3
"""Create a non-destructive COSI gene locus case-study packet skeleton."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CASE_TYPES = (
    "concordant_retained_cs",
    "opposing_retained_cs",
    "subthreshold_cs_sensitivity",
    "non_cs_model_evidence",
    "audit_only",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--gene-symbol", required=True)
    parser.add_argument("--gene-id", required=True)
    parser.add_argument("--focal-gwas", required=True)
    parser.add_argument("--case-type", required=True, choices=CASE_TYPES)
    parser.add_argument(
        "--context", action="append", default=[],
        help="Exact eQTL dataset ID; repeat for multiple contexts.",
    )
    parser.add_argument("--chromosome")
    parser.add_argument("--window-start", type=int)
    parser.add_argument("--window-end", type=int)
    parser.add_argument(
        "--output-dir", type=Path,
        help="Default: <repo-root>/analysis/<GENE>.",
    )
    parser.add_argument(
        "--template", type=Path,
        help="Override the bundled JSON template.",
    )
    return parser.parse_args()


def replace_gene_token(value: object, symbol: str) -> object:
    if isinstance(value, str):
        return value.replace("GENE", symbol)
    if isinstance(value, list):
        return [replace_gene_token(item, symbol) for item in value]
    if isinstance(value, dict):
        return {key: replace_gene_token(item, symbol) for key, item in value.items()}
    return value


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    if not repo_root.is_dir():
        raise SystemExit(f"Repository root is not a directory: {repo_root}")

    symbol = args.gene_symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]*", symbol):
        raise SystemExit(f"Unsafe or invalid gene symbol: {args.gene_symbol!r}")
    gene_id = args.gene_id.strip()
    if not re.fullmatch(r"ENSG\d+(?:\.\d+)?", gene_id):
        raise SystemExit(f"Expected an ENSG identifier, received: {gene_id!r}")
    if not args.focal_gwas.strip():
        raise SystemExit("--focal-gwas must be nonempty")

    window_values = (args.chromosome, args.window_start, args.window_end)
    if any(value is not None for value in window_values) and not all(
        value is not None for value in window_values
    ):
        raise SystemExit("Provide chromosome, window-start, and window-end together")
    if args.window_start is not None and args.window_start >= args.window_end:
        raise SystemExit("Plot window start must be smaller than end")

    skill_root = Path(__file__).resolve().parents[1]
    template_path = (
        args.template.expanduser().resolve()
        if args.template
        else skill_root / "assets" / "case_study_config.template.json"
    )
    if not template_path.is_file():
        raise SystemExit(f"Config template is missing: {template_path}")
    with template_path.open(encoding="utf-8") as handle:
        config = replace_gene_token(json.load(handle), symbol)

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else repo_root / "analysis" / symbol
    )
    config_path = output_dir / f"{symbol}_case_study.config.json"
    if config_path.exists():
        raise SystemExit(
            f"Refusing to overwrite existing config: {config_path}. "
            "Edit the existing packet intentionally."
        )

    config["gene"] = {"gene_id": gene_id, "gene_symbol": symbol}
    config["case_type"] = args.case_type
    config["focal_gwas"] = args.focal_gwas.strip()
    config["plot_contexts"] = list(dict.fromkeys(args.context))
    if args.chromosome is not None:
        config["plot_window"] = {
            "chromosome": str(args.chromosome),
            "start": args.window_start,
            "end": args.window_end,
        }

    for name in ("inputs", "figures", "checks", "provenance"):
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    with config_path.open("x", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=False)
        handle.write("\n")

    print(config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
