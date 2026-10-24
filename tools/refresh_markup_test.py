import tempfile,unittest
from pathlib import Path
from html.parser import HTMLParser
from browser_demo import Demo

class BannerParser(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.inside=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='style' and a.get('id')=='fejes-depth-style':self.inside=any('fmc-mode' in x.split() for x in self.stack)
  if tag not in ('input','br','hr','img','meta','link','wbr','source'):self.stack.append(a.get('class',''))
 def handle_endtag(self,tag):
  if self.stack:self.stack.pop()

class RefreshMarkup(unittest.TestCase):
 def test_dashboard_refresh_banner_retains_depth_styles(self):
  with tempfile.TemporaryDirectory() as folder:
   demo=Demo(Path(folder))
   for lang in ('hu','en','de'):
    with self.subTest(language=lang):
     parser=BannerParser();parser.feed(demo.render('FejesMover.Dashboard.page','idle',lang,None));self.assertTrue(parser.inside,'Polling replaces fmd-mode with .fmc-mode; depth CSS must be inside it')

 def test_selective_polling_targets_exist_in_rendered_page(self):
  with tempfile.TemporaryDirectory() as folder:
   demo=Demo(Path(folder))
   for lang in ('hu','en','de'):
    with self.subTest(language=lang):
     rendered=demo.render('FejesMoverSelective.page','idle',lang,None)
     for marker in ('id="fms-run"','id="fms-last"','id="fms-refresh-state"','data-fms-status-card','data-fms-space-card'):
      self.assertIn(marker,rendered)

if __name__=='__main__':unittest.main()
