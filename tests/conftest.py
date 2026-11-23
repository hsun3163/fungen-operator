"""All host tests use per-test account state, including subprocess inheritance."""
import pytest


@pytest.fixture(autouse=True)
def isolated_account(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp('account-home')
    for key,value in {'HOME':home, 'XDG_CONFIG_HOME':home/'.config', 'CODEX_HOME':home/'.codex',
                      'XDG_DATA_HOME':home/'.local/share', 'XDG_CACHE_HOME':home/'.cache',
                      'JUPYTER_DATA_DIR':home/'.local/share/jupyter', 'JUPYTER_CONFIG_DIR':home/'.jupyter',
                      'JUPYTER_RUNTIME_DIR':home/'.local/share/jupyter/runtime', 'UV_CACHE_DIR':home/'.cache/uv'}.items():
        monkeypatch.setenv(key,str(value))
