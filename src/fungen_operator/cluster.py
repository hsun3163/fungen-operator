"""Small Snakemake 7 profile adapter for native LSF and Slurm clients."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['submit','status'])
    p.add_argument('--scheduler',choices=['lsf','slurm'],required=True)
    p.add_argument('--account',default='acc_LOAD')
    p.add_argument('--queue',default='premium')
    p.add_argument('--logs',required=True)
    p.add_argument('value')
    a=p.parse_args(argv)
    if a.operation=='submit':
        text=Path(a.value).read_text()
        props=next(json.loads(line.partition('=')[2]) for line in text.splitlines() if line.startswith('# properties ='))
        n=int(props.get('threads',1));resources=props.get('resources',{})
        mem=int(resources.get('mem_mb',4000));minutes=int(resources.get('runtime',120))
        Path(a.logs).mkdir(parents=True,exist_ok=True)
        name=re.sub('[^a-zA-Z0-9_-]','_',props.get('rule','xqtl'))[:64]
        if a.scheduler=='lsf':
            cmd=['bsub','-P',a.account,'-q',a.queue,'-J',name,'-n',str(n),'-R',f'span[hosts=1] rusage[mem={max(1,(mem+n-1)//n)}]',
                 '-W',f'{minutes//60}:{minutes%60:02}','-oo',str(Path(a.logs)/'%J.out'),'-eo',str(Path(a.logs)/'%J.err'),'bash',a.value]
        else:
            cmd=['sbatch','--parsable','--cpus-per-task',str(n),'--mem',str(mem),'--time',str(minutes),
                 '--output',str(Path(a.logs)/'%j.out'),'--error',str(Path(a.logs)/'%j.err'),a.value]
        r=subprocess.run(cmd,text=True,capture_output=True,check=True)
        job=re.search(r'Job <(\d+)>',r.stdout) if a.scheduler=='lsf' else re.match(r'(\d+)',r.stdout)
        if not job: raise RuntimeError('Submission returned no job ID: '+r.stdout+r.stderr)
        print(job.group(1));return
    if not a.value.isdecimal(): raise ValueError('job ID must be numeric')
    if a.scheduler=='lsf':
        r=subprocess.run(['bjobs','-noheader','-o','stat',a.value],capture_output=True,text=True)
        s=r.stdout.strip()
        if not s and 'not found' in r.stderr:
            r=subprocess.run(['bacct','-l',a.value],capture_output=True,text=True)
            m=re.search(r'Status <(DONE|EXIT)>',r.stdout);s=m.group(1) if m else ''
        if not s: raise RuntimeError('Scheduler status unknown; inspect bjobs/bacct before resuming.')
        print('success' if s=='DONE' else 'failed' if s in ['EXIT','ZOMBI'] else 'running')
    else:
        r=subprocess.run(['sacct','-j',a.value,'--format=State','--noheader','--parsable2'],text=True,capture_output=True,check=True)
        s=r.stdout.splitlines()
        if not s: raise RuntimeError('Scheduler accounting unavailable; inspect sacct before resuming.')
        print('success' if s[0]=='COMPLETED' else 'failed' if s[0].split()[0] in ['FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL'] else 'running')

if __name__=='__main__':
    main()
