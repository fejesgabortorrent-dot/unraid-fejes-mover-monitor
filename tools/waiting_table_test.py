import unittest
from selection_policy import waiting_table,REQUIRED_GUARDS

class WaitingTable(unittest.TestCase):
    def setUp(self):
        self.now=2_000_000_000;self.root='/mnt/user/Filmek';self.key=self.root+'/example.mkv'
        self.item=dict(path=self.key,regular=True,symlink=False,nlink=1,open=False,stable=True,mtime=self.now-9*86400,first_seen=self.now-86400)
        self.inventory={self.key:{'signature':[1,2,123,0,0]}}
        self.mounts=[dict(Type='bind',Source=self.root,Destination='/data')]
        self.guards={k:'pass' for k in REQUIRED_GUARDS}
        self.torrents=[dict(content_path='/data/unrelated',progress=1,state='stalledUP',completion_on=self.now-9*86400,upspeed=0,dlspeed=0)]
    def table(self,torrents=None):
        return waiting_table([self.item],torrents or self.torrents,self.mounts,self.inventory,self.guards,days=7,now=self.now,root=self.root)
    def test_recent_arrival_overrides_old_mtime(self):
        row=self.table()['rows'][0]
        self.assertEqual(row['age_ready_at'],self.now+6*86400)
        self.assertEqual(row['reason'],'too_young')
    def test_recent_quiet_completion_sets_later_date(self):
        torrent=dict(content_path='/data/example.mkv',progress=1,state='stalledUP',completion_on=self.now,upspeed=0,dlspeed=0)
        self.assertEqual(self.table([torrent])['rows'][0]['age_ready_at'],self.now+7*86400)
    def test_incomplete_and_active_torrents_have_no_promised_date(self):
        for state,progress in [('downloading',.5),('uploading',1)]:
            row=self.table([dict(content_path='/data/example.mkv',progress=progress,state=state,completion_on=0,upspeed=1,dlspeed=1)])['rows'][0]
            self.assertIsNone(row['age_ready_at']);self.assertEqual(row['reason'],'protected_content')
    def test_open_file_has_no_promised_date(self):
        self.item['open']=True
        self.assertIsNone(self.table()['rows'][0]['age_ready_at'])
    def test_oversized_file_is_not_counted_down_to_movement(self):
        self.inventory[self.key]['signature'][2]=16*1024**3+1
        row=self.table()['rows'][0]
        self.assertIsNone(row['age_ready_at']);self.assertEqual(row['reason'],'file_exceeds_batch_limit')
    def test_global_blocker_does_not_hide_age_but_never_authorizes(self):
        self.guards['backup']='wait';table=self.table()
        self.assertEqual(table['blockers'],['backup']);self.assertFalse(table['execution_allowed'])
        self.assertIsNotNone(table['rows'][0]['age_ready_at'])
    def test_no_files_is_valid_empty_table(self):
        table=waiting_table([],self.torrents,self.mounts,{},self.guards,days=7,now=self.now,root=self.root)
        self.assertEqual(table['rows'],[]);self.assertEqual(table['total_bytes'],0)
    def test_invalid_torrent_state_does_not_publish_a_countdown(self):
        with self.assertRaises(ValueError):
            self.table([dict(content_path='/data/example.mkv',progress=1,state='unknown')])

if __name__=='__main__':unittest.main()
