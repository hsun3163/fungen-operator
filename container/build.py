"""Prepare a portable allowlisted context, or assemble a local Docker archive.

The archive route uses the same install.sh as Docker, executed in an isolated
user-namespace chroot over the pinned Ollama rootfs. It needs neither a Docker
daemon nor subordinate UIDs.
"""

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
TOP = {"pyproject.toml", "README.md", "MANIFESTO.md"}
PREFIX = ("src/", "skills/", "container/")
EXTRA = {"docs/operator_prototype.md", "benchmark/mws01.py", "benchmark/__init__.py",
         "benchmark/tasks/regression/MWS-01.yaml"}


def admitted(name):
    path=Path(name)
    return (bool(name) and (name in TOP or name in EXTRA or name.startswith(PREFIX))
            and not any(part in {"__pycache__", ".pytest_cache", "evidence"} for part in path.parts)
            and (path.suffix in {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".patch", ".lock", ".R", ".sh", ".lsf", ".def", ".dockerignore"} or path.name in {"Dockerfile", ".gitignore"})
            and name!="container/VALIDATION.md"
            and not (name.startswith("container/") and (path.name=="conftest.py" or path.name.startswith("test_"))))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode()


def committed_files(commit):
    """Read one captured Git tree and refuse differing admitted worktree inputs."""
    status=git('status','--porcelain=v1','-z','--untracked-files=all','--no-renames').split('\0')
    dirty=sorted(entry for entry in status if entry and admitted(entry[3:]))
    if dirty:raise ValueError('Build context must match the commit HEAD. Commit or stash these admitted paths:\n'+'\n'.join('  '+entry for entry in dirty))
    entries={}
    for item in git('ls-tree','-r','-z','--full-tree',commit).split('\0'):
        if not item:continue
        info,name=item.split('\t',1);mode,kind,oid=info.split()
        if not admitted(name):continue
        if kind!='blob' or mode not in ('100644','100755'):
            raise ValueError('Build allowlist contains a symlink or unsupported Git object: '+name)
        entries[name]=(mode,oid)
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
                                input=''.join(oid+'\n' for _,oid in entries.values()).encode())
    stream=io.BytesIO(raw);files={}
    for name,(mode,oid) in entries.items():
        header=stream.readline().decode().split()
        if len(header)!=3 or header[:2]!=[oid,'blob']:raise ValueError('Unexpected Git blob response for '+name)
        data=stream.read(int(header[2]))
        if stream.read(1)!=b'\n':raise ValueError('Truncated Git blob response for '+name)
        source=ROOT/name
        if source.is_symlink():raise ValueError('Build allowlist contains a symlink: '+name)
        try:matches=source.read_bytes()==data and bool(source.stat().st_mode&0o111)==(mode=='100755')
        except OSError:matches=False
        if not matches:raise ValueError('Build context must match the commit HEAD: '+name)
        files[name]=(mode,oid,data)
    return files


def context(destination,refresh=False):
    if destination.exists() and not refresh:raise ValueError('Use a new context directory to avoid stale/private files.')
    commit=git('rev-parse','HEAD').strip()
    files=committed_files(commit)
    destination.mkdir(parents=True,exist_ok=refresh)
    if refresh:
        expected=set(files)|{'container/source.json'}
        for old in destination.rglob('*'):
            if old.is_symlink() or (old.is_file() and str(old.relative_to(destination)) not in expected):
                raise ValueError(f'Unexpected existing context member: {old.name}')
    hashes={}
    for name,(mode,oid,data) in files.items():
        try:text=data.decode()
        except UnicodeDecodeError:raise ValueError('Unexpected binary in source allowlist: '+name)
        text=re.sub(r'/(?:sc/arion/(?:projects/load/users|work)|hpc/users)/sunh14','/workspace',text)
        text=text.replace('/sc/arion/projects/load/scripts/','/workspace/site-tools/')
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text);target.chmod(int(mode,8)&0o777)
        hashes[name]=hashlib.sha256(text.encode()).hexdigest()
    version_tree=ast.parse(files['src/fungen_operator/__init__.py'][2].decode())
    versions=[ast.literal_eval(node.value) for node in version_tree.body
              if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in node.targets)]
    if len(versions)!=1 or not isinstance(versions[0],str) or not re.fullmatch(r'\d+\.\d+\.\d+',versions[0]):
        raise ValueError('Source must declare one semantic __version__')
    identity={'version':versions[0],'commit':commit,'files':hashes,'source_blobs':{name:oid for name,(_,oid,_) in files.items()}}
    (destination/'container/source.json').write_text(json.dumps(identity,indent=2)+'\n')
    print(f'Prepared {len(files)} allowlisted source files in {destination}')


def add_json(archive, name, data):
    body = json.dumps(data).encode()
    info = tarfile.TarInfo(name)
    info.size = len(body)
    archive.addfile(info, io.BytesIO(body))


def archive_rootfs(rootfs, output):
    layer = output.with_suffix(".layer.tar")
    with tarfile.open(layer, "w", copybufsize=1024 * 1024) as archive:
        temporary=tarfile.TarInfo("tmp"); temporary.type=tarfile.DIRTYPE; temporary.mode=0o1777
        archive.addfile(temporary)
        for child in sorted(rootfs.iterdir()):
            # These are generated by Singularity's sandbox materialization, not
            # by the Docker base. In particular its private metadata directory
            # must not become root-owned mode 0700 in the portable OCI layer.
            if child.name in {"proc", "sys", "dev", "hpc", "root", "tmp", ".singularity.d", ".exec", ".run", ".shell", ".test",
                              "singularity", "environment", "Singularity"}:
                continue
            def image_owner(info):
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                return info
            archive.add(child, arcname=child.name, recursive=True, filter=image_owner)
    digest = hashlib.file_digest(layer.open("rb"), "sha256").hexdigest()
    config = {"architecture": "amd64", "os": "linux",
              "config": {"Env": [
                  "PATH=/opt/python/bin:/opt/agent/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                  "OLLAMA_HOST=127.0.0.1:11434", "OLLAMA_CONTEXT_LENGTH=32768",
                  "OLLAMA_FLASH_ATTENTION=1", "OLLAMA_KV_CACHE_TYPE=q8_0",
                  "OLLAMA_NUM_PARALLEL=1", "OLLAMA_MAX_LOADED_MODELS=1"],
                  "WorkingDir": "/workspace",
                  "Entrypoint": ["/opt/python/bin/python3", "/opt/fungen-operator/container/fungen.py"],
                  "Cmd": ["setup"],
                  "Labels": {"org.opencontainers.image.base.name": "ollama/ollama:0.40.6"}},
              "rootfs": {"type": "layers", "diff_ids": ["sha256:" + digest]}}
    with tarfile.open(output, "w", copybufsize=1024 * 1024) as archive:
        archive.add(layer, arcname="layer.tar")
        add_json(archive, "config.json", config)
        add_json(archive, "manifest.json", [{"Config": "config.json",
                 "RepoTags": ["fungen-operator:ollama0.40.6-codex0.155.1"], "Layers": ["layer.tar"]}])
    print(f"Docker archive: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("context")
    p.add_argument("destination", type=Path)
    p.add_argument("--refresh", action="store_true")
    p = subs.add_parser("archive")
    p.add_argument("rootfs", type=Path)
    p.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "context":
        try:
            context(args.destination.resolve(), args.refresh)
        except ValueError as error:
            parser.exit(1, f"build.py context: {error}\n")
    else:
        archive_rootfs(args.rootfs.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
