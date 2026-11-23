"""The guided notebook records consent boundaries and native execution profiles."""
from pathlib import Path
import json
import nbformat
import pytest
import yaml
from fungen_operator import onboarding as o


def test_notebook_retains_every_confirmed_step(tmp_path):
    p=o.notebook(tmp_path); nb=nbformat.read(p,as_version=4)
    cells=[c for c in nb.cells if c.cell_type=='code']
    assert [c.metadata.fungen_setup.step for c in cells]==list(o.STEPS)
    assert all('perform(' in c.source and not c.outputs for c in cells)
    stamp=p.stat().st_mtime_ns
    assert o.notebook(tmp_path)==p and p.stat().st_mtime_ns==stamp


def test_old_generated_notebook_keeps_cells_when_kernel_is_upgraded(tmp_path):
    path=o.notebook(tmp_path);nb=nbformat.read(path,as_version=4)
    nb.metadata.kernelspec={'name':'python3','display_name':'Python 3','language':'python'}
    nb.cells[2].outputs=[nbformat.v4.new_output('stream',name='stdout',text='retained evidence')]
    nbformat.write(nb,path)
    o.notebook(tmp_path);upgraded=nbformat.read(path,as_version=4)
    assert upgraded.metadata.kernelspec.name=='fungen-operator'
    assert upgraded.cells==nb.cells


def test_existing_unrelated_notebook_is_preserved(tmp_path):
    path=tmp_path/'setup.ipynb';nbformat.write(nbformat.v4.new_notebook(),path)
    original=path.read_bytes()
    with pytest.raises(ValueError,match='another --root'):o.notebook(tmp_path)
    assert path.read_bytes()==original


def test_refusing_a_step_prevents_execution(tmp_path,monkeypatch):
    (tmp_path/'setup.json').write_text('{}')
    monkeypatch.setattr(o,'ask',lambda prompt,default,*a:'no' if prompt=='Run this step? (yes/no)' else default)
    monkeypatch.setattr(o,'run',lambda *a,**k:pytest.fail('execution after refusal'))
    with pytest.raises(RuntimeError,match='prepared'):
        o.perform(tmp_path,'workflow')
    assert not (tmp_path/'workflow').exists()


def test_profiles_keep_native_scheduler_parallelism(tmp_path):
    o.profiles(tmp_path,{'account':'a','queue':'q','software':'/software','scheduler':'lsf'})
    hosts=yaml.safe_load((tmp_path/'sos.yaml').read_text())['hosts']
    assert hosts['q']['max_running_jobs']==2000
    from fungen_operator.cluster import task_submit_command
    assert hosts['q']['submit_cmd']==task_submit_command('lsf',o.guided_run(tmp_path)/'work/logs/rules')
    assert hosts['q']['submit_cmd_output']=='{job_id}'
    for sched in ['lsf','slurm','sge','local']:
        p=yaml.safe_load((tmp_path/'profiles'/sched/'config.yaml').read_text())
        assert p['jobs']==(4 if sched=='local' else 2000)
        if sched!='local':
            assert 'cluster.py submit' in p['cluster'] and '--scheduler '+sched in p['cluster']
            assert 'cluster.py status' in p['cluster-status']


@pytest.mark.parametrize('sched,submit,status',[('sge','submit-task --scheduler sge','qstat -j'),('slurm','submit-task --scheduler slurm','squeue -h')])
def test_native_profile_and_task_host(tmp_path,monkeypatch,sched,submit,status):
    c={'account':'xqtl','queue':'','software':'/software','scheduler':sched}
    o.profiles(tmp_path,c)
    p=yaml.safe_load((tmp_path/f'profiles/{sched}/config.yaml').read_text())
    assert '--scheduler '+sched+' --account xqtl' in p['cluster'] and '--account xqtl' in p['cluster-status']
    host=yaml.safe_load((tmp_path/'sos.yaml').read_text())['hosts'][o.task_queue(c)]
    assert submit in host['submit_cmd'] and status in host['status_cmd']
    assert 'bsub' not in host['submit_cmd'] and 'bjobs' not in host['status_cmd']
    assert host['max_running_jobs']==2000 and '{cores}' in host['task_template'] and 'int(mem)' in host['task_template']
    calls=[];monkeypatch.setattr(o,'run',lambda *a,**k:calls.append((a,k)))
    o.check_step(tmp_path,'scheduler',c)
    assert len(calls)==1 and json.loads(calls[0][1]['input'])['template']==host['task_template']


