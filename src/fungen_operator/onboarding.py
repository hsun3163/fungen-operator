"""Guided xQTL setup: fixed, confirmed, re-runnable notebook steps."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import urllib.request
import nbformat
import yaml
from .bootstrap import ask, read_config, run, scheduler

COMMIT='e1095f6354da6a4d2c43ef812eeb099a19fe93d2'
STEPS=('workflow','software','reference','scheduler','fixture','test','handoff')
RESOURCES=Path(__file__).with_name('resources')
DESCRIPTIONS={
 'workflow':'Clone StatFunGen/xqtl-protocol at '+COMMIT+' (about 500 MB source budget).',
 'software':'Install tools (35 GB disk budget); mamba is required for acceptance. The Pixi Minerva test fails in upstream safe_expose_remove: invalid jq expression .[].exposed.[].exposed_name. It remains offered with that limitation.',
 'reference':'Record the prepared-input reference contract: GRCh38 coordinates, synthetic trait annotation (<100 KB), synthetic LD (0 external bytes). Optional Ensembl 103 FASTA 840 MB and GTF 47 MB are not needed for this PLINK/normalized-BED chain.',
 'scheduler':'Generate native LSF, Slurm, SGE and local Snakemake profiles; clusters use jobs: 2000.',
 'fixture':'Generate 500 de novo synthetic samples, 512 variants, six RNA contexts and 24 planted cis-eQTLs with seed 20261020. Freeze recovery before fitting.',
 'test':'Run genotype QC, sample matching, PCA, phenotype preparation, hidden factors, TensorQTL and SuSiE/TWAS through the upstream Snakemake DAG; grade actual products and planted truth.',
 'handoff':'Write the operator deployment and retain the installed versions, configuration, notebook and acceptance record.'}


def acquire_mamba(storage):
    """Install the pinned native Miniforge distribution without a system Python."""
    storage=Path(storage);prefix=storage/'mamba';binary=prefix/'bin/mamba'
    if binary.is_file(): return str(binary)
    storage.mkdir(parents=True,exist_ok=True)
    installer=storage/'Miniforge3-26.7.2-0-Linux-x86_64.sh'
    checksum='281b0ac7d550802efc81af633225a5e6116d29ae72f3ab4eae7168c3931a4c05'
    if not installer.exists():
        url='https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/Miniforge3-Linux-x86_64.sh'
        with urllib.request.urlopen(url,timeout=120) as response, installer.open('wb') as stream:
            shutil.copyfileobj(response,stream)
    if hashlib.sha256(installer.read_bytes()).hexdigest()!=checksum:
        raise ValueError('Miniforge installer hash differs; acquire the pinned installer again before software setup.')
    run(['bash',installer,'-b','-p',prefix])
    return str(binary)


def sos_patch_directory(c):
    code = 'import sysconfig; print(sysconfig.get_path("purelib"))'
    return Path(run([Path(c['software'])/'bin/python', '-c', code],
                    env=env_for(c), capture_output=True, text=True).stdout.strip())


def patch_sos(c):
    """Keep the published running-task heartbeat present during monitor startup."""
    directory = sos_patch_directory(c)
    patch = RESOURCES/'sos-pulse.patch'
    reverse = ['git', '-C', str(directory), 'apply', '--reverse', '--check', str(patch)]
    if subprocess.run(reverse, capture_output=True).returncode == 0:
        return
    run(['git', '-C', directory, 'apply', '--check', patch])
    run(['git', '-C', directory, 'apply', patch])


def settings(root):
    return json.loads((Path(root)/'setup.json').read_text())


def env_for(c):
    env=dict(os.environ)
    for k in ('PYTHONPATH','R_LIBS','R_LIBS_USER','R_LIBS_SITE','R_HOME','PIXI_HOME'):
        env.pop(k,None)
    prefix=Path(c['software'])
    env['PATH']=str(prefix/'bin')+':'+env.get('PATH','')
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        env[k]='1'
    env['CONDA_PREFIX']=str(prefix)
    return env


def guided_run(root):
    """Runtime boundary registered by the emitted deployment."""
    return Path(root)/'user-runs/guided-test'


def write_deployment(root,c):
    from .actions import Deployment
    root=Path(root)
    if c['mamba']=='managed':
        c['mamba']=acquire_mamba(Path(c['software']).parent)
        (root/'setup.json').write_text(json.dumps(c,indent=2)+'\n')
    conda_sh=Path(c['mamba']).resolve().parents[1]/'etc/profile.d/conda.sh'
    sources=[root/'workflow/code/snakemake/rules',root/'workflow/code/script',root/'workflow.applied.patch',
             root/'setup.json',root/'profiles/jobscript.sh']
    if c['scheduler']!='local':sources += [root/'sos.yaml',root/'profiles/test-controller.sh']
    d=Deployment(repository=str(root/'workflow'),snakefile=str(root/'workflow/code/snakemake/Snakefile'),
                 default_config=str(root/'config.yaml'),profile_path=str(root/'profiles'/c['scheduler']),
                 conda_sh=str(conda_sh),conda_env=c['software'],run_root=str(root/'user-runs'),backend=c['scheduler'],
                 scheduler_account=c['account'],scheduler_queue=c['queue'],
                 action_provider=str(Path(__file__).with_name('onboarding_actions.py'))+':provider',
                 canonical_source_paths=[str(path) for path in sources])
    (root/'deployment.json').write_text(d.model_dump_json(indent=2)+'\n')
    return d


def profiles(root,c):
    root=Path(root)
    work=guided_run(root)/'work'
    home=work/'sos_runtime/home';home.mkdir(parents=True,exist_ok=True)
    template=root/'profiles/jobscript.sh';template.parent.mkdir(parents=True,exist_ok=True)
    template.write_text('#!/bin/bash\n# properties = {properties}\nexport HOME='+shlex.quote(str(home))+'\nexport XDG_CONFIG_HOME="$HOME/.config"\nexport PYTHONDONTWRITEBYTECODE=1\n{exec_job}\n')
    for sched in ('lsf','slurm','sge','local'):
        p=root/'profiles'/sched;p.mkdir(parents=True,exist_ok=True)
        cfg={'jobs':2000 if sched!='local' else 4,'latency-wait':120,'rerun-incomplete':True,'printshellcmds':True}
        if sched!='local':
            cfg['jobscript']=str(template)
            base=[sys.executable,str(Path(__file__).with_name('cluster.py'))]
            common=['--scheduler',sched,'--account',c['account'],'--queue',c['queue'],'--logs',str(work/'logs/rules')]
            cfg['cluster']=shlex.join(base+['submit']+common)
            cfg['cluster-status']=shlex.join(base+['status']+common)
            cfg['max-status-checks-per-second']=1
        (p/'config.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
        assert yaml.safe_load((p/'config.yaml').read_text())['jobs']==cfg['jobs']

    # Every cluster gets a native task host, so task resources are allocated
    # independently of the lightweight rule controller.
    if c['scheduler']=='local':return
    from .cluster import controller_tracking
    (root/'profiles/test-controller.sh').write_text('#!/bin/bash\nset -eo pipefail\n'+
        controller_tracking(c['scheduler'],root/'profiles'/c['scheduler'])+
        'cd '+shlex.quote(str(work))+'\n'+shlex.join(scientific_command(root,c))+'\n')
    task='\n'.join([
        '#!/bin/bash', '#BSUB -J {task}', '#BSUB -P '+c['account'], '#BSUB -q '+c['queue'],
        '#BSUB -n {cores}', '#BSUB -W {walltime.rsplit(":",1)[0]}',
        '#BSUB -R "span[hosts=1] rusage[mem={max(1,int(mem)//(1024*1024*int(cores)))}]"',
        '#BSUB -o {workdir}/.sos/{task}.out', '#BSUB -e {workdir}/.sos/{task}.err',
        'set -euo pipefail', 'export HOME='+shlex.quote(str(home)), 'export XDG_CONFIG_HOME="$HOME/.config"', 'export PATH='+shlex.quote(str(Path(c['software'])/'bin'))+':"$PATH"',
        'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1',
        'cd {__import__("shlex").quote(workdir)}', '{command}', ''])
    host={'address':'localhost','queue_type':'pbs','max_running_jobs':2000,
          'max_cores':72,'max_mem':'1T','max_walltime':'144h',
          'task_template':task,'submit_cmd_output':'{job_id}',
          'status_cmd':'bjobs -noheader -o stat {job_id}','kill_cmd':'bkill {job_id}',
          'sos':str(Path(c['software'])/'bin/sos')}
    sched=c['scheduler']
    if sched in ('slurm','sge'):
        body=task[task.index('set -euo pipefail'):]
        if sched=='sge':
            directives=['#!/bin/bash','#$ -N {task}','#$ -S /bin/bash']+(['#$ -P '+c['account']] if c['account'] else [])+(['#$ -q '+c['queue']] if c['queue'] else [])+[
                '#$ -pe smp {cores}', '#$ -l h_rt={walltime},h_vmem={max(1,(int(mem)+1024*1024*int(cores)-1)//(1024*1024*int(cores)))}M',
                '#$ -o {workdir}/.sos/{task}.out','#$ -e {workdir}/.sos/{task}.err']
            host.update(status_cmd='qstat -j {job_id}',kill_cmd='qdel {job_id}')
        else:
            directives=['#!/bin/bash','#SBATCH --job-name={task}','#SBATCH --cpus-per-task={cores}',
                '#SBATCH --mem={max(1,(int(mem)+1024*1024-1)//(1024*1024))}M','#SBATCH --time={walltime}',
                '#SBATCH --output={workdir}/.sos/{task}.out','#SBATCH --error={workdir}/.sos/{task}.err']+(
                ['#SBATCH --account='+c['account']] if c['account'] else [])+(['#SBATCH --partition='+c['queue']] if c['queue'] else [])
            host.update(status_cmd='squeue -h -j {job_id}',kill_cmd='scancel {job_id}')
        host['task_template']='\n'.join(directives)+'\n'+body
    from .cluster import task_submit_command
    host['submit_cmd']=task_submit_command(sched,work/'logs/rules')
    (root/'sos.yaml').write_text(yaml.safe_dump({'hosts':{'localhost':{'address':'localhost'},task_queue(c):host}},sort_keys=False))


def task_queue(c):
    return c['queue'] if c['scheduler']=='lsf' else 'fungen_'+c['scheduler']


def make_config(root,c):
    root=Path(root);source=root/'workflow';fixture=root/'inputs';work=guided_run(root)/'work'
    cfg=yaml.safe_load((source/'code/snakemake/config.yaml').read_text())
    cfg.update(cwd=str(work),pipeline_dir=str(source/'pipeline'),modular_script_dir=str(source/'code/script'),
               start_from='phenotype_bed',dry_run=False,chromosomes=['chr1','chr2'],minerva=str(root/'sos.yaml') if c['scheduler']!='local' else '',
               sos_bin=str(Path(c['software'])/'bin/sos'),runtime_home=str(work/'sos_runtime/home'),runtime_root=str(work/'runtime'),
               themes=[{'name':f'RNA{i}','phenotype_bed':str(fixture/f'RNA{i}.bed.gz'),
                        'covariate_file':str(fixture/'fixed.cov.gz'),'sample_participant_lookup':'','phenotype_group':''} for i in range(1,7)],
               genotype={'plink_bed':str(fixture/'synthetic.bed'),'vcf_files':[]},
               reference={k:'' for k in cfg['reference']}, containers={k:'' for k in cfg['containers']})
    cfg['pca']['n_pcs']=20
    cfg['covariate']['n_pcs']=13
    cfg['association']['cis_window']=1000000
    cfg['sos']={'defaults':{'queue':task_queue(c) if c['scheduler']!='local' else 'local','J':2000 if c['scheduler']!='local' else 1},'local_rules':[]}
    for v in cfg['resources'].values():
        v.update(threads=1,mem_mb=8000,runtime=240)
    cfg['resources']['finemapping']['mem_mb']=16000
    (root/'config.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))


def scientific_command(root,c,dry=False):
    root=Path(root)
    cmd=[str(Path(c['software'])/'bin/snakemake'),'--snakefile',str(root/'workflow/code/snakemake/Snakefile'),
         '--configfile',str(guided_run(root)/'config.yaml'),'--profile',str(root/'profiles'/c['scheduler']),
         '--cores','72' if c['scheduler']!='local' else '4','--jobs','2000' if c['scheduler']!='local' else '4']
    if dry: cmd+=['--dry-run']
    return cmd+['xqtl_core']


def guided_test_command(root,c,log_stem):
    """Submit the guide's native controller and wait for its actual exit status."""
    sched=c['scheduler']
    if sched=='local':return scientific_command(root,c)
    root=Path(root);script=root/'profiles/test-controller.sh'
    account=c['account'];queue=c['queue']
    if sched=='lsf':
        return ['bsub','-K']+(['-P',account] if account else [])+(['-q',queue] if queue else [])+[
            '-J','fungen-guided-test','-n','1','-R','span[hosts=1] rusage[mem=8192]',
            '-W','04:00','-oo',log_stem+'.%J.out','-eo',log_stem+'.%J.err','bash',str(script)]
    if sched=='sge':
        return ['qsub','-terse','-sync','y','-V','-S','/bin/bash','-N','fungen-guided-test']+(
            ['-P',account] if account else [])+(['-q',queue] if queue else [])+[
            '-l','h_vmem=8192M,h_rt=04:00:00','-o',log_stem+'.$JOB_ID.out',
            '-e',log_stem+'.$JOB_ID.err',str(script)]
    if sched=='slurm':
        return ['sbatch','--parsable','--wait']+(['--account',account] if account else [])+(
            ['--partition',queue] if queue else [])+['--job-name','fungen-guided-test',
            '--cpus-per-task','1','--mem','8192','--time','240',
            '--output',log_stem+'.%j.out','--error',log_stem+'.%j.err',str(script)]
    raise ValueError('Unsupported guided scheduler: '+sched)


