"""Install on the host; serve Laguna in Apptainer; run host Codex."""
from __future__ import annotations
import argparse
import hashlib
import errno
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
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
OFFLINE = 'No network: download on a login node or another machine, then rerun setup --download no --models-dir FOLDER.'


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'fungen/config.toml'


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
    command = runtime(config, nv=True) + ['serve', '--models-dir', '/models', '--model', config.get('serve_model',config['model']),
               '--port', str(config['port']), '--state', str(state), '--context', str(config['context'])]
    return '#!/bin/bash\n'+directives+'set -euo pipefail\nexec '+shlex.join(command)+'\n'


def setup(args):
    previous = read_config()
    interactive = not args.non_interactive
    def answer(name, prompt, default, choices=None):
        value = getattr(args, name)
        return value if value is not None else (ask(prompt, previous.get(name, default), choices) if interactive else previous.get(name, default))
    install = Path(answer('install', 'Install folder', str(Path.home()/'.fungen'))).expanduser().resolve()
    sched = answer('scheduler', 'Scheduler (lsf/slurm/local)', scheduler(), ['lsf','slurm','local'])
    backend = answer('backend', 'Model backend (local/openai)', 'local', ['local','openai'])
    memory = gpu_memory()
    host_gpu=bool(memory) or any(Path('/proc/driver/nvidia/gpus').glob('*/information'))
    if backend == 'local' and sched == 'local' and not host_gpu:
        raise ValueError('No GPU visible. Use setup --backend openai, or run on a GPU node with apptainer run --nv fungen.sif.')
    config = {'install': str(install), 'scheduler': sched, 'backend': backend,
              'image': str(Path(args.image or os.environ.get('APPTAINER_CONTAINER') or os.environ.get('SINGULARITY_CONTAINER') or previous.get('image', '')).resolve()),
              'runtime': args.runtime or shutil.which('apptainer') or shutil.which('singularity') or previous.get('runtime', 'singularity' if os.environ.get('SINGULARITY_CONTAINER') else 'apptainer'),
              'account': args.account or previous.get('account', 'acc_LOAD'),
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
    if backend == 'local':
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
        raise ValueError('GPU unavailable. Submit fungen serve on a GPU queue; use apptainer run --nv fungen.sif serve on a GPU node.')
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
        if not any(m.get('size_vram',0)>0 for m in api(url,'/api/ps')['models']):
            raise RuntimeError('GPU offload unavailable. Use --nv on a GPU node and inspect the host driver/CUDA compatibility in the serve log.')
        state = {'endpoint':f'http://{socket.getfqdn()}:{port}','node':socket.getfqdn(),'port':port,
                 'model':model,'job_id':os.environ.get('LSB_JOBID',os.environ.get('SLURM_JOB_ID','')),
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
    try:
        info = json.loads((Path(config['install'])/'server.json').read_text())
        if info['model'] == config.get('serve_model',config['model']) and any(m['name']==info['model'] for m in api(info['endpoint'])['models']):
            return info
    except (OSError, ValueError, KeyError, RuntimeError):
        pass
    return {}


def serve(config):
    if config['backend'] == 'openai':
        print('OpenAI backend: run fungen codex. No local model server is needed.')
        return
    if state(config):
        print('Server ready: '+state(config)['endpoint'])
        return
    request=Path(config['install'])/'server-request.json'
    if request.exists() and config['scheduler']=='lsf':
        saved=json.loads(request.read_text())
        r=subprocess.run(['bjobs','-noheader','-o','stat',str(saved['job_id'])],capture_output=True,text=True)
        if r.stdout.strip() in ('RUN','PEND','PSUSP','USUSP','SSUSP'):
            print('Server job '+str(saved['job_id'])+' is '+r.stdout.strip()+'; fungen codex waits for readiness.')
            return
        if not r.stdout.strip() and 'not found' not in r.stderr:
            raise RuntimeError('Server job status unknown. Inspect bjobs before submitting another server.')
    script = Path(config['install'])/f"serve.{config['scheduler']}.sh"
    if config['scheduler'] == 'lsf':
        with script.open() as f:
            r=run(['bsub'],stdin=f,capture_output=True,text=True)
        print(r.stdout,end='')
        match=re.search(r'Job <(\d+)>',r.stdout)
        if not match: raise RuntimeError('Server submission returned no job ID; inspect bjobs before retrying.')
        request.write_text(json.dumps({'job_id':match.group(1)})+'\n')
    elif config['scheduler'] == 'slurm':
        run(['sbatch',script])
    else:
        with (Path(config['install'])/'serve.log').open('a') as f:
            p=subprocess.Popen(['bash',str(script)],stdout=f,stderr=f,start_new_session=True)
        print(f'Started GPU server PID {p.pid}; log: {f.name}')


def codex(config,args):
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
        deadline=time.monotonic()+args.wait
        while not (info:=state(config)):
            if time.monotonic()>=deadline:
                raise RuntimeError('Server unavailable. Run fungen serve; inspect serve job log and fungen check.')
            time.sleep(2)
        env['CODEX_HOME']=str(Path(config['install'])/'codex')
        env['CODEX_OSS_BASE_URL']=info['endpoint']+'/v1'
        env['CODEX_OLLAMA_MODEL']=config.get('serve_model',config['model'])
        provider=['--oss','--local-provider','ollama','--model',config.get('serve_model',config['model'])]
        overrides += ['-c','model_context_window='+str(config.get('context',32768)),
                      '-c','model_auto_compact_token_limit='+str(int(config.get('context',32768)*.75))]
    elif env.get('OPENAI_API_KEY'):
        overrides += ['-c','model_provider="fungen_openai"','-c','model_providers.fungen_openai.name="OpenAI API"',
                      '-c','model_providers.fungen_openai.base_url="https://api.openai.com/v1"',
                      '-c','model_providers.fungen_openai.env_key="OPENAI_API_KEY"',
                      '-c','model_providers.fungen_openai.wire_api="responses"']
    overrides += ['-c','developer_instructions='+json.dumps('Read '+str(Path(config['install'])/'skills/fungen-operator/SKILL.md')+' before workflow operation. Ask before each setup notebook step. Operator and scheduler run on the host.')]
    if args.deployment:
        overrides += ['-c','mcp_servers.fungen.command='+json.dumps(str(Path(config['install'])/'bin/fungen-operator')),
                      '-c','mcp_servers.fungen.args='+json.dumps(['serve','--deployment',str(Path(args.deployment).resolve())])]
    # Root configuration overrides must precede exec in the pinned client.
    command=[config['codex']]+overrides+root_overrides+subcommand+provider+extra
    os.execvpe(command[0],command,env)


def check(config,online=True):
    rows=[]
    def row(name,good,fix):
        rows.append((name,bool(good),fix))
        print(('PASS ' if good else 'FAIL ')+name+('' if good else ': '+fix))
    install=Path(config['install'])
    row('install writable',os.access(install,os.W_OK),'Choose setup --install WRITABLE_FOLDER.')
    row('install on PATH',str(install/'bin') in os.environ.get('PATH','').split(':'),'export PATH='+shlex.quote(str(install/'bin'))+':"$PATH"')
    try:
        imported=subprocess.run([install/'venv/bin/fungen-operator','--help'],capture_output=True,timeout=30).returncode==0
    except (OSError,subprocess.TimeoutExpired):
        imported=False
    row('operator importable',imported,'Rerun apptainer run fungen.sif.')
    row('skill visible',(Path.home()/'.agents/skills/fungen-operator/SKILL.md').is_file(),'Rerun apptainer run fungen.sif.')
    row('Codex recent enough',recent_codex(config['codex']),'Rerun setup to install bundled Codex 0.155.1.')
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
        folder=Path(config['models'])
        present=model_present(folder,config['model'])
        row('model present',present,'Rerun setup --download yes to resume the selected model.')
        row('model folder writable or complete read-only reuse',present or os.access(folder,os.W_OK),'Choose a writable --models-dir for downloading.')
        row('model space and quota',present or (folder.exists() and shutil.disk_usage(folder).free>(MODELS[config['model']]*1.1+2)*1E9),'Free model storage and check your site quota; rerun setup --models-dir FOLDER.')
        info=state(config)
        row('server reachable; port selected',bool(info),'Run fungen serve; the GPU job selects and records a free port.')
        gpu=False
        if info:
            try:
                gpu=any(x.get('size_vram',0)>0 for x in api(info['endpoint'],'/api/ps')['models'])
            except (OSError,KeyError,RuntimeError): pass
        row('GPU visible in image; compatible driver',gpu,'Submit fungen serve to a GPU queue; use --nv and upgrade the host NVIDIA driver if the serve log reports CUDA incompatibility.')
    else:
        result=subprocess.run([config['codex'],'login','status'],capture_output=True)
        row('OpenAI sign-in or API key',bool(os.environ.get('OPENAI_API_KEY')) or result.returncode==0,
            shlex.join([config['codex'],'login','--device-auth'])+' (or export OPENAI_API_KEY in your shell).')
    return all(good for _,good,_ in rows)


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if BUNDLE.is_dir() and argv[:1] in (['codex'],['xqtl']):
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
    for name,choices in [('install',None),('backend',['local','openai']),('scheduler',['lsf','slurm','local']),('model',list(MODELS)),('models-dir',None),('download',['yes','no']),('context',['32768','262144']),('add-path',['yes','no']),('image',None),('runtime',None),('account',None),('gpu-queue',None),('port',None)]:
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
    p.add_argument('--deployment')
    p.add_argument('--wait',type=int,default=1800)
    p.add_argument('args',nargs=argparse.REMAINDER)
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
        if args.command=='check': return 0 if check(config,not args.offline) else 1
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError,EOFError) as exc:
        print('fungen: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
