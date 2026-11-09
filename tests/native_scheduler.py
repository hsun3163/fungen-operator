"""Explicit synthetic native clients for the actual guided host integration test.

Only scheduler allocation, IDs and accounting are simulated. The submitted bash,
Snakemake rules, SoS tasks, scientific tools and grader execute unchanged.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def save(path, record):
    temporary=path.with_suffix('.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps(record))
    temporary.replace(path)


def worker(root, job, script, stdout, stderr, kind, scheduler):
    record=root/(job+'.json')
    # Limit scientific children, independently of the lightweight waiting wrappers.
    slot=None
    if kind=='task':
        while slot is None:
            for index in range(4):
                candidate=(root/('slot'+str(index))).open('a')
                try:fcntl.flock(candidate,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:candidate.close()
                else:slot=candidate;break
            if slot is None:time.sleep(.1)
    env=dict(os.environ)
    env[{'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler]]=job
    save(record,dict(state='RUNNING'))
    for path in (stdout,stderr):Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(stdout,'w') as out,open(stderr,'w') as err:
        result=subprocess.run(['bash',script],env=env,stdout=out,stderr=err)
    save(record,dict(state='COMPLETED' if result.returncode==0 else 'FAILED',exit_code=result.returncode))
    return result.returncode


def main():
    if sys.argv[1:2]==['--worker']:
        raise SystemExit(worker(Path(sys.argv[2]),*sys.argv[3:]))
    name=Path(sys.argv[0]).name
    root=Path(__file__).resolve().parent/'state';root.mkdir(exist_ok=True)
    args=sys.argv[1:]
    with (root/'calls.jsonl').open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        stream.write(json.dumps(dict(client=name,argv=args,controller=os.environ.get('FUNGEN_CONTROLLER_ID'),
                                    journal=os.environ.get('FUNGEN_SUBMISSIONS')))+'\n')
    if name == 'qconf':
        if args != ['-sc']: raise RuntimeError('Expected qconf -sc')
        print((root.parent/'complexes.txt').read_text(), end=''); return
    if name in ('bsub','qsub','sbatch'):
        scheduler={'bsub':'lsf','qsub':'sge','sbatch':'slurm'}[name]
        with (root/'counter').open('a+') as counter:
            fcntl.flock(counter,fcntl.LOCK_EX);counter.seek(0)
            job=str(int(counter.read() or '100')+1)
            counter.seek(0);counter.truncate();counter.write(job);counter.flush()
        if args:
            script=Path(args[-1]);text=script.read_text()
        else:
            script=root/(job+'.sh');text=sys.stdin.read();script.write_text(text)
        kind='wrapper' if '# properties =' in text else 'controller' if script.name=='test-controller.sh' else 'task'
        def output(options,prefixes,extension):
            for option in options:
                if option in args:value=args[args.index(option)+1];break
            else:
                value=next((line[len(prefix):] for line in text.splitlines() for prefix in prefixes if line.startswith(prefix)),str(root/(job+extension)))
            return value.replace('$JOB_ID',job).replace('%j',job).replace('%J',job)
        out=output(['-oo','-o','--output'],['#BSUB -o ','#BSUB -oo ','#$ -o ','#SBATCH --output='],'.out')
        err=output(['-eo','-e','--error'],['#BSUB -e ','#BSUB -eo ','#$ -e ','#SBATCH --error='],'.err')
        save(root/(job+'.json'),dict(state='PENDING'))
        with (root/'submissions.jsonl').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            stream.write(json.dumps(dict(job_id=job,kind=kind,script=str(script),stdout=out,stderr=err))+'\n')
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(root),job,str(script),out,err,kind,scheduler],
                                 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        synchronous='-K' in args or '--wait' in args or '-sync' in args and args[args.index('-sync')+1]=='y'
        code=process.wait() if synchronous else 0
        print('Job <'+job+'> is submitted to queue <premium>.' if scheduler=='lsf' else job,flush=True)
        raise SystemExit(code)
    if name not in ('bjobs','bacct','qstat','qacct','squeue','sacct'):raise RuntimeError('Unexpected native client '+name)
    job=args[-1] if name in ('bjobs','bacct') else args[args.index('-j')+1]
    path=root/(job+'.json')
    if not path.is_file():raise RuntimeError('Unknown synthetic scheduler job '+job)
    record=json.loads(path.read_text());active=record['state'] in ('PENDING','RUNNING')
    if name=='bjobs':
        if '-json' in args:
            rows=[{'JOBID':job,'STAT':'RUN' if record['state']=='RUNNING' else 'PEND','EXIT_CODE':''}] if active else [{'ERROR':'Job <'+job+'> is not found'}]
            print(json.dumps({'RECORDS':rows}));return
        if not active:
            print('Job <'+job+'> is not found',file=sys.stderr);raise SystemExit(255)
        print('RUN' if record['state']=='RUNNING' else 'PEND')
    elif name=='bacct':
        if active:raise RuntimeError('Accounting requested before completion')
        print('Job <'+job+'>, Status <'+('DONE' if record['exit_code']==0 else 'EXIT')+'>, Exit Code <'+str(record['exit_code'])+'>')
    elif name=='qstat':
        if not active:raise SystemExit(1)
        print('job_number: '+job+'\njob_state: '+('r' if record['state']=='RUNNING' else 'qw'))
    elif name=='squeue':
        if active:print(job+'|'+record['state'])
    elif active:raise RuntimeError('Accounting requested before completion')
    elif name=='qacct':print(f'jobnumber {job}\ntaskid undefined\nfailed 0\nexit_status {record["exit_code"]}')
    else:print(f'{job}|{record["state"]}|{record["exit_code"]}:0')


if __name__=='__main__':main()


SGE_SCC_COMPLEXES = """#name shortcut type relop requestable consumable default urgency
h_vmem h_vmem MEMORY <= YES YES 0 0
mem_per_core mpc MEMORY <= YES NO 0 0
gpu gpu INT <= YES YES 0 0
gpu_memory gm MEMORY <= YES NO 0 0
"""


def fake_sge_clients(root, monkeypatch, complexes=SGE_SCC_COMPLEXES):
    """Install logged host clients; no scheduler or container allocation occurs."""
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    client = root/'native_scheduler.py'
    client.write_text('#!'+sys.executable+'\n'+Path(__file__).read_text())
    for name in ('qsub','qstat','qacct','qconf'):
        link = root/name
        if not link.exists(): link.symlink_to(client)
    client.chmod(0o755)
    (root/'complexes.txt').write_text(complexes)
    monkeypatch.setenv('PATH',str(root)+':'+os.environ.get('PATH',''))
    return root
