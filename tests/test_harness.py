import asyncio
import copy
from dataclasses import replace
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import nbformat
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.types import ElicitResult
from pydantic import ValidationError

from fungen_operator.actions import (PrepareConfig, CheckReadiness, InitiateRun, InspectRun,
                                     render, digest)
from fungen_operator.demo import lifecycle
from fungen_operator.execution import Executor
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, active, verify
from fungen_operator.server import create_server, serve_stdio


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

    def execute(self, cell, folder):
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


@pytest.mark.parametrize('state,native,expected', [
    ('DONE', 'Job stats:\n', 'ready'),
    ('DONE', 'Nothing to be done.\n', 'nothing_to_do'),
    ('EXIT', 'Job stats:\n', 'failed'),
    ('RUN', 'Job stats:\n', 'executing'),
    ('UNKNOWN', 'Job stats:\n', 'unknown'),
    ('DONE', 'incomplete native log\n', 'unknown'),
])
def test_interrupted_readiness_recovers_native_job_without_submission(setup, monkeypatch, state, native, expected):
    deployment, kwargs = setup
    deployment.backend = 'lsf'
    execution = Executor(deployment, host_approved=True)
    stem = Path(kwargs['notebook']).parent / 'interrupted'
    stem.parent.mkdir(parents=True, exist_ok=True)
    Path(str(stem) + '.123.out').write_text(native)
    monkeypatch.setattr(execution, 'controller_scheduler', lambda s,j: {'status': state, 'job_id': j})
    cell = nbformat.v4.new_code_cell(metadata={'fungen': {'slots': {'bindings': {'log_stem': str(stem)}}}})
    result = execution.recover_readiness(cell)
    assert result['status'] == expected
    assert result['job_id'] == '123'
    assert 'synchronous_exit_code' not in result
    Path(str(stem) + '.456.out').write_text(native)
    assert execution.recover_readiness(cell) is None


@pytest.mark.parametrize('action,method,status', [
    ('check_readiness', 'recover_readiness', 'ready'),
    ('initiate_run', 'recover_submission', 'submitted'),
])
def test_inspect_reconciles_interrupted_readiness_in_its_native_cell(setup, monkeypatch, action, method, status):
    harness, execution, kwargs = unit_harness(setup)
    harness.run('check_readiness', CheckReadiness(**kwargs))
    if action == 'initiate_run':
        harness.run(action, InitiateRun(**kwargs))
    book = Notebook(kwargs['notebook'])
    nb = book.read()
    cell = next(c for c in nb.cells if c.metadata.get('fungen', {}).get('action') == action)
    cell.metadata.fungen.status = 'executing'
    cell.metadata.fungen.pop('result', None)
    saved_identity = copy.deepcopy(cell.metadata.fungen.identity)
    # Simulate the historical external/stale writer, bypassing the native
    # publication guard only in this deliberately damaged synthetic fixture.
    nbformat.write(nb, book.path)
    monkeypatch.setattr(execution, method, lambda c: {
        'status': status, 'job_id': '123', 'scheduler': {'status': 'DONE'}, 'logs': {}}, raising=False)
    monkeypatch.setattr(harness, '_job_snapshot', lambda *a, **k: {
        'jobs': {}, 'count': 0, 'dead_children': [], 'scheduler_ok': True, 'coverage': {'verified': True}})
    monkeypatch.setattr(execution, 'scheduler', lambda j: {'status': 'DONE'})
    harness.inspect(InspectRun(notebook=kwargs['notebook']))
    recovered = next(c for c in book.read().cells if c.id == cell.id)
    assert recovered.metadata.fungen.status == status
    assert recovered.metadata.fungen.result.job_id == '123'
    assert recovered.metadata.fungen.identity == saved_identity
    assert len(execution.cells) == (3 if action == 'initiate_run' else 2)


@pytest.mark.parametrize('state,expected', [('RUN','submitted'), ('PEND','submitted'),
                                         ('DONE','submitted'), ('EXIT','failed'), ('UNKWN','unknown')])
