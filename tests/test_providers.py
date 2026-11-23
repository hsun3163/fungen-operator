"""Deployment-local contracts use the native registry, lifecycle and identity gates."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from fungen_operator.actions import Deployment, MODELS
from fungen_operator.fixture import create_fixture
from fungen_operator.harness import Harness
from fungen_operator.notebook import Notebook, verify
from fungen_operator.providers import builtin_registry


PROVIDER = '''from fungen_operator.providers import Provider, ActionSpec
from fungen_operator.slots import Model, PathSlot
class Request(Model):
    notebook: PathSlot
    configfile: PathSlot
    workdir: PathSlot
    log_dir: PathSlot

def create_provider(deployment):
    return Provider(actions=(ActionSpec("note", Request,
        {"1": lambda slots: "print('old')\\n", "2": lambda slots: "print('VALUE')\\n"},
        current_version="2", bindings=lambda d,a,c: {}, order=1),))
'''


@pytest.fixture
def provided(tmp_path):
    deployment = create_fixture(tmp_path / 'fixture')
    deployment.backend = 'lsf'
    folder = tmp_path / 'deployment'
    folder.mkdir()
    provider = folder / 'provider.py'
    provider.write_text(PROVIDER.replace('VALUE', 'first'))
    deployment.action_provider = 'provider.py:create_provider'
    path = folder / 'deployment.json'
    path.write_text(deployment.model_dump_json())
    deployment = Deployment.load(path)
    args = dict(notebook=str(Path(deployment.run_root, 'operator.ipynb')),
                configfile=str(Path(deployment.run_root, 'config.yml')),
                workdir=str(Path(deployment.run_root, 'work')),
                log_dir=str(Path(deployment.run_root, 'logs')))
    return deployment, path, provider, args


def test_provider_registry_isolated_and_relative_to_deployment(provided, tmp_path):
    deployment, path, provider, args = provided
    registry = deployment.registry
    assert set(registry.models) == set(MODELS) | {'note'}
    assert 'note' not in builtin_registry().models
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'provider.py').write_text(PROVIDER.replace('VALUE', 'second'))
    (other / 'deployment.json').write_text(path.read_text())
    second = Deployment.load(other / 'deployment.json')
    slots = {'arguments': args, 'bindings': {}}
    assert registry.render('note', slots) == "print('first')\n"
    assert second.registry.render('note', slots) == "print('second')\n"
    assert registry.render('note', slots) == "print('first')\n"
    assert deployment.registry.source_paths == (str(provider),)


def test_provider_versions_preserve_saved_source_and_reject_unknown(provided):
    deployment, _, _, args = provided
    registry = deployment.registry
    book = Notebook(args['notebook'], registry)
    nb = book.read()
    cell = book.append(nb, 'note', {'arguments': args, 'bindings': {}}, {}, 'fixed')
    assert cell.metadata.fungen.template_version == '2'
    cell.metadata.fungen.template_version = '1'
    cell.source = "print('old')\n"
    verify(nb, registry)
    cell.metadata.fungen.template_version = '999'
    with pytest.raises(ValueError, match='unknown template version'):
        verify(nb, registry)
    with pytest.raises(ValueError, match='unknown action'):
        verify(nb)


@pytest.mark.parametrize("reserved", ["prepare_config", "inspect_run"])
def test_duplicate_builtin_and_non_strict_models_are_refused(provided, reserved):
    _, path, provider, _ = provided
    provider.write_text(PROVIDER.replace('"note"', '"' + reserved + '"'))
    with pytest.raises(ValueError, match='duplicate'):
        Deployment.load(path)
    provider.write_text(PROVIDER.replace('class Request(Model):', 'from pydantic import BaseModel\nclass Request(BaseModel):'))
    with pytest.raises(ValueError, match='strict'):
        Deployment.load(path)


def test_unknown_current_version_is_refused(provided):
    _, path, provider, _ = provided
    provider.write_text(PROVIDER.replace('current_version="2"', 'current_version="3"'))
    with pytest.raises(ValueError, match='unknown current template version'):
        Deployment.load(path)


def test_provider_edit_updates_identity_renderer_and_pending_gate(provided):
    deployment, path, provider, args = provided
    h = Harness(deployment, deployment_file=str(path))
    request = h.registry.models['note'](**args)
    result = h.run('note', request)
    assert result['status'] == 'host_approval_required'
    first = deployment.identity()
    provider.write_text(provider.read_text().replace('first', 'changed'))
    assert deployment.identity()['source_hashes'][str(provider)] != first['source_hashes'][str(provider)]
    assert deployment.registry.render('note', {'arguments': args, 'bindings': {}}) == "print('changed')\n"
    # A fresh host process uses the current provider and rejects staged old source.
    with pytest.raises(ValueError, match='re-render|changed'):
        Harness(Deployment.load(path), deployment_file=str(path)).execute_pending(args['notebook'], result['cell_id'])


def test_cli_deployment_schemas_and_verify_use_same_registry(provided):
    deployment, path, _, args = provided
    book = Notebook(args['notebook'], deployment.registry)
    book.append(book.read(), 'note', {'arguments': args, 'bindings': {}}, {}, 'fixed')
    schemas = subprocess.run([sys.executable, '-m', 'fungen_operator', 'schemas', '--deployment', str(path)],
                             text=True, capture_output=True, check=True)
    assert set(json.loads(schemas.stdout)) == set(MODELS) | {'inspect_run', 'note'}
    plain = subprocess.run([sys.executable, '-m', 'fungen_operator', 'schemas'],
                           text=True, capture_output=True, check=True)
    assert set(json.loads(plain.stdout)) == set(MODELS) | {'inspect_run'}
    result = subprocess.run([sys.executable, '-m', 'fungen_operator', 'verify', args['notebook'],
                             '--deployment', str(path)], text=True, capture_output=True)
    assert result.returncode == 0 and 're-render identically' in result.stdout


def test_operational_patterns_match_exact_segments_and_preserve_science(provided):
    deployment, _, _, _ = provided
    deployment.operational_parameters = ['minerva', 'tasks.*.queue', 'tasks.*.J']
    before = {'minerva': '/old.yml', 'tasks': {'step': {'queue': 'express', 'J':10000, 'model':'old'}}}
    after = copy.deepcopy(before)
    after['minerva'] = '/new.yml'
    after['tasks']['step'].update(queue='premium', J=5000, model='new')
    assert deployment.scientific_diff(before, after) == {'tasks.step.model': {'before':'old','after':'new'}}
    for path in ('tasks.step.queue', 'tasks.step.J', 'minerva'):
        assert deployment.is_operational(path, leaf_only=True)
    for path in ('tasks.step', 'tasks.step.queue.nested', 'tasks.step.extra.queue', 'tasks.bad;name.J', 'tasks..J'):
        assert not deployment.is_operational(path, leaf_only=True)
