import unittest
from selection_policy import plan, waiting_table, REQUIRED_GUARDS

class DirectoryExclusion(unittest.TestCase):
    def test_exclusion_is_bounded_to_exact_top_level_directory(self):
        root='/mnt/user/Media'; now=2000000000
        names=['EMBY/cache/a.jpg','EMBY','EMBY-backup/a.jpg','Movie/EMBY/a.jpg','movie.mkv']
        files=[dict(path=root+'/'+n,regular=True,symlink=False,nlink=1,open=False,stable=True,mtime=now-10*86400,first_seen=now-10*86400) for n in names]
        guards={k:'pass' for k in REQUIRED_GUARDS}
        mounts=[dict(Type='bind',Source=root,Destination='/data')]
        torrents=[dict(content_path='/data/unrelated',progress=1,state='stalledUP',completion_on=now-10*86400,upspeed=0,dlspeed=0)]
        result=plan(files,torrents,mounts,guards,days=1,now=now,observed_at=now,root=root)
        self.assertEqual(result['candidates'],[root+'/'+n for n in names[2:]])
        self.assertEqual([x['reason'] for x in result['skipped']],['excluded_directory']*2)
        inventory={x['path']:{'signature':[1,2,10,0,0]} for x in files}
        rows=waiting_table(files,torrents,mounts,inventory,guards,days=1,now=now,root=root)['rows']
        excluded=[x for x in rows if x['reason']=='excluded_directory']
        self.assertEqual(len(excluded),2)
        self.assertTrue(all(x['age_ready_at'] is None for x in excluded))