@pytest.mark.parametrize('sched,config,flag,expected',[
    ('lsf','',None,'acc_LOAD'),('sge','',None,''),('slurm','',None,''),('local','',None,''),
    ('sge','scheduler = "sge"\naccount = "xqtl"\n',None,'xqtl'),('lsf','scheduler = "lsf"\naccount = "acc_OTHER"\n',None,'acc_OTHER'),
    ('sge','scheduler = "sge"\naccount = "xqtl"\n','other','other'),
])
def test_new_setup_account_defaults(tmp_path,monkeypatch,sched,config,flag,expected):
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    if config:(tmp_path/'config/fungen').mkdir(parents=True);(tmp_path/'config/fungen/config.toml').write_text(config)
    monkeypatch.setattr(o,'ask',lambda prompt,default,*a:'no' if prompt=='Run this step? (yes/no)' else default)
    root=tmp_path/'xqtl'
    with pytest.raises(RuntimeError,match='prepared'):
        o.main(['--root',str(root),'--step','workflow','--manager','mamba','--software',str(tmp_path/'software'),'--scheduler',sched]+(['--account',flag] if flag else []))
    assert o.settings(root)['account']==expected


def test_scientific_commands_use_pinned_native_snakefile(tmp_path):
    c={'software':'/software folder','scheduler':'lsf'}
    cmd=o.scientific_command(tmp_path,c,True)
    assert cmd[0]=='/software folder/bin/snakemake'
    assert str(tmp_path/'workflow/code/snakemake/Snakefile') in cmd
    assert cmd[-1]=='xqtl_core' and '--dry-run' in cmd
    assert cmd[cmd.index('--jobs')+1]=='2000'


def test_frozen_recovery_is_declared_before_any_fit():
    from fungen_operator.synthetic import RECOVERY, SEED
    assert SEED==20261020 and RECOVERY['planted_required']==24
    assert RECOVERY['nominal_p']==5E-8 and RECOVERY['credible_set_coverage']==.95
    assert RECOVERY['null_max']==1


def test_miniforge_hash_is_checked_before_execution(tmp_path,monkeypatch):
    installer=tmp_path/'Miniforge3-26.7.2-0-Linux-x86_64.sh';installer.write_text('invalid installer')
    monkeypatch.setattr(o,'run',lambda *a,**k:pytest.fail('unverified installer executed'))
    with pytest.raises(ValueError,match='hash differs'):
        o.acquire_mamba(tmp_path)


def test_software_install_uses_frozen_lock_and_detects_lock_changes(tmp_path,monkeypatch):
    resources=tmp_path/'resources';resources.mkdir()
    (resources/'xqtl-mamba.yaml').write_text('dependencies: [r-susier=0.16.6]')
    (resources/'sos-pulse.patch').write_text('native heartbeat repair')
    monkeypatch.setattr(o,'patch_sos',lambda c:None)
    lock=resources/'xqtl-linux-64.lock';lock.write_text('@EXPLICIT\nhttps://example.org/pinned.conda#hash\n')
    prefix=tmp_path/'software'
    (tmp_path/'setup.json').write_text(json.dumps({'manager':'mamba','mamba':'/managed/mamba','software':str(prefix)}))
    monkeypatch.setattr(o,'RESOURCES',resources)
    monkeypatch.setattr(o,'ask',lambda *a:'yes')
    monkeypatch.setattr(o,'check_step',lambda *a:None)
    commands=[];monkeypatch.setattr(o,'run',lambda cmd,**kw:commands.append([str(x) for x in cmd]))
    o.perform(tmp_path,'software')
    assert commands[0]==['/managed/mamba','create','-y','-p',str(prefix),'--file',str(lock)]
    commands.clear();o.perform(tmp_path,'software')
    assert all('create' not in x and 'install' not in x for x in commands)
    (prefix/'conda-meta').mkdir(parents=True);(prefix/'conda-meta/history').touch()
    lock.write_text(lock.read_text()+'https://example.org/updated.conda#newhash\n')
    commands.clear();o.perform(tmp_path,'software')
    assert commands[0][1]=='install' and commands[0][-1]==str(lock)


