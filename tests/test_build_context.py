"""Build-context refresh cannot retain private files outside the allowlist."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('fungen_build',Path(__file__).parents[1]/'container/build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def test_context_boundaries():
    for name in ['.env','models/weights.gguf','runs/private.json','src/fungen_operator/__pycache__/x.pyc','container/VALIDATION.md','tests/.env']:
        assert not b.admitted(name)
    assert b.admitted('src/fungen_operator/resources/xqtl-upstream.patch')

def test_refresh_rejects_existing_secret_even_if_repo_file(tmp_path,monkeypatch):
    (tmp_path/'.env').write_text('SECRET=example')
    monkeypatch.setattr(b.subprocess,'check_output',lambda *a,**k:b'.env\0')
    with pytest.raises(ValueError,match='Unexpected'):
        b.context(tmp_path,True)
