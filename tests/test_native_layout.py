from pathlib import Path

import pytest

from fungen_operator.actions import PrepareConfig
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.execution import Executor


def native(tmp_path):
    d = create_fixture(tmp_path / 'fixture')
    root = Path(d.repository)
    (root / 'scripts').mkdir()
    d.native_run_paths = [str(root / 'run.yaml'), str(root / 'operator.ipynb'), str(root / 'output')]
    d.canonical_source_paths = [str(root / 'scripts')]
    args = PrepareConfig(notebook=str(root / 'operator.ipynb'), configfile=str(root / 'run.yaml'), workdir=str(root))
    return d, args


def test_native_layout_stages_and_preserves_source(tmp_path):
    d, args = native(tmp_path)
    d.validate_arguments(args)
    d.backend = "lsf"
    h = Harness(d, Executor(d))
    proposal = h.propose_config(args)
    assert proposal['scientific_changes'] == {}
    source = Path(d.snakefile).read_bytes()
    result = h.prepare_config(proposal)
    assert result['status'] == 'host_approval_required'
    assert Path(d.snakefile).read_bytes() == source
    # A newly created native notebook does not change workflow identity.
    assert d.identity() == proposal['identity']


@pytest.mark.parametrize('name', ['Snakefile', 'scripts/worker.py', '.git/config', 'unregistered.yaml'])
def test_native_layout_rejects_undeclared_and_source_writes(tmp_path, name):
    d, args = native(tmp_path)
    with pytest.raises(ValueError):
        d.validate_arguments(args.model_copy(update={'configfile': str(Path(d.repository, name))}))


def test_native_layout_rejects_overlapping_source_grant_and_symlink(tmp_path):
    d, args = native(tmp_path)
    d.native_run_paths.append(d.repository)
    with pytest.raises(ValueError, match='disjoint'):
        d.validate_layout()
    d.native_run_paths.pop()
    Path(d.repository, 'output').symlink_to(Path(d.repository, 'scripts'), target_is_directory=True)
    with pytest.raises(ValueError, match='disjoint'):
        d.validate_layout()


def test_absent_cwd_is_not_added(tmp_path):
    import yaml
    d, args = native(tmp_path)
    cfg = yaml.safe_load(Path(d.default_config).read_text())
    cfg.pop('cwd', None)
    Path(d.default_config).write_text(yaml.safe_dump(cfg))
    result, diff = d.config(args, cfg)
    assert 'cwd' not in result
    assert result == cfg and diff == {}


def test_native_runtime_outputs_do_not_change_identity(tmp_path):
    d, args = native(tmp_path)
    before = d.identity()
    Path(args.configfile).write_text('native: run\n')
    assert d.identity() == before


def test_cli_stages_existing_config_through_harness(tmp_path):
    import json
    import subprocess
    import sys
    d, args = native(tmp_path)
    d.backend = 'lsf'
    deploy = tmp_path / 'deployment.json'
    deploy.write_text(d.model_dump_json())
    request = tmp_path / 'request.json'
    request.write_text(args.model_dump_json())
    result = subprocess.run([sys.executable, '-m', 'fungen_operator', 'action',
        '--deployment', str(deploy), '--action', 'prepare_config', '--request', str(request)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['status'] == 'host_approval_required'
    assert receipt['host_command'][2:4] == ['fungen_operator', 'execute']
    request.write_text(args.model_copy(update={'parameters': {'pca.n_pcs': 1}}).model_dump_json())
    before = Path(args.notebook).read_bytes()
    denied = subprocess.run([sys.executable, '-m', 'fungen_operator', 'action',
        '--deployment', str(deploy), '--action', 'prepare_config', '--request', str(request)],
        capture_output=True, text=True)
    assert denied.returncode != 0 and 'scientific approval required' in denied.stderr
    assert Path(args.notebook).read_bytes() == before


def test_cli_verify_loads_deployment_from_external_path(tmp_path):
    import json
    import subprocess
    import sys
    d, args = native(tmp_path)
    d.backend = "lsf"
    h = Harness(d)
    h.prepare_config(h.propose_config(args))
    external = tmp_path / "workflow-owned" / "operator.json"
    external.parent.mkdir()
    external.write_text(d.model_dump_json())
    result = subprocess.run([sys.executable, "-m", "fungen_operator", "verify", args.notebook,
        "--deployment", str(external)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "All active cells re-render identically." in result.stdout
    bad = d.model_copy(update={"run_root": str(tmp_path / "elsewhere"), "native_run_paths": []})
    external.write_text(bad.model_dump_json())
    result = subprocess.run([sys.executable, "-m", "fungen_operator", "verify", args.notebook,
        "--deployment", str(external)], text=True, capture_output=True)
    assert result.returncode != 0 and "write path" in result.stderr
