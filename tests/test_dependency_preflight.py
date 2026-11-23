from pathlib import Path
import sys

import pytest

from fungen_operator.actions import PrepareConfig, InitiateRun
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, active, verify


def prepared(tmp_path):
    d = create_fixture(tmp_path / "fixture")
    args = dict(notebook=str(Path(d.run_root, "operator.ipynb")),
                configfile=str(Path(d.run_root, "run.yaml")),
                workdir=str(Path(d.run_root, "work")))
    h = Harness(d)
    h.prepare_config(h.propose_config(PrepareConfig(**args)))
    run = dict(**args, log_dir=str(Path(d.run_root, "logs")), targets=["all"])
    return d, h, run


def test_dependency_preflight_executes_before_production(tmp_path):
    d, h, run = prepared(tmp_path)
    result = h.run("initiate_run", InitiateRun(**run, depends_on=["123", "456"], defer_readiness=True))
    assert result["status"] == "submitted"
    assert result["scheduler"]["status"] == "DONE"
    assert result["readiness_policy"] == "canonical_dry_run_at_controller_start"
    assert Path(run["workdir"], "output/result.txt").is_file()
    nb = Notebook(run["notebook"]).read()
    source = active(nb)[-1].source
    assert '#BSUB -w "done(123) && done(456)"' in source
    assert source.count("python -m snakemake") == 2
    assert source.index("--dry-run") < source.rindex("python -m snakemake")
    assert "set -eo pipefail" in source
    verify(nb)


def test_cells_run_in_their_notebook_folder(tmp_path):
    # Like Jupyter, a cell runs in its notebook's folder, so the LSF job starts and activates its env in the run folder.
    d, h, run = prepared(tmp_path)
    marker = tmp_path / "activation_folder"
    Path(d.conda_sh).write_text(f"conda() {{ pwd -P > {str(marker)!r}; }}\n")
    h.run("initiate_run", InitiateRun(**run, depends_on=["123"], defer_readiness=True))
    assert marker.read_text().strip() == str(Path(run["notebook"]).resolve().parent)


def test_failed_dependency_preflight_never_executes_production(tmp_path):
    d, h, run = prepared(tmp_path)
    marker = Path(d.conda_env, "production_was_called")
    Path(d.conda_env, "bin/python").write_text(
        f"#!{sys.executable}\nimport sys\nfrom pathlib import Path\n"
        "if '--dry-run' in sys.argv:\n    print('Synthetic canonical readiness failure')\n    sys.exit(17)\n"
        f"Path({str(marker)!r}).write_text('production')\n")
    result = h.run("initiate_run", InitiateRun(**run, depends_on=["123"], defer_readiness=True))
    assert result["scheduler"]["status"] == "EXIT"
    assert not marker.exists()
    assert not Path(run["workdir"], "output/result.txt").exists()


def test_dependency_preflight_requires_prerequisite_and_preserves_default_gate(tmp_path):
    d, h, run = prepared(tmp_path)
    with pytest.raises(ValueError, match="requires native LSF prerequisites"):
        h.run("initiate_run", InitiateRun(**run, defer_readiness=True))
    with pytest.raises(ValueError, match="successful matching check_readiness"):
        h.run("initiate_run", InitiateRun(**run, depends_on=["123"]))
