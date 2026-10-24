import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent))
import selective_mover as mover
from selection_policy import plan, REQUIRED_GUARDS

class SelectionSafety(unittest.TestCase):
    def setUp(self):
        self.now=2_000_000_000
        self.guards={k:'pass' for k in REQUIRED_GUARDS}
        self.root='/mnt/user/Filmek'
        self.item=dict(path=self.root+'/old.bin',regular=True,symlink=False,nlink=1,
                       open=False,stable=True,mtime=self.now-9*86400,first_seen=self.now-9*86400)
        self.torrent=dict(content_path='/data/other.bin',progress=1,state='stalledUP',
                          completion_on=self.now-10*86400,upspeed=0,dlspeed=0)
        self.mounts=[dict(Type='bind',Source=self.root,Destination='/data')]

    def select(self,item=None,torrents=None,guards=None,days=7):
        return plan([item or self.item],torrents or [self.torrent],self.mounts,
                    guards or self.guards,days=days,now=self.now,observed_at=self.now,root=self.root)

    def test_old_independent_file_selected(self):
        self.assertEqual(self.select()['candidates'],[self.item['path']])

    def test_each_global_guard_blocks(self):
        for guard in REQUIRED_GUARDS:
            with self.subTest(guard=guard):
                result=self.select(guards=dict(self.guards,**{guard:'unknown'}))
                self.assertFalse(result['candidates'])

    def test_young_mtime_or_arrival_always_excluded(self):
        for field in ('mtime','first_seen'):
            with self.subTest(field=field):
                self.assertFalse(self.select(item=dict(self.item,**{field:self.now-86400}))['candidates'])

    def test_open_unstable_symlink_and_hardlinks_excluded(self):
        for change in (dict(open=True),dict(stable=False),dict(symlink=True),dict(nlink=2),dict(regular=False)):
            self.assertFalse(self.select(item=dict(self.item,**change))['candidates'])

    def test_all_busy_or_incomplete_torrents_excluded(self):
        for change in (dict(state='downloading',progress=.5),dict(state='checkingUP'),
                       dict(state='moving'),dict(state='uploading'),dict(state='stalledDL'),dict(upspeed=1)):
            torrent=dict(self.torrent,content_path='/data/old.bin',**change)
            self.assertFalse(self.select(torrents=[torrent])['candidates'])

    def test_old_idle_completed_seed_can_be_selected(self):
        self.assertTrue(self.select(torrents=[dict(self.torrent,content_path='/data/old.bin')])['candidates'])

    def test_recent_completion_excluded(self):
        self.assertFalse(self.select(torrents=[dict(self.torrent,content_path='/data/old.bin',completion_on=self.now-86400)])['candidates'])

    def test_unrelated_download_does_not_block_independent_file(self):
        self.assertTrue(self.select(torrents=[dict(self.torrent,progress=.5,state='downloading')])['candidates'])

    def test_folder_overlap_protected(self):
        self.assertFalse(self.select(item=dict(self.item,path=self.root+'/folder/old.bin'),torrents=[dict(self.torrent,content_path='/data/folder',state='downloading',progress=.5)])['candidates'])

    def test_unknown_state_and_missing_completion_fail_closed(self):
        for change in (dict(state='error'),dict(completion_on=0),dict(completion_on=self.now+1),dict(upspeed=None)):
            self.assertEqual(self.select(torrents=[dict(self.torrent,**change)])['decision'],'unknown')

    def test_14_and_30_day_choices_not_accidentally_7(self):
        for days in (14,30): self.assertFalse(self.select(days=days)['candidates'])

class NativeSafety(unittest.TestCase):
    def test_sticky_integrity_failure_prevents_another_launch(self):
        with patch.object(mover,'read_json',return_value={'requires_inspection':True}):
            with self.assertRaises(ValueError): mover.guards()

    def test_interrupted_running_report_blocks_before_storage_access(self):
        for prior in [{'state':'running'},{'active_file_started':True}]:
            with patch.object(mover,'read_json',return_value=prior):
                with self.assertRaises(ValueError):mover.guards()

    def test_no_native_invocation_when_fresh_check_fails(self):
        with patch.object(mover,'fresh_candidate',return_value=(Path('/unused'),False)),patch.object(mover.subprocess,'run') as native:
            self.assertEqual(mover.execute_file('/unused',{},7)['state'],'skipped')
            native.assert_not_called()

    def test_existing_array_copy_never_overwritten(self):
        with patch.object(mover,'fresh_candidate',return_value=(Path('/unused'),True)),patch.object(mover,'destinations',return_value=[Path('/existing')]),patch.object(mover.subprocess,'run') as native:
            self.assertEqual(mover.execute_file('/unused',{},7)['reason'],'existing_array_copy')
            native.assert_not_called()

    def test_reject_symlink_hardlink_and_native_path_ambiguity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            good=root/'good';good.write_bytes(b'x')
            with patch.object(mover,'SOURCE',root):
                self.assertTrue(mover.valid_file(good))
                for name in ("bad'quote",'bad\nline','bad\rline'):
                    p=root/name;p.write_bytes(b'x')
                    with self.assertRaises(ValueError): mover.valid_file(p)
                link=root/'link';link.symlink_to(good)
                with self.assertRaises(ValueError): mover.valid_file(link)
                os.link(good,root/'hardlink')
                with self.assertRaises(ValueError): mover.valid_file(good)

