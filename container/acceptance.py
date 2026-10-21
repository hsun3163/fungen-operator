"""Stranger acceptance driver; every interactive installer runs through a real PTY.

Run from a reviewed host/LSF allocation. State lives only under --root; model
stores supplied via --staged are bound read-only. This driver never kills jobs.
"""
import argparse
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shlex
import socket
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def drive(command,answers,transcript,env,cwd,timeout=3600,expected_codes=(0,)):
    master,slave=pty.openpty()
    p=subprocess.Popen([str(x) for x in command],stdin=slave,stdout=slave,stderr=slave,env=env,cwd=cwd,start_new_session=True)
    os.close(slave)
    pending=list(answers);data=bytearray();seen=0;deadline=time.monotonic()+timeout
    with Path(transcript).open('wb') as log:
        try:
            while time.monotonic()<deadline:
                if select.select([master],[],[],1)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError as e:
                        if e.errno==errno.EIO:break
                        raise
                    if not chunk:break
                    log.write(chunk);log.flush();data.extend(chunk)
                    sys.stdout.write(chunk.decode(errors='replace'));sys.stdout.flush()
                    while pending and pending[0][0].encode() in data[seen:]:
                        prompt,answer=pending.pop(0)
                        seen=data.index(prompt.encode(),seen)+len(prompt.encode())
                        os.write(master,(answer+'\n').encode())
                elif p.poll() is not None:break
            else:
                raise RuntimeError(f'PTY timeout; process {p.pid} remains for inspection. Transcript: {transcript}')
        finally:os.close(master)
    code=p.wait(timeout=30)
    if code not in expected_codes or pending:raise RuntimeError(f'PTY command failed: exit={code}, unanswered={len(pending)}; see {transcript}')
    return data.decode(errors='replace')


def clean_env(home):
    home=Path(home);home.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),CODEX_HOME=str(home/'.codex'),
             PYTHONDONTWRITEBYTECODE='1',UV_CACHE_DIR=str(home/'.cache/uv'),
             XDG_DATA_HOME=str(home/'.local/share'),XDG_CACHE_HOME=str(home/'.cache'),
             JUPYTER_DATA_DIR=str(home/'.local/share/jupyter'),JUPYTER_CONFIG_DIR=str(home/'.jupyter'),
             JUPYTER_RUNTIME_DIR=str(home/'.local/share/jupyter/runtime'))
    for key in ('OPENAI_API_KEY','OPENAI_ORG_ID','OPENAI_PROJECT_ID','PYTHONPATH','R_LIBS','R_LIBS_USER','FUNGEN_HOST_CODEX'):
        env.pop(key,None)
    # Keep native scheduler/runtime clients; remove host Codex and Python envs.
    paths=[p for p in env['PATH'].split(':') if not (Path(p)/'codex').exists() and '/conda/' not in p]
    env['PATH']=':'.join(paths)
    return env


def setup(root,image,staged,model,scenario='staged',host_codex=None,sched='lsf',backend='local',context=32768):
    home=root/scenario/'home';work=root/scenario/'work';work.mkdir(parents=True,exist_ok=True)
    env=clean_env(home)
    if host_codex:
        import shutil
        binary=home/'.local/bin/codex';binary.parent.mkdir(parents=True,exist_ok=True)
        if not binary.exists(): shutil.copy2(Path(host_codex).resolve(),binary)
        env['FUNGEN_HOST_CODEX']=str(binary)
        env['PATH']=str(binary.parent)+':'+env['PATH']
        user_config=home/'.codex/config.toml';user_config.parent.mkdir(parents=True,exist_ok=True)
        if not user_config.exists():user_config.write_text('# Existing user configuration\nmodel = "gpt-6.1-sol"\n')
    runtime=os.environ.get('FUNGEN_RUNTIME','singularity')
    command=[runtime,'run','--home',f'{home}:{home}']
    if staged:command+=['--bind',f'{staged}:{staged}'+('' if scenario in ('xs','advanced') else ':ro')]
    command += [image,'setup','--runtime',runtime]
    answers=[('Install folder',str(home/'.fungen')),('Scheduler',sched),('Model backend',backend)]
    if backend=='local':
        answers += [('Model tag',model),('Download model?','yes' if scenario=='xs' else 'no'),('Model folder',str(staged)),('Context',str(context))]
    answers += [('Add the install bin','no')]
    drive(command,answers,root/f'{scenario}.pty.log',env,work)
    env['PATH']=str(home/'.fungen/bin')+':'+env['PATH']
    return home,work,env


