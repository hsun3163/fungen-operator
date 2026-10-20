"""Live resource edits use the real harness and host materialization boundary."""
import copy
from pathlib import Path

import pytest
import yaml

from test_harness import setup, LocalExecution, run_args
from fungen_operator.actions import PrepareConfig, CheckReadiness, InitiateRun, set_parameter
from fungen_operator.execution import Executor
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, active


RESOURCES = {
    'sos_tasks.rss.mem': '34G', 'sos_tasks.rss.walltime': '11h',
    'sos_tasks.rss.queue': 'premium', 'jobs.rss.mem_mb': 34000,
    'jobs.rss.runtime': 120, 'jobs.rss.queue': 'premium',
}
OTHER = {'cwd': None, 'pca.n_pcs': 2, 'outputs': ['different.txt'],
         'resources.default.threads': 2, 'resources.default.mem_mb': 50000,
         'resources.default.runtime': 120, 'sos_tasks.rss.job_size': 2,
         'jobs.rss.threads': 2}


def running(setup, state='RUN'):
    d, args = setup
    cfg = d.defaults()
    cfg['sos_tasks'] = {'rss': {'mem': '56G', 'walltime': '1h', 'queue': 'express', 'job_size': 1}}
    cfg['jobs'] = {'rss': {'mem_mb': 56000, 'runtime': 60, 'queue': 'express', 'threads': 1}}
    Path(d.default_config).write_text(yaml.safe_dump(cfg))
    d.backend = 'lsf'
    d.operational_parameters += list(RESOURCES)
    h = Harness(d, LocalExecution())
    h.prepare_config(h.propose_config(PrepareConfig(**args)))
    kw = run_args(d, args)
    h.run('check_readiness', CheckReadiness(**kw))
    h.run('initiate_run', InitiateRun(**kw))
    book = Notebook(args['notebook'])
    nb = book.read()
    active(nb)[-1].metadata.fungen.result.scheduler.status = state
    book.save(nb)
    return d, args, kw


def host(d, state):
    ex = Executor(d, host_approved=True)
    ex.scheduler = lambda job: {'job_id': job, 'status': state}
    return Harness(d, ex)


@pytest.mark.parametrize('state', ['RUN', 'PEND'])
@pytest.mark.parametrize('key,value', RESOURCES.items())
def test_pending_resource_host_materializes(setup, state, key, value):
    d, args, _ = running(setup, state)
    stage = Harness(d)
    result = stage.prepare_config(stage.propose_config(PrepareConfig(**args, parameters={key: value})))
    assert result['status'] == 'host_approval_required'
    result = host(d, state).execute_pending(args['notebook'], result['cell_id'])
    assert result['status'] == 'materialized'
    cfg = yaml.safe_load(Path(args['configfile']).read_text())
    section, member, field = key.split('.')
    assert cfg[section][member][field] == value


@pytest.mark.parametrize('state', ['RUN', 'PEND'])
def test_prepare_resource_uses_same_host_guard(setup, state):
    d, args, _ = running(setup, state)
    h = host(d, state)
    result = h.prepare_config(h.propose_config(PrepareConfig(**args, parameters=RESOURCES)))
    assert result['status'] == 'materialized'


@pytest.mark.parametrize('key,value', OTHER.items())
@pytest.mark.parametrize('mixed', [False, True])
@pytest.mark.parametrize('pending', [False, True])
def test_other_fixture_fields_and_mixed_edits_blocked(setup, key, value, mixed, pending):
    d, args, _ = running(setup)
    value = args['workdir'] if key == 'cwd' else value
    params = {key: value, **({'sos_tasks.rss.mem': '34G'} if mixed else {})}
    # cwd is path-bound: represent a real different graph via the request itself.
    request = PrepareConfig(**args, parameters=params)
    if key == 'cwd':
        request = request.model_copy(update={'workdir': args['workdir'] + '_other'})
        request.parameters['cwd'] = request.workdir
    h = host(d, 'RUN')
    before = Path(args['configfile']).read_bytes()
    try:
        stage = Harness(d) if pending else h
        proposal = stage.propose_config(request)
        proof = {'fingerprint': proposal['fingerprint']} if proposal['scientific_changes'] else None
        result = stage.prepare_config(proposal, proof)
        if pending:
            h.execute_pending(args['notebook'], result['cell_id'])
    except ValueError:
        pass
    else:
        pytest.fail('nonresource edit passed active-controller guard')
    assert Path(args['configfile']).read_bytes() == before


@pytest.mark.parametrize('path', [(), ('sos_tasks',), ('sos_tasks','rss'),
    ('jobs','rss'), ('sos_tasks','rss','job_size'), ('jobs','rss','threads'),
    ('sos_tasks','rss','mem','nested'), ('x','sos_tasks','rss','mem'),
    ('sos_tasks','rss.extra','mem'), ('sos_tasks','','mem'),
    ('sos_tasks','rss\n','mem'), ('sos_tasks','rss;echo','mem'),
    ('jobs','rss','runtime\n'), ('resources','rss','mem_mb')])
