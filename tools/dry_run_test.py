import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fejes_service as service


class DryRunTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.source=Path(__file__).resolve().parents[1]/'tests/fixtures/threshold-reviewed.sh'
        (self.root/'script').write_bytes(self.source.read_bytes())
        (self.root/'mdstat').write_text('mdResync=0\n')
        for name,file in [('LAUNCHER','script'),('BACKUP_MARKER','backup'),('MDSTAT','mdstat'),('ATTEMPT','stamp'),('MOVER_PID','mover.pid'),('SHARE','share')]:
            p=patch.object(service,name,self.root/file);p.start();self.addCleanup(p.stop)
        (self.root/'share').mkdir()
        self.snapshot={'cache':'available','cache_free_bytes':100*1024**3,'torrent':'no_torrent_blocker','blocking_torrents':0}

    def run_preview(self):
        before={str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        with patch.object(service,'status',return_value=self.snapshot.copy()), patch.object(service.subprocess,'run') as execute:
            report=service.dry_run()
            execute.assert_not_called()
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        self.assertNotIn(str(self.root),json.dumps(report))
        return report['dry_run']

    def test_ready_does_not_execute_or_write(self):
        report=self.run_preview()
        self.assertEqual(report['decision'],'ready')
        self.assertEqual(len(report['checks']),7)
        self.assertTrue(report['read_only'])

    def test_multiple_reasons_remain_visible(self):
        self.snapshot.update(cache_free_bytes=400*1024**3,torrent='defer',blocking_torrents=2)
        (self.root/'mdstat').write_text('mdResync=1\n')
        (self.root/'mover.pid').write_text('123')
        with patch.object(service.time,'time',return_value=10000):
            (self.root/'stamp').write_text('9999')
            report=self.run_preview()
        self.assertEqual(report['decision'],'wait')
        self.assertEqual({c['key'] for c in report['checks'] if c['state']=='wait'}, {'capacity','torrent','parity','mover','cooldown'})

    def test_unknown_parity_and_launcher_fail_closed(self):
        (self.root/'mdstat').write_text('unreadable format')
        (self.root/'script').write_text('# unexpected script')
        self.assertEqual(self.run_preview()['decision'],'unknown')

    def test_zero_capacity_and_busy_backup(self):
        self.snapshot['cache_free_bytes']=0
        (self.root/'backup').write_text('1234')
        with patch.object(service.os,'kill'):
            report=self.run_preview()
        states={c['key']:c['state'] for c in report['checks']}
        self.assertEqual(states['capacity'],'pass')
        self.assertEqual(states['backup'],'wait')

    def test_unavailable_torrent_and_bad_timestamp_never_ready(self):
        self.snapshot['torrent']='unavailable'
        (self.root/'stamp').write_text('invalid')
        self.assertEqual(self.run_preview()['decision'],'unknown')

    def test_missing_required_share_is_not_ready(self):
        (self.root/'share').rmdir()
        self.assertEqual(self.run_preview()['decision'],'unknown')

    def test_private_names_are_opt_in_and_never_include_paths(self):
        torrents=[{'state':'downloading','progress':.5,'content_path':'/data/example.mkv','amount_left':20}]
        mounts=[{'Type':'bind','Destination':'/data','Source':'/mnt/user/private-parent'}]
        with patch.object(service,'read_snapshot',return_value=(torrents,mounts)),patch.object(service.os.path,'ismount',return_value=False):
            public=service.status()
            private=service.status(include_items=True)
        self.assertNotIn('example.mkv',json.dumps(public))
        self.assertEqual(private['protected_items'][0]['name'],'example.mkv')
        self.assertNotIn('/mnt/user/private-parent',json.dumps(private))


if __name__=='__main__':unittest.main()
