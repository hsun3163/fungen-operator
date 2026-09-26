#!/usr/bin/env python3
"""Create the 500-sample behavioral MWE with native PLINK and exact trait slicing."""

import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/sketch_to_plink1/behavioral_fixture"
OUTPUT = ROOT / "output/sketch_to_plink1/behavioral_fixture_500"
PLINK = Path("/sc/arion/work/sunh14/conda/envs/py3.11/bin/plink")
BIN = Path("/sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin")
SAMPLES = 500
FILES = ["genotype.bed", "genotype.bim", "genotype.fam",
         "traits/phenotypes.bed.gz", "traits/phenotypes.bed.gz.tbi",
         "traits/covariates.cov.gz"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_table(path, metadata_columns, source_ids):
    with gzip.open(path, "rt") as stream:
        rows = [line.rstrip("\n").split("\t") for line in stream]
    if rows[0][metadata_columns:] != source_ids:
        raise ValueError(f"Source sample order differs from FAM: {path}")
    if any(len(row) != metadata_columns + len(source_ids) for row in rows):
        raise ValueError(f"Ragged source table: {path}")
    return ["\t".join(row[:metadata_columns + SAMPLES]) + "\n" for row in rows]


def main():
    before = {name: sha256(SOURCE / name) for name in FILES}
    fam = [line.split() for line in (SOURCE / "genotype.fam").read_text().splitlines()]
    if len(fam) < SAMPLES or SAMPLES % 4:
        raise ValueError("Expected at least 500 samples and a whole number of BED bytes")
    ids = [row[1] for row in fam]
    if len(set(ids)) != len(ids) or not all(s.startswith("SYN_EUR_") for s in ids):
        raise ValueError("Expected unique synthetic fixture identifiers")
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT / "traits").mkdir()
    keep = OUTPUT / "samples.keep"
    keep.write_text("".join(f"{row[0]}\t{row[1]}\n" for row in fam[:SAMPLES]))
    command = [str(PLINK), "--bfile", str(SOURCE / "genotype"), "--keep", str(keep),
               "--make-bed", "--keep-allele-order", "--indiv-sort", "none",
               "--memory", "32768", "--threads", "1", "--out", str(OUTPUT / "genotype")]
    subprocess.run(command, check=True)

    phenotype = project_table(SOURCE / "traits/phenotypes.bed.gz", 4, ids)
    covariate = project_table(SOURCE / "traits/covariates.cov.gz", 1, ids)
    bed = OUTPUT / "traits/phenotypes.bed.gz"
    with bed.open("wb") as stream:
        subprocess.run([str(BIN / "bgzip"), "-c"], input="".join(phenotype).encode(),
                       stdout=stream, check=True)
    subprocess.run([str(BIN / "tabix"), "-p", "bed", str(bed)], check=True)
    cov = OUTPUT / "traits/covariates.cov.gz"
    with cov.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write("".join(covariate).encode())

    # Validate native PLINK output against the parent calls, alleles, and order.
    observed_fam = [line.split() for line in (OUTPUT / "genotype.fam").read_text().splitlines()]
    if observed_fam != fam[:SAMPLES]:
        raise ValueError("PLINK changed the requested FAM rows or order")
    bim = [line.split() for line in (SOURCE / "genotype.bim").read_text().splitlines()]
    if [line.split() for line in (OUTPUT / "genotype.bim").read_text().splitlines()] != bim:
        raise ValueError("PLINK changed variant order or allele orientation")
    source_width, width = (len(fam) + 3) // 4, SAMPLES // 4
    with (SOURCE / "genotype.bed").open("rb") as parent, (OUTPUT / "genotype.bed").open("rb") as child:
        if parent.read(3) != b"\x6c\x1b\x01" or child.read(3) != b"\x6c\x1b\x01":
            raise ValueError("Expected SNP-major PLINK BED")
        for _ in bim:
            block, selected = parent.read(source_width), child.read(width)
            if len(block) != source_width or len(selected) != width or selected != block[:width]:
                raise ValueError("Subset genotype calls differ from parent")
        if parent.read(1) or child.read(1):
            raise ValueError("BED dimensions disagree with BIM/FAM")
    for path, expected in [(bed, phenotype), (cov, covariate)]:
        with gzip.open(path, "rt") as stream:
            if list(stream) != expected:
                raise ValueError(f"Serialized table differs from selected source values: {path}")
    chromosomes = sorted({line.split("\t", 1)[0] for line in phenotype[1:]})
    for chrom in chromosomes:
        observed = subprocess.check_output([str(BIN / "tabix"), str(bed), chrom], text=True)
        expected = "".join(line for line in phenotype[1:] if line.startswith(chrom + "\t"))
        if observed != expected:
            raise ValueError(f"Indexed phenotype retrieval differs for {chrom}")
    if before != {name: sha256(SOURCE / name) for name in FILES}:
        raise ValueError("Parent fixture changed during subsetting")
    hashes = {name: sha256(OUTPUT / name) for name in FILES}
    metadata = {
        "object_type": "genotype", "format": "PLINK1", "prefix": "genotype",
        "purpose": "behavioral_benchmark", "sample_kind": "synthetic_pseudo_individuals",
        "sample_count": SAMPLES, "variant_count": len(bim),
        "phenotype_count": len(phenotype) - 1, "covariate_count": len(covariate) - 1,
        "scientific_fidelity": "not_claimed", "scientific_integration_fixture": False,
        "selection": "first 500 FAM rows in original order; exact stored-value subset",
        "parent": str(SOURCE), "parent_sha256": before, "input_sha256": hashes,
        "phenotype_file": "traits/phenotypes.bed.gz", "covariate_file": "traits/covariates.cov.gz",
        "phenotype_header_bytes": len(phenotype[0].encode()),
        "phenotype_max_line_bytes": max(len(line.encode()) for line in phenotype),
        "checks": {"genotype_calls_and_alleles": True, "sample_order": True,
                   "trait_values": True, "tabix_retrieval": True, "parent_unchanged": True},
        "plink_command": command, "script_sha256": sha256(Path(__file__)),
        "lsf_job_id": os.environ.get("LSB_JOBID"),
        "reproduction_commands": "../../../experiments/sketch_to_plink1/RUN.md",
        "limitation": "Parent full-sample association and empirical variance diagnostics do not describe this subset."
    }
    (OUTPUT / "fixture_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
