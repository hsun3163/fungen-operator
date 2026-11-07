"""Small Snakemake 7 profile adapter for native LSF, Slurm and SGE clients."""
import argparse
import fcntl
import os
import shlex
import uuid
import yaml
import json
from pathlib import Path
import re
import subprocess
import sys


def profile_logs(profile,scheduler):
    doc=yaml.safe_load((Path(profile)/'config.yaml').read_text())
    cmd=shlex.split(doc['cluster'])
    if len(cmd)<3 or Path(cmd[0]).resolve()!=Path(sys.executable).resolve() or Path(cmd[1]).resolve()!=Path(__file__).resolve() or cmd[2]!='submit':
        raise ValueError('Native profile must use the canonical tracked cluster adapter; regenerate scheduler setup')
    for key in ('--scheduler','--logs'):
        if key not in cmd or cmd.index(key)+1>=len(cmd):raise ValueError('Native profile must declare '+key)
    if cmd[cmd.index('--scheduler')+1]!=scheduler:raise ValueError('Native profile scheduler differs from deployment')
    logs=Path(cmd[cmd.index('--logs')+1])
    if not logs.is_absolute():raise ValueError('Native log directory must be absolute')
    return logs


def task_submit_command(scheduler,logs):
    return 'mkdir -p {workdir}/.sos; '+shlex.join([sys.executable,str(Path(__file__).resolve()),'submit-task','--scheduler',scheduler,'--logs',str(logs)])+' {job_file}'


def journal_event(path,**event):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        stream.write(json.dumps(dict(version=1,**event),sort_keys=True)+'\n');stream.flush();os.fsync(stream.fileno())


def journal_records(path,controllers):
    with Path(path).open() as stream:
        fcntl.flock(stream,fcntl.LOCK_SH)
        records=[json.loads(line) for line in stream]
    if any(not isinstance(x,dict) or x.get('version')!=1 for x in records):raise ValueError('Invalid submission journal schema')
    return [x for x in records if x.get('controller') in controllers]


