"""Fail loudly if an isolated Python test reaches a production write/command.

Loaded automatically in child Python interpreters by isolated_test.py.
This is a regression tripwire, not an OS security boundary for arbitrary code.
"""
import os
import sys


class TestIsolationViolation(BaseException):
    pass


def production_path(value):
    if not isinstance(value,(str,bytes,os.PathLike)):return False
    path=os.fsdecode(value).replace('\\','/')
    return any(path==root or path.startswith(root+'/') for root in
               ('/boot','/mnt','/var','/etc','/usr/local/emhttp','/usr/libexec/unraid'))


def audit(event,args):
    if event=='open':
        path,mode,flags=args
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and production_path(path):
            raise TestIsolationViolation('Test attempted a production write')
    elif event in {'os.remove','os.rmdir','os.mkdir','os.chmod','os.chown','os.utime',
                   'os.truncate','os.rename','os.link','os.symlink'}:
        if any(production_path(p) for p in args[:2]):
            raise TestIsolationViolation('Test attempted a production filesystem mutation')
    elif event in {'subprocess.Popen','os.system'}:
        command=args[1] if event=='subprocess.Popen' else args[0]
        words=command if isinstance(command,(list,tuple)) else [command]
        if any(os.path.basename(os.fsdecode(w)) in {'docker','logger','ssh','scp','virsh','mover','move','fuser'}
               for w in words if isinstance(w,(str,bytes,os.PathLike))):
            raise TestIsolationViolation('Test attempted a live service/native command')


if os.environ.get('FEJES_ISOLATED_TEST')=='1':sys.addaudithook(audit)
