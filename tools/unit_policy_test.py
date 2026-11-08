import unittest
from selection_policy import plan, unit_groups, REQUIRED_GUARDS
class UnitPolicy(unittest.TestCase):
 root='/mnt/cache/Filmek'; now=2_000_000_000
 mounts=[dict(Type='bind',Source=root,Destination='/data')]
 guards={key:'pass' for key in REQUIRED_GUARDS}
 def file(self,suffix,first=None,opened=False):
  return dict(path=self.root+'/'+suffix,regular=True,symlink=False,nlink=1,open=opened,stable=True,mtime=self.now-60,first_seen=self.now-60 if first is None else first)
 def plan(self,files,torrents=()):
  return plan(files,list(torrents) or [dict(content_path='/data/unrelated',progress=1,state='stalledUP',completion_on=self.now-10*86400,upspeed=0,dlspeed=0)],self.mounts,self.guards,days=1,now=self.now,observed_at=self.now,root=self.root)
 def test_recent_torrent_waits_ordinary_does_not(self):
  a=self.file('ordinary.mkv');b=self.file('torrent.mkv',first=self.now-4000)
  t=dict(content_path='/data/torrent.mkv',progress=1,state='stalledUP',completion_on=self.now-10*86400,upspeed=0,dlspeed=0)
  result=self.plan([a,b],[t]);self.assertEqual(result['candidates'],[a['path']]);self.assertIn({'path':b['path'],'reason':'too_young'},result['skipped'])
 def test_busy_sidecar_blocks_folder(self):
  a=self.file('Movie/video.mkv');b=self.file('Movie/poster.jpg',opened=True)
  result=self.plan([a,b]);self.assertEqual(result['candidates'],[]);self.assertIn({'path':a['path'],'reason':'unit_not_ready'},result['skipped'])
 def test_loose_files_group_by_arrival(self):
  a=self.file('one.mkv',first=self.now-1000);b=self.file('one.srt',first=self.now-900,opened=True)
  self.assertEqual(self.plan([a,b])['candidates'],[]);self.assertEqual(unit_groups([a,b],self.root),[[a['path'],b['path']]])
 def test_separate_arrivals_and_folder(self):
  a=self.file('old.mkv',first=self.now-4000);b=self.file('new.mkv',first=self.now-900);c=self.file('Movie/part.mkv')
  self.assertEqual(len(unit_groups([a,b,c],self.root)),3)
