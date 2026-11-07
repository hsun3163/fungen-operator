"""Install on the host; serve Laguna in Apptainer; run host Codex; switch backend local/openai."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import errno
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request

MODELS = {"laguna-xs-2.1:q4_K_M": 20, "laguna-xs-2.1:q8_0": 36,
          "laguna-s-2.1:q4_K_M": 96, "laguna-s-2.1:q8_0": 128}
FITS = {'laguna-xs-2.1:q4_K_M':'one 24–48 GB GPU','laguna-xs-2.1:q8_0':'one 48–80 GB GPU',
        'laguna-s-2.1:q4_K_M':'one 141 GB GPU or two 80 GB GPUs',
        'laguna-s-2.1:q8_0':'one 141 GB GPU (tight) or two 80 GB GPUs'}
MIN_CODEX = (0, 155, 1)
BUNDLE = Path('/opt/fungen')
# Written by the local branch of setup; the first five are required to serve.
LOCAL_KEYS = ('model', 'models', 'gpus', 'context', 'port', 'source_models', 'runtime_models', 'serve_model', 'local_codex')
OFFLINE = 'No network: download on a login node or another machine, then rerun setup --download no --models-dir FOLDER.'


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'fungen/config.toml'


def mount_info(path):
    """Identify the deepest mount, preserving its source and filesystem root."""
    path=os.path.realpath(path);matches=[]
    try:
        lines=Path('/proc/self/mountinfo').read_text().splitlines()
        for line in lines:
            fields,sep,tail=line.partition(' - ')
            fields=fields.split();tail=tail.split()
            if not sep or len(fields)<6 or len(tail)<3:
                return None
            unescape=lambda x:re.sub(r'\\([0-7]{3})',lambda m:chr(int(m.group(1),8)),x)
            point=unescape(fields[4])
            if path==point or path.startswith(point.rstrip('/')+'/'):
                matches.append(dict(point=point,root=unescape(fields[3]),fstype=tail[0],source=unescape(tail[1]),device=fields[2]))
    except (OSError,UnicodeError):
        return None
    if not matches:return None
    deepest=max(len(x['point']) for x in matches)
    matches=[x for x in matches if len(x['point'])==deepest]
    return matches[0] if len(matches)==1 else None


def mount_type(path):
    info=mount_info(path)
    return info['fstype'] if info else None


def host_disk_source(info):
    """Positive kernel evidence of a physical host block-device source.

    Private loop/dm/ram devices and unavailable device identities are unverified.
    A subdirectory mount root alone supplies no storage-origin evidence.
    """
    try:
        source=Path(info['source']).stat()
        device=f'{os.major(source.st_rdev)}:{os.minor(source.st_rdev)}'
        kernel=Path('/sys/dev/block')/device
        return (stat.S_ISBLK(source.st_mode) and device==info['device'] and kernel.exists()
                and '/virtual/' not in str(kernel.resolve()))
    except (OSError,ValueError,KeyError):
        return False


def host_visible(path):
    info=mount_info(path)
    if not info or info['point']=='/' or info['source'] in ('none','overlay','squashfs','tmpfs','ramfs'):
        return False
    if info['fstype'] in ('tmpfs','overlay','squashfs','ramfs'):
        return False
    shared=info['fstype'] in ('nfs','nfs4','gpfs','lustre','beegfs')
    return shared or (info['root']!='/' and host_disk_source(info))


def read_config():
    return tomllib.loads(config_path().read_text()) if config_path().exists() else {}


def write_config(config):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ''.join(f'{k} = {json.dumps(v)}\n' for k, v in config.items())
    if path.exists() and path.read_text() == content:
        return
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        f.write(content)
    os.chmod(f.name, 0o600)
    os.replace(f.name, path)


def ask(prompt, default, choices=None):
    while True:
        value = input(f'{prompt} [{default}]: ').strip() or str(default)
        if choices is None or value in choices:
            return value
        print('Choose: ' + ', '.join(choices))


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def api(url, path='/api/tags', data=None, timeout=5):
    request = urllib.request.Request(url+path, data=None if data is None else json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as r:
            result = json.load(r)
    except urllib.error.HTTPError as exc:
        try: message=json.loads(exc.read()).get('error',str(exc))
        except ValueError: message=str(exc)
        raise RuntimeError('Ollama API: '+message) from exc
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result


def scheduler():
    if shutil.which('bsub') or os.environ.get('LSF_BINDIR'):
        return 'lsf'
    if shutil.which('sbatch'):
        return 'slurm'
    if shutil.which('qsub') and (os.environ.get('SGE_ROOT') or shutil.which('qconf')):
        return 'sge'
    return 'local'


def gpu_memory():
    try:
        visible=os.environ.get('CUDA_VISIBLE_DEVICES')
        if visible in ('','-1','NoDevFiles'): return []
        command=['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits']
        if visible is not None: command += ['--id='+visible]
        p = run(command,
                capture_output=True, text=True)
        return [int(x)/1024 for x in p.stdout.split()]
    except (OSError, ValueError, subprocess.CalledProcessError):
        return []


def model_default(memory):
    # Reserve memory for runtime/KV cache; do not assume all devices are visible.
    if memory and (max(memory) >= 140 or sum(sorted(memory, reverse=True)[:2]) >= 150):
        return 'laguna-s-2.1:q8_0'
    if memory and max(memory) >= 48:
        return 'laguna-xs-2.1:q8_0'
    return 'laguna-xs-2.1:q4_K_M'


def gpu_count(model, memory, context=32768):
    need = MODELS[model] + (24 if context == 262144 else 4)
    if memory:
        total=0
        for count,value in enumerate(sorted(memory,reverse=True),1):
            total+=value
            if total>=need: return count
    return 2 if model.startswith('laguna-s-') or context==262144 else 1


def model_folder(install, sched):
    if sched == 'local':
        return install/'models'
    print('Cluster home directories have quotas: prefer scratch or project space for 20–128 GB models.')
    for key in ('SCRATCH', 'PROJECT', 'WORK'):
        if os.environ.get(key):
            return Path(os.environ[key])/'fungen/models'
    user = os.environ.get('USER', Path.home().name)
    for p in (Path('/scratch')/user, Path('/sc/arion/scratch')/user):
        if p.is_dir() and os.access(p, os.W_OK):
            return p/'fungen/models'
    return install/'models'


def manifest(folder, model):
    name, tag = model.split(':')
    return Path(folder)/'manifests/registry.ollama.ai/library'/name/tag


def model_present(folder, model):
    try:
        doc = json.loads(manifest(folder, model).read_text())
        for layer in [doc['config'], *doc['layers']]:
            p = Path(folder)/'blobs'/layer['digest'].replace(':', '-')
            if not p.is_file() or p.stat().st_size != layer['size']:
                return False
        return True
    except (OSError, KeyError, ValueError):
        return False


def check_folder(folder, download, size):
    folder = Path(folder).expanduser().resolve()
    if download:
        folder.mkdir(parents=True, exist_ok=True)
        required = int((size*1.1+2)*1E9)
        print(f'Download budget {required/1E9:.1f} GB; free {shutil.disk_usage(folder).free/1E9:.1f} GB. Site quota must also allow this budget.')
        if shutil.disk_usage(folder).free < required:
            raise ValueError('Insufficient free space. Choose --models-dir on scratch/project storage.')
        try:
            with tempfile.TemporaryFile(dir=folder) as probe:
                if hasattr(os,'posix_fallocate'):
                    os.posix_fallocate(probe.fileno(),0,required)
        except OSError as exc:
            raise ValueError('Model storage quota/reservation check failed: '+str(exc)+'. Choose --models-dir on storage with enough quota.') from exc
    elif not folder.is_dir() or not os.access(folder, os.R_OK | os.X_OK):
        raise ValueError('Existing model folder must be readable; choose --models-dir FOLDER.')
    return str(folder)


def recent_codex(path):
    try:
        m = re.search(r'(\d+)\.(\d+)\.(\d+)', run([path, '--version'], capture_output=True, text=True).stdout)
        return m is not None and tuple(map(int, m.groups())) >= MIN_CODEX
    except (OSError, subprocess.CalledProcessError):
        return False


def host_codex():
    candidates = [os.environ.get('FUNGEN_HOST_CODEX'), shutil.which('codex'), str(Path.home()/'.local/bin/codex')]
    candidates += [str(Path(p)/'codex') for p in os.environ.get('PATH', '').split(':') if not p.startswith('/opt/')]
    for p in candidates:
        if p and not p.startswith('/opt/') and recent_codex(p):
            return str(Path(p).absolute())
    return None


def install_kernel(install):
    """Make setup notebook cells use the operator's installed host Python."""
    data=Path(os.environ.get('JUPYTER_DATA_DIR',str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'jupyter')))
    path=data/'kernels/fungen-operator/kernel.json'
    content=json.dumps({'argv':[str(install/'venv/bin/python'),'-m','ipykernel_launcher','-f','{connection_file}'],
                        'display_name':'Fungen Operator','language':'python',
                        'env':{'PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1'}},indent=2)+'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or path.read_text()!=content:path.write_text(content)
    return path


