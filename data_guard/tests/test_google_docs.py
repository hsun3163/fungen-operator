"""Recorded synthetic API responses only; all network/credential access is stubbed."""
import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import masking as m
import google_docs as g
from test_masking import files

FIXTURE = Path(__file__).with_name('fixtures') / 'google_docs.json'


@pytest.fixture
def recorded():
    return json.loads(FIXTURE.read_text())


def setup_google(files, recorded, monkeypatch):
    calls = []
    def fake(config, method, identifier, *, params=None, body=None):
        calls.append((method, identifier, params, body))
        if method == 'GET':
            return copy.deepcopy(recorded['document'])
        return copy.deepcopy(recorded['batch_update'])
    monkeypatch.setattr(g, 'api', fake)
    source = {'kind':'google','id':'synthetic-doc','tab':'synthetic-tab'}
    m.do_export(files[0], 'synthetic', source, files[2], files[3])
    return source, calls


def test_google_export_and_noop_import_preserve_structure(files, recorded, monkeypatch):
    source, calls = setup_google(files, recorded, monkeypatch)
    text = files[2].read_text()
    assert 'FABLE1' not in text and '2 x 10' not in text
    assert '# **Synthetic findings**' in text
    assert '\ufffc' in text and 'Suggested prose' in text
    dictionary = m.load_dictionary(files[0]['dictionary_path'])
    assert any(r.get('italic') for e in dictionary['entries'].values() for r in e['runs'])
    assert any(r.get('superscript') for e in dictionary['entries'].values() for r in e['runs'])
    m.do_import(files[0], 'synthetic')
    assert all(method == 'GET' for method, *_ in calls)
    assert all(params['suggestionsViewMode'] == 'SUGGESTIONS_INLINE' for _,_,params,_ in calls)


def test_only_changed_paragraph_is_written_with_revision_and_utf16(files, recorded, monkeypatch):
    source, calls = setup_google(files, recorded, monkeypatch)
    files[2].write_text(files[2].read_text().replace('Invented', 'Revised'))
    m.do_import(files[0], 'synthetic')
    posts = [body for method, _, _, body in calls if method == 'POST']
    assert len(posts) == 1
    assert posts[0]['writeControl'] == {'requiredRevisionId':'synthetic-r1'}
    old = g.paragraphs(recorded['document'], source)
    requests = posts[0]['requests']
    deletion = next(r['deleteContentRange']['range'] for r in requests if 'deleteContentRange' in r)
    assert deletion['startIndex'] == old[1]['start']
    assert deletion['endIndex'] == old[1]['end'] - 1
    assert deletion['tabId'] == 'synthetic-tab'
    insert = next(r['insertText']['text'] for r in requests if 'insertText' in r)
    assert insert == 'Revised 😀 FABLE1 at 2 x 10−7.'
    italic = next(r['updateTextStyle'] for r in requests if r.get('updateTextStyle',{}).get('textStyle',{}).get('italic'))
    assert italic['range']['startIndex'] == old[1]['start'] + g.utf16('Revised 😀 ')
    superscript = next(r['updateTextStyle'] for r in requests if r.get('updateTextStyle',{}).get('textStyle',{}).get('baselineOffset') == 'SUPERSCRIPT')
    assert superscript['range']['endIndex'] - superscript['range']['startIndex'] == 2
    assert all(next(iter(r.values())).get('range',{}).get('startIndex', old[1]['start']) < old[2]['start'] for r in requests)
    assert m.load_dictionary(files[0]['dictionary_path'])['documents']['synthetic']['revision'] == 'synthetic-r2'


def test_revision_change_blocks_before_post(files, recorded, monkeypatch):
    source, calls = setup_google(files, recorded, monkeypatch)
    recorded['document']['revisionId'] = 'human-edited'
    with pytest.raises(m.MaskError, match='source-revision-changed'):
        m.do_import(files[0], 'synthetic')
    assert not any(call[0] == 'POST' for call in calls)


def test_suggestion_or_field_paragraph_edit_is_blocked(files, recorded, monkeypatch):
    source, calls = setup_google(files, recorded, monkeypatch)
    for original in ('Suggested prose', 'Citation'):
        saved = files[2].read_text()
        files[2].write_text(saved.replace(original, 'Changed prose'))
        with pytest.raises(m.MaskError, match='changed-field-or-suggestion-paragraph'):
            m.do_import(files[0], 'synthetic')
        files[2].write_text(saved)
    assert not any(call[0] == 'POST' for call in calls)


def test_other_tabs_are_not_edited_and_ambiguous_selection_stops(recorded):
    document = recorded['document']
    document['tabs'].append({'tabProperties':{'tabId':'second'},'documentTab':{'body':{'content':[]}}})
    with pytest.raises(m.MaskError, match='select-google-tab'):
        g.selected_tab(document, {'tab':None})
    source = {'tab':'synthetic-tab'}
    d=m.empty_dictionary()
    d['documents']['x']={}
    masked=g.export_document(d,'x',document,source)
    human,_=m.import_markdown(d,'x',masked.replace('Invented','Changed'))
    requests=g.update_requests(document,human,source)
    assert all(next(iter(r.values())).get('range',next(iter(r.values())).get('location',{})).get('tabId')=='synthetic-tab' for r in requests)


def test_complex_unrepresentable_structure_fails_export(recorded):
    document=recorded['document']
    document['tabs'][0]['documentTab']['body']['content'].append({'startIndex':500,'endIndex':510,'table':{}})
    with pytest.raises(m.MaskError, match='unsupported-google-structure'):
        g.paragraphs(document, {'tab':'synthetic-tab'})


def test_dictionary_doc_sync_is_one_way_metadata_only(recorded, monkeypatch):
    d=m.empty_dictionary()
    d['documents']['x']={'source':{'kind':'markdown','path':'synthetic-human.md'},'revision':'invented-hash'}
    identifier=m.add_entry(d,'x','FABLE1',[{'text':'FABLE1','italic':True}])
    before=copy.deepcopy(d)
    calls=[]
    def fake(config,method,doc,*,params=None,body=None):
        calls.append((method,params,body))
        return recorded['dictionary_metadata' if method=='GET' else 'dictionary_update']
    monkeypatch.setattr(g,'api',fake)
    g.sync_dictionary(d,{'dictionary_doc':'synthetic-dictionary'})
    assert calls[0][1] == {'fields':'documentId,revisionId,body(content(endIndex))'}
    assert 'textRun' not in calls[0][1]['fields']
    assert calls[1][2]['writeControl']=={'requiredRevisionId':'synthetic-d1'}
    text=calls[1][2]['requests'][-1]['insertText']['text']
    assert identifier in text and 'FABLE1' in text and 'invented-hash' in text
    assert d==before


def test_api_errors_never_expose_response_or_credentials(monkeypatch):
    monkeypatch.setattr(g,'access_token',lambda _: 'synthetic-secret-token')
    def failure(*args,**kwargs):
        raise RuntimeError('PRIVATE RESPONSE FABLE1 token synthetic-secret-token')
    monkeypatch.setattr(g,'urlopen',failure)
    with pytest.raises(m.MaskError) as caught:
        g.api({},'GET','synthetic-doc')
    assert str(caught.value)=='google-request at position 0'
