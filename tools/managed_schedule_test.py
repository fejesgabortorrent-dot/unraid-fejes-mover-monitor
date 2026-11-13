import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import managed_schedule as scheduler
from selective_profile import DEFAULT

class ManagedSchedule(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'automation.json'
        self.data=dict(version=1,enabled=True,scope=dict(pool='cache',share='Filmek',torrent_container='binhex-qbittorrentvpn'),threshold_gib=300,cooldown_minutes=60,interval_minutes=15)
    def load(self):
        self.path.write_text(json.dumps(self.data))
        return scheduler.load(self.path,DEFAULT)
    def test_absent_config_never_creates_schedule(self):
        self.assertIsNone(scheduler.load(self.path,DEFAULT))
        self.assertEqual(scheduler.cron_text(None),'')
    def test_disabled_config_has_no_cron(self):
        self.data['enabled']=False
        self.assertEqual(scheduler.cron_text(self.load()),'')
    def test_valid_schedule_contains_only_fixed_command(self):
        self.assertEqual(scheduler.cron_text(self.load()),'*/15 * * * * /usr/bin/python3 /boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py tick >/dev/null 2>&1\n')
    def test_managed_threshold_does_not_require_legacy_script(self):
        import fejes_service as service
        with patch.object(service,'load_automation',return_value=self.data),patch.object(service,'SHARE',self.path.parent),patch.object(service,'LAUNCHER',self.path.parent/'no-user-script'),patch.object(service,'status',return_value={'cache':'available','cache_free_bytes':100*1024**3,'torrent':'no_torrent_blocker'}):
            checks={c['key']:c for c in service.dry_run()['dry_run']['checks']}
        self.assertEqual(checks['launcher']['state'],'pass')
        self.assertEqual(checks['capacity']['state'],'pass')
        self.assertEqual(checks['capacity']['detail']['threshold_gib'],300)

    def test_scope_drift_rejected(self):
        self.data['scope']['share']='Other'
        with self.assertRaises(ValueError):self.load()
    def test_invalid_types_and_ranges_rejected(self):
        for field,value in [('version',True),('enabled',1),('threshold_gib',0),('threshold_gib',True),('cooldown_minutes',0),('interval_minutes','15; reboot'),('interval_minutes',60)]:
            with self.subTest(field=field,value=value):
                original=self.data[field];self.data[field]=value
                with self.assertRaises(ValueError):self.load()
                self.data[field]=original
    def test_broken_symlink_is_not_missing_configuration(self):
        self.path.symlink_to(self.path.parent/'missing')
        with self.assertRaises(ValueError):scheduler.load(self.path,DEFAULT)
    def test_disabled_tick_never_enters_executor(self):
        self.data['enabled']=False
        with patch.object(scheduler,'load',return_value=self.data),patch('selective_mover.run') as run:
            self.assertEqual(scheduler.tick()['state'],'deferred');run.assert_not_called()
    def test_removed_plugin_never_enters_executor(self):
        with patch.object(scheduler,'load',return_value=self.data),patch.object(scheduler,'RUNTIME',self.path.parent/'missing'),patch('selective_mover.run') as run:
            self.assertEqual(scheduler.tick()['state'],'deferred');run.assert_not_called()
    def test_enabled_tick_uses_existing_guarded_executor(self):
        self.path.touch()
        with patch.object(scheduler,'load',return_value=self.data),patch.object(scheduler,'RUNTIME',self.path),patch('selective_mover.run',return_value={'state':'deferred','blockers':['parity']}) as run:
            self.assertEqual(scheduler.tick()['blockers'],['parity']);run.assert_called_once_with()

if __name__=='__main__':unittest.main()