def atomic_copy(source,target):
    """Preserve live executable mappings and leave identical files untouched."""
    source,target=Path(source),Path(target)
    if target.is_file() and source.stat().st_size==target.stat().st_size:
        with source.open('rb') as a,target.open('rb') as b:
            if hashlib.file_digest(a,'sha256').digest()==hashlib.file_digest(b,'sha256').digest():return str(target)
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as stream:temporary=Path(stream.name)
    try:
        shutil.copy2(source,temporary)
        os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()
    return str(target)


def install_host(install):
    install.mkdir(parents=True, exist_ok=True)
    if not BUNDLE.is_dir():
        raise ValueError('Run setup from the SIF: apptainer run fungen.sif')
    identity = hashlib.sha256()
    for source in sorted((BUNDLE/'wheels').glob('*')):
        identity.update(source.read_bytes())
    for source in sorted((BUNDLE/'skills/fungen-operator').rglob('*')):
        if source.is_file(): identity.update(source.read_bytes())
    if (BUNDLE/'README.md').exists(): identity.update((BUNDLE/'README.md').read_bytes())
    version = identity.hexdigest()
    stamp = install/'bundle.sha256'
    changed = not stamp.exists() or stamp.read_text() != version
    if changed:
        for name in ('python', 'wheels', 'skills'):
            shutil.copytree(BUNDLE/name, install/name, dirs_exist_ok=True,copy_function=atomic_copy)
        if (BUNDLE/'docs').is_dir(): shutil.copytree(BUNDLE/'docs',install/'docs',dirs_exist_ok=True,copy_function=atomic_copy)
        if (BUNDLE/'README.md').exists(): atomic_copy(BUNDLE/'README.md',install/'README.md')
    if (BUNDLE/'source.json').exists(): atomic_copy(BUNDLE/'source.json',install/'source.json')
    (install/'bin').mkdir(exist_ok=True)
    atomic_copy(BUNDLE/'bin/uv', install/'bin/uv')
    python = install/'python/bin/python3'
    venv = install/'venv'
    if not (venv/'bin/python').exists():
        run([install/'bin/uv', 'venv', '--relocatable', '--python', python, venv])
    if changed:
        run([install/'bin/uv', 'pip', 'install', '--python', venv/'bin/python', '--no-index',
             '--find-links', install/'wheels', '--reinstall-package', 'fungen-operator', 'fungen-operator'])
        stamp.write_text(version)
    install_kernel(install)
    codex = host_codex()
    if not codex and recent_codex(install/'bin/codex'):codex=str(install/'bin/codex')
    if codex:
        print(f'Keeping host Codex: {codex}')
    else:
        for name in ('codex', 'bwrap'):
            atomic_copy(BUNDLE/'bin'/name, install/'bin'/name)
        codex = str(install/'bin/codex')
        print('Installed bundled Codex 0.155.1 on the host.')
    for name in ('fungen', 'fungen-operator'):
        link = install/'bin'/name
        target = venv/'bin'/name
        if not link.exists():
            link.symlink_to(target)
    # A dedicated skill is visible both to ordinary host Codex and local sessions.
    for root in (Path.home()/'.agents/skills', Path.home()/'.codex/skills', install/'codex/skills'):
        root.mkdir(parents=True, exist_ok=True)
        dest = root/'fungen-operator'
        source = install/'skills/fungen-operator'
        if dest.is_symlink() and dest.resolve() == source.resolve():
            continue
        if dest.exists():
            raise ValueError(f'Existing skill at {dest}; move it aside explicitly before setup.')
        dest.symlink_to(source, target_is_directory=True)
    return codex


