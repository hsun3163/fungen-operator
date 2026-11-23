"""Regression coverage for displaced native submission records."""

import copy
from types import SimpleNamespace

import nbformat
import pytest

from fungen_operator.notebook import Notebook


def prepared_book(tmp_path):
    registry = SimpleNamespace(render=lambda *args: 'pass')
    book = Notebook(tmp_path / 'operator.ipynb', registry)
    cell = nbformat.v4.new_code_cell('pass', id='native-controller', metadata={
        'fungen': {'action': 'initiate_run', 'template_version': '1',
                   'slots': {'arguments': {}, 'bindings': {}},
                   'identity': {'source': 'frozen'}, 'status': 'prepared'}})
    book.save(nbformat.v4.new_notebook(cells=[cell]))
    return book


@pytest.mark.parametrize('published', ['executing', 'submitted'])
def test_stale_prepared_snapshot_cannot_displace_started_controller(tmp_path, published):
    book = prepared_book(tmp_path)
    stale = book.read()
    current = book.read()
    meta = current.cells[0].metadata.fungen
    meta.status = published
    if published == 'submitted':
        meta['result'] = {'job_id': '123', 'scheduler': {'status': 'RUN'}}
    book.save(current)
    before = book.path.read_bytes()
    with pytest.raises(ValueError, match='stale notebook publication'):
        book.save(stale)
    assert book.path.read_bytes() == before


@pytest.mark.parametrize('change', ['missing', 'receipt', 'identity'])
def test_publication_retains_submitted_history_and_original_binding(tmp_path, change):
    book = prepared_book(tmp_path)
    current = book.read()
    current.cells[0].metadata.fungen.update(
        status='submitted', result={'job_id': '123', 'scheduler': {'status': 'RUN'}})
    book.save(current)
    stale = copy.deepcopy(current)
    if change == 'missing':
        stale.cells = []
    elif change == 'receipt':
        stale.cells[0].metadata.fungen.result.job_id = '456'
    else:
        stale.cells[0].metadata.fungen.identity.source = 'different'
    with pytest.raises(ValueError, match='executed cell changed or disappeared'):
        book.save(stale)
    assert book.read().cells[0].metadata.fungen.result.job_id == '123'


def test_native_terminal_observation_preserves_receipt_and_new_history(tmp_path):
    book = prepared_book(tmp_path)
    nb = book.read()
    nb.cells[0].metadata.fungen.update(
        status='submitted', result={'job_id': '123', 'scheduler': {'status': 'RUN'}})
    book.save(nb)
    nb = book.read()
    nb.cells[0].metadata.fungen.result.scheduler.status = 'DONE'
    nb.cells.append(nbformat.v4.new_markdown_cell('A retained native observation'))
    book.save(nb)
    restored = book.read()
    assert restored.cells[0].metadata.fungen.result.scheduler.status == 'DONE'
    assert restored.cells[-1].source == 'A retained native observation'


@pytest.mark.parametrize('change', ['missing', 'prepared', 'result'])
def test_completed_readonly_collection_cannot_be_displaced(tmp_path, change):
    book = prepared_book(tmp_path)
    nb = book.read()
    nb.cells[0].metadata.fungen.action = 'correct_refinemapping'
    nb.cells[0].metadata.fungen.update(
        status='completed', started='2026-11-14T16:00:00+00:00',
        result={'status': 'completed', 'logs': {'stdout': 'native counts'}})
    book.save(nb)
    before = book.path.read_bytes()
    stale = copy.deepcopy(nb)
    if change == 'missing':
        stale.cells = []
    elif change == 'prepared':
        stale.cells[0].metadata.fungen.status = 'prepared'
    else:
        stale.cells[0].metadata.fungen.pop('result')
    with pytest.raises(ValueError, match='stale notebook publication'):
        book.save(stale)
    assert book.path.read_bytes() == before


def test_completed_readonly_collection_allows_fresh_observation(tmp_path):
    book = prepared_book(tmp_path)
    nb = book.read()
    nb.cells[0].metadata.fungen.action = 'correct_refinemapping'
    nb.cells[0].metadata.fungen.update(
        status='completed', result={'status': 'completed', 'logs': {'stdout': 'native counts'}})
    book.save(nb)
    fresh = book.read()
    fresh.cells.append(nbformat.v4.new_markdown_cell('Next native observation'))
    book.save(fresh)
    assert book.read().cells[0].metadata.fungen.result.logs.stdout == 'native counts'


@pytest.mark.parametrize('status', ['prepared', 'host_approval_required'])
def test_stale_writer_cannot_drop_published_unexecuted_action(tmp_path, status):
    book = prepared_book(tmp_path)
    stale = book.read()
    current = book.read()
    cell = copy.deepcopy(current.cells[0])
    cell.id = 'native-observer'
    cell.metadata.fungen.status = status
    current.cells[0].metadata['tags'] = ['superseded']
    current.cells.append(cell)
    book.save(current)
    published = book.path.read_bytes()
    with pytest.raises(ValueError, match='stale notebook publication'):
        book.save(stale)
    assert book.path.read_bytes() == published


def test_published_prepared_action_can_advance_to_execution(tmp_path):
    book = prepared_book(tmp_path)
    current = book.read()
    current.cells[0].metadata.fungen.status = 'executing'
    book.save(current)
    current = book.read()
    current.cells[0].metadata.fungen.update(status='completed', result={'status': 'completed'})
    book.save(current)
    assert book.read().cells[0].metadata.fungen.status == 'completed'


def test_unchanged_historical_prepared_cell_with_started_timestamp_is_retained(tmp_path):
    book = prepared_book(tmp_path)
    current = book.read()
    current.cells[0].metadata.fungen.started = '2026-11-14T16:00:00+00:00'
    book.save(current)
    fresh = book.read()
    fresh.cells.append(nbformat.v4.new_markdown_cell('A fresh native observation'))
    book.save(fresh)
    assert book.read().cells[0].metadata.fungen.status == 'prepared'
    assert book.read().cells[0].metadata.fungen.started == '2026-11-14T16:00:00+00:00'
