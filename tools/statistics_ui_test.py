"""Render the embedded statistics panel with untrusted, temporary input."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('php'), 'PHP CLI required')
class StatisticsPanelTest(unittest.TestCase):
    def render(self, data, mode="advanced"):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            for name, content in data.items():
                (path/name).write_text(json.dumps(content))
            source=(ROOT/'src/FejesMoverStatistics.php').read_text().replace('/boot/config/plugins/fejes.mover.monitor/', path.as_posix()+'/')
            panel=path/'panel.php'; panel.write_text(source)
            php='''$fmc=['mode'=>'advanced']; $fmT=fn($hu,$en,$de)=>$hu; $fmEsc=fn($x)=>htmlspecialchars((string)$x,ENT_QUOTES|ENT_SUBSTITUTE,"UTF-8"); include $argv[1];'''
            php=php.replace("'advanced'", repr(mode))
            return subprocess.run(['php','-r',php,str(panel)],capture_output=True,text=True,check=True).stdout
    def test_data_and_chart(self):
        out=self.render({'selective-last.json':{'moved_files':2,'moved_bytes':1073741824},'github-download-history.json':[{'date':'2026-11-21','total':3},{'date':'2026-11-22','total':6}]})
        self.assertIn('1.00 GiB',out)
        self.assertIn('<polyline',out)
        self.assertIn('2026-11-21',out)
        self.assertIn('>6</strong>',out)
    def test_demo_never_reads_live_values(self):
        out=self.render({'github-downloads.json':{'total':845}}, mode='demo')
        self.assertNotIn('>845</strong>', out)
        self.assertIn('Nincs mérés', out)
    def test_untrusted_records_are_not_rendered_and_missing_is_not_zero(self):
        out=self.render({'github-download-history.json':[{'date':'<script>','total':3}],'completed-seed-events.json':{'version':1,'origin':'unknown','events':[{'time':1,'event':'<script>'}]}})
        self.assertNotIn('<script>',out)
        self.assertIn('Nincs mérés',out)
        self.assertNotIn('<polyline',out)

class PanelIntegrationTest(unittest.TestCase):
    def test_all_languages_include_shared_panel(self):
        page=(ROOT/'src/FejesMover.page').read_text()
        self.assertEqual(page.count("include '/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverStatistics.php'"),3)

if __name__=='__main__': unittest.main()
