import unittest
from hot_seed_policy import plan
from selection_policy import REQUIRED_GUARDS

class HotSeedPolicy(unittest.TestCase):
    def setUp(self):
        self.now=2_000_000_000;self.gib=1024**3
        self.file=dict(path='/mnt/user/Filmek/movie.mkv',bytes=8*self.gib,location='array',copies=1,regular=True,stable=True,all_owners_complete=True,user_share_binding=True,nlink=1,symlink=False,open=False,quiet=True,last_move_at=self.now-2*86400,previous=dict(at=self.now-1800,uploaded=0,generation=1),current=dict(at=self.now,uploaded=128*1024**2,generation=1))
        self.guards={k:'pass' for k in REQUIRED_GUARDS}
    def run_plan(self,files=None,**kw):
        options=dict(now=self.now,observed_at=self.now,free_bytes=400*self.gib,seed_cache_bytes=0);options.update(kw)
        return plan(files if files is not None else [self.file],self.guards,**options)
    def test_hot_quiet_content_is_only_a_read_only_suggestion(self):
        r=self.run_plan();self.assertEqual(r['candidates'],[self.file['path']]);self.assertFalse(r['execution_allowed']);self.assertTrue(r['read_only'])
    def test_current_nas_pressure_prevents_promotion(self):
        self.assertEqual(self.run_plan(free_bytes=173*self.gib)['candidates'],[])
    def test_exact_reserve_is_preserved(self):
        r=self.run_plan(free_bytes=308*self.gib);self.assertEqual(r['remaining_free_bytes'],300*self.gib)
        self.assertEqual(self.run_plan(free_bytes=308*self.gib-1)['candidates'],[])
    def test_busy_incomplete_open_or_physical_binding_never_selected(self):
        for change in [dict(quiet=False),dict(open=True),dict(all_owners_complete=False),dict(user_share_binding=False),dict(nlink=2),dict(copies=2),dict(symlink=True)]:
            self.assertEqual(self.run_plan([dict(self.file,**change)])['candidates'],[])
    def test_recent_move_prevents_ping_pong(self):
        self.assertEqual(self.run_plan([dict(self.file,last_move_at=self.now-3600)])['candidates'],[])
    def test_stale_reset_unknown_and_low_demand_are_withheld(self):
        for sample in [dict(at=self.now-100,uploaded=10**9,generation=1),dict(at=self.now,uploaded=10**9,generation=2),dict(at=self.now,uploaded=0,generation=1),None]:
            self.assertEqual(self.run_plan([dict(self.file,current=sample)])['candidates'],[])
    def test_guard_unknown_blocks_every_promotion(self):
        self.guards['integrity']='unknown';self.assertEqual(self.run_plan()['decision'],'blocked')
    def test_duplicate_or_escaping_paths_fail_closed(self):
        for files in [[self.file,self.file],[dict(self.file,path='/mnt/user/other/movie')]]:
            r=self.run_plan(files);self.assertEqual(r['decision'],'unknown');self.assertEqual(r['candidates'],[])
    def test_budget_and_file_count_apply_across_all_candidates(self):
        files=[dict(self.file,path=f'/mnt/user/Filmek/{i}') for i in range(5)]
        r=self.run_plan(files);self.assertEqual(len(r['candidates']),2);self.assertEqual(r['planned_bytes'],16*self.gib)

    def test_total_seed_cache_limit_includes_existing_residents(self):
        r=self.run_plan(seed_cache_bytes=92*self.gib)
        self.assertEqual(r['projected_seed_cache_bytes'],100*self.gib)
        self.assertEqual(r['planned_bytes'],8*self.gib)
        for used in [93,100,110]:
            self.assertEqual(self.run_plan(seed_cache_bytes=used*self.gib)['candidates'],[])
    def test_smallest_of_three_budgets_wins(self):
        for changes in [dict(seed_cache_limit=7*self.gib),dict(batch_bytes=7*self.gib),dict(free_bytes=307*self.gib)]:
            self.assertEqual(self.run_plan(**changes)['candidates'],[])
    def test_unknown_or_disabled_seed_capacity_cannot_promote(self):
        for changes in [dict(seed_cache_bytes=None),dict(seed_cache_bytes=True),dict(seed_cache_limit=-1),dict(seed_cache_limit=0)]:
            self.assertEqual(self.run_plan(**changes)['candidates'],[])
