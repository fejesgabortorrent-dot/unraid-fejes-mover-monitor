"""Safety checks for Unraid mode selection; all paths point to disposable fixtures."""
from pathlib import Path
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from localize import compile_page

ROOT=Path(__file__).resolve().parents[1]
checks=[]
with tempfile.TemporaryDirectory(prefix='fejes-modes-') as directory:
    lab=Path(directory)
    (lab/'pools').mkdir(); (lab/'automation').mkdir(); (lab/'config').mkdir()
    for pool in ['cache','fast']: (lab/'pools'/f'{pool}.cfg').write_text('fixture\n')
    config=lab/'config/settings.json'; script=lab/'automation/script'; metrics=lab/'metrics'
    original='#!/bin/bash\nKUSZOB_GIB=2\nUJRA_PROBALKOZAS_MP=5\n'
    script.write_text(original,newline='\n')
    (lab/'var.ini').write_text('csrf_token="test-token"\n')
    (lab/'syslog').write_text('mover: LIVE_LOG_SENTINEL\n')
    (lab/'script.log').write_text('LIVE_SCRIPT_SENTINEL\n')
    def mount(fast=True):
        (lab/'mountinfo').write_text('1 0 0:1 / /mnt/cache rw - btrfs /dev/a rw\n'+('2 0 0:2 / /mnt/fast rw - btrfs /dev/b rw\n' if fast else ''))
    mount()
    paths={
        '/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverRuntime.php':lab/'FejesMoverRuntime.php',
        '/boot/config/plugins/fejes.mover.monitor/settings.json':lab/'config/settings.json',
        '/boot/config/pools/':str(lab/'pools')+'/',
        '/var/run/fejes-mover-config.lock':lab/'config.lock',
        '/var/local/emhttp/var.ini':lab/'var.ini',
        '/proc/self/mountinfo':lab/'mountinfo',
        '/var/run/mover.pid':lab/'mover.pid',
        '/var/run/fejes-mover-settings.lock':lab/'settings.lock',
        '/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script':script,
        '/boot/config/plugins/fejes.mover.monitor/backups':lab/'backups',
        '/var/log/syslog':lab/'syslog',
        '/tmp/user.scripts/tmpScripts/Filmek_Mover_Threshold/log.txt':lab/'script.log',
        '/proc/':str(lab/'proc')+'/',
    }
    def mapped(source):
        for old,new in paths.items(): source=source.replace(old,str(new).replace('\\','/'))
        return source.replace('/bin/bash -n ','bash -n ') if os.name=='nt' else source
    (lab/'FejesMoverRuntime.php').write_text(mapped((ROOT/'src/FejesMoverRuntime.php').read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    def render(name,post=None,language='hu'):
        source=compile_page((ROOT/'src'/name).read_text(encoding='utf-8')).split('---\n',1)[1]
        namespace='<?php namespace Fixture; use \\RuntimeException; use \\Throwable; '
        namespace+='function disk_total_space($p){file_put_contents('+json.dumps(metrics.as_posix())+',$p."\\n",FILE_APPEND);return 100*1073741824;} function disk_free_space($p){return 10*1073741824;} '
        source=source.replace('<?php',namespace,1)
        (lab/name).write_text(mapped(source),encoding='utf-8',newline='\n')
        encoded=base64.b64encode(json.dumps(post or {}).encode()).decode()
        (lab/'layout').mkdir(exist_ok=True)
        (lab/'layout/run.php').write_text('<?php $_COOKIE["fejes_mover_lang"]='+json.dumps(language)+';$_SERVER["REQUEST_METHOD"]='+json.dumps('GET' if post is None else 'POST')+';$_POST=json_decode(base64_decode('+json.dumps(encoded)+'),true);eval(substr(file_get_contents('+json.dumps(str(lab/name))+'),5));',encoding='utf-8')
        result=subprocess.run(['php','-d','display_errors=stderr','-d','error_reporting=32767',str(lab/'layout/run.php')],capture_output=True,text=True,encoding='utf-8')
        assert result.returncode==0 and not result.stderr.strip(),result.stderr
        return result.stdout
    def check(label,condition):
        assert condition,label
        checks.append(label);print('PASS:',label)
    def raw():return config.read_bytes() if config.exists() else b''
    def choose(mode='observer',pool='cache',**extra):
        post={'fmc_csrf':'test-token','config_hash':hashlib.sha256(raw()).hexdigest(),'mode':mode,'pool':pool}
        post.update(extra)
        return render('FejesMoverSetup.page',post)
    def blocked(label,post):
        before=raw();out=render('FejesMoverSetup.page',post)
        check(label,raw()==before and 'role="alert"' in out and script.read_text()==original)
    settings=render('FejesMoverSettings.page')
    check('Default is observer; GET does not create configuration','scriptszerkesztés ebben a módban tiltva' in settings and not config.exists())
    attempted={'ms_csrf':'test-token','source_hash':hashlib.sha256(script.read_bytes()).hexdigest(),'KUSZOB_GIB':'3','UJRA_PROBALKOZAS_MP':'10'}
    check('Observer direct POST cannot edit automation','scriptszerkesztés ebben a módban tiltva' in render('FejesMoverSettings.page',attempted) and script.read_text()==original and not (lab/'backups').exists())
    common={'fmc_csrf':'test-token','config_hash':hashlib.sha256(raw()).hexdigest(),'mode':'advanced','pool':'cache'}
    blocked('Advanced mode requires explicit acknowledgment',common)
    for label,changes in [('CSRF rejection',{'fmc_csrf':'wrong'}),('Stale configuration hash',{'config_hash':'0'*64}),('Unknown mode',{'mode':'root'}),('Pool path traversal',{'pool':'../cache'}),('Unknown Unraid pool',{'pool':'unknown'}),('Advanced custom pool rejected',{'pool':'fast'})]:
        blocked(label,{**common,'advanced_ack':'yes',**changes})
    out=choose('demo')
    check('Demo mode saves plugin configuration only',json.loads(raw())['mode']=='demo' and script.read_text()==original and 'elmentve' in out)
    check('Demo direct POST cannot edit automation','scriptszerkesztés ebben a módban tiltva' in render('FejesMoverSettings.page',attempted) and script.read_text()==original)
    if metrics.exists():metrics.unlink()
    demo=render('FejesMover.page')
    check('Demo does not show live logs or read disk capacity','LIVE_LOG_SENTINEL' not in demo and 'LIVE_SCRIPT_SENTINEL' not in demo and 'DEMO' in demo and not metrics.exists())
    choose('observer','fast')
    monitor=render('FejesMover.page')
    check('Configured custom pool is measured',metrics.read_text().splitlines()[-1]=='/mnt/fast' and 'data-available="1"' in monitor)
    check('Custom pool never compares the cache-only script threshold','2 GiB alatt' not in monitor and 'A küszöb nem ellenőrizhető.' in monitor)
    check('Mode banner is inside the refreshed monitor fragment',monitor.index('id="fm-monitor"')<monitor.index('class="fmc-mode"') and 'data-mode="observer"' in monitor and 'data-pool="fast"' in monitor)
    mount(False);metrics.unlink()
    monitor=render('FejesMover.page')
    check('Unmounted custom pool stays unavailable','data-available="0"' in monitor and not metrics.exists())
    mount()
    for payload in ['{broken','null','[]',json.dumps({'version':1,'mode':'root','pool':'cache'}),json.dumps({'version':1,'mode':'advanced','pool':'../cache'})]:
        config.write_text(payload)
        check(f'Corrupt configuration fails closed: {payload[:24]}','scriptszerkesztés ebben a módban tiltva' in render('FejesMoverSettings.page',attempted) and script.read_text()==original)
        old=raw()
        out=choose('observer')
        check('Validated recovery replaces malformed configuration',json.loads(raw())=={'version':1,'mode':'observer','pool':'cache'} and 'elmentve' in out)
    config.unlink()
    out=choose('advanced','cache',advanced_ack='yes')
    check('Advanced explicit activation persists',json.loads(raw())['mode']=='advanced' and 'elmentve' in out)
    out=render('FejesMoverSettings.page',attempted)
    expected=original.replace('KUSZOB_GIB=2','KUSZOB_GIB=3').replace('UJRA_PROBALKOZAS_MP=5','UJRA_PROBALKOZAS_MP=10')
    check('Advanced save works with verified backup',script.read_text()==expected and 'Sikeresen mentve' in out and len(list((lab/'backups').glob('*.sh')))==1)
    before=script.read_bytes();choose('observer');render('FejesMoverSettings.page',attempted)
    check('Revoked advanced mode blocks previously valid form',script.read_bytes()==before)
    for language,heading in [('en','Operating mode and monitored pool'),('de','Betriebsmodus und überwachter Pool')]:
        check(f'{language}: setup renders translated heading and options',heading in render('FejesMoverSetup.page',language=language))
print(f'{len(checks)} mode safety checks passed; no live NAS access.')
