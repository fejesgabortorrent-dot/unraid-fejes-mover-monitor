"""Ratio ordering cannot turn protected content into eligible content."""
import unittest
from selection_policy import content_ratio, prioritize, ratio_target, plan, REQUIRED_GUARDS, batch_bytes

class RatioPriority(unittest.TestCase):
    def setUp(self):
        self.root='/mnt/user/Filmek'
        self.mounts=[dict(Type='bind',Source=self.root,Destination='/data')]
        self.torrents=[dict(content_path='/data/b',ratio=2.0),dict(content_path='/data/a',ratio=.5)]
    def test_target_met_goes_first_but_low_ratio_is_retained(self):
        files=[self.root+'/a',self.root+'/b',self.root+'/c']
        self.assertEqual(prioritize(files,self.torrents,self.mounts,1),[files[1],files[0],files[2]])
        self.assertEqual(prioritize(files,self.torrents,self.mounts,0),files)
    def test_larger_files_first_with_ratio_priority_disabled(self):
        files=[self.root+'/small',self.root+'/large',self.root+'/medium']
        sizes=dict(zip(files,[12,12*1024**3,8*1024**3]))
        self.assertEqual(prioritize(files,[],self.mounts,0,sizes=sizes),[files[1],files[2],files[0]])

    def test_ratio_group_still_precedes_size_and_unknown_content_is_retained(self):
        a,b,c=[self.root+'/'+name for name in ('a','b','c')]
        sizes={a:20*1024**3,b:10,c:30*1024**3}
        ordered=prioritize([a,b,c],self.torrents,self.mounts,1,sizes=sizes)
        self.assertEqual(ordered,[b,c,a])
        self.assertEqual(set(ordered),{a,b,c})

    def test_equal_size_ties_are_deterministic(self):
        files=[self.root+'/z',self.root+'/a']
        self.assertEqual(prioritize(files,[],self.mounts,0,sizes={k:10 for k in files}),list(reversed(files)))

    def test_missing_or_invalid_size_fails_closed(self):
        key=self.root+'/a'
        for sizes in ({},{key:-1},{key:True},{key:1.0},{key:'1'}):
            with self.assertRaises(ValueError):prioritize([key],[],self.mounts,0,sizes=sizes)

    def test_shared_file_uses_lowest_owner_ratio(self):
        self.torrents.append(dict(content_path='/data/b',ratio=.1))
        self.assertEqual(content_ratio(self.root+'/b',self.torrents,self.mounts),.1)
    def test_invalid_missing_infinite_and_boolean_values_remain_unknown(self):
        for value in [None,True,-1,float('inf'),float('nan'),'2']:
            self.assertIsNone(content_ratio(self.root+'/b',[dict(content_path='/data/b',ratio=value)],self.mounts))
    def test_invalid_target_rejected(self):
        for value in [None,True,-1,101,float('inf'),'1']:
            with self.assertRaises(ValueError):ratio_target(value)
    def test_high_ratio_does_not_release_incomplete_or_young_content(self):
        now=2_000_000_000;key=self.root+'/b'
        item=dict(path=key,regular=True,symlink=False,nlink=1,open=False,stable=True,mtime=now,first_seen=now)
        torrent=dict(content_path='/data/b',ratio=100,progress=.5,state='downloading')
        result=plan([item],[torrent],self.mounts,{k:'pass' for k in REQUIRED_GUARDS},days=7,now=now,observed_at=now,root=self.root)
        self.assertEqual(prioritize(result['candidates'],[torrent],self.mounts,1),[])

    def test_batch_choices_reject_unknown_or_unbounded_limits(self):
        for n in (16,32,64,128):self.assertEqual(batch_bytes(n),n*1024**3)
        for n in (0,-1,256,16.0,True,'32'):
            with self.assertRaises(ValueError):batch_bytes(n)

    def test_one_day_age_still_requires_cache_arrival_and_completion_age(self):
        now=2_000_000_000;key=self.root+'/b'
        item=dict(path=key,regular=True,symlink=False,nlink=1,open=False,stable=True,mtime=now-3*86400,first_seen=now-2*86400)
        torrent=dict(content_path='/data/b',ratio=2,progress=1,state='stalledUP',completion_on=now-2*86400,upspeed=0,dlspeed=0)
        def eligible(i,t):
            return plan([i],[t],self.mounts,{k:'pass' for k in REQUIRED_GUARDS},days=1,now=now,observed_at=now,root=self.root)['candidates']
        self.assertEqual(eligible(item,torrent),[key])
        self.assertEqual(eligible(dict(item,first_seen=now-3600),torrent),[])
        self.assertEqual(eligible(item,dict(torrent,completion_on=now-3600)),[])
        self.assertEqual(eligible(dict(item,open=True),torrent),[])
        self.assertEqual(eligible(item,dict(torrent,state='uploading',upspeed=1)),[])