def operator_smoke(root,scenario,home,work,env,software,operator_python=None):
    import hashlib
    base=root/scenario/'operator'
    source=base/'source';runroot=base/'run';native=runroot/'work'
    source.mkdir(parents=True,exist_ok=True);native.mkdir(parents=True,exist_ok=True)
    snake=source/'Snakefile'
    snake.write_text('rule all:\n    input: "proof.txt"\nrule proof:\n    output: "proof.txt"\n    shell: "printf FUNGEN_LSF_COMPLETED > {output}"\n')
    default=source/'config.yaml';default.write_text('cwd: '+str(native)+'\n')
    profile=source/'profile';profile.mkdir(exist_ok=True)
    (profile/'config.yaml').write_text('cores: 1\njobs: 2000\n')
    if not (source/'.git').exists():
        subprocess.run(['git','init',str(source)],check=True,capture_output=True)
    if subprocess.run(['git','-C',str(source),'rev-parse','--verify','HEAD'],capture_output=True).returncode:
        subprocess.run(['git','-C',str(source),'add','Snakefile','config.yaml','profile/config.yaml'],check=True)
        project=Path(__file__).resolve().parents[1]
        import re
        ident=subprocess.check_output(['git','-C',str(project),'var','GIT_AUTHOR_IDENT'],text=True).strip()
        match=re.match(r'(.+) <([^>]+)>',ident)
        if not match: raise ValueError('Git default author identity is unavailable')
        name,email=match.groups()
        subprocess.run(['git','-C',str(source),'-c','user.name='+name,'-c','user.email='+email,'commit','-qm','Acceptance fixture'],check=True)
    deployment=base/'deployment.json'
    deployment.write_text(json.dumps({'repository':str(source),'snakefile':str(snake),'default_config':str(default),
        'profile_path':str(profile),'conda_sh':str(Path(software).parent/'mamba/etc/profile.d/conda.sh'),
        'conda_env':str(software),'run_root':str(runroot),'backend':'lsf'},indent=2)+'\n')
    cli=home/'.fungen/bin/fungen-operator'
    notebook=runroot/'operator.ipynb';active=runroot/'active.yaml'
    slots={'notebook':str(notebook),'configfile':str(active),'workdir':str(native)}
    def action(name,arguments):
        request=base/(name+'.json');request.write_text(json.dumps(arguments))
        r=subprocess.run([str(cli),'action','--deployment',str(deployment),'--action',name,'--request',str(request)],
                          env=env,cwd=work,capture_output=True,text=True,check=True)
        result=json.loads(r.stdout)
        if result.get('host_command'):
            r=subprocess.run(shlex.split(result['host_command']) if isinstance(result['host_command'],str) else result['host_command'],env=env,cwd=work,capture_output=True,text=True,check=True)
            result=json.loads(r.stdout)
        (base/(name+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
        return result
    action('prepare_config',slots)
    runslots=dict(slots,log_dir=str(runroot/'logs'),targets=['all'],job_name='fungen_smoke',workflow_cores=1,walltime_minutes=30)
    action('check_readiness',runslots)
    prompt=('Acceptance only. Make exactly one connected MCP call to mcp__fungen__initiate_run with these arguments: '+json.dumps({'request':runslots})+'. '
            'Matching readiness and the default configuration already exist. The host approver will execute the returned host_command. '
            'Do not submit or inspect scheduler jobs with shell commands. Return only the MCP result as JSON. '
            'If the named connected MCP tool is unavailable, stop and say MCP_UNAVAILABLE without searching the filesystem.')
    launcher=([operator_python,'-m','fungen_operator.bootstrap'] if operator_python else [home/'.fungen/bin/fungen'])
    drive(launcher+['codex','--deployment',deployment,'--','-c',
           'mcp_servers.fungen.tools.initiate_run.approval_mode="approve"',
           'exec','--skip-git-repo-check','--ephemeral',
           '--sandbox','read-only','--output-last-message',base/'answer.txt',prompt],
           [],root/f'{scenario}-operator.pty.log',env,work,900)
    answer=(base/'answer.txt').read_text().strip()
    if '```' in answer:
        import re
        blocks=re.findall(r'```(?:json)?\s*([\s\S]*?)```',answer)
        if len(blocks)!=1: raise ValueError('Expected one operator result JSON block')
        answer=blocks[0]
    result=json.loads(answer)
    command=result.get('host_command')
    if not isinstance(command,list) or result.get('status')!='host_approval_required':
        raise ValueError('MCP did not return the canonical host approval command')
    allowed=str(home/'.fungen/venv/bin/python')
    expected=[allowed,'-m','fungen_operator','execute','--deployment',str(deployment),
              '--notebook',str(notebook),'--cell',result.get('cell_id')]
    if command!=expected:
        raise ValueError('Unexpected operator host entrypoint')
    executed=subprocess.run(command,env=env,cwd=work,capture_output=True,text=True,check=True)
    receipt=json.loads(executed.stdout)
    (base/'initiate-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    job=receipt['job_id']
    subprocess.run(['bwait','-w','ended('+str(int(job))+')'],env=env,check=True)
    for _ in range(12):
        inspected=subprocess.run([str(cli),'inspect','--deployment',str(deployment),'--notebook',str(notebook)],
                                 env=env,cwd=work,capture_output=True,text=True,check=True)
        record=json.loads(inspected.stdout)
        producer=next(c for c in record['cells'] if c['action']=='initiate_run' and not c['superseded'])
        if producer['scheduler'].get('status') in ('DONE','EXIT'): break
        time.sleep(5)
    (base/'inspection.json').write_text(json.dumps(record,indent=2)+'\n')
    producer=next(c for c in record['cells'] if c['action']=='initiate_run' and not c['superseded'])
    if producer['scheduler'].get('status')!='DONE':raise ValueError('Operator controller did not finish DONE')
    if (native/'proof.txt').read_text()!='FUNGEN_LSF_COMPLETED':raise ValueError('Operator proof product missing')
    r=subprocess.run([str(cli),'verify',str(notebook)],env=env,cwd=work,capture_output=True,text=True,check=True)
    (base/'verify.log').write_text(r.stdout+r.stderr)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario',choices=['pixi','staged','xs','h100-xs','advanced','edges','onboarding','operator','kernel'])
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--image',type=Path)
    p.add_argument('--staged',type=Path)
    p.add_argument('--software',type=Path)
    p.add_argument('--step',choices=['workflow','software','reference','scheduler','fixture','test','handoff'])
    p.add_argument('--busy-port',action='store_true')
    p.add_argument('--h100',action='store_true',help='Constrain this Minerva acceptance allocation to H100 GPUs')
    p.add_argument('--operator-python',type=Path,help='Use a development operator interpreter for onboarding diagnostics')
    p.add_argument('--operator-scenario',choices=['staged','xs','h100-xs'],default='xs')
    p.add_argument('--onboarding-home',type=Path,help='Use the main stranger installation for the native onboarding replay')
    a=p.parse_args();root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    report=root/'scenarios.json'
    results=json.loads(report.read_text()) if report.exists() else {}
    try:
        if a.scenario=='pixi':
            home=root/'pixi/home';work=root/'pixi/work';work.mkdir(parents=True,exist_ok=True)
            env=clean_env(home);env['INSTALL_TYPE']='full'
            repo=root.parent/'pixi-setup'
            drive(['bash',repo/'pixi-setup.sh'],[('Installation path',str(root/'pixi/software'))],root/'pixi.pty.log',env,work,7200)
        elif a.scenario=='advanced':
            home,work,env=setup(root,a.image,a.staged,'laguna-xs-2.1:q4_K_M','advanced',context=262144)
            import tomllib
            c=tomllib.loads((home/'.config/fungen/config.toml').read_text())
            assert c['serve_model']=='laguna-xs-2.1:q4_K_M-256k'
            assert 'PARAMETER num_ctx 262144' in (Path(c['runtime_models'])/'Laguna-256k.Modelfile').read_text()
            assert '--context 262144' in (home/'.fungen/serve.lsf.sh').read_text()
        elif a.scenario in ('staged','xs','h100-xs'):
            model='laguna-s-2.1:q4_K_M' if a.scenario=='staged' else 'laguna-xs-2.1:q4_K_M'
            home,work,env=setup(root,a.image,a.staged,model,a.scenario)
            if a.h100:
                script=home/'.fungen/serve.lsf.sh'
                import re
                text=re.sub(r':gmem=\d+G:',':gmodel=NVIDIAH100PCIe:gmem=70G:',script.read_text())
                script.write_text(text.replace('#BSUB -W 12:00','#BSUB -W 01:00'))
            if a.busy_port:
                script=home/'.fungen/serve.lsf.sh'
                script.write_text(script.read_text().replace('set -euo pipefail\n','set -euo pipefail\n'+shlex.join([sys.executable,'-m','http.server','11434','--bind','0.0.0.0'])+' >/dev/null 2>&1 &\nsleep 2\n'))
            # Exercise host submission (not an in-image scheduler client).
            subprocess.run([home/'.fungen/bin/fungen','serve'],env=env,cwd=work,check=True)
            answer=root/f'{a.scenario}-answer.txt'
            drive([home/'.fungen/bin/fungen','codex','--wait','10800','--','exec','--skip-git-repo-check','--ephemeral',
                   '--output-last-message',answer,'Connectivity test only. Do not call tools or read files. Reply exactly: FUNGEN_AGENT_CONNECTED'],
                  [],root/f'{a.scenario}-codex.pty.log',env,work,14400)
            if 'FUNGEN_AGENT_CONNECTED' not in answer.read_text():raise ValueError('Codex answer missing expected text')
            info=json.loads((home/'.fungen/server.json').read_text())
            if a.busy_port: assert info['port']!=11434
            from fungen_operator.bootstrap import api
            loaded=api(info['endpoint'],'/api/ps')['models']
            assert any(m.get('size_vram',0)>0 for m in loaded),'GPU offload missing'
            (root/f'{a.scenario}-gpu.json').write_text(json.dumps(loaded,indent=2)+'\n')
            checked=subprocess.run([home/'.fungen/bin/fungen','check'],env=env,cwd=work,capture_output=True,text=True)
            (root/f'{a.scenario}-check.log').write_text(checked.stdout+checked.stderr)
            if checked.returncode: raise ValueError('fungen check failed; inspect the retained check log')
        elif a.scenario=='edges':
            # Independent clean-home installations, plus a completed-setup replay.
            host=os.environ['FUNGEN_EXISTING_CODEX']
            eh,ew,ee=setup(root,a.image,a.staged,'laguna-s-2.1:q4_K_M','existing',host)
            import tomllib
            kept=tomllib.loads((eh/'.config/fungen/config.toml').read_text())
            assert kept['codex']==str(eh/'.local/bin/codex'),'Existing host Codex was not kept'
            assert (eh/'.codex/config.toml').read_text()=='# Existing user configuration\nmodel = "gpt-6.1-sol"\n'
            oh,ow,oe=setup(root,a.image,None,None,'openai',host,backend='openai')
            import tomllib
            oc=tomllib.loads((oh/'.config/fungen/config.toml').read_text())
            text=drive(['timeout','-s','INT','30s',oc['codex'],'login','--device-auth'],[],root/'openai-signin.pty.log',oe,ow,120,expected_codes=(0,124,130))
            assert 'device' in text.lower() or 'code' in text.lower()
            assert not (oh/'.codex/auth.json').exists()
            assert not (ow/'auth.json').exists()
            home,work,env=setup(root,a.image,a.staged,'laguna-s-2.1:q4_K_M','staged')
            config=home/'.config/fungen/config.toml';before=config.read_bytes();stamp=config.stat().st_mtime_ns
            setup(root,a.image,a.staged,'laguna-s-2.1:q4_K_M','staged')
            assert config.read_bytes()==before and config.stat().st_mtime_ns==stamp
            for sched in ['slurm','local']:
                # Local rendering is tested independently of GPU setup on a login host.
                from fungen_operator.bootstrap import read_config,render_serve
                import tomllib
                c=tomllib.loads(config.read_text());c['scheduler']=sched
                script=root/f'serve.{sched}.sh';script.write_text(render_serve(c))
                subprocess.run(['bash','-n',script],check=True)
            command=[os.environ.get('FUNGEN_RUNTIME','singularity'),'run','--home',f'{home}:{home}',a.image,'serve']
            r=subprocess.run([str(x) for x in command],env=env,cwd=work,capture_output=True,text=True)
            (root/'no-nv.log').write_text(r.stdout+r.stderr)
            assert r.returncode and '--nv' in r.stdout+r.stderr
            offline=dict(env,HTTPS_PROXY='http://127.0.0.1:1',https_proxy='http://127.0.0.1:1')
            r=subprocess.run([home/'.fungen/bin/fungen','check'],env=offline,cwd=work,capture_output=True,text=True)
            (root/'offline.log').write_text(r.stdout+r.stderr)
            assert r.returncode and 'download on a login node' in r.stdout
        elif a.scenario=='operator':
            home=root/a.operator_scenario/'home';work=root/a.operator_scenario/'work';env=clean_env(home)
            env['PATH']=str(home/'.fungen/bin')+':'+env['PATH']
            operator_smoke(root,a.operator_scenario,home,work,env,a.software,a.operator_python)
        elif a.scenario=='kernel':
            home=a.onboarding_home or root/'staged/home';work=home.parent/'work';env=clean_env(home)
            python=home/'.fungen/venv/bin/python'
            code=('import nbformat\nfrom nbclient import NotebookClient\n'
                  'source='+repr('import sys\nfrom fungen_operator.onboarding import perform\nassert sys.executable == '+repr(str(python))+'\nprint("FUNGEN_KERNEL_READY")')+'\n'
                  'nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(source)])\n'
                  'NotebookClient(nb,kernel_name="fungen-operator",timeout=60).execute()\n'
                  'assert "FUNGEN_KERNEL_READY" in nb.cells[0].outputs[0].text\nprint("FUNGEN_KERNEL_READY")\n')
            drive([python,'-c',code],[],root/'kernel.pty.log',env,work,180)
        elif a.scenario=='onboarding':
            home=a.onboarding_home or root/'staged/home';work=home.parent/'work';work.mkdir(parents=True,exist_ok=True);env=clean_env(home)
            env['PATH']=str(home/'.fungen/bin')+':'+env['PATH']
            prefix=([a.operator_python,'-m','fungen_operator.bootstrap','xqtl'] if a.operator_python else [home/'.fungen/bin/fungen','xqtl'])
            command=prefix+['--root',root/'xqtl','--manager','mamba','--software',a.software,
                     '--scheduler','lsf']
            if a.step: command+=['--step',a.step]
            drive(command,[('Run this step?','yes')]*(1 if a.step else 7),root/'onboarding.pty.log',env,work,14400)
        results[a.scenario]={'passed':True}
    except Exception as exc:
        results[a.scenario]={'passed':False,'error':str(exc)}
        raise
    finally:
        with (root/'scenarios.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            current=json.loads(report.read_text()) if report.exists() else {}
            current[a.scenario]=results[a.scenario]
            report.write_text(json.dumps(current,indent=2)+'\n')

if __name__=='__main__':main()
