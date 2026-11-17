import json,tempfile,unittest
from pathlib import Path
from browser_demo import Demo

class DashboardSummary(unittest.TestCase):
 def test_live_owned_seed_worker_is_running_but_stale_or_unrelated_pid_keeps_latch_visible(self):
  with tempfile.TemporaryDirectory() as folder:
   lab=Path(folder);demo=Demo(lab)
   (lab/'config/settings.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
   report={'version':2,'state':'native_intent','stage':'completed_seed_coordination',
           'requires_inspection':True,'coordination_pid':4242}
   original=json.dumps(report);(lab/'config/selective-last.json').write_text(original)
   (lab/'proc/4242/cmdline').write_bytes(b'python3\0/boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py\0tick\0')
   html=demo.render('FejesMover.Dashboard.page','running','en',None)
   self.assertIn('Checks or movement in progress',html)
   self.assertNotIn('Inspection required',html)
   self.assertEqual((lab/'config/selective-last.json').read_text(),original)
   self.assertIn('Inspection required',demo.render('FejesMover.Dashboard.page','stale','en',None))
   (lab/'proc/4242/cmdline').write_bytes(b'cat\0/boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py\0')
   self.assertIn('Inspection required',demo.render('FejesMover.Dashboard.page','running','en',None))

 def test_completed_report_and_private_details_are_not_leaked(self):
  with tempfile.TemporaryDirectory() as folder:
   lab=Path(folder);demo=Demo(lab)
   (lab/'config/settings.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
   report={'state':'completed','started':1700000000,'moved_files':2,'moved_bytes':2147483648,'error':'PRIVATE_FILE_SENTINEL'}
   (lab/'config/selective-last.json').write_text(json.dumps(report))
   for lang in ('hu','en','de'):
    rendered=demo.render('FejesMover.Dashboard.page','idle',lang,None)
    self.assertIn('2.00 GiB',rendered)
    self.assertNotIn('PRIVATE_FILE_SENTINEL',rendered)
    self.assertIn('fm-hover-help',rendered)
    self.assertIn('/Tools/FejesMoverSelective',rendered)

 def test_inspection_error_is_visible_without_claiming_transfer(self):
  with tempfile.TemporaryDirectory() as folder:
   lab=Path(folder);demo=Demo(lab)
   (lab/'config/settings.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
   (lab/'config/selective-last.json').write_text('{"state":"error","requires_inspection":true,"moved_files":1,"moved_bytes":123}')
   rendered=demo.render('FejesMover.Dashboard.page','idle','en',None)
   self.assertIn('Inspection required',rendered)
   self.assertNotIn('files verified',rendered)

 def test_observer_has_no_selective_live_report(self):
  with tempfile.TemporaryDirectory() as folder:
   lab=Path(folder);demo=Demo(lab)
   (lab/'config/settings.json').write_text('{"version":1,"mode":"observer","pool":"cache"}')
   rendered=demo.render('FejesMover.Dashboard.page','idle','en',None)
   self.assertNotIn('Completed, files verified',rendered)

 def test_torrent_failure_is_explained_without_private_error_text(self):
  with tempfile.TemporaryDirectory() as folder:
   lab=Path(folder);demo=Demo(lab)
   (lab/'config/settings.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
   (lab/'config/selective-last.json').write_text(json.dumps({'state':'error','error_code':'torrent_snapshot_unavailable','error':'PRIVATE_COMMAND_SENTINEL','requires_inspection':False}))
   for lang,expected in [('hu','A torrentállapot nem kérdezhető le'),('en','Torrent state could not be queried'),('de','Torrentstatus konnte nicht abgefragt werden')]:
    rendered=demo.render('FejesMover.Dashboard.page','idle',lang,None)
    self.assertIn(expected,rendered)
    self.assertNotIn('PRIVATE_COMMAND_SENTINEL',rendered)

 def test_named_unraid_palettes_have_readable_translated_labels(self):
  with tempfile.TemporaryDirectory() as folder:
   demo=Demo(Path(folder))
   for lang,label in [('hu','Unraid · Fekete'),('en','Unraid · Black'),('de','Unraid · Schwarz')]:
    rendered=demo.render('FejesMover.Dashboard.page','idle',lang,None)
    self.assertIn(label,rendered)
    for value in ('white','black','gray','azure'):
     self.assertIn('value="'+value+'"',rendered)
