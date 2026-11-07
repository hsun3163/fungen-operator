"""Build contexts hold exactly the admitted files of the recorded commit."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest
spec=importlib.util.spec_from_file_location('fungen_build',Path(__file__).parents[1]/'container/build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def git(repo,*args):
    return subprocess.run(['git','-c','user.name=t','-c','user.email=t@example.org',*args],
                          cwd=repo,check=True,capture_output=True,text=True).stdout


@pytest.fixture
def repo(tmp_path,monkeypatch):
    root=tmp_path/'repo'
    for name,text in {'README.md':'# r\n','src/pkg/a.py':'A=1\n','container/build.py':'pass\n',
                      'container/VALIDATION.md':'private log\n','runs/private.json':'{}\n'}.items():
        (root/name).parent.mkdir(parents=True,exist_ok=True);(root/name).write_text(text)
    git(root,'init','-q');git(root,'add','README.md','src','container');git(root,'commit','-qm','init')
    monkeypatch.setattr(b,'ROOT',root)
    return root


def test_context_boundaries():
    for name in ['.env','models/weights.gguf','runs/private.json','src/fungen_operator/__pycache__/x.pyc','container/VALIDATION.md','tests/.env','tests/test_bootstrap.py','tests/conftest.py','container/conftest.py','container/test_setup.py']:
        assert not b.admitted(name)
    assert b.admitted('src/fungen_operator/resources/xqtl-upstream.patch')


def test_context_records_the_commit_it_copies(repo,tmp_path):
    destination=tmp_path/'context'
    b.context(destination)
    identity=json.loads((destination/'container/source.json').read_text())
    assert identity['commit']==git(repo,'rev-parse','HEAD').strip()
    assert set(identity['files'])=={'README.md','src/pkg/a.py','container/build.py'}
    assert identity['files']['src/pkg/a.py']==hashlib.sha256(b'A=1\n').hexdigest()


@pytest.mark.parametrize('change',['modified','staged','untracked','deleted'])
def test_context_refuses_admitted_paths_that_differ_from_head(repo,tmp_path,change):
    if change=='modified': (repo/'src/pkg/a.py').write_text('A=2\n')
    elif change=='staged': (repo/'src/pkg/a.py').write_text('A=2\n');git(repo,'add','src/pkg/a.py')
    elif change=='untracked': (repo/'src/pkg/new.py').write_text('B=1\n')
    else: (repo/'src/pkg/a.py').unlink()
    destination=tmp_path/'context'
    with pytest.raises(ValueError,match='must match the commit HEAD') as error:
        b.context(destination)
    assert ('src/pkg/new.py' if change=='untracked' else 'src/pkg/a.py') in str(error.value)
    assert not destination.exists()


def test_context_ignores_changes_outside_the_allowlist(repo,tmp_path):
    (repo/'container/VALIDATION.md').write_text('newer private log\n')
    (repo/'runs/private.json').write_text('{"token": 1}\n')
    destination=tmp_path/'context'
    b.context(destination)
    assert not (destination/'runs').exists() and not (destination/'container/VALIDATION.md').exists()


def test_refresh_rejects_existing_secret_even_if_repo_file(repo,tmp_path):
    destination=tmp_path/'context';destination.mkdir()
    (destination/'.env').write_text('SECRET=example')
    with pytest.raises(ValueError,match='Unexpected'):
        b.context(destination,True)


def test_context_uses_captured_commit_despite_later_worktree_and_head_changes(repo,tmp_path,monkeypatch):
    captured=git(repo,'rev-parse','HEAD').strip();original=b.committed_files
    def changed_after_read(commit):
        files=original(commit)
        (repo/'src/pkg/a.py').write_text('A=99\n')
        git(repo,'add','src/pkg/a.py');git(repo,'commit','-qm','concurrent change')
        return files
    monkeypatch.setattr(b,'committed_files',changed_after_read)
    destination=tmp_path/'context';b.context(destination)
    identity=json.loads((destination/'container/source.json').read_text())
    assert identity['commit']==captured and identity['commit']!=git(repo,'rev-parse','HEAD').strip()
    assert (destination/'src/pkg/a.py').read_text()=='A=1\n'
    assert identity['source_blobs']['src/pkg/a.py']==git(repo,'rev-parse',captured+':src/pkg/a.py').strip()


def test_context_refuses_index_hidden_worktree_changes(repo,tmp_path):
    git(repo,'update-index','--assume-unchanged','src/pkg/a.py')
    (repo/'src/pkg/a.py').write_text('A=99\n')
    assert git(repo,'status','--porcelain','--','src/pkg/a.py')==''
    destination=tmp_path/'context'
    with pytest.raises(ValueError,match='must match the commit HEAD: src/pkg/a.py'):b.context(destination)
    assert not destination.exists()


def test_context_transforms_committed_blobs_and_preserves_modes(repo,tmp_path):
    p=repo/'src/pkg/a.py';p.write_text('PATH="/hpc/users/sunh14/tools"\n');p.chmod(0o755)
    git(repo,'add','src/pkg/a.py');git(repo,'commit','-qm','executable source')
    destination=tmp_path/'context';b.context(destination)
    copied=destination/'src/pkg/a.py'
    assert copied.read_text()=='PATH="/workspace/tools"\n' and copied.stat().st_mode&0o111
    identity=json.loads((destination/'container/source.json').read_text())
    assert identity['files']['src/pkg/a.py']==hashlib.sha256(copied.read_bytes()).hexdigest()
