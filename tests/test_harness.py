import asyncio
import copy
import json
from pathlib import Path

import nbformat
import pytest
from mcp import Client
from mcp.types import ElicitResult
from pydantic import ValidationError

from fungen_operator.actions import (PrepareConfig, CheckReadiness, InitiateRun, InspectRun,
                                     render, digest)
from fungen_operator.demo import lifecycle
from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, active, verify
from fungen_operator.server import create_server


@pytest.fixture
def setup(tmp_path):
    deployment = create_fixture(tmp_path / "fixture")
    args = dict(notebook=str(Path(deployment.run_root, "operator.ipynb")),
                configfile=str(Path(deployment.run_root, "config.yaml")),
                workdir=str(Path(deployment.run_root, "work")))
    return deployment, args


class LocalExecution:
    """Unit-test double; integration below uses real nbclient and fixture binaries."""
    can_schedule = True

    def __init__(self):
        self.cells = []
        self.done = False

    def execute(self, cell):
        self.cells.append(cell.source)
        meta = cell.metadata.fungen
        if meta.action == "prepare_config":
            exec(cell.source, {})
            status = "materialized"
        elif meta.action == "check_readiness":
            status = "nothing_to_do" if self.done else "ready"
        else:
            self.done = True
            status = "submitted"
        cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text=f"LOCAL TEST: {status}\n")]
        cell.execution_count = 1
        result = {"status": status, "backend": "test-double"}
        if meta.action == "initiate_run":
            result.update(job_id=str(len(self.cells)), scheduler={"status": "DONE"})
        return result

    def scheduler(self, job):
        return {"status": "DONE", "job_id": job}

    def logs(self, stem, job):
        return {}


def run_args(deployment, args):
    return {**args, "log_dir": str(Path(deployment.run_root, "logs")), "targets": ["all"]}


def unit_harness(setup):
    deployment, args = setup
    execution = LocalExecution()
    harness = Harness(deployment, execution)
    harness.prepare_config(harness.propose_config(PrepareConfig(**args)))
    return harness, execution, run_args(deployment, args)


def test_valid_renderer_uses_native_cell(setup):
    deployment, args = setup
    values = InitiateRun(**run_args(deployment, args))
    slots = {"arguments": values.model_dump(), "bindings": {
        "snakefile": deployment.snakefile, "profile_path": deployment.profile_path,
        "conda_sh": deployment.conda_sh, "conda_env": deployment.conda_env,
        "log_stem": str(Path(deployment.run_root, "logs/attempt"))}}
    source = render("initiate_run", slots)
    assert "bsub <<'LSF'\n#BSUB -J fungen\n#BSUB -P acc_LOAD\n#BSUB -q premium\n#BSUB -W 144:00" in source
    assert '#BSUB -R "span[hosts=1] rusage[mem=40GB]"' in source
    assert "--cores 72 --jobs 100" in source and "--latency-wait 120" in source
    assert source.endswith("  all\nLSF\n")
    assert "--force" not in source and "--dry-run" not in source
    assert render("initiate_run", copy.deepcopy(slots)) == source


@pytest.mark.parametrize("field,value", [("targets", ["--forceall"]), ("targets", ["x --forceall"]),
    ("targets", ["x; touch /tmp/bad"]), ("targets", ["$(id)"]), ("targets", ["../escape"]),
    ("targets", ["x\n--forceall"]), ("jobs", 0), ("jobs", True), ("memory_gb", 16),
    ("queue", "premium\n#BSUB -w done(1)"), ("walltime_minutes", "144h"),
    ("workdir", "/tmp/a;id"), ("extra_args", "--forceall")])
def test_invalid_slots_rejected(setup, field, value):
    deployment, args = setup
    kwargs = run_args(deployment, args)
    kwargs[field] = value
    with pytest.raises(ValidationError):
        InitiateRun(**kwargs)


def test_structured_target_list_and_resource_bounds(setup):
    deployment, args = setup
    kwargs = run_args(deployment, args)
    kwargs["targets"] = ["output/foo.vcf.gz", "output/foo.vcf.gz.tbi"]
    assert InitiateRun(**kwargs).targets == kwargs["targets"]
    with pytest.raises(ValueError, match="run_root"):
        deployment.validate_arguments(PrepareConfig(**{**args, "configfile": deployment.default_config}))
    with pytest.raises(ValueError, match="12 hours"):
        deployment.validate_arguments(InitiateRun(**kwargs, queue="express"))