class DispatchSafety(unittest.TestCase):
    def test_reviewed_dispatch_is_idempotent_and_restorable(self):
        from wire_mover_gate import rewrite_launcher, DISPATCH_BLOCK
        from wire_selective import prepare
        launcher=Path(__file__).resolve().parents[1]/'tests/fixtures/threshold-reviewed.sh'
        source=launcher.read_text().replace(DISPATCH_BLOCK,'',1)
        guarded=rewrite_launcher(source)
        changed=prepare(guarded)
        self.assertEqual(prepare(changed),changed)
        self.assertEqual(changed.replace(DISPATCH_BLOCK,'',1),guarded)
        self.assertEqual(rewrite_launcher(changed),changed)
        with self.assertRaises(ValueError): rewrite_launcher(changed,remove=True)
        with self.assertRaises(ValueError): prepare(guarded+'\n# unexpected drift\n')

class BatchReporting(unittest.TestCase):
    def run_batch(self,sizes,retained=False,limit=mover.MAX_BYTES,io_error=False):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            root=Path(folder)
            candidates=[f'/mnt/user/Filmek/{i:02}.bin' for i in range(len(sizes))]
            inventory={key:{'signature':[1,i,size,0,0]} for i,(key,size) in enumerate(zip(candidates,sizes))}
            writes=[]
            stack.enter_context(patch.object(mover,'LAST',root/'last.json'))
            stack.enter_context(patch.object(mover,'PID',root/'mover.pid'))
            attempt=root/'attempt';stack.enter_context(patch.object(mover,'ATTEMPT',attempt))
            stack.enter_context(patch.object(mover,'open',side_effect=lambda *a,**k:io.StringIO(),create=True))
            stack.enter_context(patch.object(mover.fcntl,'flock'))
            stack.enter_context(patch.object(mover,'read_json',return_value={}))
            stack.enter_context(patch.object(mover,'atomic_json',side_effect=lambda p,r:writes.append(json.loads(json.dumps(r)))))
            stack.enter_context(patch.object(mover,'log'))
            stack.enter_context(patch.object(mover,'collect',return_value=({'age_days':7,'max_bytes':limit,'candidates':candidates,'blockers':[],'skipped':[]},[],inventory,[],[],{})))
            stack.enter_context(patch.object(mover,'torrent_snapshot',return_value=([],[])))
            execute=stack.enter_context(patch.object(mover,'execute_file',side_effect=lambda key,*a:{'state':'skipped','reason':'native_retained_source'} if retained else {'state':'moved','bytes':inventory[key]['signature'][2],'sha256':'fixture'}))
            if io_error:execute.side_effect=BlockingIOError('fixture file I/O unavailable')
            result=mover.run()
            self.assertEqual(writes[-1],result)
            if execute.call_count:self.assertTrue(any(w.get('active_file_started') is True for w in writes))
            self.assertFalse((root/'mover.pid').exists())
            return result,execute.call_count,attempt.exists()

    def test_explicit_larger_batch_admits_large_file_but_respects_total(self):
        gib=1024**3
        result,calls,_=self.run_batch([18*gib,15*gib],limit=32*gib)
        self.assertEqual(result['moved_bytes'],18*gib)
        self.assertEqual(result['skipped'],{'batch_size_limit':1})
        self.assertEqual(calls,1)

    def test_io_contention_during_execution_is_an_inspection_error(self):
        result,calls,_=self.run_batch([1],io_error=True)
        self.assertEqual(result['state'],'error')
        self.assertTrue(result['requires_inspection'])
        self.assertEqual(calls,1)

    def test_all_oversized_files_are_counted_without_execution(self):
        result,calls,attempt=self.run_batch([mover.MAX_BYTES+1]*3)
        self.assertEqual(result['state'],'no_files_moved')
        self.assertEqual(result['skipped'],{'file_exceeds_batch_limit':3})
        self.assertEqual(calls,0);self.assertFalse(attempt)

    def test_trailing_byte_limit_skips_are_persisted(self):
        result,calls,_=self.run_batch([mover.MAX_BYTES,1,1])
        self.assertEqual(result['state'],'completed')
        self.assertEqual(result['moved_bytes'],mover.MAX_BYTES)
        self.assertEqual(result['skipped'],{'batch_size_limit':2})
        self.assertEqual(calls,1)

    def test_file_count_limit_records_every_deferred_candidate(self):
        result,calls,_=self.run_batch([1]*(mover.MAX_FILES+3))
        self.assertEqual(result['skipped'],{'batch_file_limit':3})
        self.assertEqual(calls,mover.MAX_FILES)

    def test_oversized_file_does_not_prevent_independent_small_file(self):
        result,calls,attempt=self.run_batch([mover.MAX_BYTES+1,1])
        self.assertEqual(result['moved_files'],1)
        self.assertEqual(result['skipped'],{'file_exceeds_batch_limit':1})
        self.assertEqual(calls,1);self.assertTrue(attempt)

    def test_native_retained_source_is_not_reported_as_moved(self):
        result,calls,attempt=self.run_batch([1],retained=True)
        self.assertEqual(result['state'],'no_files_moved')
        self.assertEqual(result['skipped'],{'native_retained_source':1})
        self.assertEqual(calls,1);self.assertFalse(attempt)

if __name__=='__main__': unittest.main()
