"""Exercise the actual pinned SoS monitor/check_task interleaving on the host."""
import os
from pathlib import Path
import shutil
import subprocess
import textwrap

from fungen_operator.onboarding import RESOURCES


def test_native_sos_monitor_keeps_published_pulse(tmp_path):
    python=os.environ.get('FUNGEN_TEST_SOS_PYTHON') or shutil.which('python')
    assert python, 'Provide host SoS 0.25.1; set FUNGEN_TEST_SOS_PYTHON'
    code=r'''
import builtins
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import sos.monitor
from sos.tasks import TaskFile, TaskParams, check_task

root=Path(sys.argv[1]); patch=Path(sys.argv[2])
os.environ['HOME']=str(root/'home')
(root/'home/.sos/tasks').mkdir(parents=True)
copy=root/'source/sos/monitor.py';copy.parent.mkdir(parents=True)
shutil.copyfile(sos.monitor.__file__,copy)
# The supplied environment can already have the fix; derive the pristine source.
base=['git','-C',str(root/'source'),'apply']
if subprocess.run(base+['--reverse','--check',str(patch)],capture_output=True).returncode==0:
    subprocess.run(base+['--reverse',str(patch)],check=True)
else:
    subprocess.run(base+['--check',str(patch)],check=True)

def interleave(label):
    spec=importlib.util.spec_from_file_location('sos.monitor_'+label,copy)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    task='tpulse_'+label
    tf=TaskFile(task);tf.save(TaskParams(task,'','',{},[]));tf.status='running'
    pulse=root/'home/.sos/tasks'/f'{task}.pulse'
    seen=[]
    def observed_open(file,*args,**kwargs):
        if str(file)==str(pulse):
            seen.append(check_task(task)['status'])
        return builtins.open(file,*args,**kwargs)
    # Put the native status reader exactly between the original unlink/open.
    module.open=observed_open
    module.TaskMonitor(task,5,60)
    return seen, tf.status, pulse

seen,status,_=interleave('original')
assert seen==['aborted'] and status=='aborted', (seen,status)
print('Original SoS 0.25.1: deterministic false abort reproduced')
subprocess.run(base+['--check',str(patch)],check=True)
subprocess.run(base+[str(patch)],check=True)
seen,status,pulse=interleave('fixed')
assert seen==['running'] and status=='running', (seen,status)
print('Patched monitor: concurrent native check_task remains running')
# A genuinely lost heartbeat still fails under the same status reader.
pulse.unlink()
assert check_task('tpulse_fixed')['status']=='aborted'
print('Missing heartbeat: native abort detection retained')
'''
    result=subprocess.run([python,'-c',textwrap.dedent(code),str(tmp_path),str(RESOURCES/'sos-pulse.patch')],
                          capture_output=True,text=True)
    assert result.returncode==0, result.stdout+result.stderr
    assert 'false abort reproduced' in result.stdout
    assert 'remains running' in result.stdout
    assert 'abort detection retained' in result.stdout