def perform(root,step):
    root=Path(root).resolve();c=settings(root)
    if step not in STEPS: raise ValueError('Unknown setup step')
    # A completed predecessor is checked again, rather than trusted by a marker.
    for previous in STEPS[:STEPS.index(step)]:
        try:check_step(root,previous,c)
        except (OSError,ValueError,subprocess.CalledProcessError) as exc:
            raise ValueError(f'{previous} check failed: {exc}. Step {step} needs {previous} first. Run: fungen xqtl --root {root} --step {previous}, or fungen xqtl --root {root} to run every step in order.') from exc
    print(DESCRIPTIONS[step],flush=True)
    if ask('Run this step? (yes/no)','no',['yes','no'])!='yes':
        raise RuntimeError('Step remains prepared; rerun it when ready.')
    log=(guided_run(root)/'work/logs' if step=='test' else root/'logs')/f'{step}.log';log.parent.mkdir(parents=True,exist_ok=True)
    try:
        with log.open('a') as stream:
            def command(cmd,**kw):
                print(shlex.join([str(x) for x in cmd]),flush=True)
                return run(cmd,stdout=stream,stderr=subprocess.STDOUT,**kw)
            if step=='workflow':
                path=root/'workflow'
                if not path.exists():
                    command(['git','clone','--filter=blob:none','https://github.com/StatFunGen/xqtl-protocol.git',path])
                    command(['git','-C',path,'checkout','--detach',COMMIT])
                patch=RESOURCES/'xqtl-upstream.patch'
                applied=subprocess.run(['git','-C',str(path),'apply','--reverse','--check',str(patch)],capture_output=True).returncode==0
                if not applied:
                    previous=root/'workflow.applied.patch'
                    if previous.exists():
                        command(['git','-C',path,'apply','--reverse','--check',previous])
                        command(['git','-C',path,'apply','--reverse',previous])
                    command(['git','-C',path,'apply','--check',patch])
                    command(['git','-C',path,'apply',patch])
                (root/'workflow.applied.patch').write_bytes(patch.read_bytes())
            elif step=='software':
                if c['manager']=='mamba':
                    if c['mamba']=='managed':
                        c['mamba']=acquire_mamba(Path(c['software']).parent)
                        (root/'setup.json').write_text(json.dumps(c,indent=2)+'\n')
                    spec=RESOURCES/'xqtl-mamba.yaml'
                    lock=RESOURCES/'xqtl-linux-64.lock'
                    stamp=root/'software-spec.sha256'
                    identity=hashlib.sha256(spec.read_bytes()+b'\0'+lock.read_bytes()+b'\0'+(RESOURCES/'sos-pulse.patch').read_bytes()).hexdigest()
                    if not stamp.exists() or stamp.read_text()!=identity:
                        operation='install' if (Path(c['software'])/'conda-meta/history').exists() else 'create'
                        command([c['mamba'],operation,'-y','-p',c['software'],'--file',lock],env=dict(os.environ,CONDA_PKGS_DIRS=str(Path(c['software']).parent/'package-cache'),MAMBA_DOWNLOAD_THREADS='2',MAMBA_EXTRACT_THREADS='2'))
                    patch_sos(c)
                    (root/'software.applied.patch').write_bytes((RESOURCES/'sos-pulse.patch').read_bytes())
                    stamp.write_text(identity)
                    command([c['mamba'],'list','-p',c['software'],'--explicit'])
                else:
                    path=root/'pixi-setup'
                    if not path.exists():command(['git','clone','https://github.com/StatFunGen/pixi-setup.git',path])
                    command(['bash',path/'pixi-setup.sh'],env=dict(os.environ,PIXI_HOME=c['software'],INSTALL_TYPE='full'))
            elif step=='reference':
                (root/'reference.json').write_text(json.dumps({'coordinate_system':'GRCh38','prepared_input_only':True,
                    'required_external_download_bytes':0,'annotation':'synthetic trait coordinates in input BEDs',
                    'LD':'computed from the new synthetic genotypes','optional_genome':'Ensembl 103 primary assembly, about 840 MB compressed',
                    'optional_gtf':'Homo_sapiens.GRCh38.103.gtf.gz, about 47 MB compressed'},indent=2)+'\n')
            elif step=='scheduler':profiles(root,c)
            elif step=='fixture':
                from .synthetic import generate
                # The scientific environment supplies NumPy, bgzip and tabix.
                command([str(Path(c['software'])/'bin/python'),'-c',
                         'from fungen_operator.synthetic import generate; generate('+repr(str(root/'inputs'))+')'],
                         env=dict(env_for(c),PYTHONPATH=str(Path(__file__).parents[1])))
                make_config(root,c)
            elif step=='test':
                from .actions import PrepareConfig
                from .execution import Executor
                from .harness import Harness
                runtime=guided_run(root);work=runtime/'work'
                d=write_deployment(root,c)
                harness=Harness(d,Executor(d,host_approved=True),str(root/'deployment.json'))
                args=dict(notebook=str(runtime/'operator.ipynb'),configfile=str(runtime/'config.yaml'),workdir=str(work))
                harness.prepare_config(harness.propose_config(PrepareConfig(**args)))
                request=harness.registry.models['guided_test'](**args,log_dir=str(work/'logs'))
                result=harness.run('guided_test',request)
                print(json.dumps(result,sort_keys=True),file=stream,flush=True)
                if result['status']!='completed':raise RuntimeError('Guided native test did not complete: '+json.dumps(result))
                command([str(Path(c['software'])/'bin/python'),'-c',
                         'from fungen_operator.synthetic import grade; print(grade('+repr(str(root/'inputs'))+','+repr(str(work))+'))'],
                         env=dict(env_for(c),PYTHONPATH=str(Path(__file__).parents[1])))
            elif step=='handoff':write_deployment(root,c)
        check_step(root,step,c)
    except Exception as exc:
        raise RuntimeError(f'{step} failed: {exc}. Inspect {log}; fix this step and rerun fungen xqtl --root {root} --step {step}.') from exc
    print(f'PASS {step}; native log: {log}',flush=True)
    return log