def test_interrupted_production_recovers_exact_buffered_receipt_without_resubmission(setup, monkeypatch, state, expected):
    deployment, kwargs = setup
    deployment.backend = 'lsf'
    execution = Executor(deployment, host_approved=True)
    stem = str(Path(kwargs['notebook']).parent / 'buffered-production')
    cell = nbformat.v4.new_code_cell(metadata={'fungen': {'action': 'initiate_run',
                                           'slots': {'bindings': {'log_stem': stem}}}})
    records = [{'JOBID': '123', 'OUTPUT_FILE': stem + '.%J.out'},
               {'JOBID': '456', 'OUTPUT_FILE': stem + '-different.456.out'}]
    def query(command, **kwargs):
        assert command == ['bjobs', '-a', '-json', '-o', 'jobid stat output_file']
        return SimpleNamespace(returncode=0, stdout=json.dumps({'RECORDS': records}))
    monkeypatch.setattr('fungen_operator.execution.subprocess.run', query)
    monkeypatch.setattr(execution, 'controller_scheduler', lambda s,j: {'status': state, 'job_id': j})
    monkeypatch.setattr(execution, 'logs', lambda s,j: {})
    result = execution.recover_submission(cell)
    assert result['job_id'] == '123' and result['status'] == expected
    assert 'synchronous_exit_code' not in result
    records.append({'JOBID': '789', 'OUTPUT_FILE': stem + '.789.out'})
    assert execution.recover_submission(cell) is None


@pytest.mark.parametrize('has_native_receipt', [False, True])
def test_inspect_recovers_displaced_prepared_submission_without_dispatch(setup, monkeypatch, has_native_receipt):
    harness, execution, kwargs = unit_harness(setup)
    harness.run('check_readiness', CheckReadiness(**kwargs))
    harness.run('initiate_run', InitiateRun(**kwargs))
    book = Notebook(kwargs['notebook'])
    nb = book.read()
    cell = next(c for c in active(nb) if c.metadata.fungen.action == 'initiate_run')
    cell.metadata.fungen.status = 'prepared'
    cell.metadata.fungen.pop('result', None)
    original = copy.deepcopy(cell.metadata.fungen)
    nbformat.write(nb, book.path)  # historical displacement fixture
    calls = len(execution.cells)
    monkeypatch.setattr(execution, 'recover_submission', lambda c: ({
        'status': 'submitted', 'job_id': '123', 'scheduler': {'status': 'RUN'},
        'logs': {}, 'recovered_from': 'native_log_stem'} if has_native_receipt else None), raising=False)
    monkeypatch.setattr(harness, '_job_snapshot', lambda *a, **k: {
        'jobs': {}, 'count': 0, 'dead_children': [], 'scheduler_ok': True, 'coverage': {'verified': True}})
    harness.inspect(InspectRun(notebook=kwargs['notebook']))
    recovered = next(c for c in book.read().cells if c.id == cell.id)
    assert len(execution.cells) == calls
    assert recovered.source == cell.source
    assert recovered.metadata.fungen.identity == original.identity
    assert recovered.metadata.fungen.slots == original.slots
    assert recovered.metadata.fungen.status == ('submitted' if has_native_receipt else 'prepared')
    if has_native_receipt:
        assert recovered.metadata.fungen.result.job_id == '123'
    else:
        assert 'result' not in recovered.metadata.fungen


@pytest.mark.parametrize('has_native_receipt', [False, True])
def test_new_submission_checks_displaced_prepared_receipt_before_dispatch(setup, monkeypatch, has_native_receipt):
    harness, execution, kwargs = unit_harness(setup)
    harness.run('check_readiness', CheckReadiness(**kwargs))
    harness.run('initiate_run', InitiateRun(**kwargs))
    book = Notebook(kwargs['notebook'])
    nb = book.read()
    cell = next(c for c in active(nb) if c.metadata.fungen.action == 'initiate_run')
    cell.metadata.fungen.status = 'prepared'
    cell.metadata.fungen.pop('result', None)
    nbformat.write(nb, book.path)  # historical displacement fixture
    calls = len(execution.cells)
    monkeypatch.setattr(execution, 'recover_submission', lambda c: ({
        'status': 'submitted', 'job_id': '123', 'scheduler': {'status': 'RUN'},
        'logs': {}} if has_native_receipt else None), raising=False)
    monkeypatch.setattr(execution, 'scheduler', lambda j: {'status': 'RUN'})
    if has_native_receipt:
        with pytest.raises(ValueError, match='controller 123 is RUN'):
            harness.run('initiate_run', InitiateRun(**kwargs))
        assert len(execution.cells) == calls
    else:
        assert harness.run('initiate_run', InitiateRun(**kwargs))['status'] == 'submitted'
        assert len(execution.cells) == calls + 1


