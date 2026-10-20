#!/bin/bash
set -euo pipefail
cd /opt/fungen-operator
export PYTHONDONTWRITEBYTECODE=1
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fungen-operator --help
codex --version
if [[ ${FUNGEN_SKIP_SUITE:-0} != 1 ]]; then
    python3 -m pytest -p container.conftest tests -q -o cache_dir=/audit/pytest-cache
    python3 -m pytest container/test_setup.py -q -o cache_dir=/audit/pytest-cache
fi
fungen-setup --non-interactive --download no --tag q4_K_M-256k-t2 \
    --models-dir /models --endpoint http://127.0.0.1:11535
OLLAMA_HOST=http://127.0.0.1:11535 ollama list
python3 - <<'PY'
import json, urllib.request
with urllib.request.urlopen('http://127.0.0.1:11535/api/ps') as response:
    models = json.load(response)['models']
selected = next(m for m in models if m['name'] == 'laguna-s-2.1:q4_K_M-256k-t2')
assert selected['size_vram'] > 0, 'GPU offload was not established'
print('GPU offload bytes:', selected['size_vram'])
PY
python3 - <<'PY'
import errno, os, pty, select, subprocess, time
master, slave = pty.openpty()
process = subprocess.Popen(['fungen-setup'], stdin=slave, stdout=slave, stderr=slave)
os.close(slave)
pending = [(b'Download Laguna S?', b'no\n'), (b'Which tag?', b'\n'), (b'Model folder', b'\n')]
transcript = bytearray()
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    if select.select([master], [], [], 1)[0]:
        try:
            data = os.read(master, 65536)
        except OSError as exc:
            if exc.errno == errno.EIO:
                break
            raise
        if not data:
            break
        transcript.extend(data)
        print(data.decode(errors='replace'), end='', flush=True)
        if pending and pending[0][0] in transcript:
            _, answer = pending.pop(0)
            os.write(master, answer)
    elif process.poll() is not None:
        break
os.close(master)
assert process.wait(timeout=10) == 0 and not pending, 'Interactive setup failed'
open('/audit/interactive.txt', 'wb').write(transcript)
PY
mkdir -p /audit/agent
cd /audit/agent
fungen-agent -- exec --skip-git-repo-check --ephemeral --sandbox read-only \
    --output-last-message /audit/agent-answer.txt \
    'Connectivity test only. Do not call tools or read files. Reply with exactly: FUNGEN_AGENT_CONNECTED'
test -s /audit/agent-answer.txt
printf '\nSmoke test completed.\n'
