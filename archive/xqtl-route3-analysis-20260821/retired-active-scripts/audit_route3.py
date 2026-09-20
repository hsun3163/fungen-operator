#!/usr/bin/env python3
"""Read-only audit of concrete MESA Route3 stage outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


def nonempty(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def newest(paths: list[Path]) -> Path | None:
    candidates = [path for path in paths if path.exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def rel(path: Path | None, root: Path) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def manifest_paths(path: Path | None) -> tuple[int, int]:
    if not nonempty(path):
        return 0, 0
    rows = 0
    missing = 0
    assert path is not None
    with path.open(newline="") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            candidate = fields[-1].strip()
            if candidate.lower() in {"path", "#path"}:
                continue
            rows += 1
            if not Path(candidate).is_file():
                missing += 1
    return rows, missing


def region_keys(path: Path | None) -> tuple[set[str], int]:
    """Return canonical chromosome_gene keys and duplicate-row count."""
    if not nonempty(path):
        return set(), 0
    assert path is not None
    keys: list[str] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            return set(), 0
        chrom_field = "#chr" if "#chr" in reader.fieldnames else "chr"
        id_field = "ID" if "ID" in reader.fieldnames else "gene_id"
        if chrom_field not in reader.fieldnames or id_field not in reader.fieldnames:
            return set(), 0
        for row in reader:
            chrom = (row.get(chrom_field) or "").strip()
            region_id = (row.get(id_field) or "").strip()
            if chrom and region_id:
                keys.append(f"{chrom}_{region_id}")
    unique = set(keys)
    return unique, len(keys) - len(unique)


def artifact_inventory(
    directory: Path, expected_names: set[str]
) -> tuple[int, int, int]:
    """Return nonempty file count, missing expected count, and stale extra count."""
    actual_names = (
        {path.name for path in directory.glob("*.rds") if nonempty(path)}
        if directory.is_dir()
        else set()
    )
    return (
        len(actual_names),
        len(expected_names - actual_names),
        len(actual_names - expected_names),
    )


def plink_trio(prefix: Path | None) -> bool:
    if prefix is None:
        return False
    return all(nonempty(Path(f"{prefix}.{ext}")) for ext in ("bed", "bim", "fam"))


def shared_genotype(root: Path) -> dict[str, Any]:
    genotype_dir = root / "data_preprocessing" / "genotype"
    beds = sorted(genotype_dir.glob("*.plink_qc.bed"))
    bed = newest(beds)
    prefix = Path(str(bed)[:-4]) if bed else None
    manifest = newest(sorted(genotype_dir.glob("*.genotype_by_chrom_files.txt")))
    manifest_rows, manifest_missing = manifest_paths(manifest)
    return {
        "plink_prefix": rel(prefix, root),
        "plink_trio": plink_trio(prefix),
        "chrom_manifest": rel(manifest, root),
        "chrom_rows": manifest_rows,
        "chrom_missing": manifest_missing,
    }


def context_record(root: Path, context_dir: Path) -> dict[str, Any]:
    context = context_dir.name
    genotype_dir = context_dir / "genotype_data"
    phenotype_dir = context_dir / "phenotype_data"
    covariate_dir = context_dir / "covariates"
    tensor_dir = root / "association_scan" / context / "TensorQTL"
    susie_dir = root / "finemapping" / context / "susie_twas"

    sample_genotypes = newest(sorted(genotype_dir.glob("*.sample_genotypes.txt")))
    sample_overlap = newest(sorted(genotype_dir.glob("*.sample_overlap.txt")))
    phenotype_manifests = [
        path
        for path in phenotype_dir.glob("*.phenotype_by_chrom_files.txt")
        if ".region_list." not in path.name
    ]
    phenotype_manifest = newest(sorted(phenotype_manifests))
    phenotype_rows, phenotype_missing = manifest_paths(phenotype_manifest)
    region_list = newest(
        sorted(phenotype_dir.glob("*.phenotype_by_chrom_files.region_list.txt"))
    )
    expected_regions, region_duplicates = region_keys(region_list)
    covariate = newest(sorted(covariate_dir.glob("*.Marchenko_PC.gz")))
    tensor_summary = newest(
        sorted(tensor_dir.glob("*.cis_qtl_regional_significance.summary.txt"))
    )

    expected_fine = {
        f"{context}.{key}.univariate_bvsr.rds" for key in expected_regions
    }
    expected_twas = {
        f"{context}.{key}.univariate_twas_weights.rds" for key in expected_regions
    }
    fine_count, fine_missing, fine_extra = artifact_inventory(
        susie_dir / "fine_mapping", expected_fine
    )
    twas_count, twas_missing, twas_extra = artifact_inventory(
        susie_dir / "twas_weights", expected_twas
    )

    return {
        "context": context,
        "sample_genotypes": nonempty(sample_genotypes),
        "sample_overlap": nonempty(sample_overlap),
        "phenotype_manifest": rel(phenotype_manifest, root),
        "phenotype_rows": phenotype_rows,
        "phenotype_missing": phenotype_missing,
        "region_list": rel(region_list, root),
        "region_expected": len(expected_regions),
        "region_duplicates": region_duplicates,
        "covariate": rel(covariate, root),
        "covariate_ok": nonempty(covariate),
        "tensor_marker": (tensor_dir / ".done_cis").is_file(),
        "tensor_summary": nonempty(tensor_summary),
        "susie_marker": (susie_dir / ".done_susie_twas").is_file(),
        "fine_rds": fine_count,
        "fine_missing": fine_missing,
        "fine_extra": fine_extra,
        "twas_rds": twas_count,
        "twas_missing": twas_missing,
        "twas_extra": twas_extra,
    }


def record_ok(record: dict[str, Any]) -> bool:
    return all(
        (
            record["sample_genotypes"],
            record["sample_overlap"],
            record["phenotype_rows"] > 0,
            record["phenotype_missing"] == 0,
            record["region_expected"] > 0,
            record["region_duplicates"] == 0,
            record["covariate_ok"],
            record["tensor_marker"],
            record["tensor_summary"],
            record["susie_marker"],
            record["fine_missing"] == 0,
            record["twas_missing"] == 0,
        )
    )


def print_tsv(shared: dict[str, Any], records: list[dict[str, Any]]) -> None:
    print(
        "shared_genotype\t"
        f"plink_trio={shared['plink_trio']}\t"
        f"chrom_rows={shared['chrom_rows']}\t"
        f"chrom_missing={shared['chrom_missing']}\t"
        f"prefix={shared['plink_prefix']}"
    )
    fields = [
        "context",
        "sample_genotypes",
        "sample_overlap",
        "phenotype_rows",
        "phenotype_missing",
        "region_expected",
        "region_duplicates",
        "covariate_ok",
        "tensor_marker",
        "tensor_summary",
        "susie_marker",
        "fine_rds",
        "fine_missing",
        "fine_extra",
        "twas_rds",
        "twas_missing",
        "twas_extra",
        "verified_complete",
    ]
    writer = csv.DictWriter(os.sys.stdout, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    for record in records:
        row = {field: record.get(field, "") for field in fields}
        row["verified_complete"] = record_ok(record)
        writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Route3 work root")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--strict", action="store_true", help="exit nonzero when required evidence is incomplete"
    )
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Route3 root does not exist: {root}")

    shared = shared_genotype(root)
    preprocessing = root / "data_preprocessing"
    context_dirs = sorted(
        path for path in preprocessing.glob("mesa_*") if path.is_dir()
    )
    records = [context_record(root, path) for path in context_dirs]

    if args.json:
        print(json.dumps({"root": str(root), "shared": shared, "contexts": records}, indent=2))
    else:
        print_tsv(shared, records)

    incomplete = (
        not shared["plink_trio"]
        or shared["chrom_rows"] == 0
        or shared["chrom_missing"] > 0
        or not records
        or any(not record_ok(record) for record in records)
    )
    return 1 if args.strict and incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