@pytest.mark.parametrize('damage', ['missing', 'receipt', 'identity'])
def test_notebook_publication_preserves_submitted_receipts(setup, damage):
    harness, execution, kwargs = unit_harness(setup)
    harness.run('check_readiness', CheckReadiness(**kwargs))
    book = Notebook(kwargs['notebook'])
    stale = book.read()
    harness.run('initiate_run', InitiateRun(**kwargs))
    published = book.path.read_bytes()
    if damage != 'missing':
        stale = book.read()
        cell = next(c for c in active(stale) if c.metadata.fungen.action == 'initiate_run')
        if damage == 'receipt':
            cell.metadata.fungen.status = 'prepared'
            cell.metadata.fungen.pop('result', None)
        else:
            cell.metadata.fungen.identity['stale_writer'] = True
    with pytest.raises(ValueError, match='stale notebook publication'):
        book.save(stale)
    assert book.path.read_bytes() == published


def test_execution_start_preserves_newer_native_receipt(setup):
    harness, execution, kwargs = unit_harness(setup)
    execution.can_schedule = False
    staged = harness.run('check_readiness', CheckReadiness(**kwargs))
    book = Notebook(kwargs['notebook'])
    stale = book.read()
    cell = next(c for c in stale.cells if c.id == staged['cell_id'])
    newer = book.read()
    args = InitiateRun(**kwargs)
    receipt = book.append(newer, 'initiate_run', {
        'arguments': args.model_dump(),
        'bindings': harness.deployment.runtime_bindings(str(Path(kwargs['log_dir'])/'retained')),
    }, harness.deployment.identity(), 'retained-native-receipt')
    receipt.metadata.setdefault('tags', []).append('superseded')
    receipt.metadata.fungen.status = 'submitted'
    receipt.metadata.fungen['result'] = {'job_id': '777', 'scheduler': {'status': 'DONE'}}
    book.save(newer)
    execution.can_schedule = True
    assert harness._execute(book, stale, cell)['status'] == 'ready'
    saved = next(c for c in book.read().cells if c.id == receipt.id)
    assert saved.metadata.fungen.result.job_id == '777'
    assert saved.metadata.fungen.status == 'submitted'


@pytest.mark.parametrize('publication', [
    'fingerprint', 'append', 'proposal_save', 'fingerprint_save',
    'execution_start', 'execution_finish',
])
def test_provider_fingerprint_publication_keeps_intervening_receipt(setup, monkeypatch, publication):
    harness, execution, kwargs = unit_harness(setup)
    append = Notebook.append
    save = Notebook.save
    inserted = False

    def publish_native_observation(book):
        nonlocal inserted
        if inserted:
            return
        inserted = True
        current = book.read()
        request = InitiateRun(**kwargs)
        receipt = append(book, current, 'initiate_run', {
            'arguments': request.model_dump(),
            'bindings': harness.deployment.runtime_bindings(
                str(Path(kwargs['log_dir']) / 'intervening')),
        }, harness.deployment.identity(), 'intervening-native-receipt')
        receipt.metadata.fungen.update(
            status='submitted', result={'job_id': '777', 'scheduler': {'status': 'DONE'}})
        book.save(current)

    def append_with_native_observation(book, nb, action, *args, **options):
        cell = append(book, nb, action, *args, **options)
        if action == 'check_readiness' and publication == 'append':
            publish_native_observation(book)
        return cell

    monkeypatch.setattr(Notebook, 'append', append_with_native_observation)

    def save_with_native_observation(book, nb):
        target = next((c for c in nb.cells if c.metadata.get('fungen', {}).get('action')
                       == 'check_readiness'), None)
        if target is not None:
            meta = target.metadata.fungen
            stage = ('fingerprint_save' if meta.status == 'prepared'
                     and meta.get('run_fingerprint') else
                     'proposal_save' if meta.status == 'prepared' else
                     'execution_start' if meta.status == 'executing' else
                     'execution_finish' if meta.status == 'ready' else None)
            if publication == stage:
                publish_native_observation(book)
        return save(book, nb)

    monkeypatch.setattr(Notebook, 'save', save_with_native_observation)
    fingerprint = harness._run_fingerprint

    def fingerprint_with_native_observation(*args):
        value = fingerprint(*args)
        if publication == 'fingerprint':
            publish_native_observation(Notebook(kwargs['notebook']))
        return value

    monkeypatch.setattr(harness, '_run_fingerprint', fingerprint_with_native_observation)
    spec = replace(harness.registry.spec('check_readiness'), bindings=lambda d, a, c:
                   d.runtime_bindings(str(Path(a.log_dir) / c)))
    result = harness._provider_run(spec, CheckReadiness(**kwargs))
    assert result['status'] == 'ready'
    saved = Notebook(kwargs['notebook']).read()
    receipt = next(c for c in saved.cells if c.id == 'intervening-native-receipt')
    assert receipt.metadata.fungen.result.job_id == '777'
    assert receipt.metadata.fungen.status == 'submitted'
    observed = next(c for c in saved.cells if c.id == result['cell_id'])
    assert observed.metadata.fungen.run_fingerprint
    assert observed.metadata.fungen.status == 'ready'
    assert len(execution.cells) == 2


