from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import stat,unittest
import selective_mover as mover
from selection_policy import plan

class IntegrityMaintenance(unittest.TestCase):
 def check(self,owned=False,scanning=True,wired=True):
  commands=[b'/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/watcher\0disk1\0',b'/usr/bin/inotifywait\0/var/run/hash.pipe.disk1\0/mnt/disk1\0']
  if scanning:commands.append(b'/bin/bash\0/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/bunker\0-Vqj\0')
  entries=[SimpleNamespace(read_bytes=lambda command=command:command) for command in commands]
  def content(path,*args,**kwargs):
   if str(path).endswith('/Filmek.cfg'):return 'shareUseCache="yes"\nshareCachePool="cache"\nshareCachePool2=""\n'
   if str(path).endswith('/share.cfg'):return 'shareUserEmptying=""\n'
   return 'UJRA_PROBALKOZAS_MP=360\n'
  def read(path,default):return {'version':1,'mode':'advanced','pool':'cache'} if str(path).endswith('/settings.json') else {}
  report={'dry_run':{'checks':[{'key':k,'state':'pass'} for k in ('backup','parity','mover','cooldown','capacity','launcher')]},'integrity_config':'wired' if wired else 'unknown','integrity_active':'wired' if wired else 'unknown'}
  with ExitStack() as stack:
   for obj,key,value in [(mover,'read_json',read),(mover,'array_disks',lambda:[Path('/mnt/disk1')]),(mover,'dry_run',lambda:report),(mover.os.path,'ismount',lambda p:True),(Path,'is_symlink',lambda p:False),(Path,'is_dir',lambda p:True),(Path,'exists',lambda p:False),(Path,'read_text',content),(Path,'glob',lambda *a:entries),(Path,'lstat',lambda p:SimpleNamespace(st_mode=stat.S_IFIFO))]:stack.enter_context(patch.object(obj,key,value))
   stack.enter_context(patch.object(mover.subprocess,'check_output',side_effect=lambda cmd,**kw:'Status: finished\nno errors found\n' if 'scrub' in cmd else '[fixture].read_io_errs 0\n'))
   return mover.guards(owned)
 def test_active_scan_is_a_prelaunch_wait(self):
  guards=self.check();self.assertEqual(guards['integrity'],'wait')
  selection=plan([],[],[],guards,days=1,now=1000000,observed_at=1000000,root='/mnt/user/Filmek')
  self.assertIn('integrity',selection['blockers']);self.assertFalse(selection['candidates'])
 def test_scan_during_owned_execution_still_aborts(self):
  with self.assertRaisesRegex(ValueError,'Integrity hashing active'):self.check(owned=True)
 def test_finished_scan_can_pass_with_verified_wiring(self):self.assertEqual(self.check(scanning=False)['integrity'],'pass')
 def test_unknown_wiring_is_not_promoted_to_wait_or_pass(self):self.assertEqual(self.check(wired=False)['integrity'],'unknown')

if __name__=='__main__':unittest.main()
