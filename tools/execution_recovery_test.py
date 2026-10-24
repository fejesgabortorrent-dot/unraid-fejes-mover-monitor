"""Abrupt child-process exits in a disposable filesystem; no Unraid/native calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

def child(folder,phase):
    from unittest.mock import patch
    from contextlib import ExitStack
    import selective_mover as mover
    root=Path(folder);source=root/'source.bin';target=root/'target.bin'
    real_open=open
    key='/mnt/user/Filmek/fixture.bin'
    def execute(*args):
        if phase=='before':os._exit(77)
        shutil.copy2(source,target);source.unlink()
        os._exit(77)  # Exit before returning the move/verification outcome.
    def collect(*args):
        if phase=='restart':mover.guards()
        return ({'age_days':1,'max_bytes':16*1024**3,'candidates':[key],'blockers':[],'skipped':[]},[],{key:{'signature':[1,2,4096,0,0]}},[],[],{})
    with ExitStack() as stack:
        for name,value in [('LAST',root/'last.json'),('PID',root/'mover.pid'),('ATTEMPT',root/'attempt')]:stack.enter_context(patch.object(mover,name,value))
        stack.enter_context(patch.object(mover,'open',side_effect=lambda name,mode:real_open(root/Path(name).name,mode),create=True))
        stack.enter_context(patch.object(mover,'collect',side_effect=collect))
        stack.enter_context(patch.object(mover,'execute_file',side_effect=execute))
        stack.enter_context(patch.object(mover,'log'))
        if phase=='restart':
            # Simulate an operator-confirmed dead PID; do not touch a real PID file.
            (root/'mover.pid').unlink(missing_ok=True)
        result=mover.run()
        print(json.dumps(result))

@unittest.skipIf(os.name=='nt','Linux fsync/flock subprocess recovery test')
class AbruptExitRecovery(unittest.TestCase):
    def test_exit_before_and_after_lab_file_operation_requires_inspection(self):
        for phase in ('before','after'):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);payload=b'fixture-data'*400;(root/'source.bin').write_bytes(payload)
                command=[sys.executable,str(Path(__file__).resolve()),'child',folder]
                result=subprocess.run(command+[phase],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,77,result.stderr)
                durable=json.loads((root/'last.json').read_text())
                self.assertEqual(durable['state'],'running');self.assertTrue(durable['active_file_started'])
                existing=root/('source.bin' if phase=='before' else 'target.bin')
                self.assertEqual(hashlib.sha256(existing.read_bytes()).digest(),hashlib.sha256(payload).digest())
                restarted=subprocess.run(command+['restart'],capture_output=True,text=True,timeout=15,check=True)
                report=json.loads(restarted.stdout)
                self.assertEqual(report['state'],'error');self.assertTrue(report['requires_inspection'])
                self.assertEqual(report['moved_files'],0)
                self.assertEqual(hashlib.sha256(existing.read_bytes()).digest(),hashlib.sha256(payload).digest())
                self.assertFalse((root/'attempt').exists())

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='child':child(sys.argv[2],sys.argv[3])
    else:unittest.main()
