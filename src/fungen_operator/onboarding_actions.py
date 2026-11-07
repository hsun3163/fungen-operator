"""The guide's fixed test uses the standard action executor and receipt notebook."""
from pathlib import Path
import shlex
import time
import yaml

from fungen_operator import cluster, onboarding
from fungen_operator.providers import ActionSpec, Provider
from fungen_operator.slots import Model, PathSlot


class GuidedTest(Model):
    notebook: PathSlot
    configfile: PathSlot
    workdir: PathSlot
    log_dir: PathSlot


def provider(deployment):
    root=Path(deployment.default_config).parent
    runtime=onboarding.guided_run(root);work=runtime/'work'
    c=onboarding.settings(root)

    def validate(d,args):
        expected=dict(notebook=str(runtime/'operator.ipynb'),configfile=str(runtime/'config.yaml'),
                      workdir=str(work),log_dir=str(work/'logs'))
        if args.model_dump()!=expected:raise ValueError('Guided test must use its registered configuration and runtime paths')
        if (d.backend!=c['scheduler'] or d.conda_env!=c['software'] or
                d.scheduler_account!=c['account'] or d.scheduler_queue!=c['queue']):
            raise ValueError('Guided scheduler/runtime differs from its registered setup')
        if Path(args.configfile).read_text()!=yaml.safe_dump(d.defaults(),sort_keys=True):
            raise ValueError('Guided configuration differs from its prepared canonical inputs')

    def bindings(d,args,cell_id):
        return {'log_stem':str(Path(args.log_dir)/cell_id)}

    def validate_bindings(d,args,b):
        stem=Path(b['log_stem'])
        if set(b)!={'log_stem'} or stem.parent!=Path(args.log_dir) or not stem.name.isalnum():
            raise ValueError('Guided controller logs differ from its registered runtime')

    def render(slots):
        args=GuidedTest.model_validate(slots['arguments']);b=slots['bindings']
        validate(deployment,args);validate_bindings(deployment,args,b)
        dry=shlex.join(onboarding.scientific_command(root,c,True))
        native=shlex.join(onboarding.guided_test_command(root,c,b['log_stem']))
        return ('%%bash\nset -eo pipefail\n'+
                'unset PYTHONPATH R_LIBS R_LIBS_USER R_LIBS_SITE R_HOME PIXI_HOME\n'+
                'export PATH='+shlex.quote(str(Path(c['software'])/'bin'))+':"$PATH"\n'+
                'export CONDA_PREFIX='+shlex.quote(c['software'])+'\n'+
                'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1\n'+
                'cd '+shlex.quote(args.workdir)+'\n'+dry+'\n'+native+'\n')

    def reconcile(executor,args,b,job,error,previous_outputs):
        observations=[]
        for delay in (0,1,2,4):
            if delay:time.sleep(delay)
            state=executor.scheduler(job);observations.append(state)
            if state['status'] in ('DONE','EXIT'):break
        status='failed' if error or state['status']=='EXIT' else 'completed' if state['status']=='DONE' else 'unknown'
        return dict(status=status,scheduler=state,scheduler_observations=observations,
                    synchronous_exit_code=1 if error else 0,logs=executor.logs(b['log_stem'],job))

    def task_layout(workdir,config,log_path):
        return {'task_directory':Path(config['runtime_home'])/'.sos/tasks'}

    return Provider(actions=(ActionSpec('guided_test',GuidedTest,{'1':render},validate=validate,
        bindings=bindings,validate_bindings=validate_bindings,reconcile=reconcile,
        config_text=lambda d,args:Path(args.configfile).read_text(),controller=True,
        description='Run the fixed guided scientific test, retaining its actual native receipt.'),),
        task_layout=task_layout,source_paths=(onboarding.__file__,cluster.__file__))