def test_provider_fingerprint_does_not_reset_an_already_executed_proposal(setup, monkeypatch):
    harness, execution, kwargs = unit_harness(setup)
    append = Notebook.append

    def append_with_native_result(book, nb, action, *args, **options):
        cell = append(book, nb, action, *args, **options)
        current = book.read()
        accepted = next(c for c in current.cells if c.id == cell.id)
        accepted.metadata.fungen.update(status='ready', result={'status': 'ready'})
        accepted.outputs = [nbformat.v4.new_output('stream', name='stdout', text='native result retained')]
        book.save(current)
        return cell

    monkeypatch.setattr(Notebook, 'append', append_with_native_result)
    spec = replace(harness.registry.spec('check_readiness'), bindings=lambda d, a, c:
                   d.runtime_bindings(str(Path(a.log_dir) / c)))
    with pytest.raises(ValueError, match='already executing or executed'):
        harness._provider_run(spec, CheckReadiness(**kwargs))
    saved = next(c for c in Notebook(kwargs['notebook']).read().cells
                 if c.metadata.get('fungen', {}).get('action') == 'check_readiness')
    assert saved.metadata.fungen.status == 'ready'
    assert saved.outputs[0].text == 'native result retained'
    assert len(execution.cells) == 1


@pytest.mark.parametrize('reuse,changed', [(True, False), (False, False), (True, True)])
def test_provider_adopts_only_opted_in_identical_running_observation(setup, reuse, changed):
    harness, execution, kwargs = unit_harness(setup)
    book = Notebook(kwargs['notebook'], harness.registry)
    nb = book.read()
    request = CheckReadiness(**kwargs)
    cell = book.append(nb, 'check_readiness', {
        'arguments': request.model_dump(),
        'bindings': harness.deployment.runtime_bindings(str(Path(request.log_dir) / 'ongoing')),
    }, harness.deployment.identity(), 'ongoing-observation')
    cell.metadata.fungen.status = 'executing'
    book.save(nb)
    if changed:
        request = CheckReadiness(**{**kwargs, 'phase': 'conclusion'})
    spec = replace(harness.registry.spec('check_readiness'),
        reuse_running=(lambda args: True) if reuse else None,
        bindings=lambda d, a, c: d.runtime_bindings(str(Path(a.log_dir) / c)))
    calls = len(execution.cells)
    result = harness._provider_run(spec, request)
    if reuse and not changed:
        assert result['cell_id'] == cell.id
        assert result['status'] == 'executing' and result['reused'] is True
        assert len(execution.cells) == calls
    else:
        assert result['cell_id'] != cell.id and result['status'] == 'ready'
        assert len(execution.cells) == calls + 1


def test_completed_newer_observation_does_not_reuse_orphaned_history(setup):
    harness, execution, kwargs = unit_harness(setup)
    book = Notebook(kwargs['notebook'], harness.registry)
    request = CheckReadiness(**kwargs)
    for cid, status in [('orphaned-old', 'executing'), ('newer-finished', 'ready')]:
        nb = book.read()
        cell = book.append(nb, 'check_readiness', {
            'arguments': request.model_dump(),
            'bindings': harness.deployment.runtime_bindings(str(Path(request.log_dir) / cid)),
        }, harness.deployment.identity(), cid)
        cell.metadata.fungen.status = status
        book.save(nb)
    spec = replace(harness.registry.spec('check_readiness'), reuse_running=lambda args: True,
        bindings=lambda d, a, c: d.runtime_bindings(str(Path(a.log_dir) / c)))
    result = harness._provider_run(spec, request)
    assert result['status'] == 'ready'
    assert result['cell_id'] not in {'orphaned-old', 'newer-finished'}


