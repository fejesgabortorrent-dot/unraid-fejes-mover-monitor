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
    def render(self,post=None,mode='advanced',lang='hu',last=None,forecast=None,worker_code=0,worker_report=None):
        with tempfile.TemporaryDirectory(prefix='fejes-selective-ui-') as folder:
            lab=Path(folder)
            config='{"version":1,"age_days":7}'
            (lab/'selective.json').write_text(config)
            (lab/'selective-last.json').write_text(json.dumps(last if last is not None else {'state':'nothing_eligible','skipped':{'too_young':4}}))
            if forecast is not None:(lab/'selective-forecast.json').write_text(json.dumps(forecast))
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
            function exec($command,&$lines=null,&$code=null){$GLOBALS['calls'][]=$command;$code=__CODE__;$lines=[__REPORT__];}
            $GLOBALS['calls']=[]; $_COOKIE['fejes_mover_lang']=__LANG__;
            $_SERVER['REQUEST_METHOD']=__METHOD__;$_POST=json_decode(base64_decode(__PAYLOAD__),true);
            ob_start();include __PAGE__;$html=ob_get_clean();echo json_encode(['html'=>$html,'calls'=>$GLOBALS['calls']]);'''
            for key,value in [('__CODE__',worker_code),('__REPORT__',json.dumps(worker_report if worker_report is not None else dict(state='requested',execution_allowed=False,candidate_count=0,file_count=4))),('__LANG__',lang),('__METHOD__','POST' if post is not None else 'GET'),('__PAYLOAD__',encoded),('__PAGE__',str(page))]:
                runner=runner.replace(key,json.dumps(value))
            result=subprocess.run(['php'],input=runner,text=True,capture_output=True,check=True)
            self.assertEqual(result.stderr,'')
            output=json.loads(result.stdout)
            output['config']=json.loads((lab/'selective.json').read_text())
            return output

    def request(self,**extra):
        return dict(dict(fejes_csrf='test-token',source_hash='CURRENT',action='run'),**extra)

    def test_get_never_executes_helper_in_all_languages(self):
        for language,label in [('hu','Koralapú szelektív'),('en','Age-filtered selective'),('de','Altersabhängiges selektives')]:
            result=self.render(lang=language)
            self.assertFalse(result['calls']);self.assertIn(label,result['html'])

    def test_worker_failure_shows_bounded_specific_cause_in_all_languages(self):
        labels={
            'inspection_required':('a biztonsági zárolás aktív','the safety lock is active','die Sicherheitssperre ist aktiv'),
            'torrent_snapshot_unavailable':('A qBittorrent torrentállapota','qBittorrent state could not','Der qBittorrent-Status'),
            'integrity_hashing_active':('Integritásellenőrzés fut','Integrity verification is running','Integritätsprüfung läuft')}
        for code,translations in labels.items():
            for lang,label in zip(('hu','en','de'),translations):
                result=self.render(self.request(action='preview'),lang=lang,worker_code=20,
                    worker_report=dict(error='private command /private/path',error_code=code))
                self.assertIn(label,result['html'])
                self.assertNotIn('/private/path',result['html'])
                self.assertEqual(len(result['calls']),1)
                self.assertIn('selective_mover.py preview',result['calls'][0])

    def test_unknown_worker_cause_is_not_guessed_from_old_report(self):
        result=self.render(self.request(action='preview'),lang='en',worker_code=20,
            worker_report=dict(error='private exception',error_code='<script>private</script>'),
            last=dict(state='error',error_code='torrent_snapshot_unavailable',requires_inspection=True))
        self.assertIn('does not identify the underlying cause',result['html'])
        self.assertNotIn('<script>private</script>',result['html'])
        self.assertNotIn('private exception',result['html'])

    def test_preflight_error_without_latch_does_not_claim_inspection_lock(self):
        result=self.render(lang='en',last=dict(state='error',requires_inspection=False,error='bounded',error_code='required_state_unverified'))
        self.assertIn('Stopped: safety condition unverified',result['html'])
        self.assertNotIn('Stopped: inspection required',result['html'])

    def test_namespaced_form_action_avoids_host_collision(self):
        for lang in ('hu','en','de'):
            result=self.render(lang=lang)
            self.assertNotIn('name="action"',result['html'])
            self.assertIn('name="fms_action"',result['html'])
        post=self.request();post['fms_action']='preview';post.pop('action')
        result=self.render(post)
        self.assertEqual(len(result['calls']),1)
        self.assertIn('selective_mover.py preview',result['calls'][0])
        self.assertEqual(result['config']['age_days'],7)

    def test_integrity_deferral_has_readable_labels(self):
        for lang,label in [('hu','File Integrity'),('en','File Integrity'),('de','File-Integrity')]:
            result=self.render(lang=lang,last={'state':'deferred','blockers':['integrity','cooldown'],'moved_files':0,'moved_bytes':0})
            self.assertIn(label,result['html'])
            self.assertFalse(result['calls'])

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

    def test_private_waiting_table_escapes_names_and_shows_countdown_in_every_language(self):
        forecast={'version':1,'age_days':7,'observed_at':2_000_000_000,'total_bytes':1024,
                  'rows':[{'file':'<script>alert(1)</script>.mkv','bytes':1024,'age_ready_at':2_000_086_400,'reason':'too_young'}]}
        for lang,label in [('hu','Korhatárig hátra'),('en','Time until age eligible'),('de','Zeit bis Altersfreigabe')]:
            result=self.render(lang=lang,forecast=forecast)
            self.assertFalse(result['calls']);self.assertIn(label,result['html'])
            self.assertIn('data-fms-countdown="2000086400"',result['html'])
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;.mkv',result['html'])
            self.assertNotIn('<script>alert(1)</script>.mkv',result['html'])

    def test_changed_age_ignores_old_forecast(self):
        result=self.render(lang='en',forecast={'version':1,'age_days':14,'rows':[]})
        self.assertIn('No current observation for this age setting',result['html'])

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


    def test_ratio_settings_are_localized_and_validate_before_saving(self):
        for lang,label in [('hu','Megosztási arány'),('en','Share ratio'),('de','Freigabeverhältnis')]:
            self.assertIn(label,self.render(lang=lang)['html'])
        for ratio in ['-1','101','NaN','1e2','<script>',[]]:
            result=self.render(dict(fejes_csrf='test-token',source_hash='CURRENT',action='save',age_days='7',ratio_target=ratio))
            self.assertIn('role="alert"',result['html'])
            self.assertEqual(result['config'],{'version':1,'age_days':7})
            self.assertFalse(result['calls'])

    def test_valid_ratio_saves_without_starting_worker(self):
        result=self.render(dict(fejes_csrf='test-token',source_hash='CURRENT',action='save',age_days='14',ratio_target='1.25'))
        self.assertEqual(result['config'],{'version':1,'age_days':14,'ratio_target':1.25,'batch_gib':16})
        self.assertFalse(result['calls'])

    def test_larger_batch_is_explicit_and_saved_without_movement(self):
        result=self.render(dict(fejes_csrf='test-token',source_hash='CURRENT',action='save',age_days='7',ratio_target='1',batch_gib='32'))
        self.assertEqual(result['config']['batch_gib'],32)
        self.assertIn('8 fájl / 32 GiB',result['html'])
        self.assertFalse(result['calls'])
        for value in ['0','-1','256','32.0',[]]:
            result=self.render(dict(fejes_csrf='test-token',source_hash='CURRENT',action='save',age_days='7',batch_gib=value))
            self.assertEqual(result['config'],{'version':1,'age_days':7})

    def test_one_day_age_is_explicit_and_does_not_start_worker(self):
        result=self.render(dict(fejes_csrf='test-token',source_hash='CURRENT',action='save',age_days='1'))
        self.assertEqual(result['config']['age_days'],1)
        self.assertFalse(result['calls'])

if __name__=='__main__':unittest.main()
