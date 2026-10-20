"""Synthetic checks for the installed catalog and structure-only interface."""
import csv, io, json, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]))
import live_inventory as live

def test_schema_drift_requires_explicit_classification():
    rows=[dict(input_id='toy',path='/toy.tsv',format='tsv',columns=['gene','count','score','new'])]
    policy=dict(inputs={'toy':'/toy.tsv'},gene_columns=['gene'],protected_columns=['score'],shown_headings=['count'])
    assert live.check(rows,policy)==[dict(input_id='toy',column='new',problem='unclassified')]
    rows[0]['input_id']='new_input'
    assert any(p['problem']=='new-or-changed-input' for p in live.check(rows,policy))

def test_catalog_selection_preserves_operator_release_settings():
    policy=dict(inputs={'toy':'/toy.tsv','other':'/other.tsv'},gene_columns=['gene'],protected_columns=['score'],shown_headings=['count'],scribes=[4,4])
    selected=live.request_policy(policy,dict(inputs={'table':['toy']}))
    assert selected==dict(policy,inputs={'toy':'/toy.tsv'})
    with pytest.raises(ValueError,match='unknown-input'):
        live.request_policy(policy,dict(inputs={'table':'unknown'}))

def test_structure_probe_releases_headers_and_counts_only(tmp_path):
    table=tmp_path/'toy.tsv';table.write_text('gene\tscore\nPRIVATE_TOY_GENE\t0.123456\nOTHER_PRIVATE\t0.987654\n')
    policy=dict(private_root=str(tmp_path/'private'),inputs={'toy':str(table)},max_input_bytes=1024)
    answer=tmp_path/'answer.md'
    receipt=live.structure_probe(policy,dict(action='probe',inputs={'table':'toy'}),answer)
    assert receipt['structure_only'] and receipt['status']=='completed'
    assert answer.read_text()=='input_role\tcolumn\trow_count\ntable\tgene\t2\ntable\tscore\t2\n'
    assert json.loads((tmp_path/'private'/receipt['run_id']/'audit.json').read_text())['model_calls']==0

@pytest.mark.parametrize('run',['../escape','run-bad','/private/run-abc'])
def test_linked_request_validates_run_identity(run):
    with pytest.raises(ValueError,match='invalid-run'):
        live.request_policy({'inputs':{},'private_root':'/private'},dict(action='rephrase',run=run))
