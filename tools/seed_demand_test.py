import unittest
from seed_demand import advance,summary,MIN_BYTES

class Demand(unittest.TestCase):
    def setUp(self):
        self.now=2_000_000_000;self.mounts=[dict(Type='bind',Source='/mnt/user/Filmek',Destination='/data')]
        self.t=dict(hash='a'*40,uploaded=0,progress=1,state='uploading',content_path='/data/movie')
        self.state={'version':1,'items':{}}
    def observe(self,at,uploaded,generation='start',state=None):
        return advance(state if state is not None else self.state,[dict(self.t,uploaded=uploaded)],self.mounts,generation,at)
    def test_two_independent_windows_required(self):
        a=self.observe(self.now,0);b=self.observe(self.now+1800,MIN_BYTES,state=a)
        self.assertEqual(summary(b)['recurring_demand_torrents'],0)
        c=self.observe(self.now+3600,2*MIN_BYTES,state=b)
        self.assertEqual(summary(c)['recurring_demand_torrents'],1)
        self.assertFalse(summary(c)['execution_allowed'])
    def test_frequent_polls_do_not_double_count_window(self):
        a=self.observe(self.now,0)
        for i in range(1,7):a=self.observe(self.now+i*300,MIN_BYTES,state=a)
        self.assertEqual(len(next(iter(a['items'].values()))['windows']),1)
    def test_restart_gap_and_counter_reset_restart_baseline(self):
        a=self.observe(self.now,10*MIN_BYTES)
        for at,uploaded,generation in [(self.now+1800,20*MIN_BYTES,'other'),(self.now+7200,20*MIN_BYTES,'start'),(self.now+1800,1,'start')]:
            b=self.observe(at,uploaded,generation,state=a)
            self.assertEqual(next(iter(b['items'].values()))['windows'],[])
    def test_invalid_api_snapshot_does_not_mutate_original(self):
        import copy
        old=copy.deepcopy(self.state)
        for value in [None,True,-1,'10']:
            with self.assertRaises(ValueError):self.observe(self.now,value)
        self.assertEqual(self.state,old)
    def test_state_and_report_do_not_retain_raw_identity_or_path(self):
        import json
        a=self.observe(self.now,0);text=json.dumps(a)
        self.assertNotIn(self.t['hash'],text);self.assertNotIn('/data',text)
    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):self.observe(self.now,0,state={'version':2,'items':{}})