def native_id(scheduler):
    value=os.environ[{'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler]]
    if not value.isdecimal() or int(value)<=0:raise ValueError('Native job identity must be positive numeric')
    return value


def tracking_context(scheduler,logs):
    controller=os.environ['FUNGEN_CONTROLLER_ID'];path=Path(os.environ['FUNGEN_SUBMISSIONS'])
    if not controller.isdecimal() or int(controller)<=0 or path!=Path(logs)/'submissions.jsonl':
        raise ValueError('Submission journal/controller differs from the selected profile')
    return controller,path


def controller_tracking(scheduler,profile):
    """The native controller owns tracking for every descendant submission."""
    own={'lsf':'LSB_JOBID','sge':'JOB_ID','slurm':'SLURM_JOB_ID'}[scheduler]
    tracker=shlex.join([sys.executable,str(Path(__file__).resolve())])
    start=tracker+' controller-start --scheduler '+scheduler+' --profile '+shlex.quote(str(profile))
    end=tracker+' controller-end --scheduler '+scheduler+' --logs "$FUNGEN_RULE_LOGS"'
    return ('export FUNGEN_CONTROLLER_ID="${'+own+':?}"\n'+
            'FUNGEN_SUBMISSIONS="$('+start+')"\nexport FUNGEN_SUBMISSIONS\n'+
            'FUNGEN_RULE_LOGS="${FUNGEN_SUBMISSIONS%/*}"\nexport FUNGEN_RULE_LOGS\n'+
            'trap '+shlex.quote('rc=$?; '+end+' "$rc"; exit "$rc"')+' EXIT\n')


def tracked_rule(text,scheduler,logs,controller,journal):
    prefix=('set -eo pipefail\nexport FUNGEN_CONTROLLER_ID='+shlex.quote(controller)+'\nexport FUNGEN_SUBMISSIONS='+shlex.quote(str(journal))+'\nexport FUNGEN_SUBMISSION_TRACKED=1\n')
    base=[sys.executable,str(Path(__file__).resolve())]
    start=shlex.join(base+['wrapper-start','--scheduler',scheduler,'--logs',str(logs)])
    end=shlex.join(base+['wrapper-end','--scheduler',scheduler,'--logs',str(logs)])
    injection=prefix+start+'\ntrap '+shlex.quote('rc=$?; '+end+' "$rc"; exit "$rc"')+' EXIT\n'
    if 'FUNGEN_SUBMISSION_TRACKED=1' in text:
        if injection not in text:raise ValueError('Existing rule tracking differs from controller/profile')
        return text
    lines=text.splitlines(keepends=True)
    position=1 if lines and lines[0].startswith('#!') else 0
    # Keep completion ownership in this shell even when the native job body
    # uses exec or installs its own EXIT trap. Its native exit status is retained.
    return ''.join(lines[:position])+injection+'(\n'+''.join(lines[position:])+'\n)\n'


def submission_id(scheduler,stdout):
    pattern=(r'Job <([1-9]\d*)> is submitted to (?:default )?queue <[^>\n]+>\.\s*' if scheduler=='lsf' else
             r'([1-9]\d*)(?:;[^\s]+)?\s*' if scheduler=='slurm' else r'([1-9]\d*)\s*')
    match=re.fullmatch(pattern,stdout)
    if not match:
        raise RuntimeError(scheduler.upper()+' array or ambiguous receipt unsupported: '+stdout+'; inspect native scheduler before retrying.')
    return match.group(1)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['submit','submit-task','status','controller-start','controller-end','wrapper-start','wrapper-end'])
    p.add_argument('--scheduler',choices=['lsf','slurm','sge'],required=True)
    p.add_argument('--account')
    p.add_argument('--queue')
    p.add_argument('--logs')
    p.add_argument('--profile')
    p.add_argument('value',nargs='?')
    a=p.parse_intermixed_args(argv)
    if a.account is None:a.account='acc_LOAD' if a.scheduler=='lsf' else ''
    if a.queue is None:a.queue='premium' if a.scheduler=='lsf' else ''
    if a.operation in ('controller-start','controller-end','wrapper-start','wrapper-end'):
        job=native_id(a.scheduler)
        if a.operation=='controller-start':
            logs=profile_logs(a.profile,a.scheduler);controller=job;journal=logs/'submissions.jsonl'
        else:
            controller,journal=tracking_context(a.scheduler,a.logs)
        kind='controller' if a.operation.startswith('controller-') else 'wrapper'
        fields=dict(event='begin' if a.operation.endswith('start') else 'end',kind=kind,scheduler=a.scheduler,controller=controller,job_id=job)
        if kind=='wrapper':fields['parent']=controller
        if fields['event']=='end':fields['exit_code']=int(a.value)
        journal_event(journal,**fields)
        if a.operation=='controller-start':print(journal)
        return
    if not a.logs or not a.value:raise ValueError('This operation requires --logs and a value')
    if a.operation=='submit-task':
        controller,journal=tracking_context(a.scheduler,a.logs);parent=native_id(a.scheduler)
        task=Path(a.value).stem
        if not re.fullmatch(r't[A-Za-z0-9]+',task):raise ValueError('Unsupported SoS task identity: '+task)
        attempt=uuid.uuid4().hex
        fields=dict(kind='child',controller=controller,parent=parent,scheduler=a.scheduler,attempt=attempt,task_id=task)
        journal_event(journal,event='intent',**fields)
        cmd={'lsf':['bsub'],'sge':['qsub','-terse',a.value],'slurm':['sbatch','--parsable',a.value]}[a.scheduler]
        # LSF consumes its #BSUB allocation directives from the native stdin
        # script, while qsub/sbatch consume the same script by filename.
        with Path(a.value).open() as script:
            result=subprocess.run(cmd,stdin=script if a.scheduler=='lsf' else None,
                                  text=True,capture_output=True,check=True,timeout=60)
        job=submission_id(a.scheduler,result.stdout)
        journal_event(journal,event='receipt',job_id=job,**fields)
        print(job);return
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
        elif a.scheduler=='sge':
            cmd=['qsub','-terse','-S','/bin/bash','-N',name]+(['-P',a.account] if a.account else [])+(['-q',a.queue] if a.queue else [])+(['-pe','smp',str(n)] if n>1 else [])+['-l',f'h_vmem={max(1,(mem+n-1)//n)}M,h_rt={minutes//60}:{minutes%60:02}:00',
                 '-o',str(Path(a.logs)/'$JOB_ID.out'),'-e',str(Path(a.logs)/'$JOB_ID.err'),a.value]
        else:
            cmd=['sbatch','--parsable']+(['--account',a.account] if a.account else [])+(['--partition',a.queue] if a.queue else [])+['--cpus-per-task',str(n),'--mem',str(mem),'--time',str(minutes),
                 '--output',str(Path(a.logs)/'%j.out'),'--error',str(Path(a.logs)/'%j.err'),a.value]
        controller,journal=tracking_context(a.scheduler,a.logs)
        if props['type']=='single':rule_identity=props['rule']
        elif props['type']=='group':rule_identity=props['groupid']
        else:raise ValueError('Unsupported native Snakemake job type: '+str(props['type']))
        Path(a.value).write_text(tracked_rule(text,a.scheduler,a.logs,controller,journal))
        tracking=dict(kind='wrapper',controller=controller,parent=controller,scheduler=a.scheduler,attempt=uuid.uuid4().hex,snakemake_job_id=str(props['jobid']),rule=rule_identity)
        journal_event(journal,event='intent',**tracking)
        r=subprocess.run(cmd,text=True,capture_output=True,check=True,timeout=60)
        job=submission_id(a.scheduler,r.stdout)
        journal_event(journal,event='receipt',job_id=job,**tracking)
        print(job);return
    print(job_status(a.scheduler,a.value))


def job_status(scheduler,job_id,*,runner=None):
    """Return running/success/failed; unavailable evidence raises."""
    runner=subprocess.run if runner is None else runner
    job_id=str(job_id)
    if not job_id.isdecimal():raise ValueError('job ID must be numeric; arrays are unsupported')
    if scheduler=='lsf':
        r=runner(['bjobs','-noheader','-o','stat',job_id],capture_output=True,text=True,timeout=60)
        state=r.stdout.strip()
        if not state and 'not found' in r.stderr:
            r=runner(['bacct','-l',job_id],capture_output=True,text=True,timeout=60)
            m=re.search(r'Status <(DONE|EXIT)>',r.stdout);state=m.group(1) if m else ''
        if state not in ('DONE','EXIT','ZOMBI','RUN','PEND','PSUSP','USUSP','SSUSP','WAIT','PROV') or r.returncode!=0:
            raise RuntimeError('Scheduler status retrieval failed or unknown; inspect bjobs/bacct before resuming.')
        return 'success' if state=='DONE' else 'failed' if state in ('EXIT','ZOMBI') else 'running'
    if scheduler=='sge':
        live=runner(['qstat','-j',job_id],capture_output=True,text=True,timeout=60)
        if live.returncode==0:
            identity=re.search(r'(?m)^\s*job_number:\s*(\d+)\s*$',live.stdout)
            if not identity or identity.group(1)!=job_id:
                raise RuntimeError('SGE live job identity unavailable; inspect qstat/qacct before resuming.')
            declared=re.search(r'(?im)^\s*job_state\s*[:=]\s*(\S+)',live.stdout)
            if declared and declared.group(1) not in ('r','t','qw','hqw','hRqw','hRwq','Rr','Rt','s','S','T','ts','tS','tT','Eqw'):
                raise RuntimeError('Unknown SGE live state: '+declared.group(1))
            # qstat -j exposes scheduler/launch errors on a still-queued job.
            return 'failed' if re.search(r'(?im)^\s*(?:error reason|error_reason|job_state\s*[:=]\s*E)',live.stdout) else 'running'
        r=runner(['qacct','-j',job_id],capture_output=True,text=True,timeout=60)
        if r.returncode!=0:raise RuntimeError('Scheduler accounting unavailable; inspect qstat/qacct before resuming.')
        records=[];current={}
        for line in r.stdout.splitlines():
            if line.startswith('==='):
                if current:records.append(current);current={}
                continue
            fields=line.split()
            if not fields:continue
            key=fields[0]
            if key=='jobnumber' and 'jobnumber' in current or key=='failed' and 'failed' in current:
                records.append(current);current={}
            if key in ('jobnumber','taskid','failed','exit_status'):
                if len(fields)<2 or key in current:raise RuntimeError('Ambiguous SGE accounting; inspect qstat/qacct before resuming.')
                current[key]=fields[1]
        if current:records.append(current)
        if not records or any(not {'jobnumber','taskid','failed','exit_status'}<=r.keys() for r in records):
            raise RuntimeError('Incomplete SGE accounting; inspect qstat/qacct before resuming.')
        if any(r['jobnumber']!=job_id for r in records):
            raise RuntimeError('SGE accounting job identity differs; inspect qstat/qacct before resuming.')
        # Never discard failed attempts or array tasks. Arrays are rejected at
        # submission because this adapter cannot establish their complete task set.
        if any(r['failed']!='0' or r['exit_status']!='0' for r in records):return 'failed'
        if any(r['taskid'] not in ('undefined','0') for r in records):
            raise RuntimeError('SGE array accounting unsupported; submit individual jobs.')
        return 'success'
    if scheduler=='slurm':
        live=runner(['squeue','-h','-j',job_id,'-o','%i|%T'],capture_output=True,text=True,timeout=60)
        if live.returncode!=0 or live.stderr.strip():raise RuntimeError('Scheduler status retrieval failed; inspect squeue before resuming. '+live.stderr)
        active={'PENDING','RUNNING','CONFIGURING','COMPLETING','SUSPENDED','RESIZING','REQUEUED','REQUEUE_FED','REQUEUE_HOLD','SPECIAL_EXIT','STAGE_OUT','SIGNALING','STOPPED'}
        failed={'FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}
        rows=[line.strip().split('|') for line in live.stdout.splitlines() if line.strip()]
        if rows:
            if len(rows)!=1 or len(rows[0])!=2 or rows[0][0]!=job_id:
                raise RuntimeError('Slurm live job identity ambiguous; inspect squeue before resuming.')
            state=rows[0][1]
            if state in active:return 'running'
            if state in failed:return 'failed'
            if state!='COMPLETED':raise RuntimeError('Unknown Slurm state: '+state)
        r=runner(['sacct','-j',job_id,'--format=JobIDRaw,State,ExitCode','--noheader','--parsable2'],text=True,capture_output=True,timeout=60)
        records=[line.strip().split('|') for line in r.stdout.splitlines() if line.strip()]
        if r.returncode!=0 or r.stderr.strip() or not records or any(len(x)!=3 for x in records):
            raise RuntimeError('Scheduler accounting unavailable; inspect sacct before resuming. '+r.stderr)
        if not any(x[0]==job_id for x in records) or any(x[0]!=job_id and not re.fullmatch(re.escape(job_id)+r'\.[A-Za-z0-9_-]+',x[0]) for x in records):
            raise RuntimeError('Slurm accounting identity differs or is incomplete; inspect sacct before resuming.')
        states=[]
        for _,raw_state,code in records:
            state=raw_state.split()[0].rstrip('+') if raw_state.strip() else ''
            if state not in active|failed|{'COMPLETED'} or not re.fullmatch(r'\d+:\d+',code):
                raise RuntimeError('Slurm accounting state or exit code unknown; inspect sacct before resuming.')
            if state in failed or code!='0:0':return 'failed'
            states.append(state)
        return 'success' if all(x=='COMPLETED' for x in states) else 'running'
    raise ValueError('Unsupported scheduler: '+scheduler)


if __name__=='__main__':
    main()