def test_runtime_susier_requirement_is_pinned_in_both_specs():
    environment=yaml.safe_load((o.RESOURCES/'xqtl-mamba.yaml').read_text())
    assert o.COMMIT=='e1095f6354da6a4d2c43ef812eeb099a19fe93d2'
    assert 'r-pecotmr=0.9.5' in environment['dependencies']
    assert '/r-pecotmr-0.9.5-' in (o.RESOURCES/'xqtl-linux-64.lock').read_text()
    assert sum(line.startswith('https://') for line in (o.RESOURCES/'xqtl-linux-64.lock').read_text().splitlines())==800
    assert 'r-susier=0.16.6' in environment['dependencies']
    assert '/r-susier-0.16.6-' in (o.RESOURCES/'xqtl-linux-64.lock').read_text()


def no_execution(monkeypatch):
    fail=lambda *a,**k:pytest.fail('execution before predecessor check')
    for name in ('run','check_output','Popen'):monkeypatch.setattr(o.subprocess,name,fail)
    monkeypatch.setattr(o,'run',fail)


def test_step_needs_completed_predecessors_before_execution(tmp_path,monkeypatch):
    no_execution(monkeypatch);monkeypatch.setattr(o,'ask',lambda *a:pytest.fail('asked before predecessor check'))
    root=tmp_path/'xqtl'
    with pytest.raises(ValueError) as exc:
        o.main(['--root',str(root),'--step','test','--manager','mamba','--software',str(tmp_path/'software'),'--scheduler','lsf'])
    assert str(exc.value)==(f'workflow check failed: Missing upstream Snakefile. Step test needs workflow first. Run: fungen xqtl --root {root} --step workflow, '
                            f'or fungen xqtl --root {root} to run every step in order.')
    assert not (root/'logs').exists()


def test_new_setup_requires_new_or_empty_root(tmp_path,monkeypatch):
    monkeypatch.setattr(o,'ask',lambda *a:pytest.fail('asked before root check'))
    (tmp_path/'image.sif').write_text('x')
    with pytest.raises(ValueError,match='xQTL root must be a new or empty folder: '+str(tmp_path)):
        o.main(['--root',str(tmp_path),'--step','workflow'])
    assert [p.name for p in tmp_path.iterdir()]==['image.sif']


def test_existing_setup_root_is_accepted(tmp_path,monkeypatch):
    (tmp_path/'setup.json').write_text(json.dumps({'manager':'mamba','software':str(tmp_path/'software'),'scheduler':'lsf','mamba':'managed','account':'a','queue':'q'}))
    (tmp_path/'other.txt').write_text('kept')
    monkeypatch.setattr(o,'ask',lambda prompt,default,*a:'no' if prompt=='Run this step? (yes/no)' else default)
    with pytest.raises(RuntimeError,match='prepared'):
        o.main(['--root',str(tmp_path),'--step','workflow'])
    assert (tmp_path/'setup.ipynb').is_file()


def test_software_folder_must_differ_from_root(tmp_path):
    with pytest.raises(ValueError,match='use the default '+str(tmp_path/'software')):
        o.main(['--root',str(tmp_path),'--manager','mamba','--software',str(tmp_path),'--scheduler','lsf'])
    assert not (tmp_path/'setup.json').exists()


@pytest.mark.parametrize('sched',['sge','slurm'])
def test_cross_scheduler_account_is_not_inherited(tmp_path,monkeypatch,sched):
    monkeypatch.setattr(o,'read_config',lambda:dict(scheduler='lsf',account='acc_LOAD'))
    monkeypatch.setattr(o,'ask',lambda prompt,default,*a:'no' if prompt=='Run this step? (yes/no)' else default)
    root=tmp_path/'setup'
    with pytest.raises(RuntimeError,match='prepared'):
        o.main(['--root',str(root),'--scheduler',sched,'--step','workflow','--manager','mamba','--software',str(tmp_path/'software')])
    assert o.settings(root)['account']==''