def runtime(config, nv=False):
    command = [config['runtime'], 'run']
    if nv:
        command += ['--nv']
    # HOME must be a bind; Singularity refuses --env HOME.
    if config.get('source_models'):
        command += ['--bind', config['source_models']+':'+config['source_models']+':ro']
    command += ['--home', f'{Path.home()}:{Path.home()}', '--bind',
                f"{config.get('runtime_models',config['models'])}:/models", config['image']]
    return command


def render_serve(config):
    root = Path(config['install'])
    state = root/'server.json'
    sched = config['scheduler']
    directives = ''
    if sched == 'lsf':
        directives = (f"#BSUB -J fungen-serve\n#BSUB -P {config['account']}\n#BSUB -q {config['gpu_queue']}\n"
                      f"#BSUB -n 2\n#BSUB -R \"rusage[mem=32000] span[hosts=1]\"\n#BSUB -M 64000\n#BSUB -W 12:00\n"
                      f"#BSUB -gpu \"num={config['gpus']}:gmem={(MODELS[config['model']]+(24 if config['context']==262144 else 4)+config['gpus']-1)//config['gpus']}G:mode=exclusive_process\"\n#BSUB -o {shlex.quote(str(root/'serve.%J.log'))}\n")
    elif sched == 'slurm':
        directives = (f"#SBATCH --job-name=fungen-serve\n#SBATCH --gres=gpu:{config['gpus']}\n"
                      f"#SBATCH --cpus-per-task=4\n#SBATCH --mem=64G\n#SBATCH --time=12:00:00\n"
                      f"#SBATCH --output={shlex.quote(str(root/'serve.%j.log'))}\n")
    elif sched == 'sge':
        directives = (f"#$ -N fungen-serve\n#$ -S /bin/bash\n"+(f"#$ -P {config['account']}\n" if config.get('account') else '')+"#$ -pe smp 4\n"
                      f"#$ -l h_rt=12:00:00,h_vmem=16G,gpu={config['gpus']}\n#$ -j y\n"
                      f"#$ -o {shlex.quote(str(root))}/serve.$JOB_ID.log\n")
    command = runtime(config, nv=True) + ['serve', '--models-dir', '/models', '--model', config.get('serve_model',config['model']),
               '--port', str(config['port']), '--state', str(state), '--context', str(config['context'])]
    return '#!/bin/bash\n'+directives+'set -euo pipefail\nexec '+shlex.join(command)+'\n'


def gpu_driver():
    return any(Path('/proc/driver/nvidia/gpus').glob('*/information'))


def setup(args):
    image = args.image or os.environ.get('APPTAINER_CONTAINER') or os.environ.get('SINGULARITY_CONTAINER')
    launch = args.runtime or ('apptainer' if os.environ.get('APPTAINER_CONTAINER') or not os.environ.get('SINGULARITY_CONTAINER') else 'singularity')
    # Without the host home bound, setup would write config and tools into a container-only folder.
    if BUNDLE.is_dir():
        destinations=[Path.home(),config_path().parent]
        unknown=[p for p in destinations if not host_visible(p)]
        if not Path.home().is_dir() or unknown:
            command=[launch,'run','--home',f'{Path.home()}:{Path.home()}']
            for folder in unknown:
                if not folder.is_relative_to(Path.home()):command+=['--bind',f'{folder}:{folder}']
            command+=[image or 'fungen.sif']
            raise ValueError('Host home/config mount identity is unknown or private. Run: '+shlex.join(command))
    previous = read_config()
    interactive = not args.non_interactive
    def answer(name, prompt, default, choices=None, saved=True):
        value = getattr(args, name)
        default = previous.get(name, default) if saved else default
        return value if value is not None else (ask(prompt, default, choices) if interactive else default)
    install = Path(answer('install', 'Install folder', str(Path.home()/'.fungen'))).expanduser().resolve()
    if BUNDLE.is_dir() and not host_visible(install):
        raise ValueError(f'Install folder {install} has unknown or private mount identity. Create the folder on the host, then run: '+shlex.join([launch,'run','--home',f'{Path.home()}:{Path.home()}','--bind',f'{install}:{install}',image or 'fungen.sif','setup','--install',str(install)]))
    detected = scheduler()
    # A missing scheduler client is unavailable detection, not an explicit local choice.
    if args.scheduler is None and detected=='local':
        print('No scheduler client detected; '+('using saved scheduler '+previous['scheduler'] if previous.get('scheduler') else 'defaulting to local')+'. Select explicitly with --scheduler lsf/slurm/sge/local.')
    sched = answer('scheduler', 'Scheduler (lsf/slurm/sge/local)', detected if detected != 'local' else previous.get('scheduler', 'local'), ['lsf','slurm','sge','local'], saved=False)
    # The account/project belongs to its scheduler: LSF defaults to acc_LOAD, others to none.
    account = 'acc_LOAD' if sched == 'lsf' else ''
    account = previous.get('account', account) if previous.get('scheduler') == sched else account
    if sched == 'sge':
        print('SGE project: empty omits -P and requests the site default (not verified here). Enter - to clear a saved project; supply --account PROJECT if your site requires one.')
        account = answer('account', 'SGE project (-P)', account, saved=False)
        if account=='-':account=''
    elif args.account is not None:
        account=args.account
    backend = answer('backend', 'Model backend (local/openai)', 'local', ['local','openai'])
    memory = gpu_memory()
    host_gpu=bool(memory) or gpu_driver()
    if backend == 'local' and sched == 'local' and not host_gpu:
        raise ValueError('No GPU visible. Use setup --backend openai, or run on a GPU node with apptainer run --nv fungen.sif.')
    config = {'install': str(install), 'scheduler': sched, 'backend': backend,
              'image': str(Path(image or previous.get('image', '')).resolve()),
              'runtime': args.runtime or shutil.which('apptainer') or shutil.which('singularity') or previous.get('runtime', 'singularity' if os.environ.get('SINGULARITY_CONTAINER') else 'apptainer'),
              'account': account,
              'gpu_queue': args.gpu_queue or previous.get('gpu_queue', 'gpuexpress')}
    if backend == 'local':
        print('Models (download):\n'+ '\n'.join(f'  {m}: {s} GB; {FITS[m]}' for m,s in MODELS.items()))
        model = answer('model', 'Model tag', model_default(memory), MODELS)
        download = answer('download', 'Download model? (yes/no)', 'no', ['yes','no'])
        folder = answer('models_dir', 'Model folder to download into or reuse', previous.get('models', str(model_folder(install, sched))))
        config.update(model=model, models=check_folder(folder, download == 'yes' and not model_present(Path(folder).expanduser(),model), MODELS[model]),
                      context=int(answer('context', 'Context (32768; advanced 262144 needs extra GPU memory)', 32768, ['32768','262144'])),
                      port=int(args.port or previous.get('port',11434)))
        config['gpus'] = gpu_count(model, memory, config['context'])
        if download == 'no' and not model_present(config['models'], model):
            # A staged advanced preset is usable without modifying its read-only store.
            raise ValueError('Model is incomplete or absent. Rerun with --download yes to resume, or select the exact installed tag.')
    config['codex'] = install_host(install)
    if backend=='local':
        # The bundled model catalog is versioned with this exact local client.
        for name in ('codex','bwrap'):
            source=BUNDLE/'bin'/name
            if source.is_file():atomic_copy(source,install/'bin'/name)
        config['local_codex']=str(install/'bin/codex')
    if backend == 'openai':
        config.update({k: previous[k] for k in LOCAL_KEYS if k in previous})
    if backend == 'local':
        # Codex model metadata for the Laguna tags; fungen codex passes it as model_catalog_json.
        (install/'codex').mkdir(parents=True, exist_ok=True)
        atomic_copy(Path(__file__).with_name('resources')/'codex-models.json', install/'codex/models.json')
        if download == 'yes' and not model_present(config['models'], model):
            download_model(config)
        prepare_runtime_store(config)
        if config['context'] == 262144:
            context_variant(config)
        script = install/f'serve.{sched}.sh'
        content = render_serve(config)
        if not script.exists() or script.read_text() != content:
            script.write_text(content)
            script.chmod(0o755)
    write_config(config)
    path_answer = answer('add_path', 'Add the install bin folder to your shell PATH? (yes/no)', 'no', ['yes','no'])
    if path_answer == 'yes':
        profile = Path.home()/('.zshrc' if os.environ.get('SHELL','').endswith('zsh') else '.bashrc')
        line = 'export PATH='+shlex.quote(str(install/'bin'))+':"$PATH"'
        old = profile.read_text() if profile.exists() else ''
        if line not in old.splitlines():
            with profile.open('a') as f:
                f.write('\n'+line+'\n')
    if backend == 'openai':
        print('OpenAI sign-in on the host: '+shlex.join([config['codex'], 'login', '--device-auth']))
        print('Or set OPENAI_API_KEY in your shell. Credentials stay in Codex home, never the working folder or image.')
    check(config, online=not args.offline_check)
    print('Installed. Run on the host:\n  '+str(install/'bin/fungen')+' serve\n  '+str(install/'bin/fungen')+' codex')
    if backend == 'local' and not host_gpu:
        print('No GPU on this host: GPU offload remains unverified until fungen serve starts on the GPU job and fungen check passes. CPU-only model readiness is refused.')


