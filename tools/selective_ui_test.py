"""Authenticated selective UI tests; all paths and helper calls are isolated."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SelectiveInterface(unittest.TestCase):
    def render(self,post=None,mode='advanced',lang='hu',last=None):
        with tempfile.TemporaryDirectory(prefix='fejes-selective-ui-') as folder:
            lab=Path(folder)
            config='{"version":1,"age_days":7}'
            (lab/'selective.json').write_text(config)
            (lab/'selective-last.json').write_text(json.dumps(last if last is not None else {'state':'nothing_eligible','skipped':{'too_young':4}}))
            runtime='''<?php return ['mode'=>MODE,'pool'=>'cache','mounted'=>true,'error'=>false,'token'=>'test-token',
                't'=>static fn($hu,$en,$de)=>[$hu,$en,$de][LANG],
                'esc'=>static fn($v)=>htmlspecialchars((string)$v,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8'),'banner'=>'fixture'];'''
            (lab/'runtime.php').write_text(runtime.replace('MODE',json.dumps(mode)).replace('LANG',str({'hu':0,'en':1,'de':2}[lang])))
            source=(ROOT/'src/FejesMoverSelective.page').read_text().split('---\n',1)[1]
            source=source.replace('<?php','<?php namespace Fixture; use \\RuntimeException; use \\Throwable;',1)
            source=source.replace('/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverRuntime.php',str(lab/'runtime.php'))
            source=source.replace('/boot/config/plugins/fejes.mover.monitor/selective',str(lab/'selective'))
            source=source.replace('/var/run/fejes-selective-inventory.lock',str(lab/'inventory.lock'))
            page=lab/'page.php';page.write_text(source)
            request=dict(post or {})
            if request.get('source_hash')=='CURRENT': request['source_hash']=hashlib.sha256(config.encode()).hexdigest()
            encoded=base64.b64encode(json.dumps(request).encode()).decode()
            runner='''<?php namespace Fixture;
            function exec($command,&$lines=null,&$code=null){$GLOBALS['calls'][]=$command;$code=0;$lines=['{"state":"requested","execution_allowed":false,"candidate_count":0,"file_count":4}'];}
            $GLOBALS['calls']=[]; $_COOKIE['fejes_mover_lang']=__LANG__;
            $_SERVER['REQUEST_METHOD']=__METHOD__;$_POST=json_decode(base64_decode(__PAYLOAD__),true);
            ob_start();include __PAGE__;$html=ob_get_clean();echo json_encode(['html'=>$html,'calls'=>$GLOBALS['calls']]);'''
            for key,value in [('__LANG__',lang),('__METHOD__','POST' if post is not None else 'GET'),('__PAYLOAD__',encoded),('__PAGE__',str(page))]:
                runner=runner.replace(key,json.dumps(value))
            result=subprocess.run(['php'],input=runner,text=True,capture_output=True,check=True)
            self.assertEqual(result.stderr,'')
            return json.loads(result.stdout)

    def request(self,**extra):
        return dict(fejes_csrf='test-token',source_hash='CURRENT',action='run',**extra)

    def test_get_never_executes_helper_in_all_languages(self):
        for language,label in [('hu','Koralapú szelektív'),('en','Age-filtered selective'),('de','Altersabhängiges selektives')]:
            result=self.render(lang=language)
            self.assertFalse(result['calls']);self.assertIn(label,result['html'])

    def test_observer_cannot_launch(self):
        self.assertFalse(self.render(self.request(),mode='observer')['calls'])

    def test_zero_movement_and_both_limits_are_visible_in_every_language(self):
        last={'state':'no_files_moved','moved_files':0,'moved_bytes':0,
              'skipped':{'file_exceeds_batch_limit':3,'batch_file_limit':2,'batch_size_limit':1}}
        for lang,label in [('hu','nem történt mozgatás'),('en','no files moved'),('de','keine Dateien verschoben')]:
            with self.subTest(lang=lang):
                result=self.render(lang=lang,last=last)
                self.assertFalse(result['calls'])
                self.assertIn(label,result['html'])
                self.assertIn('16 GiB',result['html'])
                self.assertNotIn('Unverifiable or unsupported: 3',result['html'])

    def test_wrong_csrf_cannot_launch(self):
        request=self.request();request['fejes_csrf']='wrong'
        self.assertFalse(self.render(request)['calls'])

    def test_stale_config_cannot_launch(self):
        request=self.request();request['source_hash']='old'
        self.assertFalse(self.render(request)['calls'])

    def test_action_injection_rejected(self):
        request=self.request();request['action']='run; touch /tmp/unexpected'
        self.assertFalse(self.render(request)['calls'])

    def test_authenticated_run_invokes_only_fixed_async_start(self):
        result=self.render(self.request())
        self.assertEqual(result['calls'],['timeout 60 python3 /boot/config/plugins/fejes.mover.monitor/tools/selective_mover.py start 2>/dev/null'])

    def test_preview_cannot_become_run(self):
        request=self.request();request['action']='preview';request['age_days']='0'
        result=self.render(request)
        self.assertEqual(len(result['calls']),1)
        self.assertTrue(result['calls'][0].endswith('selective_mover.py preview 2>/dev/null'))

if __name__=='__main__':unittest.main()
