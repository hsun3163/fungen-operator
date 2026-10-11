"""Synthetic wrapper audience tests; no project results or model services."""
import json
from pathlib import Path
import pytest
from test_librarian import run, runs


def rule(tmp_path):
    p = tmp_path / 'release.json'
    p.write_text(json.dumps({'audience': 'research-committee', 'withheld_quantities': ['numeric INTACT posterior probabilities', 'TWAS Z scores', 'TWAS effect sizes', 'TWAS P values'], 'screen_patterns': []}))
    return p


@pytest.mark.parametrize('scribe', [False, True])
def test_committee_rule_reaches_model_and_returns_answer_without_publishing(tmp_path, scribe):
    home = tmp_path / 'userhome'; home.mkdir()
    args = tmp_path / 'native-args'
    p = run(tmp_path, *(['--scribe'] if scribe else []), '--committee', str(rule(tmp_path)), 'Synthetic named-file lookup.',
            HOME=str(home), STUB_ARGS=str(args), STUB_ANSWER='{"findings":"invented gene order","INTACT PP":"withheld"}')
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads(p.stdout)['INTACT PP'] == 'withheld'
    assert 'Committee audience:' in args.read_text() and 'TWAS Z scores' in args.read_text()
    assert 'research-committee caller' in args.read_text()
    assert not (tmp_path / 'home/latest.md').exists()
    assert not (tmp_path / 'home/answers').exists()
    assert 'NOISY' not in p.stdout


@pytest.mark.parametrize('option', ['--me', '--receipt', '--check'])
def test_committee_audience_rejects_conflicting_modes(tmp_path, option):
    p = run(tmp_path, '--scribe', '--committee', str(rule(tmp_path)), option, 'Synthetic task')
    assert p.returncode == 2
    assert not (tmp_path / 'home/runs').exists()


def test_invalid_release_rule_fails_before_backend(tmp_path):
    pth = tmp_path / 'bad.json'; pth.write_text('{"audience":"anyone"}')
    p = run(tmp_path, '--committee', str(pth), 'Synthetic task')
    assert p.returncode == 2 and 'invalid committee release rule' in p.stdout
    assert not (tmp_path / 'home/runs').exists()


def test_ordinary_call_ignores_inherited_committee_setting(tmp_path):
    p = run(tmp_path, 'Synthetic normal task', LIBRARIAN_COMMITTEE_RULE=str(rule(tmp_path)))
    assert p.returncode == 0 and p.stdout == 'FAKE ANSWER\n'
    assert (runs(tmp_path)[0] / 'task').read_text() == 'Synthetic normal task\n'