def download_model(config):
    if BUNDLE.is_dir():
        return inside_download(argparse.Namespace(models_dir=config['models'], model=config['model'], context=32768, skip_pull=False))
    # Acquisition needs no GPU and resumes Ollama's partial blob files.
    command = [config['runtime'], 'run', '--home', f'{Path.home()}:{Path.home()}',
               '--bind', f"{config['models']}:/models", config['image'], 'download', '--models-dir', '/models', '--model', config['model']]
    run(command)


def prepare_runtime_store(config):
    """Ollama 0.40 migrates manifests; keep mutable metadata off the source store."""
    source=Path(config['models'])
    overlay=Path(config['install'])/'server-models'
    (overlay/'blobs').mkdir(parents=True,exist_ok=True)
    for folder in ('manifests','manifests-v2'):
        if (source/folder).is_dir():
            shutil.copytree(source/folder,overlay/folder,dirs_exist_ok=True)
    for blob in (source/'blobs').iterdir():
        target=overlay/'blobs'/blob.name
        if not target.exists(): target.symlink_to(blob)
    config['source_models']=str(source)
    config['runtime_models']=str(overlay)


def context_variant(config):
    if os.statvfs(config['models']).f_flag & os.ST_RDONLY:
        raise ValueError('256k variant creation requires writable model blobs: Ollama refreshes their timestamps. Choose a writable --models-dir or use --context 32768 for read-only reuse.')
    if 'runtime_models' not in config: prepare_runtime_store(config)
    overlay=Path(config['runtime_models'])
    config['serve_model']=config['model']+'-256k'
    if not model_present(overlay,config['serve_model']):
        args=argparse.Namespace(models_dir=str(overlay),model=config['model'],context=262144,skip_pull=True)
        inside_download(args)


def available_port(port):
    for p in range(port, port+100):
        with socket.socket() as sock:
            try:
                sock.bind(('0.0.0.0',p))
                return p
            except OSError:
                continue
    raise RuntimeError('No free port. Set setup --port to an unused port.')


def inside_serve(args):
    if not gpu_memory():
        raise ValueError('GPU unavailable: refusing CPU-only inference. Run fungen serve on the host to submit the GPU job; on a GPU node use apptainer run --nv fungen.sif serve.')
    port = available_port(args.port)
    env = dict(os.environ, OLLAMA_HOST=f'0.0.0.0:{port}', OLLAMA_MODELS=args.models_dir, OLLAMA_NO_CLOUD='1',
               OLLAMA_CONTEXT_LENGTH=str(args.context), OLLAMA_FLASH_ATTENTION='1', OLLAMA_KEEP_ALIVE='-1', OLLAMA_NOPRUNE='1',
               OLLAMA_KV_CACHE_TYPE='q8_0', OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1')
    process = subprocess.Popen(['ollama', 'serve'], env=env)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError('Ollama exited; inspect the serve job log for driver/CUDA errors.')
            try:
                api(url)
                break
            except (OSError, ValueError):
                time.sleep(1)
        else:
            raise RuntimeError('Ollama startup timed out. Inspect the serve job log.')
        model = args.model
        answer = api(url, '/api/generate', {'model':model,'prompt':'Reply exactly: READY','stream':False,
                    'think':False,'options':{'num_ctx':args.context,'num_predict':24}}, timeout=1800)
        if not answer.get('response','').strip():
            raise RuntimeError('Model produced no answer; inspect GPU memory and the serve log.')
        if not any(m.get('name')==model and m.get('size_vram',0)>0 for m in api(url,'/api/ps')['models']):
            raise RuntimeError('GPU offload unavailable for the selected model; refusing CPU-only model readiness. Run the server as a GPU job with --nv (fungen serve does both) and check the host NVIDIA driver/CUDA compatibility in this log.')
        state = {'endpoint':f'http://{socket.getfqdn()}:{port}','node':socket.getfqdn(),'port':port,
                 'model':model,'job_id':os.environ.get('LSB_JOBID',os.environ.get('SLURM_JOB_ID',os.environ.get('JOB_ID',''))),
                 'pid':process.pid, 'ready':True}
        Path(args.state).write_text(json.dumps(state,indent=2)+'\n')
        print('FUNGEN_READY '+json.dumps(state),flush=True)
        return process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=30)