def test_notebook_publication_preserves_executing_action(setup, monkeypatch):
    harness, execution, kwargs = unit_harness(setup)
    book = Notebook(kwargs['notebook'])
    def execute(cell, folder):
        stale = book.read()
        next(c for c in stale.cells if c.id == cell.id).metadata.fungen.status = 'prepared'
        with pytest.raises(ValueError, match='stale notebook publication'):
            book.save(stale)
        return {'status': 'ready', 'backend': 'test-double'}
    monkeypatch.setattr(execution, 'execute', execute)
    assert harness.run('check_readiness', CheckReadiness(**kwargs))['status'] == 'ready'


def test_interrupted_readiness_recovers_buffered_lsf_output_only_by_exact_stem(setup, monkeypatch):
    deployment, kwargs = setup
    deployment.backend = 'lsf'
    execution = Executor(deployment, host_approved=True)
    stem = str(Path(kwargs['notebook']).parent / 'buffered')
    cell = nbformat.v4.new_code_cell(metadata={'fungen': {'slots': {'bindings': {'log_stem': stem}}}})
    records = [{'JOBID': '123', 'STAT': 'RUN', 'OUTPUT_FILE': stem + '.%J.out'},
               {'JOBID': '456', 'STAT': 'RUN', 'OUTPUT_FILE': stem + '-other.456.out'}]
    monkeypatch.setattr('fungen_operator.execution.subprocess.run', lambda *a, **k:
                        SimpleNamespace(returncode=0, stdout=json.dumps({'RECORDS': records})))
    monkeypatch.setattr(execution, 'controller_scheduler', lambda s,j: {'status': 'RUN', 'job_id': j})
    result = execution.recover_readiness(cell)
    assert result['job_id'] == '123' and result['status'] == 'executing'
    records.append({'JOBID': '789', 'STAT': 'RUN', 'OUTPUT_FILE': stem + '.789.out'})
    assert execution.recover_readiness(cell) is None
    cell.metadata.fungen['result'] = {'job_id': '123', 'status': 'executing'}
    monkeypatch.setattr(execution, 'controller_scheduler', lambda s,j: {'status': 'DONE', 'job_id': j})
    monkeypatch.setattr(execution, 'logs', lambda s,j: {'stdout': 'This was a dry-run\n'})
    assert execution.recover_readiness(cell)['status'] == 'ready'


@pytest.mark.parametrize('failed', [False, True])
def test_execution_publication_preserves_intervening_notebook_history(setup, monkeypatch, failed):
    harness, execution, kwargs = unit_harness(setup)
    book = Notebook(kwargs['notebook'])

    def execute(cell, folder):
        newer = book.read()
        newer.metadata['retained_observation'] = 'written during execution'
        newer.cells.append(nbformat.v4.new_markdown_cell('Retained native observation'))
        book.save(newer)
        cell.outputs = [nbformat.v4.new_output('stream', name='stdout', text='native result\n')]
        cell.execution_count = 1
        if failed:
            raise RuntimeError('bounded native execution failure')
        return {'status': 'ready', 'backend': 'test-double'}

    monkeypatch.setattr(execution, 'execute', execute)
    if failed:
        with pytest.raises(RuntimeError, match='bounded native execution failure'):
            harness.run('check_readiness', CheckReadiness(**kwargs))
    else:
        harness.run('check_readiness', CheckReadiness(**kwargs))
    saved = book.read()
    assert saved.metadata.get('retained_observation') == 'written during execution'
    assert any(c.source == 'Retained native observation' for c in saved.cells)
    cell = next(c for c in active(saved) if c.metadata.fungen.action == 'check_readiness')
    assert cell.metadata.fungen.status == ('unknown' if failed else 'ready')
    assert cell.outputs[0].text == 'native result\n'


