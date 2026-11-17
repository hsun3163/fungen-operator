#!/bin/bash
set -euo pipefail
umask 022
export HOME=/root
unset XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME JUPYTER_CONFIG_DIR JUPYTER_DATA_DIR
export DEBIAN_FRONTEND=noninteractive
apt-get -o APT::Sandbox::User=root update
apt-get -o APT::Sandbox::User=root install -y --no-install-recommends ca-certificates curl git jq tabix xz-utils
python_url=https://github.com/astral-sh/python-build-standalone/releases/download/20260320/cpython-3.12.13%2B20260320-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz
codex_url=https://github.com/openai/codex/releases/download/rust-v0.155.1/codex-x86_64-unknown-linux-musl.tar.gz
bwrap_url=https://github.com/openai/codex/releases/download/rust-v0.155.1/bwrap-x86_64-unknown-linux-musl.tar.gz
curl -fL --retry 3 "$python_url" -o /tmp/fungen-python.tgz
echo 'bdabcacc426ab3f04dc65ff26dffb4abaddd16ae8797f8aa50479de0c566245e  /tmp/fungen-python.tgz' | sha256sum -c -
tar --no-same-owner -xzf /tmp/fungen-python.tgz -C /opt
mkdir -p /opt/agent/bin
curl -fL --retry 3 "$codex_url" -o /tmp/fungen-codex.tgz
echo 'a0ef8b2debc3bf747e07b1a039354de31300ac0dcc2276498ba281470b5d9115  /tmp/fungen-codex.tgz' | sha256sum -c -
tar --no-same-owner -xzf /tmp/fungen-codex.tgz -C /opt/agent/bin
mv /opt/agent/bin/codex-x86_64-unknown-linux-musl /opt/agent/bin/codex
curl -fL --retry 3 "$bwrap_url" -o /tmp/fungen-bwrap.tgz
echo 'd94f189cac440eb601dea980a44a40a4bb40452fd21c06a2abfe464f293795b6  /tmp/fungen-bwrap.tgz' | sha256sum -c -
tar --no-same-owner -xzf /tmp/fungen-bwrap.tgz -C /opt/agent/bin
mv /opt/agent/bin/bwrap-x86_64-unknown-linux-musl /opt/agent/bin/bwrap
/opt/python/bin/python3 -m pip install --no-cache-dir '/opt/fungen-operator[test]'
/opt/python/bin/python3 -m ipykernel install --prefix=/opt/python --name python3
chmod -R a+rX /opt/fungen-operator /opt/agent /opt/python
# Bundle a relocatable offline host installation, including every wheel.
mkdir -p /opt/fungen/bin
# Re-resolution always starts empty, including the native update stage.
for asset in wheels python; do
    if [[ -e /opt/fungen/$asset ]]; then
        saved=$(mktemp -d /tmp/fungen-previous-XXXXXX)
        mv "/opt/fungen/$asset" "$saved/$asset"
    fi
done
mkdir -p /opt/fungen/wheels
curl -fL --retry 3 https://github.com/astral-sh/uv/releases/download/0.13.4/uv-x86_64-unknown-linux-gnu.tar.gz -o /tmp/fungen-uv.tgz
echo '2b428396f12572d4429cf210ca234dd599a33b3af0958a4d5ed569d63e3f344f  /tmp/fungen-uv.tgz' | sha256sum -c -
tar --no-same-owner -xzf /tmp/fungen-uv.tgz -C /tmp
cp /tmp/uv-x86_64-unknown-linux-gnu/uv /opt/fungen/bin/
cp /opt/agent/bin/codex /opt/agent/bin/bwrap /opt/fungen/bin/
/opt/python/bin/python3 -m fungen_operator.bundle /opt/fungen-operator /opt/fungen/wheels
# Keep build-host site-packages out of the relocatable host interpreter.
tar --no-same-owner -xzf /tmp/fungen-python.tgz -C /opt/fungen
# Bootstrap reruns also inspect scheduler receipts, so they need the production
# dependencies. Install exactly the audited offline wheels, never build-host packages.
/opt/fungen/python/bin/python3 -m pip install --no-index --find-links /opt/fungen/wheels fungen-operator
mkdir -p /opt/fungen/skills
cp -a /opt/fungen-operator/skills/. /opt/fungen/skills/
cp /opt/fungen-operator/container/source.json /opt/fungen/source.json
mkdir -p /opt/fungen/docs
cp /opt/fungen-operator/docs/operator_prototype.md /opt/fungen/docs/
cp /opt/fungen-operator/README.md /opt/fungen/README.md
chmod -R a+rX /opt/fungen
mkdir -p /workspace
chmod 755 /workspace
