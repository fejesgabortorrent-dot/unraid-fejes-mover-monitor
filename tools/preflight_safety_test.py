"""Failures on either side of the durable native boundary, with fixture I/O only."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from test_support import install
install()
from unittest.mock import patch
import selective_mover as mover


def api_error():
    return subprocess.CalledProcessError(1, ['docker','exec','binhex-qbittorrentvpn',
        'curl','--fail','http://127.0.0.1:8080/api/v2/torrents/info'])


class PreflightBoundary(unittest.TestCase):
    def batch(self, error, native=False, prior=None, first_moved=False, prior_error=None):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root=Path(folder);key='/mnt/user/Filmek/fixture'
            keys=[key+'/1',key+'/2'] if first_moved else [key]
            saved=[];calls=[]
            for name,value in [('LAST',root/'last.json'),('PID',root/'pid'),('ATTEMPT',root/'attempt')]:
                stack.enter_context(patch.object(mover,name,value))
            stack.enter_context(patch.object(mover,'open',side_effect=lambda *a,**k:io.StringIO(),create=True))
            stack.enter_context(patch.object(mover.fcntl,'flock'))
            stack.enter_context(patch.object(mover,'read_json',return_value=prior or {},side_effect=prior_error))
            stack.enter_context(patch.object(mover,'atomic_json',side_effect=lambda p,r:saved.append(json.loads(json.dumps(r)))))
            stack.enter_context(patch.object(mover,'log'))
            stack.enter_context(patch.object(mover,'collect',return_value=(
                dict(age_days=7,candidates=keys,blockers=[],skipped=[]),[],
                {k:{'signature':[1,2,100,4,5]} for k in keys},[],[],{})))
            def execute(key,expected,days,before_native):
                calls.append(key)
                if first_moved and len(calls)==1:
                    before_native();return dict(state='moved',bytes=100,sha256='fixture')
                if native:before_native()
                raise error
            stack.enter_context(patch.object(mover,'execute_file',side_effect=execute))
            result=mover.run()
            self.assertFalse((root/'pid').exists())
            if prior and mover.needs_inspection(prior):
                self.assertFalse((root/'selective-error.log').exists())
            return result,saved,calls

    def test_api_and_integrity_before_native_defer_without_latch(self):
        for error in (api_error(),mover.IntegrityHashingActive('Integrity hashing active')):
            with self.subTest(error=type(error).__name__):
                result,saved,calls=self.batch(error)
                self.assertEqual(result['state'],'deferred')
                self.assertFalse(result['requires_inspection'])
                self.assertFalse(any(r.get('active_file_started') for r in saved))
                self.assertEqual(len(calls),1)

    def test_unknown_preflight_error_stops_without_false_native_latch(self):
        result,_,_=self.batch(ValueError('Source changed'))
        self.assertEqual(result['state'],'error');self.assertFalse(result['requires_inspection'])

    def test_any_native_failure_or_unverified_postcheck_is_sticky(self):
        for error in (api_error(),mover.NativeMoveError(1,'fixture'),RuntimeError('Checksum mismatch'),BlockingIOError('I/O')):
            result,saved,_=self.batch(error,native=True)
            self.assertEqual(result['state'],'error');self.assertTrue(result['requires_inspection'])
            self.assertTrue(any(r.get('active_file_started') for r in saved))

    def test_failure_after_prior_verified_file_stays_conservative(self):
        result,_,calls=self.batch(api_error(),first_moved=True)
        self.assertEqual(result['moved_files'],1);self.assertTrue(result['requires_inspection'])
        self.assertEqual(len(calls),2)

    def test_existing_latch_and_legacy_running_never_clear(self):
        for prior in ({'requires_inspection':True},{'version':1,'state':'running'},
                      {'active_file_started':True}):
            result,saved,calls=self.batch(api_error(),prior=prior)
            self.assertTrue(result['requires_inspection']);self.assertEqual(calls,[])
            self.assertEqual(saved,[])

    def test_unreadable_prior_report_cannot_turn_into_an_unlocked_error(self):
        for error in (ValueError('corrupt JSON'),OSError('read unavailable')):
            result,saved,calls=self.batch(api_error(),prior_error=error)
            self.assertTrue(result['requires_inspection']);self.assertEqual(calls,[])
            self.assertEqual(saved,[])

    def test_only_explicit_zero_operation_v2_preflight_is_restartable(self):
        prior=dict(version=2,state='running',stage='file_preflight',
                   active_file_started=False,moved_files=0,moved_bytes=0)
        self.assertFalse(mover.needs_inspection(prior))
        for change in (dict(version=1),dict(stage='native_move_or_verification'),
                       dict(active_file_started=True),dict(moved_files=1),
                       dict(moved_bytes=100),dict(requires_inspection=True),
                       dict(moved_files=False),dict(moved_bytes=False)):
            self.assertTrue(mover.needs_inspection(dict(prior,**change)))
        for malformed in ([],{'state':'unknown'},{'stage':'file_preflight'}):
            self.assertTrue(mover.needs_inspection(malformed))

    def test_real_executor_boundary_follows_both_fresh_checks_and_fuser(self):
        events=[];path=SimpleNamespace(stat=lambda:'stat')
        with ExitStack() as stack:
            stack.enter_context(patch.object(mover,'fresh_candidate',side_effect=lambda *a:(events.append('fresh') or path,True)))
            stack.enter_context(patch.object(mover,'destinations',return_value=[]))
            stack.enter_context(patch.object(mover,'valid_file',return_value='stat'))
            stack.enter_context(patch.object(mover,'signature',return_value=[1]))
            stack.enter_context(patch.object(mover.os,'listxattr',return_value=[]))
            stack.enter_context(patch.object(mover,'sha256',return_value='hash'))
            def command(cmd,**kwargs):
                if cmd[0]=='fuser':events.append('fuser');return SimpleNamespace(returncode=1)
                events.append('native');raise mover.NativeMoveError(1,'fixture')
            stack.enter_context(patch.object(mover.subprocess,'run',side_effect=command))
            with self.assertRaises(mover.NativeMoveError):
                mover.execute_file('fixture',{},7,lambda:events.append('durable'))
            self.assertEqual(events,['fresh','fresh','fuser','durable','native'])
            events.clear()
            def failed_save():events.append('save_failed');raise OSError('fsync failed')
            with self.assertRaises(OSError):mover.execute_file('fixture',{},7,failed_save)
            self.assertNotIn('native',events)
            for failed_call in (1,2):
                events.clear();fresh_calls=[]
                def fresh(*args):
                    fresh_calls.append(1)
                    if len(fresh_calls)==failed_call:raise api_error()
                    return path,True
                with patch.object(mover,'fresh_candidate',side_effect=fresh):
                    with self.assertRaises(subprocess.CalledProcessError):
                        mover.execute_file('fixture',{},7,lambda:events.append('durable'))
                self.assertNotIn('durable',events);self.assertNotIn('native',events)

    def test_retained_source_cannot_hide_partial_destination_or_symlink(self):
        for has_target,symlink in ((False,False),(True,False),(False,True)):
            with self.subTest(target=has_target,symlink=symlink),ExitStack() as stack:
                info=SimpleNamespace(st_dev=1,st_ino=2,st_size=3,st_mtime_ns=4,st_ctime_ns=5)
                path=SimpleNamespace(stat=lambda:info,exists=lambda:True,is_symlink=lambda:symlink)
                stack.enter_context(patch.object(mover,'fresh_candidate',return_value=(path,True)))
                stack.enter_context(patch.object(mover,'valid_file',return_value=info))
                stack.enter_context(patch.object(mover,'destinations',side_effect=[[],[],[Path('/fixture-target')] if has_target else []]))
                stack.enter_context(patch.object(mover.os,'listxattr',return_value=[]))
                stack.enter_context(patch.object(mover,'sha256',return_value='fixture-hash'))
                stack.enter_context(patch.object(mover.subprocess,'run',side_effect=[SimpleNamespace(returncode=1),SimpleNamespace(returncode=0)]))
                intent=stack.enter_context(patch.object(mover,'log'))
                if has_target or symlink:
                    with self.assertRaises(RuntimeError):mover.execute_file('fixture',{},7,intent)
                else:
                    self.assertEqual(mover.execute_file('fixture',{},7,intent)['reason'],'native_retained_source')
                intent.assert_called_once_with()


if __name__=='__main__':unittest.main()
