#!/usr/bin/env python3
"""Validate the portable structure of a completed COSI locus case-study packet."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from pathlib import Path
from typing import Iterable


TRUE_VALUES = {"true", "t", "1", "yes", "y", "pass", "passed", "ok"}
ALLOWED_EVIDENCE = {
    "retained_95_cs",
    "subthreshold_cs_sensitivity",
    "model_weight_not_cs",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet_dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", newline="") if path.suffix == ".gz" else path.open(
        "r", encoding="utf-8", newline=""
    )


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def first_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    return next((item for item in candidates if item in available), None)


def main() -> int:
    args = parse_args()
    packet = args.packet_dir.expanduser().resolve()
    if not packet.is_dir():
        raise SystemExit(f"Packet directory is missing: {packet}")

    config_path = args.config.expanduser().resolve() if args.config else None
    if config_path is None:
        configs = sorted(packet.glob("*_case_study.config.json"))
        if len(configs) != 1:
            raise SystemExit(f"Expected exactly one case-study config in {packet}; found {len(configs)}")
        config_path = configs[0]
    with config_path.open(encoding="utf-8") as handle:
        config = json.load(handle)

    symbol = str(config.get("gene", {}).get("gene_symbol", "")).strip()
    gene_id = str(config.get("gene", {}).get("gene_id", "")).strip()
    artifacts = config.get("artifacts")
    if not symbol or not re.fullmatch(r"ENSG\d+(?:\.\d+)?", gene_id) or not isinstance(artifacts, dict):
        raise SystemExit("Config lacks a valid gene symbol, ENSG gene_id, or artifacts map")

    checks: list[tuple[str, bool, str]] = []

    def record(name: str, passed: bool, details: str) -> None:
        checks.append((name, bool(passed), str(details)))

    resolved: dict[str, Path] = {}
    for key, relative in artifacts.items():
        path = packet / str(relative)
        resolved[key] = path
        record(f"artifact_exists:{key}", path.is_file(), str(path))
        if path.is_file():
            record(f"artifact_nonempty:{key}", path.stat().st_size > 0, f"{path.stat().st_size} bytes")

    notebook_path = resolved.get("notebook")
    if notebook_path and notebook_path.is_file():
        with notebook_path.open(encoding="utf-8") as handle:
            notebook = json.load(handle)
        kernel = str(notebook.get("metadata", {}).get("kernelspec", {}).get("name", ""))
        code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code" and "".join(cell.get("source", [])).strip()]
        executed = all(cell.get("execution_count") is not None for cell in code_cells)
        errors = [
            output for cell in code_cells for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook.get("cells", []) if cell.get("cell_type") == "markdown"
        ).lower()
        record("notebook_r_kernel", kernel.lower() in {"ir", "irkernel"} or kernel.lower().startswith("ir"), kernel)
        record("notebook_code_executed", bool(code_cells) and executed, f"{len(code_cells)} nonempty code cells")
        record("notebook_no_errors", not errors, f"{len(errors)} error outputs")
        record("notebook_provenance_section", "provenance" in markdown, "markdown provenance heading/text")

    signatures = {
        "svg": b"<svg",
        "pdf": b"%PDF",
        "png": b"\x89PNG\r\n\x1a\n",
    }
    for key, signature in signatures.items():
        path = resolved.get(key)
        if path and path.is_file():
            head = path.read_bytes()[:4096]
            record(f"valid_{key}_signature", signature in head, str(path))

    context_path = resolved.get("context_direction")
    if context_path and context_path.is_file():
        columns, rows = read_tsv(context_path)
        required = {"gene_id", "source_gwas", "source_eqtl"}
        direction = first_column(columns, ("Z_acat", "Z_acat_num"))
        pp = first_column(columns, ("intact_pp", "intact_pp_num"))
        record("context_direction_rows", bool(rows), f"{len(rows)} rows")
        record("context_direction_schema", required.issubset(columns) and direction is not None and pp is not None, ",".join(columns))

    membership_path = resolved.get("cs_membership")
    if membership_path and membership_path.is_file():
        columns, rows = read_tsv(membership_path)
        evidence_col = first_column(columns, ("evidence_type", "evidence_class"))
        variant_col = first_column(columns, ("variant_id", "SNP", "variant"))
        record("evidence_membership_rows", bool(rows), f"{len(rows)} rows")
        record("evidence_membership_schema", evidence_col is not None and variant_col is not None, ",".join(columns))
        if evidence_col:
            values = {row[evidence_col] for row in rows if row.get(evidence_col)}
            record("evidence_types_explicit", bool(values) and values.issubset(ALLOWED_EVIDENCE), ",".join(sorted(values)))

    ld_path = resolved.get("ld_pairs")
    ld_variant_ids: set[str] = set()
    if ld_path and ld_path.is_file():
        columns, rows = read_tsv(ld_path)
        left = first_column(columns, ("variant_id1", "variant1", "SNP_A", "id1"))
        right = first_column(columns, ("variant_id2", "variant2", "SNP_B", "id2"))
        record("ld_pair_schema", left is not None and right is not None, ",".join(columns))
        if left and right:
            pairs: set[tuple[str, str]] = set()
            self_pairs = 0
            for row in rows:
                a, b = row.get(left, ""), row.get(right, "")
                if not a or not b:
                    continue
                ld_variant_ids.update((a, b))
                if a == b:
                    self_pairs += 1
                pairs.add(tuple(sorted((a, b))))
            expected = len(ld_variant_ids) * (len(ld_variant_ids) - 1) // 2
            record("ld_no_self_pairs", self_pairs == 0, f"{self_pairs} self pairs")
            record("ld_pairs_unique", len(pairs) == len(rows), f"{len(pairs)} unique / {len(rows)} rows")
            record("ld_pairs_complete", len(pairs) == expected, f"{len(ld_variant_ids)} variants; {len(pairs)} of {expected} pairs")

    variant_map_path = resolved.get("ld_variant_map")
    if variant_map_path and variant_map_path.is_file():
        columns, rows = read_tsv(variant_map_path)
        variant_col = first_column(columns, ("variant_id", "variant", "SNP"))
        mapped = {row.get(variant_col, "") for row in rows} if variant_col else set()
        record("ld_variant_map_schema", variant_col is not None, ",".join(columns))
        if ld_variant_ids:
            record("ld_variant_map_covers_pairs", ld_variant_ids.issubset(mapped), f"{len(mapped)} mapped; {len(ld_variant_ids)} in LD")

    gene_track_path = resolved.get("gene_track")
    if gene_track_path and gene_track_path.is_file():
        columns, rows = read_tsv(gene_track_path)
        id_col = first_column(columns, ("gene_id",))
        symbol_col = first_column(columns, ("gene_name", "gene_symbol"))
        matches = [
            row for row in rows
            if (id_col and row.get(id_col, "").split(".")[0] == gene_id.split(".")[0])
            or (symbol_col and row.get(symbol_col, "").upper() == symbol.upper())
        ]
        record("focal_gene_unique_in_track", len(matches) == 1, f"{len(matches)} matching rows")

    for key in ("build_checks", "notebook_checks"):
        path = resolved.get(key)
        if path and path.is_file():
            columns, rows = read_tsv(path)
            status_col = first_column(columns, ("pass", "passed", "status", "value"))
            record(f"{key}_rows", bool(rows), f"{len(rows)} rows")
            if status_col:
                failed = [row for row in rows if str(row.get(status_col, "")).strip().lower() not in TRUE_VALUES]
                record(f"{key}_all_pass", not failed, f"{len(failed)} non-passing rows")

    report_path = args.report.expanduser().resolve() if args.report else packet / "checks" / f"{symbol}_packet_validation.tsv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("check", "status", "details"))
        writer.writerows((name, "PASS" if passed else "FAIL", details) for name, passed, details in checks)

    failures = [name for name, passed, _ in checks if not passed]
    print(f"{len(checks) - len(failures)} PASS / {len(failures)} FAIL -> {report_path}")
    if failures:
        print("Failed checks: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