def test_scientific_approval_precedes_all_materialization(setup):
    deployment, args = setup
    harness = Harness(deployment, LocalExecution())
    proposal = harness.propose_config(PrepareConfig(**args, parameters={"pca.n_pcs": 1}))
    assert proposal["scientific_changes"] == {"pca.n_pcs": {"before": 20, "after": 1}}
    with pytest.raises(ValueError, match="approval required"):
        harness.prepare_config(proposal)
    assert not Path(args["notebook"]).exists() and not Path(args["configfile"]).exists()
    proof = {"fingerprint": proposal["fingerprint"], "channel": "unit-test-human"}
    harness.prepare_config(proposal, proof)
    assert Notebook(args["notebook"]).read().cells[1].metadata.fungen.approval == proof


def test_operational_parameter_and_unknown_parameter(setup):
    deployment, args = setup
    harness = Harness(deployment, LocalExecution())
    proposal = harness.propose_config(PrepareConfig(**args, parameters={"resources.default.mem_mb": 65536}))
    assert proposal["scientific_changes"] == {}
    for params in ({"does_not_exist": 1}, {"pca.n_pcs": "one"}, {"resources": {"extra_args": "--forceall"}}):
        with pytest.raises(ValueError):
            harness.propose_config(PrepareConfig(**args, parameters=params))


def test_adopting_existing_config_preserves_science_and_gates_changes(setup):
    import yaml
    deployment, args = setup
    config = deployment.defaults()
    config["pca"]["n_pcs"] = 1
    Path(args["configfile"]).write_text(yaml.safe_dump(config))
    harness = Harness(deployment, LocalExecution())
    unchanged = harness.propose_config(PrepareConfig(**args))
    assert unchanged["config"]["pca"]["n_pcs"] == 1
    assert unchanged["scientific_changes"] == {}
    changed = harness.propose_config(PrepareConfig(**args, parameters={"pca.n_pcs": 20}))
    assert changed["scientific_changes"] == {"pca.n_pcs": {"before": 1, "after": 20}}
    with pytest.raises(ValueError, match="approval required"):
        harness.prepare_config(changed)
    assert not Path(args["notebook"]).exists()


def test_external_scientific_drift_requires_approval_to_restore(setup):
    import yaml
    harness, executor, kwargs = unit_harness(setup)
    path = Path(kwargs["configfile"])
    external = yaml.safe_load(path.read_text())
    external["pca"]["n_pcs"] = 5
    path.write_text(yaml.safe_dump(external))
    args = PrepareConfig(**{k: kwargs[k] for k in ("notebook", "configfile", "workdir")})
    proposal = harness.propose_config(args)
    assert proposal["scientific_changes"] == {"pca.n_pcs": {"before": 5, "after": 20}}
    with pytest.raises(ValueError, match="approval required"):
        harness.prepare_config(proposal)
    assert yaml.safe_load(path.read_text())["pca"]["n_pcs"] == 5


def test_stale_approval_and_symlink_escape(setup):
    deployment, args = setup
    harness = Harness(deployment, LocalExecution())
    proposal = harness.propose_config(PrepareConfig(**args, parameters={"pca.n_pcs": 1}))
    Path(deployment.snakefile).write_text(Path(deployment.snakefile).read_text() + "# developer edit\n")
    with pytest.raises(ValueError, match="changed"):
        harness.prepare_config(proposal, {"fingerprint": proposal["fingerprint"]})
    link = Path(deployment.run_root, "escape")
    link.symlink_to(deployment.repository, target_is_directory=True)
    with pytest.raises(ValueError, match="run_root"):
        harness.propose_config(PrepareConfig(**{**args, "configfile": str(link / "config.yaml")}))


def test_lifecycle_replacement_replay_and_tamper(setup):
    harness, executor, kwargs = unit_harness(setup)
    harness.run("check_readiness", CheckReadiness(**kwargs))
    first = harness.run("initiate_run", InitiateRun(**kwargs))
    second = harness.run("initiate_run", InitiateRun(**kwargs))
    assert first["cell_id"] != second["cell_id"]
    final = harness.run("check_readiness", CheckReadiness(**kwargs, phase="conclusion"))
    assert final["status"] == "nothing_to_do"
    book = Notebook(kwargs["notebook"])
    nb = book.read()
    old = next(c for c in nb.cells if c.id == first["cell_id"])
    assert "superseded" in old.metadata.tags and old.outputs
    assert [c.metadata.fungen.action for c in active(nb)] == ["prepare_config", "check_readiness", "initiate_run", "check_readiness"]
    before = Path(kwargs["configfile"]).stat().st_mtime_ns
    result = harness.replay(kwargs["notebook"])
    assert result[-1]["status"] == "nothing_to_do"
    assert Path(kwargs["configfile"]).stat().st_mtime_ns == before
    nb = book.read()
    verify(nb)
    assert next(c for c in nb.cells if c.id == first["cell_id"]).outputs == old.outputs
    active(nb)[-1].source += "\necho tampered"
    with pytest.raises(ValueError, match="re-render"):
        verify(nb)


