"""Source identity excludes data before asking the filesystem about each path."""

import hashlib
from pathlib import Path

from fungen_operator.fixture import create_fixture


def test_identity_skips_data_stats_and_preserves_source_hashes(tmp_path, monkeypatch):
    deployment = create_fixture(tmp_path / "fixture")
    root = Path(deployment.repository)
    data = root / "large_data.tsv"
    data.write_text("opaque fixture data\n")
    script = root / "worker.py"
    script.write_text("print('fixture source')\n")
    deployment.canonical_source_paths = [str(script)]
    original = Path.is_file

    def source_only_stat(path):
        assert path != data, "Excluded data should never require a per-file stat"
        return original(path)

    monkeypatch.setattr(Path, "is_file", source_only_stat)
    identity = deployment.identity()
    assert identity["dirty"] is True
    assert "large_data.tsv" not in identity["source_hashes"]
    assert identity["source_hashes"]["worker.py"] == hashlib.sha256(script.read_bytes()).hexdigest()
    assert identity["source_hashes"][deployment.snakefile] == hashlib.sha256(Path(deployment.snakefile).read_bytes()).hexdigest()
    script.write_text("print('changed fixture source')\n")
    assert deployment.identity()["source_hashes"]["worker.py"] != identity["source_hashes"]["worker.py"]