@pytest.mark.parametrize('change', ['missing', 'identity'])
def test_execution_publication_refuses_changed_execution_record(setup, monkeypatch, change):
    harness, execution, kwargs = unit_harness(setup)
    book = Notebook(kwargs['notebook'])

    def execute(cell, folder):
        newer = book.read()
        if change == 'missing':
            newer.cells = [c for c in newer.cells if c.id != cell.id]
        else:
            recorded = next(c for c in newer.cells if c.id == cell.id)
            recorded.metadata.fungen.identity['changed_during_execution'] = True
        book.save(newer)
        return {'status': 'ready', 'backend': 'test-double'}

    monkeypatch.setattr(execution, 'execute', execute)
    with pytest.raises(ValueError, match='executed cell changed or disappeared'):
        harness.run('check_readiness', CheckReadiness(**kwargs))


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
    assert "--cores 72 --jobs 2000" in source and "--latency-wait 120" in source
    assert source.endswith("  all\nLSF\n")
    assert "--force" not in source and "--dry-run" not in source
    assert render("initiate_run", copy.deepcopy(slots)) == source


def test_native_job_dependency_keeps_readiness_gate(setup):
    harness, execution, kwargs = unit_harness(setup)
    args = InitiateRun(**kwargs, depends_on=["123", "456"])
    with pytest.raises(ValueError, match="successful matching"):
        harness.run("initiate_run", args)
    harness.run("check_readiness", CheckReadiness(**kwargs))
    assert harness.run("initiate_run", args)["status"] == "submitted"
    assert '#BSUB -w "done(123) && done(456)"' in execution.cells[-1]
    for bad in [["1); exit"], ["0"], ["-1"], [123], ["1\n#BSUB -q express"]]:
        with pytest.raises(ValidationError):
            InitiateRun(**kwargs, depends_on=bad)


