import copy
import unittest
from selective_plan import build_plan, pressure_policy

MOUNTS = [{'Type':'bind','Destination':'/data','Source':'/mnt/user/Filmek'}]


def torrent(digest, name, state='stalledUP', progress=1):
    return {'hash':digest*40, 'save_path':'/data', 'content_path':'/data/'+name,
            'state':state, 'progress':progress}


def candidate(name, **extra):
    return dict(path=name, regular=True, symlink=False, nlink=1, **extra)


class SelectivePlanTest(unittest.TestCase):
    def setUp(self):
        self.torrents=[torrent('a','ready.bin'),torrent('b','busy.bin','stalledDL',.9995)]
        self.files={'a'*40:[{'name':'ready.bin'}], 'b'*40:[{'name':'busy.bin'}]}
        self.candidates=[candidate('ready.bin'),candidate('busy.bin'),candidate('ordinary.bin')]

    def plan(self, **kw):
        return build_plan(kw.get('torrents',self.torrents),kw.get('mounts',MOUNTS),
                          kw.get('files',self.files),kw.get('candidates',self.candidates))

    def test_busy_does_not_block_completed_or_unrelated_files(self):
        report=self.plan()
        self.assertEqual([e['decision'] for e in report['entries']],['candidate','skip','candidate'])
        self.assertEqual(report['candidate_count'],2)
        self.assertFalse(report['live_acceptance'])

    def test_checking_moving_and_stopped_partial_protect_all_owned_files(self):
        for state,progress in [('checkingUP',1),('moving',1),('stoppedDL',.1)]:
            with self.subTest(state=state):
                self.torrents[1].update(state=state,progress=progress)
                self.files['b'*40]=[{'name':'busy.bin'},{'name':'shared.bin'}]
                report=self.plan(candidates=[candidate('busy.bin'),candidate('shared.bin'),candidate('shared.bin.!qB')])
                self.assertEqual(report['skipped_count'],3)

    def test_shared_payload_stays_protected_even_if_another_torrent_is_complete(self):
        self.files['a'*40]=[{'name':'busy.bin'}]
        self.assertEqual(self.plan()['entries'][1]['decision'],'skip')

    def test_missing_empty_unknown_or_invalid_snapshot_fails_closed(self):
        for torrents in (None,[],[{}],[torrent('a','ready.bin','futureState')]):
            with self.assertRaises(ValueError):self.plan(torrents=torrents)
        with self.assertRaises(ValueError):self.plan(files={})
        with self.assertRaises(ValueError):self.plan(mounts=[])
        with self.assertRaises(ValueError):self.plan(torrents=self.torrents*2)

    def test_newline_traversal_and_ambiguous_mounts_rejected(self):
        for name in ('../escape','bad\nfile','bad\rfile','/absolute','bad\0file'):
            with self.subTest(name=name):
                files=copy.deepcopy(self.files);files['b'*40]=[{'name':name}]
                with self.assertRaises(ValueError):self.plan(files=files)
                with self.assertRaises(ValueError):self.plan(candidates=[candidate(name)])
        mounts=MOUNTS+[{'Type':'bind','Destination':'/data/busy.bin','Source':'/mnt/user/Other'}]
        with self.assertRaises(ValueError):self.plan(mounts=mounts)

    def test_siblings_are_not_matched_by_prefix_or_glob(self):
        self.files['b'*40]=[{'name':'Show [1]/episode.mkv'}]
        report=self.plan(candidates=[candidate('Show [1]/episode.mkv'),candidate('Show 1/episode.mkv'),candidate('Show [1]/episode.mkv.extra')])
        self.assertEqual([e['decision'] for e in report['entries']],['skip','candidate','candidate'])

    def test_symlinks_directories_and_unreviewed_hardlinks_not_submitted(self):
        entries=[candidate('link'),candidate('directory'),candidate('hardlink')]
        entries[0]['symlink']=True;entries[1]['regular']=False;entries[2]['nlink']=2
        self.assertEqual(self.plan(candidates=entries)['skipped_count'],3)

    def test_low_space_alert_does_not_implicitly_pause_anything(self):
        self.assertEqual(pressure_policy(10,20),{'alert':True,'pause_requested':False,'automatic_action_performed':False})
        self.assertTrue(pressure_policy(10,20,pause_downloads=True)['pause_requested'])
        self.assertFalse(pressure_policy(20,20,pause_downloads=True)['alert'])
        with self.assertRaises(ValueError):pressure_policy(True,20)
        with self.assertRaises(ValueError):pressure_policy(10,20,pause_downloads='false')


if __name__=='__main__':unittest.main()