def repair_pull_progress(folder):
    """Restore Ollama 0.40.6's complete, numbered partition protocol.

    server/download.go: total/16, clamped to 100--1000 decimal MB. A missing
    record cannot simply be removed: Prepare sums the records and cleanup
    requires every index. Unknown completion resets only that chunk to zero.
    """
    folder=Path(folder);recovered=[]
    for blob in sorted((folder/'blobs').glob('sha256-*-partial')):
        if not re.fullmatch(r'sha256-[0-9a-f]{64}-partial',blob.name) or not blob.is_file():continue
        total=blob.stat().st_size
        if total<=0:continue
        chunk=min(1000000000,max(100000000,total//16))
        for n,offset in enumerate(range(0,total,chunk)):
            path=blob.with_name(blob.name+'-'+str(n));size=min(chunk,total-offset)
            try:
                doc=json.loads(path.read_text())
                valid=(isinstance(doc,dict) and doc.get('N')==n and doc.get('Offset')==offset
                       and doc.get('Size')==size and type(doc.get('Completed')) is int and 0<=doc['Completed']<=size)
            except (FileNotFoundError,ValueError,UnicodeError):valid=False
            if valid:continue
            if path.exists():
                archive=folder/'.fungen-download-recovery';archive.mkdir(exist_ok=True)
                path.rename(archive/(path.name+'.'+str(time.time_ns())))
            with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as stream:
                json.dump({'N':n,'Offset':offset,'Size':size,'Completed':0},stream);stream.write('\n')
                stream.flush();os.fsync(stream.fileno())
            os.replace(stream.name,path);recovered.append(path)
    if recovered:
        print(f'Rebuilt {len(recovered)} incomplete Ollama progress records; damaged originals are archived under {folder / ".fungen-download-recovery"}. Partial model bytes and valid progress are retained.',flush=True)
    return recovered


def inside_download(args):
    if not args.skip_pull:repair_pull_progress(args.models_dir)
    port = available_port(11434)
    env = dict(os.environ,OLLAMA_HOST=f'127.0.0.1:{port}',OLLAMA_MODELS=args.models_dir,OLLAMA_NO_CLOUD='1')
    process = subprocess.Popen(['ollama','serve'],env=env,stdout=sys.stderr,stderr=sys.stderr)
    try:
        for _ in range(60):
            try:
                api('http://'+env['OLLAMA_HOST'])
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError('Download server exited. Check model-folder write access.')
                time.sleep(1)
        try:
            if not args.skip_pull:
                run(['ollama','pull',args.model],env=env)
            if args.context == 262144:
                modelfile=Path(args.models_dir)/'Laguna-256k.Modelfile'
                modelfile.write_text('FROM '+args.model+'\nPARAMETER num_ctx 262144\n')
                run(['ollama','create',args.model+'-256k','-f',modelfile],env=env)
        except subprocess.CalledProcessError as exc:
            if args.skip_pull:
                raise RuntimeError('256k variant creation failed. Use a writable model store; Ollama refreshes base-blob timestamps. Use context 32768 for read-only reuse. Native error: '+str(exc)) from exc
            raise RuntimeError(OFFLINE+' Partial downloads are retained; repeat the same command.') from exc
    finally:
        process.terminate()
        process.wait(timeout=30)


def state(config):
    return runtime_status(config)[1]


def server_request(config):
    """Validate current receipts and the historical LSF-only receipt schema."""
    path=Path(config['install'])/'server-request.json'
    saved=json.loads(path.read_text())
    if not isinstance(saved,dict):raise ValueError('Invalid server receipt; inspect server-request.json and the native job before retrying.')
    if set(saved)=={'job_id'}:
        if config['scheduler']!='lsf':
            raise ValueError('Legacy server receipt belongs to LSF. Inspect bjobs/bacct for job '+str(saved['job_id'])+' and restore --scheduler lsf before reusing this launch.')
        saved={**saved,'scheduler':'lsf'}
    sched=saved.get('scheduler')
    if sched!=config['scheduler']:raise ValueError('Receipt scheduler differs from configured scheduler; inspect the recorded native job before retrying.')
    key='pid' if sched=='local' else 'job_id'
    value=str(saved.get(key,''))
    if sched not in ('lsf','sge','slurm','local') or not value.isdecimal() or int(value)<=0:
        raise ValueError('Invalid server receipt identity; inspect the recorded native job before retrying.')
    if sched=='local' and ('process_start' in saved or 'boot_id' in saved):
        if not str(saved.get('process_start','')).isdecimal() or not saved.get('boot_id'):
            raise ValueError('Local process birth identity is incomplete; inspect the recorded PID before retrying.')
    return saved


@dataclass(frozen=True)
class RuntimeObservation:
    ready: bool | None
    info: dict
    detail: str
    launch: str | None


def local_process_identity(pid):
    """Return a live process birth identity, or None for a positively ended PID."""
    try:
        os.kill(int(pid),0)
        fields=Path('/proc/'+str(int(pid))+'/stat').read_text().rsplit(')',1)[1].split()
    except (ProcessLookupError,FileNotFoundError):return None
    if len(fields)<20:raise ValueError('Local process identity is incomplete')
    if fields[0] in ('Z','X'):return None
    return {'process_start':fields[19],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def runtime_observation(config):
    root=Path(config['install']);request=root/'server-request.json';state_path=root/'server.json'
    saved=None;launch=None
    if request.exists():
        try:
            saved=server_request(config)
            if saved['scheduler']=='local':
                identity=local_process_identity(saved['pid'])
                if identity is None or ('process_start' in saved and any(saved[k]!=identity[k] for k in ('process_start','boot_id'))):
                    launch='not_running'
                else:launch='running'
            else:
                from .cluster import job_status
                launch=job_status(saved['scheduler'],str(saved['job_id']))
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
            return RuntimeObservation(False,{},'Launch status retrieval failed: '+str(exc),'unknown')
        if launch!='running':
            return RuntimeObservation(False,{},'Recorded server launch is not running ('+launch+'); inspect its job log.',launch)
    if not state_path.exists():
        return RuntimeObservation(None,{},'Recorded launch is pending readiness.' if saved else 'Server has not been started.',launch)
    try:
        info=json.loads(state_path.read_text());model=config.get('serve_model',config['model'])
        if info['model']!=model or not info['ready']:raise ValueError('server state does not match selected model/readiness')
        if saved and (state_path.stat().st_mtime_ns<request.stat().st_mtime_ns or str(info.get('job_id',''))!=str(saved.get('job_id',''))):
            return RuntimeObservation(None,{},'Current launch has not recorded readiness; previous server state is stale.',launch)
        models=api(info['endpoint'])['models']
        if not any(m['name']==model for m in models):raise ValueError('selected model is absent from server')
        return RuntimeObservation(True,info,'',launch)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        return RuntimeObservation(False,{},'Recorded server is unreachable or invalid: '+str(exc),launch)


def runtime_status(config):
    observed=runtime_observation(config)
    return observed.ready,observed.info,observed.detail


def serve(config):
    if config['backend']=='openai':
        print('OpenAI backend: run fungen codex. No local model server is needed. Switch with: fungen backend local')
        return
    observed=runtime_observation(config)
    if observed.ready:
        print('Server ready: '+observed.info['endpoint']);return
    root=Path(config['install']);request=root/'server-request.json'
    if observed.launch=='unknown':raise RuntimeError(observed.detail)
    if observed.ready is None and request.exists():
        print(observed.detail+' fungen check reports NOT VERIFIED until the endpoint and GPU offload pass.');return
    if observed.launch=='running':
        raise RuntimeError(observed.detail+' Inspect the current live launch before starting another server.')
    script=root/f"serve.{config['scheduler']}.sh";sched=config['scheduler']
    if sched=='lsf':
        with script.open() as f:r=run(['bsub'],stdin=f,capture_output=True,text=True)
        match=re.search(r'Job <(\d+)>',r.stdout)
    elif sched in ('slurm','sge'):
        r=run(['sbatch','--parsable',script] if sched=='slurm' else ['qsub','-terse',script],capture_output=True,text=True)
        match=re.fullmatch(r'(\d+)(?:;[^\s]+)?\s*',r.stdout) if sched=='slurm' else re.fullmatch(r'(\d+)\s*',r.stdout)
    else:
        with (root/'serve.log').open('a') as f:p=subprocess.Popen(['bash',str(script)],stdout=f,stderr=f,start_new_session=True)
        saved={'scheduler':'local','pid':p.pid}
        # Retain the new PID immediately, including when identity inspection fails.
        # This prevents a launched process from becoming an untracked retry.
        request.write_text(json.dumps(saved)+'\n')
        identity=local_process_identity(p.pid)
        if identity is None:raise RuntimeError('Local server process exited before startup identity was recorded; inspect serve.log.')
        saved.update(identity);request.write_text(json.dumps(saved)+'\n')
        print(f'Started GPU server PID {p.pid}; log: {f.name}');return
    print(r.stdout,end='')
    if not match:raise RuntimeError('Server submission returned no unambiguous job ID; inspect scheduler before retrying.')
    request.write_text(json.dumps({'scheduler':sched,'job_id':match.group(1)})+'\n')


def local_hint(config):
    return shlex.join([config['runtime'],'run',config['image'],'setup','--backend','local'])


def local_catalog(config):
    catalog=Path(config['install'])/'codex/models.json'
    try:
        doc=json.loads(catalog.read_text())
        shipped=json.loads((Path(__file__).with_name('resources')/'codex-models.json').read_text())
        if doc!=shipped or not doc.get('models'):
            raise ValueError('catalog differs from shipped catalog')
    except (OSError,ValueError,TypeError) as exc:
        raise ValueError('Local Codex model catalog missing or invalid. Rerun setup: '+local_hint(config)) from exc
    return catalog


def local_client(config):
    client=config.get('local_codex',config['codex'])
    try:
        version=run([client,'--version'],capture_output=True,text=True).stdout.strip()
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Local Codex client unavailable. Rerun setup: '+local_hint(config)) from exc
    if version!='codex-cli 0.155.1':
        raise ValueError('Local catalog requires Codex 0.155.1. Rerun setup: '+local_hint(config))
    return client


def served_catalog(config, endpoint, catalog):
    """Expose exact served IDs whose quantization and context are established by Ollama."""
    import copy
    import hashlib
    doc=json.loads(catalog.read_text())
    families={m['slug']:m for m in doc['models'] if m['visibility']=='none'}
    context=config.get('context',32768);selected=config.get('serve_model',config['model'])
    visible=[]
    try:
        tags=api(endpoint)['models']
        if not isinstance(tags,list):raise ValueError('invalid model inventory')
        names=[row['name'] for row in tags]
        if any(not isinstance(name,str) or not name for name in names):raise ValueError('invalid model identity')
        if len(names)!=len(set(names)):raise ValueError('ambiguous model inventory')
        loaded={row['name']:row for row in api(endpoint,'/api/ps')['models']}
        for name in sorted(names):
            family=name.split(':',1)[0]
            if family not in families:continue
            show=api(endpoint,'/api/show',{'model':name})
            quant=show['details']['quantization_level']
            tagged=re.search(r':(q4_K_M|q8_0)(?:-|$)',name)
            if tagged and tagged.group(1).upper()!=quant:
                raise ValueError('tag and payload quantization differ for '+name)
            params=dict(re.findall(r'^\s*(\w+)\s+(\S+)\s*$',show.get('parameters',''),re.M))
            model_info=show['model_info'];arch=model_info['general.architecture']
            capacity=int(model_info[arch+'.context_length'])
            # A base tag need not have a num_ctx parameter. Its loaded instance
            # must then provide positive effective-context evidence instead.
            configured=int(loaded[name]['context_length'] if name in loaded else params['num_ctx'])
            if quant not in ('Q4_K_M','Q8_0') or configured not in (32768,262144) or configured>capacity:
                raise ValueError('unsupported quantization/context for '+name)
            if configured!=context:continue
            model=copy.deepcopy(families[family])
            model.update(slug=name,display_name=name,visibility='list',context_window=context,max_context_window=context,
                         description=f'{family}, {quant}, {context} tokens; available on the current Ollama endpoint.')
            visible.append(model)
        if selected not in {m['slug'] for m in visible}:
            raise ValueError('selected model has no matching served quantization/context: '+selected)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        raise RuntimeError('Cannot verify local model override choices: '+str(exc)+'. Run fungen serve, then fungen check.') from exc
    # Exact served IDs precede the hidden family metadata used for prefix lookup.
    doc['models']=visible+list(families.values())
    encoded=(json.dumps(doc,indent=2)+'\n').encode()
    folder=catalog.parent/'served';folder.mkdir(exist_ok=True)
    target=folder/(hashlib.sha256(encoded).hexdigest()+'.json')
    if target.exists():
        if target.read_bytes()!=encoded:
            raise RuntimeError('Generated local model catalog is invalid; rerun setup before launching Codex.')
    else:
        import tempfile
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as stream:
            stream.write(encoded);temporary=Path(stream.name)
        temporary.replace(target)
    return target


def require_local(config):
    script=Path(config['install'])/f"serve.{config['scheduler']}.sh"
    if any(k not in config for k in LOCAL_KEYS[:5]) or not script.is_file():
        raise ValueError('Local backend is not configured. Run: '+local_hint(config))
    local_catalog(config)
    local_client(config)
    if not model_present(config['models'],config['model']):
        raise ValueError('Local model is incomplete. Rerun setup: '+local_hint(config))
    if config.get('runtime_models') and not model_present(config['runtime_models'],config.get('serve_model',config['model'])):
        raise ValueError('Local runtime model store is incomplete. Rerun setup: '+local_hint(config))
    if script.read_text()!=render_serve(config):
        raise ValueError('Local serve script differs from current configuration. Rerun setup: '+local_hint(config))


def backend(config,choice=None):
    if choice is None:
        print('Active backend: '+config['backend'])
        try:
            require_local(config)
            print(f"local: assets configured ({config['model']}, {config['models']}, serve.{config['scheduler']}.sh); runtime unverified: fungen serve, then fungen check")
        except ValueError as exc:
            print('local: not configured — '+str(exc))
        print('openai: authentication unverified (check with fungen check; sign in with '+shlex.join([config['codex'],'login','--device-auth'])+' or OPENAI_API_KEY)')
        return 0
    if choice == 'local': require_local(config)
    config['backend']=choice
    write_config(config)
    print('Backend: '+choice)
    print('Next: fungen serve, then fungen codex' if choice=='local' else 'Next: fungen codex (no server needed)')
    return 0


def codex(config,args):
    if args.backend:
        # One-session override; the saved config keeps its backend.
        if args.backend == 'local': require_local(config)
        config={**config,'backend':args.backend}
    env = dict(os.environ)
    extra = args.args[1:] if args.args[:1]==['--'] else args.args
    root_overrides=[]
    while extra[:1] in (['-c'],['--config']):
        if len(extra)<2: raise ValueError('Codex --config requires KEY=VALUE.')
        root_overrides.extend(extra[:2]);extra=extra[2:]
    subcommand=[]
    if extra[:1] == ['exec']:
        subcommand=['exec'];extra=extra[1:]
    overrides=[];provider=[]
    if config['backend'] == 'local':
        catalog=local_catalog(config)
        client=local_client(config)
        config={**config,'codex':client}
        deadline=time.monotonic()+args.wait
        while not (info:=state(config)):
            if time.monotonic()>=deadline:
                raise RuntimeError('Server unavailable. Run fungen serve; inspect serve job log and fungen check.')
            time.sleep(2)
        catalog=served_catalog(config,info['endpoint'],catalog)
        env['CODEX_HOME']=str(Path(config['install'])/'codex')
        env['CODEX_OSS_BASE_URL']=info['endpoint']+'/v1'
        env['CODEX_OLLAMA_MODEL']=config.get('serve_model',config['model'])
        provider=['--oss','--local-provider','ollama','--model',config.get('serve_model',config['model'])]
        # The TUI decides on the ChatGPT sign-in screen from the root config, before --oss
        # applies; naming the built-in ollama provider there skips sign-in.
        overrides += ['-c','model_provider="ollama"',
                      '-c','model_context_window='+str(config.get('context',32768)),
                      '-c','model_auto_compact_token_limit='+str(int(config.get('context',32768)*.75))]
        overrides += ['-c','model_catalog_json='+json.dumps(str(catalog))]
    elif env.get('OPENAI_API_KEY'):
        overrides += ['-c','model_provider="fungen_openai"','-c','model_providers.fungen_openai.name="OpenAI API"',
                      '-c','model_providers.fungen_openai.base_url="https://api.openai.com/v1"',
                      '-c','model_providers.fungen_openai.env_key="OPENAI_API_KEY"',
                      '-c','model_providers.fungen_openai.wire_api="responses"']
    overrides += ['-c','developer_instructions='+json.dumps('Read '+str(Path(config['install'])/'skills/fungen-operator/SKILL.md')+' before workflow operation. Ask before each setup notebook step. Operator and scheduler run on the host.')]
    if args.deployment:
        overrides += ['-c','mcp_servers.fungen.command='+json.dumps(str(Path(config['install'])/'bin/fungen-operator')),
                      '-c','mcp_servers.fungen.args='+json.dumps(['serve','--deployment',str(Path(args.deployment).resolve())]),
                      '-c','mcp_servers.fungen.required=true','-c','mcp_servers.fungen.startup_timeout_sec=60']
    # Root configuration overrides must precede exec in the pinned client.
    command=[config['codex']]+overrides+root_overrides+subcommand+provider+extra
    os.execvpe(command[0],command,env)


def check(config,online=True):
    rows=[]
    def row(name,good,fix):
        # None means verification is incomplete and keeps the aggregate non-successful.
        rows.append((name,None if good is None else bool(good),fix))
        print(('PENDING ' if good is None else 'PASS ' if good else 'FAIL ')+name+('' if good else ': '+fix))
    install=Path(config['install'])
    row('install writable',os.access(install,os.W_OK),'Choose setup --install WRITABLE_FOLDER.')
    row('install on PATH',str(install/'bin') in os.environ.get('PATH','').split(':'),'export PATH='+shlex.quote(str(install/'bin'))+':"$PATH"')
    try:
        imported=subprocess.run([install/'venv/bin/fungen-operator','--help'],capture_output=True,timeout=30).returncode==0
    except (OSError,subprocess.TimeoutExpired):
        imported=False
    row('operator importable',imported,'Rerun apptainer run fungen.sif.')
    row('skill visible',(Path.home()/'.agents/skills/fungen-operator/SKILL.md').is_file(),'Rerun apptainer run fungen.sif.')
    row('Codex recent enough',recent_codex(config.get('local_codex',config['codex']) if config['backend']=='local' else config['codex']),'Rerun setup to install bundled Codex 0.155.1.')
    if online:
        url=('https://registry.ollama.ai/v2/library/'+config['model'].replace(':','/manifests/')) if config['backend']=='local' else 'https://api.openai.com/v1/models'
        try:
            with urllib.request.urlopen(url,timeout=10): pass
            reachable=True
        except urllib.error.HTTPError as e:
            reachable=e.code in (401,403)
        except OSError:
            reachable=False
        row('internet reachable',reachable,OFFLINE)
    else:
        row('internet reachable',False,OFFLINE)
    if config['backend']=='local':
        try:
            require_local(config)
            assets_good=True;assets_detail=''
        except ValueError as exc:
            assets_good=False;assets_detail=str(exc)
        row('local backend assets',assets_good,assets_detail)
        folder=Path(config['models'])
        present=model_present(folder,config['model'])
        row('model present',present,'Rerun setup --download yes to resume the selected model.')
        row('model folder writable or complete read-only reuse',present or os.access(folder,os.W_OK),'Choose a writable --models-dir for downloading.')
        row('model space and quota',present or (folder.exists() and shutil.disk_usage(folder).free>(MODELS[config['model']]*1.1+2)*1E9),'Free model storage and check your site quota; rerun setup --models-dir FOLDER.')
        runtime_good,info,detail=runtime_status(config)
        next_action='Run fungen serve, then fungen check.'
        row('server reachable; port selected',runtime_good,detail+' '+next_action)
        gpu=None
        gpu_detail='GPU offload not verified. '+next_action
        if info:
            try:
                loaded=api(info['endpoint'],'/api/ps')['models']
                if not isinstance(loaded,list) or any(not isinstance(x,dict) for x in loaded):
                    raise ValueError('invalid /api/ps model list')
                selected=[x for x in loaded if x.get('name')==config.get('serve_model',config['model'])]
                gpu=any(x.get('size_vram',0)>0 for x in selected)
                gpu_detail='Selected model has no observed GPU offload. '+next_action
            except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
                gpu=False
                gpu_detail='GPU status retrieval failed: '+str(exc)+'. '+next_action
        row('GPU offload for selected model',gpu,gpu_detail)
    else:
        result=subprocess.run([config['codex'],'login','status'],capture_output=True)
        row('OpenAI sign-in or API key',bool(os.environ.get('OPENAI_API_KEY')) or result.returncode==0,
            shlex.join([config['codex'],'login','--device-auth'])+' (or export OPENAI_API_KEY in your shell).')
    verified=all(good is True for _,good,_ in rows)
    if verified:print('VERIFIED')
    elif any(good is False for _,good,_ in rows):
        print('NOT VERIFIED: correct failed checks; for local runtime run fungen serve, then fungen check.')
    else:print('NOT VERIFIED: runtime verification is pending. Run fungen serve, then fungen check.')
    return verified


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if BUNDLE.is_dir() and argv[:1] in (['codex'],['xqtl'],['check'],['backend']):
        install=Path(read_config().get('install',str(Path.home()/'.fungen')))
        print('fungen: Codex and workflows run on the host. Exit the image and run: '+shlex.join([str(install/'bin/fungen'),argv[0]]),file=sys.stderr)
        return 1
    if argv[:1]==['xqtl']:
        from .onboarding import main as onboard
        try:
            return onboard(argv[1:])
        except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError,EOFError) as exc:
            print('fungen: '+str(exc),file=sys.stderr)
            return 1
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command')
    p=sub.add_parser('setup',help='Install host tools and configure a backend')
    p.add_argument('--non-interactive',action='store_true')
    for name,choices in [('install',None),('backend',['local','openai']),('scheduler',['lsf','slurm','sge','local']),('model',list(MODELS)),('models-dir',None),('download',['yes','no']),('context',['32768','262144']),('add-path',['yes','no']),('image',None),('runtime',None),('account',None),('gpu-queue',None),('port',None)]:
        p.add_argument('--'+name,choices=choices,default=os.environ.get('FUNGEN_'+name.replace('-','_').upper()))
    p.add_argument('--offline-check',action='store_true',help='Report offline guidance without a network probe')
    for name in ('serve','download'):
        p=sub.add_parser(name,help='Start the GPU server' if name=='serve' else 'Image only: acquire/resume model blobs')
        p.add_argument('--models-dir',default='/models')
        p.add_argument('--model',default=next(iter(MODELS)))
        p.add_argument('--skip-pull',action='store_true')
        p.add_argument('--port',type=int,default=11434)
        p.add_argument('--context',type=int,choices=[32768,262144],default=32768)
        p.add_argument('--state',default=str(Path.home()/'.fungen/server.json'))
    p=sub.add_parser('codex',help='Host only: wait for the server, then run Codex')
    p.add_argument('--backend',choices=['local','openai'],help='Use this backend for one session')
    p.add_argument('--deployment')
    p.add_argument('--wait',type=int,default=1800)
    p.add_argument('args',nargs=argparse.REMAINDER)
    p=sub.add_parser('backend',help='Host only: show the model backend, or switch it (local/openai)')
    p.add_argument('choice',nargs='?',choices=['local','openai'])
    p=sub.add_parser('check',help='Report each installation check and its exact fix')
    p.add_argument('--offline',action='store_true')
    p=sub.add_parser('xqtl',help='Host only: guided xQTL setup and synthetic test')
    p.add_argument('args',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv or ['--help'])
    try:
        if args.command=='setup': return setup(args)
        if args.command=='xqtl':
            from .onboarding import main as onboard
            return onboard(args.args)
        if args.command=='download': return inside_download(args)
        if args.command=='serve' and BUNDLE.is_dir(): return inside_serve(args)
        config=read_config()
        if not config: raise ValueError('Run apptainer run fungen.sif to set up first.')
        if args.command=='serve': return serve(config)
        if args.command=='codex': return codex(config,args)
        if args.command=='backend': return backend(config,args.choice)
        if args.command=='check': return 0 if check(config,not args.offline) else 1
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError,EOFError) as exc:
        print('fungen: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
