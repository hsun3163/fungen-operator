"""Read-only reconciliation of a notebook's native Snakemake/SoS/LSF evidence.

Only retained controller receipts, their exact wrapper submission lines, and
job-ID files under exported per-unit SoS homes establish run membership. A
shared working directory by itself never establishes membership.
"""
from __future__ import annotations

from datetime import datetime
import json
import re
import shlex
import struct
import subprocess
from pathlib import Path

import yaml


_FIELDS = "jobid stat exit_code queue submit_time pend_time sub_cwd command job_name user exit_reason output_file error_file combined_resreq"
_SUBMISSION = re.compile(r"Job (\d+) has been submitted with LSF jobid (\d+) \(log: (.+?)\)\.")
_TERMINAL = {"EXIT", "DONE", "NOT_FOUND"}


def _text(path):
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def _inside(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def _time(value, current):
    if isinstance(value, (float, int)) or str(value).isdigit():
        return float(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%a %b %d %H:%M:%S %Y", "%b %d %H:%M:%S %Y", "%b %d %H:%M"):
        try:
            parsed = datetime.strptime(str(value), fmt)
            if "%Y" not in fmt:
                parsed = parsed.replace(year=datetime.fromtimestamp(current).year)
                if parsed.timestamp() > current + 86400:
                    parsed = parsed.replace(year=parsed.year - 1)
            return parsed.timestamp()
        except ValueError:
            pass
    return None


def _header(path):
    # The fixed SoS 1/2/3 header prefix contains no pickle payload. Reading it
    # neither imports SoS nor changes its records or task status.
    try:
        with Path(path).open("rb") as handle:
            values = struct.unpack("!2h8d", handle.read(68))
        if values[0] not in {1, 2, 3} or values[1] not in range(7):
            return None
        return {"sos_state": ("new", "pending", "submitted", "running", "aborted", "failed", "completed")[values[1]],
                "submitted_time": values[5], "running_time": values[6]}
    except (OSError, struct.error):
        return None


def _controller_actions(deployment):
    registry = getattr(deployment, "registry", None)
    return {"initiate_run", "check_readiness"} | {
        name for name, spec in getattr(registry, "specs", {}).items() if spec.controller}


def _evidence(deployment, nb):
    evidence, homes, observations = {}, {}, []
    task_dirs, resolved_dirs = {}, {}
    run_root = Path(deployment.run_root).resolve()
    registry = getattr(deployment, "registry", None)
    layout = registry.task_layout if registry else None
    controllers = _controller_actions(deployment)
    for cell in nb.cells:
        meta = cell.metadata.get("fungen", {})
        is_sweep = meta.get("action") == "control_run" and meta.get("slots", {}).get("arguments", {}).get("operation") == "sweep"
        if meta.get("action") not in controllers and not is_sweep:
            continue
        slots, result = meta.get("slots", {}), meta.get("result", {})
        args, bindings = slots.get("arguments", {}), slots.get("bindings", {})
        job_id = str(result.get("job_id", ""))
        if not job_id.isdigit():
            continue
        workdir = args.get("workdir", deployment.run_root)
        if not _inside(workdir, deployment.run_root):
            continue
        stem = bindings.get("log_stem", "")
        if not stem or not _inside(stem, deployment.run_root):
            continue
        evidence[job_id] = {"job_id": job_id, "kind": "sweep" if is_sweep else "controller", "workdir": workdir,
                            "log_stem": stem, "configfile": args.get("configfile", ""),
                            "rule": None, "unit": {}}
        if is_sweep:
            continue
        config = yaml.safe_load(_text(args.get("configfile", ""))) or {}
        # Controller LSF streams retain exact Snakemake submission lines, even
        # while the controller is running. Do not claim unrelated .snakemake logs.
        for suffix in ("out", "err"):
            path = Path(f"{stem}.{job_id}.{suffix}")
            if not path.exists():
                continue
            scheduled_time = None
            with path.open(errors="replace") as handle:
                for line in handle:
                    timestamp = re.match(r"^\[([^]]+)\]$", line.strip())
                    if timestamp:
                        scheduled_time = _time(timestamp.group(1), datetime.now().timestamp())
                    match = _SUBMISSION.search(line)
                    native = _NATIVE_SUBMISSION.search(line)
                    if native:
                        from .cluster import profile_logs
                        internal,wrapper=native.groups()
                        if not wrapper.isdecimal():raise ValueError('Unsupported native wrapper identity: '+wrapper)
                        log_path=str(profile_logs(deployment.profile_path,deployment.backend)/(wrapper+'.out'))
                    elif match:
                        internal, wrapper, log_path = match.groups()
                    else:
                        continue
                    if ".." in Path(log_path).parts or not Path(log_path).is_relative_to(workdir):
                        continue
                    key = (workdir, args.get("configfile"), log_path)
                    if key not in task_dirs:
                        task_dirs[key] = layout(workdir, config, log_path) if layout else None
                    descriptor = task_dirs[key] or {}
                    rule, unit = descriptor.get("rule"), descriptor.get("unit", {})
                    evidence[wrapper] = {"job_id": wrapper, "kind": "wrapper", "controller_job_id": job_id,
                                         "snakemake_job_id": internal, "rule": rule, "unit": unit,
                                         "task_kind": descriptor.get("task_kind", rule), "scheduled_time": scheduled_time,
                                         "log_path": log_path, "workdir": workdir}
                    task_dir = descriptor.get("task_directory")
                    if task_dir:
                        raw_path = str(task_dir)
                        if raw_path not in resolved_dirs:
                            resolved_dirs[raw_path] = Path(task_dir).resolve()
                        task_dir = resolved_dirs[raw_path]
                    if task_dir and task_dir.is_relative_to(run_root):
                        homes.setdefault(task_dir, []).append(evidence[wrapper])
                        if native:
                            streams=_native_logs([log_path,str(Path(log_path).with_suffix('.err'))])
                            pairs=_native_receipts(streams,_TASK_SUBMISSION,re.compile(r'\bsubmitted\s+to\b|with job id'))
                            for task_id,child in pairs:
                                if not re.fullmatch(r't[A-Za-z0-9]+',task_id) or not child.isdecimal():
                                    raise ValueError('Unsupported native task receipt')
                                header=_header(task_dir/(task_id+'.task'))
                                if not header:raise ValueError('Native task state unavailable: '+task_id)
                                if header['sos_state'] in ('submitted','running'):
                                    ids=yaml.safe_load((task_dir/(task_id+'.job_id')).read_text())
                                    script=(task_dir/(task_id+'.sh')).read_text()
                                    if str(ids['job_id'])!=child or not re.search(r'\bsos\s+execute\s+'+re.escape(task_id)+r'(?:\s|$)',script):
                                        raise ValueError('Native task identity/provenance differs: '+task_id)
                                if child in evidence and evidence[child].get('wrapper_job_id')!=wrapper:
                                    raise ValueError('Ambiguous native child lineage: '+child)
                                evidence[child]={'job_id':child,'kind':'child','task_id':task_id,**header,
                                    'task_dir':str(task_dir),'runlog':str(task_dir.parents[3]),
                                    'wrapper_job_id':wrapper,'wrapper_candidates':[wrapper],
                                    'rule':rule,'unit':unit,'task_kind':descriptor.get('task_kind',rule),'workdir':workdir}
    for task_dir, wrappers in homes.items():
        # SoS retains .job_id while submitted/running and removes it on completed
        # task packing. This directory-only census avoids decoding task payloads.
        for job_file in sorted(task_dir.glob("*.job_id")):
            if not _inside(job_file, deployment.run_root):
                continue
            task_id = job_file.name[:-7]
            header = _header(task_dir / f"{task_id}.task")
            if header and header["sos_state"] not in {"submitted", "running"}:
                continue
            ids = yaml.safe_load(_text(job_file))
            child = str(ids.get("job_id", "")) if isinstance(ids, dict) else ""
            if not child.isdigit() or not header:
                observations.append({"task_id": task_id, "status": "unresolved_task_record"})
                continue
            if child in evidence:
                if evidence[child].get('task_id')!=task_id:raise ValueError('Native child task identity differs')
                continue
            # The submission script must name exactly this task; it is executable
            # evidence, read as text only. Its path remains under the isolated home.
            script = _text(task_dir / f"{task_id}.sh")
            if not re.search(r"\bsos\s+execute\s+" + re.escape(task_id) + r"(?:\s|$)", script):
                observations.append({"task_id": task_id, "status": "missing_submission_script"})
                continue
            # Multiple attempts can have wrappers for the same unit. The newest
            # submission preceding this task is the waiting wrapper; live state
            # below selects a still-active wrapper when present.
            wrapper = wrappers[-1]
            evidence[child] = {"job_id": child, "kind": "child", "task_id": task_id,
                               **header, "task_dir": str(task_dir), "runlog": str(task_dir.parents[3]),
                               "wrapper_job_id": wrapper["job_id"], "wrapper_candidates": list(dict.fromkeys(w["job_id"] for w in wrappers)),
                               "rule": wrapper["rule"], "unit": wrapper["unit"], "task_kind": wrapper.get("task_kind"), "workdir": wrapper["workdir"]}
    return evidence, observations


def _history(text, ids):
    records = {}
    for match in re.finditer(r"(?ms)^Job <(\d+)>.*?(?=^Job <|\Z)", text):
        job_id = match.group(1)
        if job_id not in ids:
            continue
        body = re.sub(r"\n\s+", " ", match.group(0))
        if "is not found" in body:
            continue
        states = re.findall(r"Status <(\w+)>", body)
        if re.search(r"Done successfully|Completed <done>", body, re.I):
            state = "DONE"
        elif re.search(r"Exited with exit code|Completed <exit>", body, re.I):
            state = "EXIT"
        else:
            state = states[-1] if states else "UNKNOWN"
        reason = re.search(r"(?:Exited with exit code[^;\n.]*|TERM_[A-Z_]+[^;\n]*)", body)
        records[job_id] = {"job_id": job_id, "status": state, "lsf_state": state,
                           "exit_reason": reason.group(0) if reason else "", "live": False}
    return records



def _complete_history_batch(proc, requested, records):
    """Only complete native records permit inference from silently omitted IDs."""
    if proc.returncode != 0 or proc.stderr.strip() or not records:
        return False
    blocks = list(re.finditer(r"(?ms)^Job <(\d+)>.*?(?=^Job <|\Z)", proc.stdout))
    if not blocks or proc.stdout[:blocks[0].start()].strip():
        return False
    if {block.group(1) for block in blocks} != set(records):
        return False
    # bhist -l terminates every native record with its complete state-duration
    # table. A header or terminal event alone can also be a truncated response.
    footer = re.compile(
        r"(?m)^\s*PEND\s+PSUSP\s+RUN\s+USUSP\s+SSUSP\s+UNKWN\s+TOTAL\s*\n"
        r"[ \t]*[0-9]+(?:\.[0-9]+)?(?:[ \t]+[0-9]+(?:\.[0-9]+)?){6}[ \t\r\n]*\Z")
    for block in blocks:
        if (block.group(1) not in requested or not footer.search(block.group(0))
                or records[block.group(1)]["status"] == "UNKNOWN"):
            return False
    return True

def _lineage(child, evidence, jobs):
    candidates = child["wrapper_candidates"]
    if len(candidates) == 1:
        return candidates[0]
    # An older submitted task can survive a wrapper restart. Match the exact
    # task/job submission in its dated engine log, then bind that engine launch
    # to the controller's dated wrapper submission interval. RUN alone cannot
    # distinguish the original wrapper from a later retry for the same unit.
    engine_times = []
    task = re.compile(re.escape(child["task_id"]) + r".*submitted.*(?:job id|job_id)\s+" + re.escape(child["job_id"]) + r"(?:\s|$)")
    for path in Path(child["runlog"]).glob("*.log"):
        stamp = re.match(r"(\d{8}_\d{6})\.", path.name)
        if not stamp:
            continue
        with path.open(errors="replace") as handle:
            if any(task.search(line) for line in handle):
                engine_times.append(datetime.strptime(stamp.group(1), "%Y%m%d_%H%M%S").timestamp())
    # SoS can reset a task's submission header during a later retry while
    # retaining its original .job_id. The header cannot date wrapper lineage.
    # An exact retained task/job submission log is required across retries.
    if not engine_times:
        return None
    reference_time = max(engine_times)
    eligible = []
    for wrapper in candidates:
        when = evidence[wrapper].get("scheduled_time") or jobs.get(wrapper, {}).get("submit_time")
        if not when:
            return None
        if when <= reference_time:
            eligible.append((when, wrapper))
    if not eligible:
        return None
    latest = max(when for when, _ in eligible)
    matches = [wrapper for when, wrapper in eligible if when == latest]
    return matches[0] if len(matches) == 1 else None


def _decisive(child):
    patterns = re.compile(r"permission denied|Lmod has detected|Unable to parse|TERM_[A-Z_]+|Traceback|Error:|error:|command not found|No such file|\bKilled\b|segmentation fault", re.I)
    runlog, task_id, job = Path(child["runlog"]), child["task_id"], child["job_id"]
    for path in (runlog / f"{job}.err", runlog / f"{job}.out",
                 Path(child["task_dir"], f"{task_id}.err"), Path(child["task_dir"], f"{task_id}.out")):
        if path.exists():
            with path.open(errors="replace") as handle:
                for line in handle:
                    if patterns.search(line):
                        return line.strip()[:2000]
    return None


def _membership(evidence, record):
    if not evidence:
        return False, "job ID is absent from this notebook's controller receipts, wrapper submissions and SoS task directories"
    cwd, command = record.get("sub_cwd", ""), record.get("command", "")
    if evidence["kind"] not in {"controller", "sweep"} and (not cwd or not _inside(cwd, evidence["workdir"])):
        return False, "live submission working directory differs from this run's recorded job evidence"
    output, error = record.get("output_file", ""), record.get("error_file", "")
    if evidence["kind"] in {"controller", "sweep"}:
        expected = f"{evidence['log_stem']}.{evidence['job_id']}.out"
        command_match = "snakemake" in command and evidence.get("configfile", "") in command and evidence["workdir"] in command
        matched = output == expected or command_match
    elif evidence["kind"] == "wrapper":
        matched = output == evidence["log_path"] or error == evidence["log_path"]
    else:
        matched = (re.search(r"\bsos\s+execute\s+" + re.escape(evidence["task_id"]) + r"(?:\s|$)", command) is not None
                   or evidence["task_dir"] in command)
        # The task's LSF streams may be relative to its exact per-unit runlog.
        matched = matched and Path(cwd).resolve() == Path(evidence["runlog"]).resolve()
    return matched, "live scheduler record matches retained run evidence" if matched else "live command or scheduler output path differs from this run's recorded job evidence"


_NATIVE_SUBMISSION = re.compile(r"(?:Submitted (?:job|group job)|Resuming incomplete job) (\S+) with external jobid '([^']+)'\.")
_TASK_SUBMISSION = re.compile(r"\b(\S+)\s+submitted\s+to\s+\S+\s+with job id\s+(\S+)")
_ANSI = re.compile(r'\x1b\[[0-9;]*m')


def _native_logs(paths):
    """Read only the exact streams bound by receipts/profile, with no silent loss."""
    content=[]
    for path in paths:
        try:content.append(Path(path).read_text())
        except (OSError,UnicodeError) as exc:
            raise RuntimeError('Native child inspection cannot read retained stream '+str(path)+': '+str(exc)) from exc
    return _ANSI.sub('', '\n'.join(content))


class NativeDiscoveryIncomplete(RuntimeError):
    def __init__(self,message,jobs):
        self.observed_jobs={key:dict(row) for key,row in jobs.items()}
        self.coverage_verified=False
        statuses=', '.join(key+':'+row['status'] for key,row in list(jobs.items())[:20])
        super().__init__('Native submission coverage incomplete: '+message+'; observed jobs: '+statuses)


def _native_receipts(text,pattern,marker):
    found=[]
    for line in text.splitlines():
        if marker.search(line):
            match=pattern.search(line)
            if not match:raise ValueError('Malformed/truncated native submission line: '+line[:300])
            found.append(match.groups())
    return list(dict.fromkeys(found))


def _submission_graph(records,controllers):
    begins={};ends={};intents={};receipts={}
    for record in records:
        event=record['event'];kind=record['kind']
        if kind=='controller' and record.get('job_id')!=record['controller']:raise ValueError('Controller boundary identity differs')
        if kind=='wrapper' and record['parent']!=record['controller']:raise ValueError('Wrapper controller identity differs')
        if event=='end' and (type(record.get('exit_code')) is not int or not 0<=record['exit_code']<=255):raise ValueError('Invalid native completion exit code')
        if kind not in ('controller','wrapper','child'):raise ValueError('Unknown submission kind')
        if event in ('begin','end'):
            if kind=='child':raise ValueError('Unexpected child boundary')
            key=(kind,record['job_id'])
            target=begins if event=='begin' else ends
            if key in target:raise ValueError('Ambiguous repeated submission boundary')
            target[key]=record
        elif event in ('intent','receipt'):
            if kind=='controller':raise ValueError('Unexpected controller intent')
            target=intents if event=='intent' else receipts;key=record['attempt']
            if key in target:raise ValueError('Ambiguous repeated submission intent/receipt')
            target[key]=record
        else:raise ValueError('Unknown submission journal event')
    if set(intents)!=set(receipts):raise ValueError('Native submission intent has no complete receipt; inspect scheduler before retrying')
    for attempt,intent in intents.items():
        receipt=receipts[attempt]
        if {k:v for k,v in receipt.items() if k not in ('event','job_id')}!={k:v for k,v in intent.items() if k!='event'}:
            raise ValueError('Native intent and receipt identity differ')
        if not str(receipt['job_id']).isdecimal():raise ValueError('Unsupported journal job identity')
    for controller in controllers:
        if ('controller',controller) not in begins:raise ValueError('Controller has no recorded discovery start: '+controller)
    if any(key not in begins for key in ends):raise ValueError('Discovery end has no matching start')
    wrappers=[r for r in receipts.values() if r['kind']=='wrapper']
    children=[r for r in receipts.values() if r['kind']=='child']
    wrapper_ids={r['job_id'] for r in wrappers}
    if len({r['job_id'] for r in receipts.values()})!=len(receipts):raise ValueError('Ambiguous repeated native job identity')
    owners={r['job_id']:r['controller'] for r in wrappers}
    if any(owners.get(r['parent'])!=r['controller'] for r in children):raise ValueError('Child controller identity differs')
    if any(r['parent'] not in controllers for r in wrappers) or any(r['parent'] not in wrapper_ids for r in children):
        raise ValueError('Submission receipt has no identified parent')
    if any(kind=='wrapper' and job not in wrapper_ids for kind,job in begins):raise ValueError('Wrapper discovery start has no receipt')
    return begins,ends,wrappers,children


def inspect_native_jobs(deployment,nb,*,grace_minutes=10,runner=None,now=None,requested_ids=None):
    """Verify the current native submission set and query every identified job.

    The canonical adapter journals intent before submission and receipt afterward.
    Controller/wrapper start/end records prove zero-child boundaries. Exact native
    streams must agree with this independent set. A stable journal snapshot and
    complete records are required for verified coverage, including child-free jobs.
    """
    from .cluster import job_status,profile_logs,journal_records,task_submit_command
    runner=subprocess.run if runner is None else runner
    current=datetime.now().timestamp() if now is None else float(now)
    scheduler=deployment.backend;jobs={};dead=[];processed=set()
    def incomplete(message):raise NativeDiscoveryIncomplete(message,jobs)
    def observe(job,**evidence):
        if job in jobs:
            if any(jobs[job].get(k)!=v for k,v in evidence.items() if k in ('kind','controller_job_id','wrapper_job_id','task_id')):
                incomplete('Ambiguous native job lineage for '+job)
            return jobs[job]
        try:status=job_status(scheduler,job,runner=runner)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
            raise RuntimeError(scheduler+' inspection failed for job '+job+': '+str(exc)) from exc
        if status not in ('running','success','failed'):raise RuntimeError('Unknown native status for '+job)
        row=dict(evidence,job_id=job,status={'running':'RUN','success':'DONE','failed':'EXIT'}[status],scheduler=scheduler,
                 membership=True,membership_reason='verified native submission lineage')
        jobs[job]=row;return row
    controllers=[]
    for cell in nb.cells:
        meta=cell.metadata.get('fungen',{})
        if meta.get('action') not in _controller_actions(deployment):continue
        job=str(meta.get('result',{}).get('job_id',''))
        if not job:continue
        if not job.isdecimal():incomplete('Unsupported controller identity: '+job)
        slots=meta['slots'];args=slots['arguments'];stem=slots['bindings']['log_stem']
        if not _inside(stem,deployment.run_root) or not _inside(args['workdir'],deployment.run_root):incomplete('Controller evidence outside run root')
        observe(job,kind='controller');controllers.append((job,args,stem))
    if not controllers:incomplete('No retained controller receipts')
    controller_ids={job for job,_,_ in controllers}
    try:
        logs=profile_logs(deployment.profile_path,scheduler);journal=logs/'submissions.jsonl'
        records=journal_records(journal,controller_ids)
        if any(r['scheduler']!=scheduler for r in records):raise ValueError('Journal scheduler differs from deployment')
        begins,ends,wrappers,children=_submission_graph(records,controller_ids)
        for job,args,stem in controllers:
            text=_native_logs([f'{stem}.{job}.out',f'{stem}.{job}.err'])
            found=_native_receipts(text,_NATIVE_SUBMISSION,re.compile(r'(?:Submitted (?:job|group job)|Resuming incomplete job|external jobid)'))
            expected={(r['snakemake_job_id'],r['job_id']) for r in wrappers if r['parent']==job}
            if set(found)!=expected:incomplete('Controller stream does not establish the journaled rule submissions for '+job)
            if not expected and (('controller',job) not in ends or jobs[job]['status']=='RUN'):
                incomplete('Controller has no proven zero-submission completion boundary: '+job)
            config=yaml.safe_load(Path(args['configfile']).read_text())
            if config.get('minerva'):
                hosts=yaml.safe_load(Path(config['minerva']).read_text())['hosts']
                for host in hosts.values():
                    if host.get('queue_type')=='pbs' and host.get('submit_cmd')!=task_submit_command(scheduler,logs):
                        incomplete('SoS task host does not use the canonical tracked native adapter; regenerate scheduler setup')
            for internal,wrapper in found:
                row=observe(wrapper,kind='wrapper',controller_job_id=job,snakemake_job_id=internal)
                if wrapper in processed:continue
                processed.add(wrapper)
                if ('wrapper',wrapper) not in begins:incomplete('Wrapper discovery has not started: '+wrapper)
                output=_native_logs([logs/(wrapper+'.out'),logs/(wrapper+'.err')])
                task_pairs=_native_receipts(output,_TASK_SUBMISSION,re.compile(r'\bsubmitted\s+to\b|with job id'))
                expected_tasks={(r['task_id'],r['job_id']) for r in children if r['parent']==wrapper}
                if set(task_pairs)!=expected_tasks:incomplete('Wrapper stream does not establish the journaled task submissions for '+wrapper)
                if not expected_tasks and (('wrapper',wrapper) not in ends or row['status']=='RUN'):
                    incomplete('Wrapper has no proven child-free completion boundary: '+wrapper)
                for task,child in task_pairs:
                    if not re.fullmatch(r't[A-Za-z0-9]+',task) or not child.isdecimal():incomplete('Unsupported task/job identity')
                    home=Path(config['runtime_home']).resolve()
                    if not home.is_relative_to(Path(deployment.run_root).resolve()):
                        canonical=yaml.safe_load(Path(deployment.default_config).read_text())
                        if home!=Path(canonical['runtime_home']).resolve():incomplete('SoS home differs from canonical configuration')
                    task_dir=home/'.sos/tasks';header=_header(task_dir/(task+'.task'))
                    if not header:incomplete('SoS task state unavailable for '+task)
                    child_row=observe(child,kind='child',wrapper_job_id=wrapper,controller_job_id=job,task_id=task,**header)
                    if header['sos_state'] not in ('submitted','running'):continue
                    ids=yaml.safe_load((task_dir/(task+'.job_id')).read_text())
                    if not isinstance(ids,dict) or str(ids.get('job_id'))!=child:incomplete('SoS job-ID record differs for '+task)
                    script=(task_dir/(task+'.sh')).read_text()
                    if not re.search(r'\bsos\s+execute\s+'+re.escape(task)+r'(?:\s|$)',script):incomplete('SoS execution script differs for '+task)
                    submitted=header['submitted_time']
                    if submitted<=0:incomplete('SoS submission time unavailable')
                    if current-submitted>grace_minutes*60 and child_row['status'] in ('DONE','EXIT'):
                        dead.append(dict(task_id=task,job_id=child,wrapper_job_id=wrapper,scheduler=scheduler,
                                         scheduler_state=child_row['status'],sos_state=header['sos_state'],submitted_time=submitted))
        if journal_records(journal,controller_ids)!=records:incomplete('Submission set changed during inspection')
    except NativeDiscoveryIncomplete:raise
    except (OSError,ValueError,KeyError,TypeError,yaml.YAMLError) as exc:incomplete(str(exc))
    if requested_ids:
        for job in requested_ids:
            if str(job) not in jobs:jobs[str(job)]={'job_id':str(job),'membership':False,'membership_reason':'absent from verified native submission lineage'}
    coverage={'verified':True,'controllers':len(controller_ids),'wrappers':len(wrappers),'tasks':len(children)}
    return dict(jobs=jobs,dead_children=dead,count=len(dead),scheduler_ok=True,observations=[],coverage=coverage,grace_minutes=grace_minutes)


def inspect_jobs(deployment, nb, *, grace_minutes=10, runner=None, now=None, requested_ids=None, require_coverage=False):
    """Return a single batch snapshot; scheduler failures always fail closed.

    ``jobs`` includes all currently retained jobs for the current LSF user so an
    explicit outside ID gets an auditable membership refusal. Historical records
    are queried only for active SoS children missing from the one bjobs result.
    The caller owns host approval and must run this function outside the sandbox.
    """
    runner=subprocess.run if runner is None else runner
    if deployment.backend in ('lsf','sge','slurm') and (require_coverage or deployment.backend!='lsf'):
        try:
            return inspect_native_jobs(deployment,nb,grace_minutes=grace_minutes,runner=runner,now=now,requested_ids=requested_ids)
        except NativeDiscoveryIncomplete as exc:
            if not require_coverage:raise
            return dict(jobs=exc.observed_jobs,dead_children=[],count=None,scheduler_ok=False,
                        observations=[str(exc)],coverage={'verified':False,'reason':str(exc)},
                        grace_minutes=grace_minutes)
        except (OSError,ValueError,KeyError,TypeError,yaml.YAMLError) as exc:
            raise RuntimeError('Native child inspection evidence unavailable: '+str(exc)) from exc
    if deployment.backend not in ('lsf','fixture'):
        raise ValueError('External scheduler inspection is not applicable to backend '+deployment.backend)
    current = datetime.now().timestamp() if now is None else float(now)
    observations = []
    snapshot = {"jobs": {}, "dead_children": [], "count": 0, "observations": observations,
                "scheduler_ok": False, "grace_minutes": grace_minutes,
                "coverage": {"verified":False,"reason":"Observed membership only; use public inspect for journal coverage verification."}}
    try:
        proc = runner(["bjobs", "-a", "-json", "-o", _FIELDS], text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        observations.append({"status": "scheduler_query_failed", "diagnostic": str(error)})
        return snapshot
    try:
        raw = json.loads(proc.stdout)
        records = raw["RECORDS"]
        if proc.returncode or not isinstance(records, list) or any("ERROR" in row or "error" in row for row in records):
            raise ValueError("scheduler returned an unsuccessful response")
    except (ValueError, KeyError, TypeError):
        observations.append({"status": "scheduler_query_failed", "diagnostic": proc.stderr})
        return snapshot
    snapshot["scheduler_ok"] = True
    # An explicit ID outside the run directory can belong only through a saved
    # controller receipt. Refuse these live outsiders before scanning task homes.
    controllers = {str(c.metadata.get("fungen", {}).get("result", {}).get("job_id"))
                   for c in nb.cells if c.metadata.get("fungen", {}).get("action") in
                   _controller_actions(deployment) or
                   (c.metadata.get("fungen", {}).get("action") == "control_run" and
                    c.metadata.get("fungen", {}).get("slots", {}).get("arguments", {}).get("operation") == "sweep")}
    if requested_ids and all(job not in controllers for job in requested_ids):
        selected = {str(r.get("JOBID", r.get("jobid", ""))): r for r in records}
        if all(job not in selected or not _inside(str(selected[job].get("SUB_CWD", selected[job].get("sub_cwd", "/"))), deployment.run_root)
               for job in requested_ids):
            snapshot["jobs"] = {job: {"job_id": job, "membership": False,
                "membership_reason": "live job is outside this run's task directories and controller receipts"}
                for job in requested_ids}
            return snapshot
    evidence, found = _evidence(deployment, nb)
    observations.extend(found)
    jobs = snapshot["jobs"]
    for raw in records:
        row = {str(k).lower(): v for k, v in raw.items()}
        job = str(row.pop("jobid", ""))
        if not job.isdigit():
            continue
        state = str(row.pop("stat", "UNKNOWN"))
        record = {**evidence.get(job, {}), **row, "job_id": job, "status": state,
                  "lsf_state": state, "live": True}
        resource = row.get("combined_resreq", "")
        memory = re.search(r"\brusage\[([^]]*)\]", resource)
        memory = re.search(r"(?:^|[:,\s])mem=([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)", memory.group(1)) if memory else None
        if memory:
            value, unit = float(memory.group(1)), memory.group(2).upper()
            factors = {"": 1/1024, "M": 1/1024, "MB": 1/1024, "G": 1, "GB": 1,
                       "K": 1/(1024*1024), "KB": 1/(1024*1024), "T": 1024, "TB": 1024}
            record["memory_reservation_gb"] = value * factors[unit] if unit in factors else None
        else:
            record["memory_reservation_gb"] = None
        if state in {"EXIT", "DONE"} and not record.get("exit_reason"):
            code = str(record.get("exit_code", "")).strip()
            record["exit_reason"] = (f"Exited with exit code {code}" if code not in {"", "-", "None"}
                                     else "LSF did not provide an exit reason")
        record["submit_time"] = _time(row.get("submit_time"), current)
        # LSF's accumulated pending seconds survive requeues; elapsed time
        # since initial submission can include earlier running intervals.
        try:
            pending_seconds = float(row["pend_time"])
        except (KeyError, TypeError, ValueError):
            pending_seconds = current - record["submit_time"] if record["submit_time"] else 0
        record["pending_minutes"] = max(0, pending_seconds / 60) if state == "PEND" else 0
        record["membership"], record["membership_reason"] = _membership(evidence.get(job), record)
        jobs[job] = record
    history_ids = {job for job, ev in evidence.items() if ev["kind"] in {"controller", "sweep"}}
    for job, ev in evidence.items():
        if ev.get("sos_state") in {"submitted", "running"}:
            history_ids.add(job)
            history_ids.update(ev["wrapper_candidates"])
    missing = sorted(history_ids - jobs.keys(), key=int)
    history = {}
    if missing:
        try:
            proc = runner(["bhist", "-a", "-l", *sorted(missing, key=int)], text=True, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            proc = subprocess.CompletedProcess([], 1, "", str(error))
        history = _history(proc.stdout, missing)
        # bhist's explicit per-ID absence is distinct from command/network errors.
        absent = {m.group(1) for m in re.finditer(r"Job <(\d+)> is not found", proc.stdout + proc.stderr)}
        if (re.fullmatch(r"\s*No matching job found\.?\s*", proc.stdout + proc.stderr)
                or _complete_history_batch(proc, missing, history)):
            absent.update(set(missing) - set(history))
        for job in missing:
            if job in history:
                jobs[job] = {**evidence[job], **history[job], "membership": False,
                             "membership_reason": "historical job is absent from live bjobs"}
            elif job in absent:
                jobs[job] = {**evidence[job], "status": "NOT_FOUND", "lsf_state": "NOT_FOUND", "live": False,
                             "membership": False, "membership_reason": "LSF has no record of this retained task submission", "exit_reason": "LSF has no record"}
            else:
                observations.append({"job_id": job, "status": "history_query_unresolved"})
    for job, child in evidence.items():
        if child.get("sos_state") not in {"submitted", "running"}:
            continue
        record = jobs.get(job, {})
        submitted = child["submitted_time"]
        if submitted <= 0 or current - submitted <= grace_minutes * 60 or record.get("status") not in _TERMINAL:
            continue
        wrapper_id = _lineage(child, evidence, jobs)
        if wrapper_id is None:
            observations.append({"task_id": child["task_id"], "status": "wrapper_lineage_unresolved"})
        snapshot["dead_children"].append({"task_id": child["task_id"], "lsf_job_id": job,
            "job_id": job, "lsf_state": record["status"], "exit_reason": record.get("exit_reason", ""),
            "wrapper_job_id": wrapper_id, "rule": child["rule"], "unit": child["unit"],
            "sos_state": child["sos_state"], "submitted_time": submitted,
            "first_error_line": _decisive(child)})
    snapshot["count"] = len(snapshot["dead_children"])
    return snapshot
