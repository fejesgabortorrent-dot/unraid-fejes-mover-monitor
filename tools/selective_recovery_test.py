#!/usr/bin/env python3
"""Regression tests for explicit, fail-closed inspection recovery."""
import copy
import json
import unittest
from unittest.mock import patch
from test_support import install
install()
import selective_recovery as recovery


def prior(**overrides):
    row={'source':'/mnt/user/Filmek/movie.mkv',
         'destination':'/mnt/disk4/Filmek/movie.mkv',
         'sha256':'a'*64,'bytes':100,'source_signature':[1,2,100,3,4]}
    payload={'version':2,'state':'error','requires_inspection':True,
             'active_file_started':False,'stage':'file_preflight',
             'error_code':'required_state_unverified','moved_files':1,
             'moved_bytes':100,'verified_files':[row],
             'scope':f'{recovery.mover.PROFILE.pool}/{recovery.mover.PROFILE.share} -> Array; selected files only'}
    payload.update(overrides)
    return payload


class RecoveryPolicy(unittest.TestCase):
    def test_exact_pre_native_ledger_is_eligible(self):
        self.assertEqual(len(recovery.validate_report(prior())),1)

    def test_native_intent_never_recovers(self):
        for fields in (dict(active_file_started=True),dict(active_sha256='a'*64),
                       dict(stage='native_move_or_verification'),
                       dict(state='running'),dict(requires_inspection=False)):
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                recovery.validate_report(prior(**fields))

    def test_incomplete_or_incorrect_evidence_rejected(self):
        for fields in (dict(verified_files=[]),dict(moved_bytes=99),
                       dict(moved_files=True),dict(version=1),
                       dict(error_code='torrent_snapshot_unavailable'),
                       dict(scope='other'),dict(verified_files=[{
                           'source':'/mnt/user/Filmek/movie.mkv','destination':'/mnt/disk3/Other/movie.mkv',
                           'bytes':100,'sha256':'a'*64,'source_signature':[1,2,100,3,4]}])):
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                recovery.validate_report(prior(**fields))

    def test_ambiguous_source_or_signature_rejected(self):
        data=prior()
        for row in [dict(data['verified_files'][0],source='/mnt/cache/Filmek/movie.mkv'),
                    dict(data['verified_files'][0],source_signature=[1,2,99,3,4]),
                    dict(data['verified_files'][0],sha256='bad')]:
            with self.subTest(row=row),self.assertRaises(ValueError):
                recovery.validate_report(prior(verified_files=[row]))


class RecoveryDispatch(unittest.TestCase):
    def setUp(self):
        self.payload=prior()
        self.checks={'checked_destinations':1,'matched_torrents':1,
                     'verified_torrent_files':2,'torrent_membership_stable':True}
        self.digest='b'*64
        self.raw=b'original-report'
        self.patcher=patch.object(recovery,'inspect_locked',return_value=(
            self.raw,self.digest,self.payload,self.checks))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.open_patch=patch('builtins.open')
        self.open_patch.start()
        self.addCleanup(self.open_patch.stop)
        self.lock_patch=patch.object(recovery.fcntl,'flock')
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)

    def test_inspect_does_not_back_up_or_unlock(self):
        with patch.object(recovery,'backup_locked') as backup,patch.object(recovery.mover,'atomic_json') as write:
            out=recovery.run('inspect')
            self.assertTrue(out['eligible'])
            self.assertEqual(out['report_sha256'],self.digest)
            backup.assert_not_called()
            write.assert_not_called()

    def test_recover_requires_exact_approval(self):
        with patch.object(recovery,'backup_locked') as backup,patch.object(recovery.mover,'atomic_json') as write:
            for approval,confirm in [(None,None),('wrong',recovery.CONFIRM),
                                      (self.digest,None)]:
                with self.assertRaises(ValueError):
                    recovery.run('recover',approval,confirm)
            backup.assert_not_called()
            write.assert_not_called()

    def test_recover_preserves_evidence_and_never_moves_media(self):
        from pathlib import Path
        writes=[]
        def save(path,data):writes.append((path,copy.deepcopy(data)))
        with patch.object(recovery,'backup_locked',return_value=Path('/mnt/disk5/saved.json')) as backup,\
             patch.object(recovery.mover,'atomic_json',side_effect=save),\
             patch.object(recovery.mover,'read_json',return_value=prior(state='deferred',requires_inspection=False)),\
             patch.object(recovery.hashlib,'sha256') as digest:
            digest.return_value.hexdigest.return_value=self.digest
            out=recovery.run('recover',self.digest,recovery.CONFIRM)
        self.assertTrue(out['recovered'])
        backup.assert_called_once()
        self.assertEqual(len(writes),2)
        record=writes[1][1]
        self.assertFalse(record['requires_inspection'])
        self.assertEqual(record['verified_files'],self.payload['verified_files'])
        self.assertEqual(record['moved_files'],1)
        self.assertEqual(record['recovery']['historical_torrent_continuity'],'not_available')

    def test_changed_evidence_cannot_unlock(self):
        with patch.object(recovery,'inspect_locked',side_effect=[
            (self.raw,self.digest,self.payload,self.checks),
            (self.raw,'c'*64,self.payload,self.checks)]),\
             patch.object(recovery,'backup_locked') as backup:
            with self.assertRaises(ValueError):
                recovery.run('recover',self.digest,recovery.CONFIRM)
            backup.assert_not_called()


if __name__=='__main__':
    unittest.main()