def test_existing_account_update_requires_new_root(tmp_path,monkeypatch):
    c=dict(manager='mamba',software='/software',scheduler='sge',mamba='managed',account='old',queue='')
    (tmp_path/'setup.json').write_text(json.dumps(c))
    monkeypatch.setattr(o,'perform',lambda *a:pytest.fail('ran before rejecting changed setup'))
    with pytest.raises(ValueError,match='Existing setup account differs.*new --root'):
        o.main(['--root',str(tmp_path),'--account','new'])
    assert o.settings(tmp_path)==c


def test_unexpected_predecessor_error_is_visible(tmp_path,monkeypatch):
    (tmp_path/'setup.json').write_text('{}')
    def broken(*a):raise ImportError('native dependency broken')
    monkeypatch.setattr(o,'check_step',broken)
    with pytest.raises(ImportError,match='native dependency broken'):o.perform(tmp_path,'software')


def test_predecessor_actual_pin_error_is_preserved(tmp_path,monkeypatch):
    (tmp_path/'setup.json').write_text('{}')
    def broken(*a):raise ValueError('Workflow pin differs; use exact pin')
    monkeypatch.setattr(o,'check_step',broken)
    with pytest.raises(ValueError,match='Workflow pin differs; use exact pin.*Step software needs workflow first.*--step workflow'):
        o.perform(tmp_path,'software')


@pytest.mark.parametrize('scheduler',['lsf','sge','slurm','local'])
def test_emitted_deployment_registers_disjoint_guided_runtime(tmp_path,scheduler):
    from fungen_operator.actions import Deployment
    root=tmp_path/'setup';root.mkdir()
    snakefile=root/'workflow/code/snakemake/Snakefile'
    snakefile.parent.mkdir(parents=True);snakefile.write_text('rule xqtl_core:\n    shell: "true"\n')
    software=root/'software';software.mkdir()
    mamba=root/'mamba/bin/mamba'
    conda=mamba.parent.parent/'etc/profile.d/conda.sh';conda.parent.mkdir(parents=True);conda.write_text('')
    c=dict(scheduler=scheduler,account='science',queue='',software=str(software),mamba=str(mamba))
    (root/'setup.json').write_text(json.dumps(c));(root/'config.yaml').write_text('cwd: '+str(o.guided_run(root)/'work')+'\n')
    o.profiles(root,c);o.write_deployment(root,c)
    d=Deployment.load(root/'deployment.json');d.validate_layout()
    assert not Path(d.repository).is_symlink()
    assert Path(d.repository).is_relative_to(root) and Path(d.run_root).is_relative_to(root)
    for path in ('operator.ipynb','config.yaml','work','work/logs','work/sos_runtime/home'):
        d.validate_write_path(str(o.guided_run(root)/path))
        assert (o.guided_run(root)/path).is_relative_to(Path(d.run_root))
    assert not Path(d.repository).is_relative_to(Path(d.run_root))
    assert not Path(d.run_root).is_relative_to(Path(d.repository))
    with pytest.raises(ValueError,match='outside canonical source'):
        d.validate_write_path(str(snakefile))


def test_fresh_sge_guide_prompts_and_checks_predecessors(tmp_path,monkeypatch):
    monkeypatch.setattr(o,'scheduler',lambda:'sge')
    monkeypatch.setattr(o,'read_config',lambda:dict(scheduler='lsf',account='acc_LOAD'))
    answers=iter(['','','','science'])
    prompts=[]
    def respond(prompt):
        prompts.append(prompt)
        return next(answers)
    monkeypatch.setattr('builtins.input',respond)
    no_execution(monkeypatch)
    root=tmp_path/'guide'
    with pytest.raises(ValueError,match='Step test needs workflow first'):
        o.main(['--root',str(root),'--step','test'])
    assert 'Scheduler (lsf/slurm/sge/local) [sge]: ' in prompts
    assert 'SGE project (-P) []: ' in prompts
    assert o.settings(root)['scheduler']=='sge'
    assert o.settings(root)['account']=='science'
    assert len(prompts)==4
