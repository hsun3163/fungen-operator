"""Invented values only; no live librarian, manuscripts, dictionary or credentials."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import masking as m


@pytest.fixture
def files(tmp_path):
    private = tmp_path / 'private'
    codex = private / 'codex'
    codex.mkdir(parents=True)
    config_path = codex / 'config.toml'
    config_path.write_text('[masking]\ndictionary = "../dict.json.zst"\n')
    config = m.settings(config_path)
    source = tmp_path / 'human.md'
    masked = tmp_path / 'masked.md'
    status = tmp_path / 'masked.slots.tsv'
    return config, source, masked, status, config_path


def export(files, text):
    config, source, masked, status, _ = files
    source.write_text(text)
    m.do_export(config, 'synthetic', {'kind': 'markdown', 'path': str(source)}, masked, status)
    return m.load_dictionary(config['dictionary_path'])


def entries(dictionary):
    return list(dictionary['entries'].values())


def test_repeated_equal_values_and_generic_reuse(files):
    d = export(files, 'First **12** and second **12**.\n')
    assert len(entries(d)) == 1
    assert files[2].read_text().count(entries(d)[0]['id']) == 2
    m.add_entry(d, 'synthetic', '12', [{'text': '12'}], context='another quantity')
    m.save_dictionary(files[0]['dictionary_path'], d)
    d = export(files, 'First **12** and second **12**.\n')
    generic = d['documents']['synthetic']['generics']['12']
    assert len(entries(d)) == 3
    d2 = export(files, 'Again **12**.\n')
    assert len(entries(d2)) == 3 and generic in files[2].read_text()


def test_adjacent_overlapping_and_partial_token_spans(files):
    d = export(files, 'Study CO**UN**T-1.2.\n')
    assert entries(d)[0]['value'] == 'COUNT-1.2'
    assert 'COUNT' not in files[2].read_text()
    d = export(files, 'Study FA**BL**E**1**.\n')
    assert 'FABLE1' in [e['value'] for e in entries(d)]
    dictionary = m.empty_dictionary()
    dictionary['documents']['x'] = {}
    masked = m.mask_runs(dictionary, 'x', [{'text':'GLIMMER', 'bold':True}, {'text':'7', 'bold':True, 'italic':True}])
    assert len(entries(dictionary)) == 1
    assert entries(dictionary)[0]['value'] == 'GLIMMER7'
    assert m.ID.fullmatch(m.plain(masked))


def test_known_value_scan_in_headings_and_without_bold(files):
    d = export(files, '# **FABLE1** heading\n\nObserved **FABLE1** and FABLE1.\n\n## FABLE1 again\n')
    identifier = entries(d)[0]['id']
    assert files[2].read_text().count(identifier) == 4
    assert 'FABLE1' not in files[2].read_text()
    assert len(entries(d)) == 1


def test_heading_bold_structural_but_standalone_body_bold_is_private(files):
    d = export(files, '# **Public title**\n\n**Private body**\n')
    assert [e['value'] for e in entries(d)] == ['Private body']
    assert '**Public title**' in files[2].read_text()


def test_longest_match_token_boundaries_and_normalization(files):
    d = export(files, 'A **FABLE1** and **FABLE1-2** and **−3\u2009×\u00a010−7**.\n\nFABLE1-2 FABLE10 -3 x 10-7.\n')
    masked = files[2].read_text()
    assert 'FABLE10' in masked and 'FABLE1-2' not in masked and '-3 x 10-7' not in masked
    assert len(entries(d)) == 3
    assert m.normalize('−3\u2009×\u00a010−7') == '-3 x 10-7'


def test_whole_bold_span_wins_over_known_subvalue(files):
    d = export(files, 'A **12**.\n')
    d = export(files, 'A **12 synthetic findings**.\n')
    assert any(e['value'] == '12 synthetic findings' for e in entries(d))
    assert len(m.ID.findall(files[2].read_text())) == 1


def test_human_changed_value_gets_new_immutable_id(files):
    first = export(files, 'Observed **12**.\n')
    old = entries(first)[0]
    second = export(files, 'Observed **13**.\n')
    assert len(entries(second)) == 2
    assert second['entries'][old['id']] == old
    second['entries'][old['id']]['value'] = 'different'
    with pytest.raises(m.MaskError, match='immutable-entry'):
        m.save_dictionary(files[0]['dictionary_path'], second)


def test_reordered_and_bold_wrapped_placeholders(files):
    d = export(files, 'First **12**, then **34**.\n')
    first, second = [e['id'] for e in entries(d)]
    files[2].write_text(f'First **{second}**, then {first}.\n')
    m.do_import(files[0], 'synthetic')
    assert files[1].read_text() == 'First **34**, then **12**.\n'
    assert files[2].read_text() == f'First {second}, then {first}.\n'


@pytest.mark.parametrize('bad', ['{{VALUE-AAAA}}', '{{VALUE-123}}', '{{value-ABCD}}', '{{VALUE_ABCD}}',
                                  r'\{\{VALUE-ABCD\}\}', r'\{{VALUE-ABCD}}', '{{VALUE-ABCD}',
                                  '[VALUE-ABCD]', '&#123;&#123;VALUE-ABCD&#125;&#125;'])
def test_unknown_malformed_and_escaped_placeholders(files, bad):
    export(files, 'Original public prose.\n')
    before = files[1].read_bytes()
    files[2].write_text('Invalid ' + bad + '.\n')
    with pytest.raises(m.MaskError):
        m.do_import(files[0], 'synthetic')
    assert files[1].read_bytes() == before


def test_foreign_document_id_is_rejected(files):
    d = export(files, 'A **12**.\n')
    foreign = m.add_entry(d, 'different-document', '99', [{'text':'99'}])
    m.save_dictionary(files[0]['dictionary_path'], d)
    files[2].write_text(f'Count {foreign}.\n')
    with pytest.raises(m.MaskError, match='unknown-placeholder'):
        m.do_import(files[0], 'synthetic')


def test_pending_slot_resolves_once_and_unresolved_needs_human(files):
    export(files, 'A public sentence.\n')
    files[2].write_text('Count **number of imaginary hits** and **unavailable imaginary value**.\n')
    m.do_import(files[0], 'synthetic')
    d = m.load_dictionary(files[0]['dictionary_path'])
    a, b = entries(d)
    assert a['status'] == b['status'] == 'pending'
    assert a['context'] == 'Count number of imaginary hits and unavailable imaginary value.'
    before = files[2].read_text()
    def retrieve(slots):
        assert {s['id'] for s in slots} == {a['id'], b['id']}
        return {a['id']: {'value':'17'}, b['id']: {'status':'needs-human'}}
    m.do_retrieve(files[0], 'synthetic', retrieve)
    resolved = m.load_dictionary(files[0]['dictionary_path'])
    assert resolved['entries'][a['id']]['value'] == '17'
    assert 'description' not in resolved['entries'][a['id']] and 'status' not in resolved['entries'][a['id']]
    assert resolved['entries'][b['id']]['status'] == 'needs-human'
    assert files[2].read_text() == before
    assert '**17**' in files[1].read_text()
    assert a['id'] + '\tresolved' in files[3].read_text()
    assert b['id'] + '\tneeds-human' in files[3].read_text()
    m.do_retrieve(files[0], 'synthetic', lambda _: pytest.fail('resolved slots must never be retrieved again'))


def test_pending_description_exports_to_same_id(files):
    export(files, 'A sentence.\n')
    files[2].write_text('Count **imaginary slot description**.\n')
    m.do_import(files[0], 'synthetic')
    d = m.load_dictionary(files[0]['dictionary_path'])
    expected = entries(d)[0]['id']
    d = export(files, files[1].read_text())
    assert len(entries(d)) == 1 and expected in files[2].read_text()
    assert entries(d)[0]['value'] is None


def test_private_reply_file_commits_only_its_slots_without_another_model(files):
    export(files, 'A public sentence.\n')
    files[2].write_text('Counts **imaginary count** and **unavailable count** and **later count**.\n')
    m.do_import(files[0], 'synthetic')
    before = m.load_dictionary(files[0]['dictionary_path'])
    a, b, c = entries(before)
    reply = files[1].parent / 'private-reply.json'
    reply.write_text(json.dumps({a['id']: {'value': '17'}, b['id']: {'status': 'needs-human'}}))
    with patch.object(m, 'request_slots', side_effect=AssertionError('must not start another model')):
        m.do_retrieve(files[0], 'synthetic', reply_file=reply)
    after = m.load_dictionary(files[0]['dictionary_path'])
    assert after['entries'][a['id']]['value'] == '17'
    assert after['entries'][b['id']]['status'] == 'needs-human'
    assert after['entries'][c['id']] == c
    assert '**17**' in files[1].read_text()
    assert c['id'] + '\tpending' in files[3].read_text()


def test_retry_needs_human_equal_value_preserves_original_bindings(files):
    export(files, 'A public sentence.\n')
    files[2].write_text('Counts **first imaginary count**, **second imaginary count**, '
                        '**unavailable imaginary count**, and **later imaginary count**.\n')
    m.do_import(files[0], 'synthetic')
    a, b, c, d = entries(m.load_dictionary(files[0]['dictionary_path']))
    reply = files[1].parent / 'private-reply.json'
    reply.write_text(json.dumps({a['id']: {'value': '17'},
                                 b['id']: {'status': 'needs-human'},
                                 c['id']: {'status': 'needs-human'}}))
    m.do_retrieve(files[0], 'synthetic', reply_file=reply)
    before = m.load_dictionary(files[0]['dictionary_path'])
    reply.write_text(json.dumps({b['id']: {'value': '17'}}))
    with patch.object(m, 'request_slots', side_effect=AssertionError('must not start another model')):
        m.do_retrieve(files[0], 'synthetic', reply_file=reply)
    after = m.load_dictionary(files[0]['dictionary_path'])
    assert after['entries'][a['id']] == before['entries'][a['id']]
    assert after['entries'][b['id']]['value'] == '17'
    assert 'status' not in after['entries'][b['id']]
    assert after['entries'][c['id']] == before['entries'][c['id']]
    assert after['entries'][d['id']] == before['entries'][d['id']]
    assert files[1].read_text().count('**17**') == 2
    assert b['id'] + '\tresolved' in files[3].read_text()
    # A later export uses the documented generic alias, without rebinding
    # either original slot or resolving any unrelated request.
    exported = export(files, files[1].read_text())
    generic = exported['documents']['synthetic']['generics']['17']
    assert files[2].read_text().count(generic) == 2
    for original in (a, b, c, d):
        assert exported['entries'][original['id']] == after['entries'][original['id']]
    again = export(files, files[1].read_text())
    assert again['documents']['synthetic']['generics']['17'] == generic
    assert len(again['entries']) == len(exported['entries'])


@pytest.mark.parametrize('bad', ['not JSON', '[]', '{}', '{"{{VALUE-AAAA}}":{"value":"19"}}'])
def test_invalid_private_reply_file_changes_nothing(files, bad):
    export(files, 'A public sentence.\n')
    files[2].write_text('Count **imaginary count**.\n')
    m.do_import(files[0], 'synthetic')
    paths = [files[0]['dictionary_path'], *files[1:4]]
    before = [p.read_bytes() for p in paths]
    reply = files[1].parent / 'private-reply.json'
    reply.write_text(bad)
    with pytest.raises(m.MaskError, match='retrieval-response'):
        m.do_retrieve(files[0], 'synthetic', reply_file=reply)
    assert [p.read_bytes() for p in paths] == before


@pytest.mark.parametrize('needs_human', [False, True])
def test_private_reply_cli_and_immutable_binding(files, needs_human):
    export(files, 'A public sentence.\n')
    files[2].write_text('Count **imaginary count**.\n')
    m.do_import(files[0], 'synthetic')
    entry = entries(m.load_dictionary(files[0]['dictionary_path']))[0]
    reply = files[1].parent / 'private-reply.json'
    if needs_human:
        reply.write_text(json.dumps({entry['id']: {'status': 'needs-human'}}))
        m.do_retrieve(files[0], 'synthetic', reply_file=reply)
    reply.write_text(json.dumps({entry['id']: {'value': '17'}}))
    command = [sys.executable, str(Path(m.__file__)), '--config', str(files[4]),
               'retrieve', '--document', 'synthetic', '--reply-file', str(reply)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == 'OK\n'
    assert '**17**' in files[1].read_text()
    paths = [files[0]['dictionary_path'], *files[1:4]]
    before = [p.read_bytes() for p in paths]
    reply.write_text(json.dumps({entry['id']: {'value': '18'}}))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1 and 'retrieval-response' in result.stderr
    assert '18' not in result.stdout + result.stderr
    assert [p.read_bytes() for p in paths] == before


def test_revision_change_blocks_import_and_long_retrieval(files):
    export(files, 'Original **12**.\n')
    files[1].write_text('Human edit **13**.\n')
    with pytest.raises(m.MaskError, match='source-revision-changed'):
        m.do_import(files[0], 'synthetic')
    export(files, 'Public.\n')
    files[2].write_text('Want **imaginary count**.\n')
    m.do_import(files[0], 'synthetic')
    def retrieve(slots):
        files[1].write_text('Another human edit.\n')
        return {slots[0]['id']: {'value':'17'}}
    with pytest.raises(m.MaskError, match='source-revision-changed'):
        m.do_retrieve(files[0], 'synthetic', retrieve)
    assert files[1].read_text() == 'Another human edit.\n'


def test_multirun_formatting_roundtrip(files):
    d = export(files, 'Signal **_FABLE1_ at 2 x 10<sup>−7</sup>** and **H<sub>2</sub>O**.\n')
    assert any(r.get('italic') for r in entries(d)[0]['runs'])
    assert any(r.get('superscript') for r in entries(d)[0]['runs'])
    assert any(r.get('subscript') for r in entries(d)[1]['runs'])
    m.do_import(files[0], 'synthetic')
    assert files[1].read_text() == 'Signal **_FABLE1_ at 2 x 10<sup>−7</sup>** and **H<sub>2</sub>O**.\n'
    assert 'FABLE1' not in files[2].read_text()


def test_dictionary_save_failure_releases_no_masked_output(files):
    with patch.object(m, 'save_dictionary', side_effect=m.MaskError('dictionary-save')):
        with pytest.raises(m.MaskError, match='dictionary-save'):
            export(files, 'Secret **12345**.\n')
    assert not files[2].exists() and not files[3].exists()
    assert not list(files[2].parent.glob('.masked*'))


def test_shared_home_and_dictionary_in_repo_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    shared = tmp_path / '.codex'
    shared.mkdir()
    config = shared / 'config.toml'
    config.write_text('[masking]\ndictionary="../dict.json.zst"\n')
    with pytest.raises(m.MaskError, match='shared-codex-home'):
        m.settings(config)
    other = tmp_path / 'repo' / 'codex'
    other.mkdir(parents=True)
    (other.parent / '.git').mkdir()
    (other.parent / '.git/HEAD').write_text('ref: refs/heads/main\n')
    config = other / 'config.toml'
    config.write_text('[masking]\ndictionary="../dict.json.zst"\n')
    with pytest.raises(m.MaskError, match='dictionary-in-repository'):
        m.settings(config)


def test_cli_only_reads_synthetic_fixtures_and_errors_hide_content(files):
    config, source, masked, status, config_path = files
    source.write_text('Synthetic **12**.\n')
    command = [sys.executable, str(Path(m.__file__)), '--config', str(config_path), 'export',
               '--document', 'synthetic', '--markdown', str(source), '--masked', str(masked)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == 'OK\n'
    source.write_text('Private broken **FABLESECRET.\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and 'FABLESECRET' not in result.stdout + result.stderr


def test_adjacent_runs_trim_whitespace_and_preserve_unicode_normalization():
    dictionary=m.empty_dictionary()
    dictionary['documents']['x']={}
    source=[{'text':'  FABLE','bold':True}, {'text':'1  ','bold':True,'italic':True}]
    masked=m.mask_runs(dictionary,'x',source)
    assert list(dictionary['entries'].values())[0]['value']=='FABLE1'
    rendered=m.render_runs(masked)
    assert rendered.startswith('  {{') and rendered.endswith('}}  ')
    assert not m.protected_ranges(m.chars(m.markdown_blocks(rendered)[0]['runs']))


def test_request_path_uses_existing_librarian_with_private_stdin(monkeypatch):
    captured=[]
    def fake(command,**kwargs):
        captured.append((command,kwargs))
        return type('Result',(),{'stdout':'{"{{TEXT-ABCD}}":{"value":"17"}}'})()
    monkeypatch.setattr(m.subprocess,'run',fake)
    response=m.request_slots([{'id':'{{TEXT-ABCD}}','description':'invented count','context':'We count imaginary genes.'}],
                             document='synthetic',masked_path=Path('/invented/paper/text/masked.md'))
    assert response['{{TEXT-ABCD}}']['value']=='17'
    assert captured[0][0][-1]=='--slots'
    assert 'invented count' not in ' '.join(captured[0][0])
    assert 'invented count' in captured[0][1]['input']
    payload=json.loads(captured[0][1]['input'].split('Request:\n',1)[1])
    assert payload['document']=='synthetic'
    assert payload['masked_path']=='/invented/paper/text/masked.md'
    assert 'active-run provenance' in captured[0][1]['input']


@pytest.mark.parametrize('failure',['transport','invalid-json'])
def test_failed_retrieval_keeps_pending_slots_and_outputs_unchanged(files,monkeypatch,failure):
    export(files,'Public.\n')
    files[2].write_text('Count **invented count**.\n')
    m.do_import(files[0],'synthetic')
    watched=(files[0]['dictionary_path'],files[1],files[2],files[3])
    before=[p.read_bytes() for p in watched]
    def fake(*args,**kwargs):
        if failure=='transport':
            raise subprocess.CalledProcessError(1,['invented'],output='PRIVATE invented value')
        return type('Result',(),{'stdout':'PRIVATE malformed reply'})()
    monkeypatch.setattr(m.subprocess,'run',fake)
    with pytest.raises(m.MaskError,match='^retrieval-request at position 0$'):
        m.do_retrieve(files[0],'synthetic')
    assert [p.read_bytes() for p in watched]==before


def test_retrieved_value_also_masks_existing_unbold_occurrences(files):
    export(files,'Public reference 12.\n')
    files[2].write_text('Public reference 12.\n\nWe need **invented count**.\n')
    m.do_import(files[0],'synthetic')
    entry,=m.load_dictionary(files[0]['dictionary_path'])['entries'].values()
    m.do_retrieve(files[0],'synthetic',lambda _: {entry['id']:{'value':'12'}})
    assert files[2].read_text().count(entry['id'])==2
    assert '12' not in files[2].read_text()
    assert m.load_dictionary(files[0]['dictionary_path'])['entries'][entry['id']]['value']=='12'


def test_new_requests_must_be_imported_before_retrieval(files):
    export(files,'Public.\n')
    files[2].write_text('Want **invented count**.\n')
    with pytest.raises(m.MaskError,match='import-slot-requests-first'):
        m.do_retrieve(files[0],'synthetic',lambda _:pytest.fail('no request before import'))


def test_unrelated_markdown_escapes_do_not_invalidate_ids(files):
    dictionary=export(files,'Value **12**.\n')
    identifier=entries(dictionary)[0]['id']
    files[2].write_text(f'\\[A label\\] has {identifier}.\n')
    m.do_import(files[0],'synthetic')
    assert '**12**' in files[1].read_text()


def test_atomic_dictionary_rename_failure_leaves_no_output(files, monkeypatch):
    original=m.os.replace
    def failure(source,destination):
        if destination==files[0]['dictionary_path']:
            raise OSError('invented PRIVATE ERROR DETAIL')
        return original(source,destination)
    monkeypatch.setattr(m.os,'replace',failure)
    with pytest.raises(m.MaskError) as caught:
        export(files,'Synthetic **123**.\n')
    assert str(caught.value)=='dictionary-save at position 0'
    assert not files[2].exists() and not files[3].exists()
    assert not files[0]['dictionary_path'].exists()


def test_private_value_in_unsupported_link_metadata_fails_closed(files):
    with pytest.raises(m.MaskError,match='unmasked-structural-value'):
        export(files,'Synthetic **FABLE1** [resource](https://example.invalid/FABLE1).\n')
    assert not files[2].exists()


def test_other_bold_with_an_existing_id_is_a_new_slot_request(files):
    dictionary=export(files,'Count **12**.\n')
    original=entries(dictionary)[0]['id']
    description=f'the fraction of {original} imaginary genes'
    files[2].write_text(f'We need **{description}**.\n')
    m.do_import(files[0],'synthetic')
    updated=m.load_dictionary(files[0]['dictionary_path'])
    pending=[entry for entry in entries(updated) if entry.get('status')=='pending']
    assert len(pending)==1 and pending[0]['description']==description
    assert pending[0]['id'] in files[2].read_text() and original not in files[2].read_text()
