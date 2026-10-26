import json,tempfile,unittest
from pathlib import Path
from browser_demo import Demo

class DashboardSummary(unittest.TestCase):
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