def check_step(root,step,c):
    root=Path(root)
    if step=='workflow':
        if not (root/'workflow/code/snakemake/Snakefile').is_file():raise ValueError('Missing upstream Snakefile')
        actual=subprocess.check_output(['git','-C',str(root/'workflow'),'rev-parse','HEAD'],text=True).strip()
        if subprocess.run(['git','-C',str(root/'workflow'),'apply','--reverse','--check',str(RESOURCES/'xqtl-upstream.patch')],capture_output=True).returncode:
            raise ValueError('Required upstream interface patch is missing or changed; rerun workflow setup.')
        if actual!=COMMIT:raise ValueError('Workflow pin differs; use a clean checkout at '+COMMIT)
    elif step=='software':
        prefix=Path(c['software'])
        for name in ('python','Rscript','snakemake','sos','plink','plink2','bcftools','bgzip','tabix'):
            if not (prefix/'bin'/name).is_file():raise ValueError('Missing software: '+name)
        try:
            run([prefix/'bin/python','-c','import tensorqtl'],env=env_for(c),capture_output=True)
            directory=sos_patch_directory(c)
            run(['git','-C',directory,'apply','--reverse','--check',RESOURCES/'sos-pulse.patch'],capture_output=True)
            packages=['pecotmr','flashpcaR','PCAtools','RMTstat','BiocSingular','tidyverse','igraph','plinkQC','vroom','Rsamtools','GenomicRanges','optparse','argparser','gridExtra']
            code='stopifnot(all(vapply('+ 'c('+','.join(json.dumps(x) for x in packages)+')'+',requireNamespace,logical(1),quietly=TRUE)))'
            run([prefix/'bin/Rscript','-e',code],env=env_for(c),capture_output=True)
        except subprocess.CalledProcessError as exc:
            raise ValueError('Runtime import failed: '+exc.stderr.decode(errors='replace')+'; repair the pinned software environment and rerun software setup.') from exc
    elif step=='reference':json.loads((root/'reference.json').read_text())
    elif step=='scheduler':
        for sched in ('lsf','slurm','sge','local'):
            doc=yaml.safe_load((root/'profiles'/sched/'config.yaml').read_text())
            if doc['jobs']!=(4 if sched=='local' else 2000):raise ValueError('Profile job cap differs for '+sched+'; rerun scheduler setup.')
        if c['scheduler']=='local':return
        code='import json,sys,subprocess; from sos.eval import cfg_interpolate; d=json.load(sys.stdin); s=cfg_interpolate(d["template"],d["values"]); subprocess.run(["bash","-n"],input=s,text=True,check=True)'
        host=yaml.safe_load((root/'sos.yaml').read_text())['hosts'][task_queue(c)]
        values={'task':'tfixture','cores':1,'mem':2147483648,'walltime':'01:00:00','workdir':str(guided_run(root)/'work'),'command':'true'}
        run([Path(c['software'])/'bin/python','-c',code],input=json.dumps({'template':host['task_template'],'values':values}),text=True,env=env_for(c),capture_output=True)
    elif step=='fixture':
        meta=json.loads((root/'inputs/fixture.json').read_text())
        if meta['samples']!=500:raise ValueError('Fixture sample count differs from 500; rerun fixture setup.')
        if (root/'inputs/synthetic.bed').stat().st_size!=64003:raise ValueError('Synthetic PLINK BED size differs; rerun fixture setup.')
        if not (root/'config.yaml').is_file():raise ValueError('Missing fixture config.yaml; rerun fixture setup.')
    elif step=='test':
        result=json.loads((guided_run(root)/'acceptance.json').read_text())
        if not result['passed']:raise ValueError('Frozen planted-signal recovery failed')
    elif step=='handoff':
        from .actions import Deployment
        Deployment.load(root/'deployment.json').validate_layout()