def test_changed_config_requires_fresh_readiness(setup):
    harness, executor, kwargs = unit_harness(setup)
    harness.run("check_readiness", CheckReadiness(**kwargs))
    with pytest.raises(ValueError, match="matching"):
        harness.run("initiate_run", InitiateRun(**{**kwargs, "targets": ["output/another.txt"]}))
    Path(kwargs["configfile"]).write_text("pca: {}\n")
    with pytest.raises(ValueError, match="differs"):
        harness.run("initiate_run", InitiateRun(**kwargs))


def test_replay_continues_after_asynchronous_submission(setup):
    harness, executor, kwargs = unit_harness(setup)
    harness.run("check_readiness", CheckReadiness(**kwargs))
    harness.run("initiate_run", InitiateRun(**kwargs))
    harness.run("check_readiness", CheckReadiness(**kwargs, phase="conclusion"))
    original_execute = executor.execute
    def delayed(cell):
        result = original_execute(cell)
        if cell.metadata.fungen.action == "initiate_run":
            result["scheduler"] = {"status": "RUN"}
        return result
    executor.execute = delayed
    executor.scheduler = lambda job: {"status": "RUN", "job_id": job}
    first = harness.replay(kwargs["notebook"])
    assert first[-1]["status"] == "submitted"
    nb = Notebook(kwargs["notebook"]).read()
    assert len(active(nb)) == 4 and active(nb)[-1].metadata.fungen.status == "awaiting_controller"
    executor.scheduler = lambda job: {"status": "DONE", "job_id": job}
    second = harness.replay(kwargs["notebook"])
    assert len(second) == 1 and second[0]["status"] == "nothing_to_do"


def test_configuration_replacement_supersedes_dependents(setup):
    harness, executor, kwargs = unit_harness(setup)
    harness.run("check_readiness", CheckReadiness(**kwargs))
    harness.run("initiate_run", InitiateRun(**kwargs))
    harness.run("check_readiness", CheckReadiness(**kwargs, phase="conclusion"))
    args = PrepareConfig(**{k: kwargs[k] for k in ("notebook", "configfile", "workdir")},
                         parameters={"resources.default.mem_mb": 65536})
    harness.prepare_config(harness.propose_config(args))
    nb = Notebook(kwargs["notebook"]).read()
    assert [c.metadata.fungen.action for c in active(nb)] == ["prepare_config"]
    assert all(c.outputs for c in nb.cells if c.cell_type == "code")


def test_host_backend_defers_without_running_lsf(setup):
    deployment, args = setup
    harness, _, kwargs = unit_harness(setup)
    live = deployment.model_copy(update={"backend": "lsf"})
    harness = Harness(live, Executor(live), "/tmp/deployment.json")
    result = harness.run("check_readiness", CheckReadiness(**kwargs))
    assert result["status"] == "host_approval_required"
    assert "execute" in result["host_command"] and result["cell_id"] in result["host_command"]
    assert not Path(deployment.conda_env, "scheduler.json").exists()


def test_mcp_approval_decline_and_schema(setup):
    deployment, args = setup
    harness = Harness(deployment, LocalExecution())
    server = create_server(harness)
    asked = []
    async def decline(ctx, params):
        asked.append(params.message)
        assert not Path(args["notebook"]).exists()
        return ElicitResult(action="decline")
    async def exercise():
        async with Client(server, elicitation_callback=decline) as client:
            tools = await client.list_tools()
            prepare = next(t for t in tools.tools if t.name == "prepare_config")
            assert set(prepare.input_schema["properties"]) == {"request"}
            response = await client.call_tool("prepare_config", {"request": {**args, "parameters": {"pca.n_pcs": 1}}})
            assert not response.is_error, response
            assert response.structured_content["status"] == "approval_declined"
    asyncio.run(exercise())
    assert len(asked) == 1
    assert not Path(args["notebook"]).exists() and not Path(args["configfile"]).exists()


def test_end_to_end_mcp_notebook_execution_and_replay(setup):
    deployment, args = setup
    result = asyncio.run(lifecycle(deployment))
    assert result["approval_requests"] == 1
    assert result["initial_scheduler_state"] == "EXIT"
    assert result["final_status"] == "nothing_to_do"
    book = Notebook(result["notebook"])
    nb = book.read()
    assert len(active(nb)) == 4
    assert all(c.execution_count is not None and c.outputs for c in active(nb))
    files = list(Path(args["workdir"], "output").iterdir())
    stamps = {p: p.stat().st_mtime_ns for p in files}
    replay = Harness(deployment).replay(result["notebook"])
    assert replay[-1]["status"] == "nothing_to_do"
    assert {p: p.stat().st_mtime_ns for p in files} == stamps
    verify(book.read())
