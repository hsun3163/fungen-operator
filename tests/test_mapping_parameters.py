import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from fungen_operator.actions import PrepareConfig
from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness


def setup_mapping(tmp_path):
    d = create_fixture(tmp_path / "fixture")
    schema = {"file": "", "n_sample": 0, "n_case": 0, "n_control": 0, "colmap": ""}
    path = Path(d.default_config)
    defaults = yaml.safe_load(path.read_text())
    defaults["eqtl"] = {"original": schema}
    path.write_text(yaml.safe_dump(defaults))
    d.mapping_parameters = {"eqtl": schema}
    d.backend = "lsf"
    args = PrepareConfig(notebook=str(Path(d.run_root, "operator.ipynb")),
                         configfile=str(Path(d.run_root, "run.yaml")),
                         workdir=d.run_root)
    config = dict(defaults)
    config["eqtl"] = {"SingleBrain_Ast_fixed_meta": {**schema, "n_sample": 945}}
    Path(args.configfile).write_text(yaml.safe_dump(config))
    return d, args, config


def test_cli_adopts_new_study_names_without_changing_science(tmp_path):
    d, args, config = setup_mapping(tmp_path)
    deploy, request = tmp_path / "deployment.json", tmp_path / "request.json"
    deploy.write_text(d.model_dump_json())
    request.write_text(args.model_dump_json())
    before = Path(args.configfile).read_bytes()
    result = subprocess.run([sys.executable, "-m", "fungen_operator", "action",
        "--deployment", str(deploy), "--action", "prepare_config", "--request", str(request)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "host_approval_required"
    assert Path(args.configfile).read_bytes() == before
    assert yaml.safe_load(before) == config


@pytest.mark.parametrize("bad", [
    {"file": "", "extra_args": "--forceall"},
    {"n_sample": "945"},
    {"file": "$(id)"},
])
def test_dynamic_studies_keep_field_type_and_shell_checks(tmp_path, bad):
    d, args, config = setup_mapping(tmp_path)
    config["eqtl"] = {"new_study": bad}
    Path(args.configfile).write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError):
        Harness(d, Executor(d)).propose_config(args)
    assert not Path(args.notebook).exists()


def test_new_member_edits_remain_scientific_and_registered(tmp_path):
    d, args, config = setup_mapping(tmp_path)
    h = Harness(d, Executor(d))
    proposal = h.propose_config(args.model_copy(update={
        "parameters": {"eqtl.SingleBrain_Ast_fixed_meta.n_sample": 946}}))
    assert proposal["scientific_changes"] == {
        "eqtl.SingleBrain_Ast_fixed_meta.n_sample": {"before": 945, "after": 946}}
    with pytest.raises(ValueError, match="scientific approval required"):
        h.prepare_config(proposal)
    with pytest.raises(ValueError, match="unregistered"):
        h.propose_config(args.model_copy(update={"parameters": {"eqtl.new.extra_args": "bad"}}))


def test_unregistered_mappings_still_reject_new_names(tmp_path):
    d, args, _ = setup_mapping(tmp_path)
    d.mapping_parameters = {}
    with pytest.raises(ValueError, match="unregistered canonical parameter"):
        Harness(d, Executor(d)).propose_config(args)


def test_mapping_schema_is_part_of_source_identity(tmp_path):
    d, _, _ = setup_mapping(tmp_path)
    before = d.identity()
    d.mapping_parameters["eqtl"]["extra"] = ""
    assert d.identity() != before


def test_registered_source_scope_bounds_git_and_detects_source_drift(tmp_path, monkeypatch):
    d, _, _ = setup_mapping(tmp_path)
    source = Path(d.repository, "scripts")
    source.mkdir(exist_ok=True)
    script = source / "worker.py"
    script.write_text("print('source')\n")
    d.canonical_source_paths = [str(source)]
    original = subprocess.check_output
    commands = []

    def observe(argv, **kwargs):
        assert "--others" not in argv, "Source identity must never enumerate untracked trees"
        if "--" in argv:
            for spec in argv[argv.index("--") + 1:]:
                assert spec.startswith(":(literal)")
                assert Path(d.repository, spec.removeprefix(":(literal)")).is_file()
        commands.append(argv)
        return original(argv, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", observe)
    before = d.identity()
    generated = Path(d.repository, "generated")
    generated.mkdir()
    (generated / "result.py").write_text("generated output\n")
    assert d.identity() == before
    scans = [c for c in commands if "ls-files" in c or "status" in c]
    assert scans and all("." not in c[c.index("--") + 1:] for c in scans)
    assert all(any("scripts/worker.py" in arg for arg in c) for c in scans)
    script.write_text("print('changed source')\n")
    assert d.identity() != before
