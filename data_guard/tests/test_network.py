"""Per-call network override, command construction only."""
import pytest
from test_librarian import run

@pytest.mark.parametrize('scribe', [False, True])
@pytest.mark.parametrize('mode', ['', 'on', 'off'])
def test_network_override(tmp_path, scribe, mode):
    home = tmp_path / 'userhome'; home.mkdir()
    args = tmp_path / 'args'
    p = run(tmp_path, *(['--scribe'] if scribe else []), 'Synthetic task', HOME=str(home), STUB_ARGS=str(args), LIBRARIAN_NETWORK=mode)
    assert p.returncode == 0, p.stdout + p.stderr
    assert ('sandbox_workspace_write.network_access=false' in args.read_text()) == (mode == 'off')
