"""One host ABI policy for offline resolution, wheel auditing and setup preflight."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

LOCK = Path(__file__).with_name('resources')/'host-requirements.lock'

POLICY = json.loads((Path(__file__).with_name('resources')/'host-platform.json').read_text())
MIN_GLIBC = tuple(map(int, POLICY['minimum_glibc'].split('.')))


def platforms():
    major, minor = MIN_GLIBC
    assert major == 2
    return [f'manylinux_2_{n}_{POLICY["architecture"]}' for n in range(minor, 4, -1)] + [
        f'{tag}_{POLICY["architecture"]}' for tag in ('manylinux2014', 'manylinux2010', 'manylinux1')]


def audit_wheels(folder):
    wheels = list(Path(folder).glob('*.whl'))
    if not wheels:
        raise ValueError('Offline bundle has no wheels')
    aliases = {'manylinux1': (2, 5), 'manylinux2010': (2, 12), 'manylinux2014': (2, 17)}
    for wheel in wheels:
        tags = wheel.stem.rsplit('-', 1)[-1].split('.')
        compatible = False
        for tag in tags:
            if tag == 'any':
                compatible = True
            elif tag.endswith('_'+POLICY['architecture']):
                base = tag.removesuffix('_'+POLICY['architecture'])
                match = re.fullmatch(r'manylinux_(\d+)_(\d+)', base)
                version = tuple(map(int, match.groups())) if match else aliases.get(base)
                compatible |= version is not None and version <= MIN_GLIBC
        if not compatible:
            raise ValueError(f'Wheel {wheel.name} has no platform compatible with glibc {POLICY["minimum_glibc"]} {POLICY["architecture"]}')
    return len(wheels)


def audit_locked_wheels(folder):
    """Require a target-compatible wheel for every exact production pin."""
    audit_wheels(folder)
    available = {tuple(w.name.split('-')[:2]) for w in Path(folder).glob('*.whl')}
    for line in LOCK.read_text().splitlines():
        if not line or line.startswith('#'): continue
        name, version = line.split('==')
        if (name.replace('-', '_'), version) not in available:
            raise ValueError('Offline bundle missing locked wheel: '+line)
    return len(available)


def host_preflight():
    try:
        value = os.confstr('CS_GNU_LIBC_VERSION')
        version = tuple(map(int, value.split()[-1].split('.')))
    except (OSError, ValueError, AttributeError, TypeError):
        raise ValueError('Cannot identify host glibc; offline bundle requires glibc '+POLICY['minimum_glibc']+' or newer') from None
    if version < MIN_GLIBC:
        raise ValueError(f'Host glibc {value} is older than offline bundle minimum {POLICY["minimum_glibc"]}; use a supported host before installing packages')
    print(f'Host ABI preflight: {value}; bundle minimum glibc {POLICY["minimum_glibc"]}', flush=True)


def build(project, destination):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Wheel destination must be empty; use a fresh bundle build')
    destination.mkdir(parents=True, exist_ok=True)
    pip = [sys.executable, '-m', 'pip']
    subprocess.run(pip+['wheel', '--no-deps', '--wheel-dir', str(destination), str(project)], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        constraints = Path(tmp)/'constraints.txt'
        constraints.write_text(''.join(name+item['specifier']+'\n' for name,item in POLICY['constraints'].items()))
        command = pip+['download', '--only-binary=:all:', '--python-version', POLICY['python'],
                       '--implementation', 'cp', '--abi', 'cp312', '--abi', 'abi3', '--abi', 'none',
                       '--dest', str(destination), '--constraint', str(constraints),
                       '--requirement', str(LOCK)]
        for platform in platforms():
            command += ['--platform', platform]
        subprocess.run(command+[str(next(destination.glob('fungen_operator-*.whl')))], check=True)
    audit_locked_wheels(destination)
    # Prove dependency closure using only this wheelhouse for the host target.
    command = pip+['install', '--dry-run', '--ignore-installed', '--no-index',
                   '--find-links', str(destination), '--only-binary=:all:',
                   '--python-version', POLICY['python'], '--implementation', 'cp',
                   '--abi', 'cp312', '--abi', 'abi3', '--abi', 'none',
                   '--requirement', str(LOCK)]
    for platform in platforms(): command += ['--platform', platform]
    subprocess.run(command+['fungen-operator'], check=True)
    print(f'Host wheel audit: {audit_wheels(destination)} wheels compatible with glibc {POLICY["minimum_glibc"]}')


if __name__ == '__main__':
    build(*sys.argv[1:])