def notebook(root):
    root=Path(root);path=root/'setup.ipynb'
    kernel={'name':'fungen-operator','display_name':'Fungen Operator','language':'python'}
    if path.exists():
        nb=nbformat.read(path,as_version=4)
        recorded=[c.metadata['fungen_setup']['step'] for c in nb.cells if c.metadata.get('fungen_setup',{}).get('step')]
        if recorded!=list(STEPS):raise ValueError('Existing setup.ipynb is not this guided sequence; choose another --root.')
        if nb.metadata.get('kernelspec',{}).get('name')=='python3':
            nb.metadata['kernelspec']=kernel
            nbformat.write(nb,path)
        return path
    cells=[nbformat.v4.new_markdown_cell('# Set up xQTL through fine-mapping\nEach step asks first, checks its predecessors, and stops on failure. Run in order. Scheduler operations require the host approval path.\nThe scientific fixture and recovery criterion are frozen in fixture.json before fitting.')]
    for step in STEPS:
        cells.append(nbformat.v4.new_markdown_cell('**'+step+'** — '+DESCRIPTIONS[step]))
        cells.append(nbformat.v4.new_code_cell('from fungen_operator.onboarding import perform\nperform('+repr(str(root))+', '+repr(step)+')',metadata={'fungen_setup':{'step':step,'version':1}}))
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':kernel})
    nbformat.write(nb,path);return path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--step',choices=STEPS)
    p.add_argument('--manager',choices=['mamba','pixi'])
    p.add_argument('--software',type=Path)
    p.add_argument('--scheduler',choices=['lsf','slurm','sge','local'])
    p.add_argument('--mamba',help='Mamba executable, or managed for pinned Miniforge 26.7.2-0')
    p.add_argument('--account',help='Scheduler account/project; inherit only from the same scheduler');p.add_argument('--queue')
    a=p.parse_args(argv);root=a.root.expanduser().resolve()
    if not (root/'setup.json').exists() and root.exists() and any(root.iterdir()):
        raise ValueError(f'xQTL root must be a new or empty folder: {root}. Choose a dedicated folder, e.g. fungen xqtl --root ~/xqtl-setup.')
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'setup.json').exists():
        manager=a.manager or ask('Package manager (mamba recommended; pixi on Minerva fails in upstream safe_expose_remove with invalid jq .[].exposed.[].exposed_name)','mamba',['mamba','pixi'])
        print('Software budget: 35 GB. Choose scratch/project storage on a cluster.')
        software=(a.software or Path(ask('Software folder',str(root/'software')))).expanduser().resolve()
        if software==root:raise ValueError(f'Software folder must differ from the xQTL root; use the default {root/"software"}.')
        launcher=read_config()
        a.scheduler=a.scheduler or scheduler()
        account=a.account if a.account is not None else (launcher.get('account','') if launcher.get('scheduler')==a.scheduler else 'acc_LOAD' if a.scheduler=='lsf' else '')
        (root/'setup.json').write_text(json.dumps({'manager':manager,'software':str(software.resolve()),'scheduler':a.scheduler,
                      'mamba':a.mamba or 'managed','account':account,'queue':a.queue if a.queue is not None else 'premium' if a.scheduler=='lsf' else ''},indent=2)+'\n')
    else:
        c=settings(root)
        for key in ('scheduler','account','queue','software','manager'):
            value=getattr(a,key)
            if value is not None and str(value)!=str(c[key]):
                raise ValueError('Existing setup '+key+' differs. Use a new --root for changed settings; existing profiles and configuration remain tied to setup.json.')
        if a.mamba is not None:
            c['mamba']=a.mamba
            (root/'setup.json').write_text(json.dumps(c,indent=2)+'\n')
    path=notebook(root)
    print('Setup notebook: '+str(path),flush=True)
    steps=[a.step] if a.step else STEPS
    for step in steps:
        nb=nbformat.read(path,as_version=4)
        cell=next(cell for cell in nb.cells if cell.metadata.get('fungen_setup',{}).get('step')==step)
        try:
            log=perform(root,step)
            cell.outputs=[nbformat.v4.new_output('stream',name='stdout',text=f'PASS {step}; log: {log.relative_to(root)}\n')]
            cell.execution_count=STEPS.index(step)+1
        except Exception as exc:
            cell.outputs=[nbformat.v4.new_output('stream',name='stderr',text=str(exc)+'\n')]
            nbformat.write(nb,path)
            raise
        nbformat.write(nb,path)

if __name__=='__main__':
    main()
