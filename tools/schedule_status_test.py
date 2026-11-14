"""Read-only UI status must reflect active cron, not merely saved intent."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ScheduleStatus(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.scope=dict(pool='cache',share='Filmek',torrent_container='binhex-qbittorrentvpn')
        self.data=dict(version=1,enabled=True,scope=self.scope,threshold_gib=300,cooldown_minutes=60,interval_minutes=10)
        self.write('selective-profile.json',dict(version=1,**self.scope))
        self.write('settings.json',dict(version=1,mode='advanced',pool='cache'))
        self.cron='*/10 * * * * /usr/bin/python3 /boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py tick >/dev/null 2>&1\n'
        (self.root/'cron').write_text(self.cron)
        # Execute the real status block without unrelated dashboard rendering.
        source=(ROOT/'src/FejesMoverRuntime.php').read_text()
        source=source.split('    // A saved preference is not proof',1)[1].split('    $token =',1)[0]
        source='    // A saved preference is not proof'+source
        source=source.replace("'/boot/config/plugins/fejes.mover.monitor/automation.json'",json.dumps(str(self.root/'automation.json')))
        source=source.replace("'/boot/config/plugins/fejes.mover.monitor/selective-profile.json'",json.dumps(str(self.root/'selective-profile.json')))
        source=source.replace("'/etc/cron.d/root'",json.dumps(str(self.root/'cron')))
        self.source=source
    def write(self,name,data): (self.root/name).write_text(json.dumps(data))
    def status(self,mode='advanced'):
        prefix='<?php $mode='+json.dumps(mode)+";$pool='cache';"
        result=subprocess.run(['php'],input=prefix+self.source+'echo json_encode($schedule);',text=True,capture_output=True,check=True)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)
    def test_valid_active_interval(self):
        self.write('automation.json',self.data)
        self.assertEqual(self.status(),dict(source='managed',state='scheduled',interval=10))
    def test_saved_configuration_without_active_cron_is_unknown(self):
        self.write('automation.json',self.data);(self.root/'cron').write_text('')
        self.assertEqual(self.status()['state'],'unknown')
    def test_duplicate_or_wrong_interval_not_reported_active(self):
        self.write('automation.json',self.data)
        for cron in [self.cron*2,self.cron.replace('*/10','*/15'),'# '+self.cron]:
            (self.root/'cron').write_text(cron)
            self.assertEqual(self.status()['state'],'unknown')
    def test_disabled_with_stale_cron_still_disabled(self):
        self.data['enabled']=False;self.write('automation.json',self.data)
        self.assertEqual(self.status()['state'],'disabled')
    def test_missing_config_preserves_legacy_display(self):
        self.assertEqual(self.status()['source'],'legacy')
    def test_invalid_or_changed_scope_not_active(self):
        for data in [dict(self.data,version=True),dict(self.data,scope=dict(self.scope,share='Other')),dict(self.data,threshold_gib=0)]:
            self.write('automation.json',data);self.assertEqual(self.status()['state'],'unknown')
    def test_observer_never_reports_enabled_schedule(self):
        self.write('automation.json',self.data)
        self.assertEqual(self.status('observer')['state'],'unknown')
    def test_demo_does_not_read_live_configuration(self):
        self.write('automation.json',self.data)
        self.assertEqual(self.status('demo')['source'],'legacy')
    def test_broken_symlink_is_not_legacy(self):
        (self.root/'automation.json').symlink_to(self.root/'missing')
        self.assertEqual(self.status()['source'],'managed')
        self.assertEqual(self.status()['state'],'unknown')

if __name__=='__main__':unittest.main()