@pytest.mark.parametrize("field,value", [("targets", ["--forceall"]), ("targets", ["x --forceall"]),
    ("targets", ["x; touch /tmp/bad"]), ("targets", ["$(id)"]), ("targets", ["../escape"]),
    ("targets", ["x\n--forceall"]), ("jobs", 0), ("jobs", True), ("memory_gb", 0),
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
    def delayed(cell, folder):
        result = original_execute(cell, folder)
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


DRY_RUN_LOG = "Job stats:\njob count\nall 1\ntotal 21\nThis was a dry-run (flag -n).\n"


def completed_readiness(setup, monkeypatch, states, logs, *, cell_error=False):
    """Run the real executor and notebook lifecycle with external observations simulated."""
    harness, _, kwargs = unit_harness(setup)
    executor = Executor(setup[0])
    harness.executor = executor
    delays, queries, log_reads = [], [], []

    class CompletedCell:
        def __init__(self, notebook, **options):
            self.notebook = notebook

        def create_kernel_manager(self):
            return SimpleNamespace(kernel_spec=SimpleNamespace(argv=[]))

        def execute(self, **options):
            cell = self.notebook.cells[0]
            cell.execution_count = 1
            cell.outputs = [nbformat.v4.new_output("stream", name="stdout",
                text="Job <1001> is submitted to queue <express>.\n<<Job is finished>>\n")]
            if cell_error:
                cell.outputs.append(nbformat.v4.new_output("error", ename="CalledProcessError",
                    evalue="bsub -K returned nonzero", traceback=[]))

    def scheduler(job_id):
        observed = copy.deepcopy(states[min(len(queries), len(states) - 1)])
        queries.append(job_id)
        return {"job_id": job_id, **observed}

    def read_logs(stem, job_id):
        observed = copy.deepcopy(logs[min(len(log_reads), len(logs) - 1)])
        log_reads.append((stem, job_id))
        return observed

    monkeypatch.setattr("fungen_operator.execution.NotebookClient", CompletedCell)
    monkeypatch.setattr("fungen_operator.execution.time.sleep", delays.append)
    monkeypatch.setattr(executor, "scheduler", scheduler)
    monkeypatch.setattr(executor, "logs", read_logs)
    result = harness.run("check_readiness", CheckReadiness(**kwargs))
    nb = Notebook(kwargs["notebook"]).read()
    verify(nb)
    assert active(nb)[-1].metadata.fungen.result == {
        k: v for k, v in result.items() if k not in {"cell_id", "notebook"}}
    assert queries == ["1001"] * len(log_reads)
    return result, harness, kwargs, delays


@pytest.mark.parametrize("exit_code", ["0", ""])
def test_readiness_reconciles_run_to_done(setup, monkeypatch, exit_code):
    result, harness, kwargs, delays = completed_readiness(setup, monkeypatch,
        [{"status": "RUN", "exit_code": ""}, {"status": "DONE", "exit_code": exit_code}],
        [{"stdout": DRY_RUN_LOG}])
    assert result["status"] == "ready"
    assert result["synchronous_exit_code"] == 0
    assert [s["status"] for s in result["scheduler_observations"]] == ["RUN", "DONE"]
    assert result["scheduler"]["status"] == "DONE" and delays
    assert "total 21" in result["logs"]["stdout"]
    # The unchanged gate accepts this recorded readiness for the same graph.
    assert harness.run("initiate_run", InitiateRun(**kwargs))["status"] == "submitted"


@pytest.mark.parametrize("states,logs,cell_error,expected", [
    ([{"status": "RUN"}, {"status": "EXIT", "exit_code": "17"}],
     [{"stdout": DRY_RUN_LOG}], False, "failed"),
    ([{"status": "DONE", "exit_code": "17"}],
     [{"stdout": DRY_RUN_LOG}], False, "failed"),
    ([{"status": "DONE", "exit_code": "0"}],
     [{"stdout": DRY_RUN_LOG}], True, "failed"),
    ([{"status": "RUN"}, {"status": "UNKNOWN"}],
     [{"stdout": DRY_RUN_LOG}], False, "unknown"),
    ([{"status": "UNKNOWN"}], [{"stdout": DRY_RUN_LOG}], False, "unknown"),
    ([{"status": "RUN"}], [{"stdout": DRY_RUN_LOG}], False, "unknown"),
    ([{"status": "PEND"}], [{"stdout": DRY_RUN_LOG}], False, "unknown"),
    ([{"status": "DONE", "exit_code": "unknown"}],
     [{"stdout": DRY_RUN_LOG}], False, "unknown"),
    ([{"status": "DONE", "exit_code": "0"}], [{}], False, "unknown"),
    ([{"status": "DONE", "exit_code": "0"}],
     [{"stdout": "Successfully completed.\n"}], False, "unknown"),
])
def test_readiness_preserves_incomplete_and_failed_evidence(
        setup, monkeypatch, states, logs, cell_error, expected):
    result, harness, kwargs, delays = completed_readiness(
        setup, monkeypatch, states, logs, cell_error=cell_error)
    assert result["status"] == expected
    assert sum(delays) <= 7
    with pytest.raises(ValueError, match="successful matching check_readiness"):
        harness.run("initiate_run", InitiateRun(**kwargs))


@pytest.mark.parametrize("native,expected", [
    (DRY_RUN_LOG, "ready"),
    ("Nothing to be done (all requested files are present and up to date).\n", "nothing_to_do"),
])
def test_readiness_rereads_delayed_logs(setup, monkeypatch, native, expected):
    result, _, _, delays = completed_readiness(setup, monkeypatch,
        [{"status": "DONE", "exit_code": "0"}], [{}, {"stdout": native}])
    assert result["status"] == expected and delays
    assert result["logs"] == {"stdout": native}
    assert len(result["scheduler_observations"]) == 2


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


def test_stdio_reports_blocked_local_sockets(monkeypatch):
    def denied():
        raise PermissionError("Operation not permitted")
    monkeypatch.setattr("fungen_operator.server.socket.socketpair", denied)
    with pytest.raises(SystemExit, match="approved host execution path"):
        serve_stdio(None)


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_stdio_tools_and_scientific_approval(setup, tmp_path, mode):
    """Real subprocess/JSON-RPC connection; live backend stages without submitting."""
    deployment, args = setup
    deployment = deployment.model_copy(update={"backend": "lsf"})
    deployment_path = tmp_path / "deployment.json"
    deployment_path.write_text(deployment.model_dump_json())
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fungen_operator", "serve", "--deployment", str(deployment_path)],
        cwd=str(Path(__file__).resolve().parents[1]),
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    answers = iter([False, True])
    asked = []

    async def simulated_human(ctx, params):
        asked.append(params.message)
        assert "pca.n_pcs" in params.message
        assert not Path(args["notebook"]).exists()
        assert not Path(args["configfile"]).exists()
        return ElicitResult(action="accept", content={"approve": next(answers)})

    async def exercise():
        async with Client(server, mode=mode, read_timeout_seconds=15,
                          elicitation_callback=simulated_human) as client:
            listed = await client.list_tools()
            assert {t.name for t in listed.tools} == {
                "prepare_config", "check_readiness", "initiate_run", "inspect_run", "control_run"}
            request = {"request": {**args, "parameters": {"pca.n_pcs": 1}}}
            declined = await client.call_tool("prepare_config", request)
            assert not declined.is_error, declined
            assert declined.structured_content["status"] == "approval_declined"
            accepted = await client.call_tool("prepare_config", request)
            assert not accepted.is_error, accepted
            assert accepted.structured_content["status"] == "host_approval_required"
            assert "execute" in accepted.structured_content["host_command"]
            inspected = await client.call_tool("inspect_run", {"request": {"notebook": args["notebook"]}})
            assert not inspected.is_error, inspected
            assert inspected.structured_content["status"] == "host_approval_required"
            assert "inspect" in inspected.structured_content["host_command"]
            invalid = await client.call_tool("initiate_run", {
                "request": {**run_args(deployment, args), "targets": ["--forceall"]}})
            assert invalid.is_error

    asyncio.run(exercise())
    assert len(asked) == 2
    nb = Notebook(args["notebook"]).read()
    assert active(nb)[0].metadata.fungen.approval.channel == "mcp_human_elicitation"
    assert not Path(args["configfile"]).exists()
    assert not Path(deployment.conda_env, "scheduler.json").exists()


@pytest.mark.parametrize("action,model", [("check_readiness", CheckReadiness),
                                         ("initiate_run", InitiateRun)])
def test_rerun_triggers_render_only_when_selected(setup, action, model):
    deployment, args = setup
    values = model(**run_args(deployment, args))
    bindings = {"snakefile": deployment.snakefile, "profile_path": deployment.profile_path,
                "conda_sh": deployment.conda_sh, "conda_env": deployment.conda_env,
                "log_stem": str(Path(deployment.run_root, "logs/attempt"))}
    arguments = values.model_dump()
    legacy = {k: v for k, v in arguments.items() if k != "rerun_triggers"}
    original = render(action, {"arguments": legacy, "bindings": bindings})
    assert render(action, {"arguments": arguments, "bindings": bindings}) == original
    assert "--rerun-triggers" not in original
    arguments["rerun_triggers"] = ["mtime", "input", "code", "software-env"]
    selected = render(action, {"arguments": arguments, "bindings": bindings})
    option = "  --rerun-triggers mtime input code software-env " + "\\\n"
    assert selected == original.replace("  --printshellcmds", option + "  --printshellcmds")
    arguments["rerun_triggers"] = ["mtime", "params", "input", "software-env", "code"]
    assert "--rerun-triggers mtime params input software-env code" in render(
        action, {"arguments": arguments, "bindings": bindings})


@pytest.mark.parametrize("value", [[], ["mtime", "mtime"], ["--forceall"],
    ["mtime; id"], ["input\n--forceall"], "mtime input", [True], {"mtime": True},
    ["mtime", "params", "input", "software-env", "code", "mtime"]])
@pytest.mark.parametrize("model", [CheckReadiness, InitiateRun])
def test_invalid_rerun_triggers_rejected(setup, value, model):
    deployment, args = setup
    with pytest.raises(ValidationError):
        model(**run_args(deployment, args), rerun_triggers=value)


def test_rerun_triggers_require_matching_readiness_and_preserve_legacy_fingerprint(setup):
    harness, executor, kwargs = unit_harness(setup)
    args = InitiateRun(**kwargs)
    legacy = args.model_dump()
    for option in ("rerun_triggers", "allowed_rules", "keep_incomplete"):
        legacy.pop(option, None)
    for key in ("job_name", "walltime_minutes", "phase", "log_dir", "depends_on", "defer_readiness"):
        legacy.pop(key, None)
    assert harness._run_fingerprint(args, {}, "config") == digest(
        {"arguments": legacy, "identity": {}, "config": "config"})
    harness.run("check_readiness", CheckReadiness(**kwargs))
    selected = {**kwargs, "rerun_triggers": ["mtime", "input", "code", "software-env"]}
    with pytest.raises(ValueError, match="matching"):
        harness.run("initiate_run", InitiateRun(**selected))
    harness.run("check_readiness", CheckReadiness(**selected))
    for different in (kwargs, {**selected, "rerun_triggers": ["mtime", "params"]}):
        with pytest.raises(ValueError, match="matching"):
            harness.run("initiate_run", InitiateRun(**different))
    result = harness.run("initiate_run", InitiateRun(**selected))
    assert result["status"] == "submitted"
    verify(Notebook(kwargs["notebook"]).read())
