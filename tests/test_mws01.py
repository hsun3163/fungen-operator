"""MWS-01 grader acceptance and rejection checks using tiny synthetic BEDs."""

import copy
import gzip
import subprocess
from pathlib import Path

import pytest

from benchmark.mws01 import partition_checks, protected_config

BIN = Path("/sc/arion/work/sunh14/conda/envs/xqtl-r-base-fsusie/bin")
HEADER = "#chr\tstart\tend\tID\tSYN_1\tSYN_2\n"
ROWS = ["chr1\t1\t2\tOTHER\t0\t1\n", "chr22\t10\t11\tTRAIT\t1.25\t-2.5\n"]


@pytest.fixture
def products(tmp_path):
    source = tmp_path / "input.bed.gz"
    with gzip.open(source, "wt") as stream:
        stream.write(HEADER + "".join(ROWS))
    output = tmp_path / "output"
    output.mkdir()
    bed = output / "phenotypes.chr22.bed.gz"
    with bed.open("wb") as stream:
        subprocess.run([str(BIN / "bgzip"), "-c"], input=(HEADER + ROWS[1]).encode(),
                       stdout=stream, check=True)
    subprocess.run([str(BIN / "tabix"), "-p", "bed", str(bed)], check=True)
    (output / "phenotypes.phenotype_by_chrom_files.txt").write_text(f"#id\t#dir\n22\t{bed}\n")
    (output / "phenotypes.phenotype_by_chrom_files.region_list.txt").write_text(
        f"#chr\tstart\tend\tID\tpath\nchr22\t10\t11\tTRAIT\t{bed}\n")
    return source, output, bed


def test_mws01_grader_accepts_exact_partition(products):
    source, output, _ = products
    checks, samples, phenotypes = partition_checks(source, output, ["chr22"], BIN / "tabix")
    assert all(checks.values())
    assert (samples, phenotypes) == (2, 1)


@pytest.mark.parametrize("damage", ["missing_bed", "missing_index", "value", "samples", "manifest", "duplicate"])
def test_mws01_grader_rejects_incomplete_or_changed_products(products, damage):
    source, output, bed = products
    if damage == "missing_bed":
        bed.unlink()
    elif damage == "missing_index":
        Path(str(bed) + ".tbi").unlink()
    elif damage in {"value", "samples"}:
        header = HEADER if damage == "value" else HEADER.replace("SYN_1\tSYN_2", "SYN_2\tSYN_1")
        row = ROWS[1].replace("1.25", "9.99") if damage == "value" else ROWS[1]
        with bed.open("wb") as stream:
            subprocess.run([str(BIN / "bgzip"), "-c"], input=(header + row).encode(), stdout=stream, check=True)
        subprocess.run([str(BIN / "tabix"), "-f", "-p", "bed", str(bed)], check=True)
    else:
        path = output / "phenotypes.phenotype_by_chrom_files.txt"
        text = path.read_text()
        path.write_text(text.replace("22\t", "1\t") if damage == "manifest" else text + f"22\t{bed}\n")
    checks, _, _ = partition_checks(source, output, ["chr22"], BIN / "tabix")
    assert not all(checks.values())


def test_mws01_grader_distinguishes_resources_and_scientific_scope():
    original = {"cwd": "/trial/work", "chromosomes": ["chr22"], "resources": {"mem_mb": 32768}}
    changed = copy.deepcopy(original)
    changed["resources"]["mem_mb"] = 65536
    assert protected_config(original) == protected_config(changed)
    changed["chromosomes"] = ["chr1"]
    assert protected_config(original) != protected_config(changed)


def test_saved_trial_retains_original_sample_contract(tmp_path, monkeypatch):
    from benchmark import mws01

    current = tmp_path / "current.yaml"
    current.write_text("revision: 2\ninitial_environment:\n  input_root: output/fixture_500\ndeclared_outcome:\n  samples: 500\n")
    monkeypatch.setattr(mws01, "TASK_PATH", current)
    old = tmp_path / "old_trial"
    old.mkdir()
    (old / "task.yaml").write_text("revision: 1\ninitial_environment: {}\ndeclared_outcome:\n  samples: 10000\n")
    assert mws01.task(old)["declared_outcome"]["samples"] == 10000
    assert mws01.inputs(mws01.task(old)).name == "behavioral_fixture"
    assert mws01.task(tmp_path / "new_trial")["declared_outcome"]["samples"] == 500
    assert mws01.inputs(mws01.task()).name == "fixture_500"
