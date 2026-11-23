"""Host GPU evidence and bounded Ollama discovery excerpts; never select devices."""
from collections import deque
import os
import re
from pathlib import Path
import shlex
import socket
import subprocess
import threading


def probe(command):
    print('FUNGEN_GPU_COMMAND '+shlex.join(command), flush=True)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        print(f'FUNGEN_GPU_RESULT exit={result.returncode}\n{result.stdout}{result.stderr}', flush=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f'FUNGEN_GPU_RESULT unavailable: {exc}', flush=True)


def host_diagnostics():
    print('FUNGEN_GPU_HOST '+socket.gethostname(), flush=True)
    keys = ('CUDA_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES_ORIG','CUDA_VISIBLE_DEVICES1','CUDA_VISIBLE_DEVICES2','CUDA_DEVICE_ORDER','NVIDIA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL',
            'LSB_JOBID','LSB_GPU_ID','LSB_GPU_REQ','LSB_GPU_NEW_SYNTAX','SLURM_JOB_ID','SLURM_JOB_GPUS',
            'SLURM_STEP_GPUS','SGE_HGR_gpu','SGE_GPU','JOB_ID')
    for key in keys:
        print(f'FUNGEN_GPU_ENV {key}={os.environ.get(key,"<unset>")}', flush=True)
    devices = sorted(Path('/dev').glob('nvidia*'))
    print('FUNGEN_GPU_DEVICES '+', '.join(f'{p} mode={p.stat().st_mode:o} read={os.access(p,os.R_OK)} write={os.access(p,os.W_OK)}' for p in devices), flush=True)
    # nvidia-smi prints the driver version and its maximum supported CUDA version.
    probe(['nvidia-smi'])
    assigned = os.environ.get('CUDA_VISIBLE_DEVICES')
    selector = ['-i', assigned] if assigned else []
    probe(['nvidia-smi', *selector, '--query-gpu=index,driver_version,name,uuid,memory.total,compute_mode,mig.mode.current', '--format=csv'])


def ollama_library(override=None):
    """Select one CUDA backend from the driver on the allocated host."""
    if override:
        if not isinstance(override, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', override) or override in ('.', '..'):
            raise ValueError('Ollama library must be one backend directory name')
        return override

    command = ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader']
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
        versions = [re.fullmatch(r'(\d+)(?:\.\d+)*', line.strip())
                    for line in result.stdout.splitlines() if line.strip()]
        if versions and all(version and int(version[1]) >= 580 for version in versions):
            return 'cuda_v13'
    except (OSError, subprocess.SubprocessError):
        pass
    return 'cuda_v12'


def runtime_requirements(root=Path('/usr/lib/ollama')):
    requirements = {'cuda_v12': 'bundled CUDA 12.8: Linux driver >=550 required by Ollama fatbin filter (>=570 for compute <7 PTX); CUDA generic minor-compatibility floor 525.60.13 is insufficient here',
                    'cuda_v13': 'Linux driver >=580 (CUDA 13 minor compatibility)'}
    for name, requirement in requirements.items():
        folder = root/name
        if folder.is_dir():
            libraries = ','.join(p.name for p in sorted(folder.glob('libcudart.so*')))
            print(f'FUNGEN_GPU_RUNTIME {name} {libraries}; {requirement}', flush=True)


class DiscoveryLog:
    def __init__(self, stream):
        self.lines = deque(maxlen=400)
        self.thread = threading.Thread(target=self.copy, args=(stream,), daemon=True)
        self.thread.start()

    def copy(self, stream):
        for line in stream:
            print(line, end='', flush=True)
            if 'inference compute' in line and re.search(r'\bid="?cpu\b', line):
                print('WARNING: Ollama selected CPU although a GPU was visible to serve. '
                      'Check OLLAMA_LLM_LIBRARY, driver compatibility and GPU compute mode; '
                      'GPU readiness still requires positive VRAM offload.', flush=True)
            if any(key in line.lower() for key in ('cuda','gpu','discover','runner','driver','error','compute','library')):
                self.lines.append(line.rstrip())

    def failure(self):
        print('FUNGEN_GPU_FAILURE_BEGIN', flush=True)
        probe(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'])
        runtime_requirements()
        for line in list(self.lines):
            print('FUNGEN_GPU_DISCOVERY '+line, flush=True)
        print('FUNGEN_GPU_FAILURE_END', flush=True)