def test_strict_resource_path(setup, path):
    d, _ = setup
    d.operational_parameters = list(RESOURCES)
    assert not d.is_operational(".".join(path), leaf_only=True)


@pytest.mark.parametrize('params', [
    {'sos_tasks.rss': {'mem':'34G', 'walltime':'1h', 'queue':'express', 'job_size':1}},
    {'sos_tasks.rss.mem': '34G; echo unsafe'},
    {'sos_tasks.rss.extra': '34G'},
    {'jobs.rss': {'mem_mb':34000}},
])
def test_parent_replacement_shell_and_unknown_catalog_blocked(setup, params):
    d, args, _ = running(setup)
    h = host(d, 'RUN')
    with pytest.raises(ValueError):
        p = h.propose_config(PrepareConfig(**args, parameters=params))
        h.prepare_config(p, {'fingerprint':p['fingerprint']})


@pytest.mark.parametrize('drift', ['source', 'scientific', 'resource', 'comment'])
@pytest.mark.parametrize('pending', [False, True])
def test_drift_still_blocks_live_resource_edit(setup, drift, pending):
    d, args, _ = running(setup)
    stage = Harness(d) if pending else host(d, 'RUN')
    req = PrepareConfig(**args, parameters={'sos_tasks.rss.mem':'34G'})
    proposal = stage.propose_config(req)
    result = stage.prepare_config(proposal) if pending else None
    if drift == 'source':
        path = Path(d.snakefile)
        path.write_text(path.read_text() + '# source drift\n')
    else:
        path = Path(args['configfile'])
        if drift == 'comment':
            path.write_text(path.read_text() + '# external drift\n')
        else:
            cfg = yaml.safe_load(path.read_text())
            set_parameter(cfg, 'pca.n_pcs' if drift == 'scientific' else 'sos_tasks.rss.mem', 3 if drift == 'scientific' else '99G')
            path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):
        if pending:
            host(d, 'RUN').execute_pending(args['notebook'], result['cell_id'])
        else:
            stage.prepare_config(proposal)


@pytest.mark.parametrize('state', ['RUN','PEND','UNKNOWN'])
@pytest.mark.parametrize('action', ['check_readiness', 'initiate_run', 'replay'])
def test_nonconfig_idle_gates_remain(setup, state, action):
    d, args, kw = running(setup, state)
    h = host(d, state)
    with pytest.raises(ValueError, match='inspect before'):
        if action == 'replay':
            h.replay(args['notebook'])
        else:
            h.run(action, (CheckReadiness if action == 'check_readiness' else InitiateRun)(**kw))


def test_unknown_controller_still_blocks_resource_edit(setup):
    d, args, _ = running(setup, 'UNKNOWN')
    h = host(d, 'UNKNOWN')
    with pytest.raises(ValueError, match='inspect before'):
        h.prepare_config(h.propose_config(PrepareConfig(**args, parameters=RESOURCES)))


@pytest.mark.parametrize('extra', ['pca.n_pcs', 'resources.default.mem_mb'])
def test_saved_actual_proposal_cannot_hide_mixed_diff(setup, extra):
    from fungen_operator.actions import render
    d, args, _ = running(setup)
    stage = Harness(d)
    r = stage.prepare_config(stage.propose_config(PrepareConfig(**args, parameters={'sos_tasks.rss.mem':'34G'})))
    book = Notebook(args['notebook'])
    nb = book.read()
    cell = next(c for c in active(nb) if c.id == r['cell_id'])
    cfg = yaml.safe_load(cell.metadata.fungen.slots.bindings.config_text)
    set_parameter(cfg, extra, 123)
    cell.metadata.fungen.slots.bindings.config_text = yaml.safe_dump(cfg, sort_keys=True)
    cell.source = render('prepare_config', cell.metadata.fungen.slots)
    book.save(nb)
    with pytest.raises(ValueError, match='saved configuration differs'):
        host(d, 'RUN').execute_pending(args['notebook'], r['cell_id'])


@pytest.mark.parametrize('action', ['check_readiness', 'initiate_run'])
def test_pending_nonconfig_still_blocks(setup, action):
    d, args, kw = running(setup)
    cls = CheckReadiness if action == 'check_readiness' else InitiateRun
    result = Harness(d).run(action, cls(**kw))
    with pytest.raises(ValueError, match='inspect before'):
        host(d, 'RUN').execute_pending(args['notebook'], result['cell_id'])


def test_historical_identity_shape_keeps_current_proposal_identity_gate(setup):
    d, args, _ = running(setup)
    book = Notebook(args['notebook'])
    nb = book.read()
    accepted = next(c for c in nb.cells if c.metadata.get('fungen', {}).get('action') == 'prepare_config')
    # Older accepted history predates this optional identity catalog field.
    accepted.metadata.fungen.identity.pop('mapping_parameters')
    book.save(nb)
    stage = Harness(d)
    result = stage.prepare_config(stage.propose_config(PrepareConfig(**args, parameters=RESOURCES)))
    assert host(d, 'RUN').execute_pending(args['notebook'], result['cell_id'])['status'] == 'materialized'
