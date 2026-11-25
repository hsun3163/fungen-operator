"""Regenerate the xQTL explicit lock using only its YAML channels, in order."""
import argparse
from pathlib import Path
import subprocess

import yaml

from .onboarding import RESOURCES


def generate(mamba, prefix, output, spec=RESOURCES/'xqtl-mamba.yaml', env=None):
    environment = yaml.safe_load(Path(spec).read_text())
    channels = environment['channels']
    packages = environment['dependencies']
    if not channels or not packages or not all(isinstance(x, str) for x in channels + packages):
        raise ValueError('Lock generation needs ordered channels and conda package specs')
    # env create merges configured channels. An explicit override is essential
    # when site/user condarc files enable strict priority with another order.
    command = [str(mamba), 'create', '-y', '-p', str(prefix), '--override-channels']
    for channel in channels:
        command += ['-c', channel]
    subprocess.run(command + packages, check=True, env=env)
    lock = subprocess.run([str(mamba), 'list', '-p', str(prefix), '--explicit', '--md5'],
                          check=True, capture_output=True, text=True, env=env).stdout
    # Mamba 2 prints the URLs without the @EXPLICIT header that --file needs.
    urls = [line for line in lock.splitlines() if line.startswith('https://')]
    if not urls:
        raise ValueError('Mamba did not return an explicit package lock')
    Path(output).write_text('@EXPLICIT\n' + '\n'.join(urls) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mamba', required=True)
    parser.add_argument('--prefix', required=True, type=Path, help='Dedicated solve environment')
    parser.add_argument('--output', type=Path, default=RESOURCES/'xqtl-linux-64.lock')
    parser.add_argument('--spec', type=Path, default=RESOURCES/'xqtl-mamba.yaml')
    args = parser.parse_args(argv)
    generate(args.mamba, args.prefix, args.output, args.spec)


if __name__ == '__main__':
    main()
