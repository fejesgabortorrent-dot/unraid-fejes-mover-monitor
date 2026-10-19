"""Exercise PHP pages against disposable local fixtures, never the host NAS."""
from pathlib import Path
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import os
from localize import compile_page

ROOT = Path(__file__).resolve().parents[1]
if not shutil.which('php'):
    raise SystemExit('PHP CLI required')
if not shutil.which('node'):
    raise SystemExit('Node.js is required for JavaScript syntax checks')
checks = []
checked_js = set()
with tempfile.TemporaryDirectory(prefix='fejesmover-app-') as directory:
    lab = Path(directory)
    paths = {
        '/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverRuntime.php': str(lab/'FejesMoverRuntime.php'),
        '/boot/config/plugins/fejes.mover.monitor/settings.json': str(lab/'config.json'),
        '/boot/config/pools/': str(lab/'pools')+'/',
        '/var/run/fejes-mover-config.lock': str(lab/'mode.lock'),
        '/var/local/emhttp/var.ini': str(lab / 'var.ini'),
        '/var/run/mover.pid': str(lab / 'mover.pid'),
        '/var/run/fejes-mover-settings.lock': str(lab / 'settings.lock'),
        '/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script': str(lab / 'automation/script'),
        '/boot/config/plugins/fejes.mover.monitor/backups': str(lab / 'backups'),
        '/boot/config/plugins/fejes.mover.monitor/tools/': str(lab / 'helpers') + '/',
        '/var/log/syslog': str(lab / 'syslog'),
        '/tmp/user.scripts/tmpScripts/Filmek_Mover_Threshold/log.txt': str(lab / 'script.log'),
        '/mnt/cache': str(lab / 'cache'),
        '/proc/': str(lab / 'proc') + '/',
    }
    (lab / 'var.ini').write_text('csrf_token="test-token"\n')
    (lab / 'syslog').write_text('Oct 17 mover: <script>alert("test")</script>\n')
    (lab / 'automation').mkdir()
    (lab/'pools').mkdir()
    (lab/'pools/cache.cfg').write_text('fixture\n')
    (lab/'config.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
    (lab/'layout').mkdir()
    script = lab / 'automation/script'
    mounted = True
    free_bytes = 10 * 1073741824
    total_bytes = 100 * 1073741824
    def render(name, post=None, language='hu'):
        source = compile_page((ROOT / 'src' / name).read_text(encoding='utf-8')).split('---\n', 1)[1]
        source = source.replace('<?php', '<?php namespace Fixture; use \\RuntimeException; use \\Throwable;', 1)
        source = source.replace('namespace Fixture;', 'namespace Fixture; function disk_total_space($p){return '+json.dumps(total_bytes).lower()+';} function disk_free_space($p){return '+json.dumps(free_bytes).lower()+';}', 1)
        if os.name == 'nt':
            source = source.replace('/bin/bash -n ', 'bash -n ')
        (lab / 'mountinfo').write_text('1 0 0:1 / '+(lab / 'cache').as_posix()+' rw - btrfs /dev/test rw\n' if mounted else '1 0 0:1 / / rw - rootfs rootfs rw\n')
        source = source.replace('/proc/self/mountinfo', (lab / 'mountinfo').as_posix())
        for old, new in paths.items():
            source = source.replace(old, new.replace('\\', '/'))
        runtime=(ROOT/'src/FejesMoverRuntime.php').read_text(encoding='utf-8')
        runtime=runtime.replace('/proc/self/mountinfo',(lab/'mountinfo').as_posix())
        for old,new in paths.items():runtime=runtime.replace(old,new.replace('\\','/'))
        runtime=runtime.replace("'/mnt/'",json.dumps(lab.as_posix()+'/'))
        (lab/'FejesMoverRuntime.php').write_text(runtime,encoding='utf-8',newline='\n')
        page = lab / name
        page.write_text(source, encoding='utf-8', newline='\n')
        encoded = base64.b64encode(json.dumps(post or {}).encode()).decode()
        wrapper = lab / 'layout/run.php'
        wrapper.write_text('<?php $_COOKIE["fejes_mover_lang"]='+json.dumps(language)+'; $_SERVER["REQUEST_METHOD"]=' + json.dumps('POST' if post is not None else 'GET') + '; $_POST=json_decode(base64_decode(' + json.dumps(encoded) + '),true); eval(substr(file_get_contents(' + json.dumps(str(page)) + '),5)); if(isset($mytiles)) echo "TILE=".json_encode($mytiles);')
        result = subprocess.run(['php', '-d', 'display_errors=stderr', '-d', 'error_reporting=32767', str(wrapper)], capture_output=True, text=True, encoding='utf-8')
        assert result.returncode == 0, result.stderr
        assert not result.stderr.strip(), result.stderr
        for javascript in re.findall(r'<script>(.*?)</script>', result.stdout, re.S):
            syntax = subprocess.run(['node', '--check'], input=javascript, text=True, capture_output=True)
            assert syntax.returncode == 0, syntax.stderr
            checked_js.add(name)
        return result.stdout
    def check(label, condition):
        assert condition, label
        checks.append(label)
    mounted = False
    page = render('FejesMover.page')
    check('Idle detail page renders without PHP warnings', '● Nem fut' in page)
    check('Missing cache shows unavailable capacity', '<span>—</span>' in page)
    check('Syslog HTML is escaped', '&lt;script&gt;' in page and '<script>alert("test")</script>' not in page)
    settings = render('FejesMoverSettings.page')
    check('Missing optional automation is handled', 'A script nincs telepítve' in settings)
    protection = render('FejesMoverProtection.page')
    check('Common protection page renders without API calls', 'Összehangolt védelem' in protection and 'Állapot ellenőrzése' in protection)
    rejected = render('FejesMoverProtection.page', {'fp_csrf':'wrong', 'fp_action':'wire'})
    check('Protection actions reject invalid CSRF', 'Lejárt munkamenet' in rejected)
    rejected = render('FejesMoverProtection.page', {'fp_csrf':'test-token', 'fp_action':'run-mover'})
    check('Protection UI cannot start Mover', 'Ismeretlen művelet' in rejected)
    (lab / 'helpers').mkdir()
    (lab / 'helpers/fejes_service.py').write_text('import json\nprint(json.dumps('+repr({'torrent':'defer','checked_torrents':7,'blocking_torrents':2,'cache_free_bytes':1073741824,'remaining_upper_bound_bytes':2147483648,'pressure':'warning','integrity_config':'wired','integrity_active':'not_verified'})+'))\n')
    snapshot = render('FejesMoverProtection.page', {'fp_csrf':'test-token', 'fp_action':'check'})
    check('Authenticated protection check renders returned diagnostics', 'Halasztás: félkész' in snapshot and '1,0 GiB' in snapshot and 'Az aktív bekötés nem igazolt' in snapshot)
    dry_fixture={'protected_items':[{'name':'<b>example</b>.mkv','kind':'unknown'}],'torrent':'defer','blocking_torrents':2,'dry_run':{'decision':'wait','read_only':True,'checks':[{'key':key,'state':'wait' if key in ('capacity','torrent') else 'pass','detail':2 if key=='torrent' else ''} for key in ('launcher','capacity','torrent','backup','parity','mover','cooldown')]}}
    (lab/'helpers/fejes_service.py').write_text('import sys,json\nassert "dry-run" in sys.argv and "--include-items" in sys.argv\nprint(json.dumps('+repr(dry_fixture)+'))\n')
    dry=render('FejesMoverProtection.page',{'fp_csrf':'test-token','fp_action':'dry-run'})
    check('Dry-run POST shows seven visual conditions and the wait result', 'Most várakozna' in dry and all(label in dry for label in ['Indító ellenőrzése','Szabad hely és küszöb','Torrentvédelem','Appdata-mentés','Paritásművelet','Futó Mover','Újrapróbálkozási várakozás']))
    check('Private item basenames are HTML escaped', '&lt;b&gt;example&lt;/b&gt;.mkv' in dry and '<b>example</b>.mkv' not in dry)
    check('Monitor dry-run button uses CSRF-protected POST', 'value="dry-run"' in render('FejesMover.page') and 'name="fp_csrf"' in render('FejesMover.page'))
    for language in ('en','de'):
        translated_dry=render('FejesMoverProtection.page',{'fp_csrf':'test-token','fp_action':'dry-run'},language)
        check(language+': protection descriptions and native title translated', ('Coordinated protection' if language=='en' else 'Abgestimmter Schutz') in translated_dry and 'Helyhiánynál sincs' not in translated_dry and 'Az eseményfigyelő korábbi' not in translated_dry and ('FejesMover Protection' if language=='en' else 'FejesMover Schutz') in translated_dry)
        check(language+': dry-run heading translated', ('Would wait now' if language=='en' else 'Würde jetzt warten') in translated_dry)
    marker = lab / 'wired'
    (lab / 'helpers/wire_integrity_cron.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
    mounted=True
    rejected=render('FejesMoverProtection.page', {'fp_csrf':'test-token','fp_action':'wire'})
    check('Wiring requires separate consent', not marker.exists() and 'külön jóváhagyás' in rejected)
    (lab/'config.json').write_text('{"version":1,"mode":"observer","pool":"cache"}')
    rejected=render('FejesMoverProtection.page', {'fp_csrf':'test-token','fp_action':'wire','wire_ack':'yes'})
    check('Observer rejects schedule writes', not marker.exists() and 'külön jóváhagyás' in rejected)
    dry=render('FejesMoverProtection.page',{'fp_csrf':'test-token','fp_action':'dry-run'})
    check('Observer permits dry run without schedule mutation', 'Most várakozna' in dry and not marker.exists())
    (lab/'config.json').write_text('{"version":1,"mode":"demo","pool":"cache"}')
    (lab/'helpers/fejes_service.py').write_text('raise RuntimeError("must not execute in demo")')
    demo=render('FejesMoverProtection.page', {'fp_csrf':'test-token','fp_action':'check'})
    check('Demo diagnostics never invoke live helper', 'Szimulált állapot' in demo)
    demo_dry=render('FejesMoverProtection.page',{'fp_csrf':'test-token','fp_action':'dry-run'})
    check('Demo dry-run is synthetic and never invokes live helper', 'Szimulált állapot' in demo_dry and 'Most várakozna' in demo_dry)
    (lab/'config.json').write_text('{"version":1,"mode":"advanced","pool":"cache"}')
    wired = render('FejesMoverProtection.page', {'fp_csrf':'test-token', 'fp_action':'wire','wire_ack':'yes'})
    check('Authenticated wiring invokes only the fixed helper', marker.exists() and 'bekötése lefutott' in wired)
    mounted=False
    dashboard = render('FejesMover.Dashboard.page')
    check('Dashboard embeds offline FM icon', 'data:image/svg+xml;base64,' in json.loads(dashboard.split('TILE=',1)[1])['fejes.mover.monitor']['column2'])
    check('Dashboard tile renders without PHP warnings', 'TILE=' in dashboard and 'MOVER FIGYEL' in dashboard)
    (lab / 'cache').mkdir()
    unmounted = render('FejesMover.page')
    check('Unmounted directory is not cache capacity', 'data-available="0"' in unmounted)
    tile = json.loads(render('FejesMover.Dashboard.page').split('TILE=', 1)[1])['fejes.mover.monitor']['column2']
    check('Unmounted dashboard capacity is unavailable', 'font-size:19px">—</span>' in tile)
    mounted = True
    available = render('FejesMover.page')
    check('Mounted cache publishes available capacity', 'data-available="1"' in available and 'data-used="90"' in available)
    total_bytes = False
    unreadable = render('FejesMover.page')
    check('Unreadable cache stays unavailable', 'data-available="0"' in unreadable)
    total_bytes = 100 * 1073741824
    (lab / 'mover.pid').write_text('4242')
    stale = render('FejesMover.page')
    check('Stale PID is marked uncertain', 'data-uncertain="1"' in stale and 'Nem ellenőrizhető PID' in stale)
    proc = lab / 'proc/4242'
    proc.mkdir(parents=True)
    (proc / 'cmdline').write_bytes(b'/usr/local/sbin/mover\0')
    (proc / 'status').write_text('Pid:\t4242\nPPid:\t1\n')
    running = render('FejesMover.page')
    check('Mover process fixture is detected', 'data-running="1"' in running and '● Mover fut' in running)
    (lab / 'mover.pid').unlink()
    original = '#!/bin/bash\nKUSZOB_GIB=2\nUJRA_PROBALKOZAS_MP=5\n# fixture only; never executed\n'
    script.write_text(original, newline='\n')
    free_bytes = 0
    full = render('FejesMoverSettings.page')
    check('Zero free bytes render as valid capacity', '0,0 GiB</strong>' in full and 'free=0' in full)
    preview_script = next(js for js in re.findall(r'<script>(.*?)</script>', full, re.S) if 'ms-threshold' in js)
    preview_test = '''const vm=require('node:vm'),assert=require('node:assert/strict');
const elements={}; for(const id of ['ms-threshold','ms-slider','ms-cooldown','ms-hours','ms-marker','ms-preview']) elements[id]={value:'2',style:{},addEventListener(){},form:{addEventListener(){}}};
vm.runInNewContext(SCRIPT,{document:{getElementById:id=>elements[id]}});
assert.match(elements['ms-preview'].textContent,/A szabad hely már a küszöb alatt van/);'''.replace('SCRIPT', json.dumps(preview_script))
    preview_result = subprocess.run(['node'], input=preview_test, capture_output=True, text=True, encoding='utf-8')
    check('Zero free bytes trigger below-threshold preview', preview_result.returncode == 0)
    check('Full cache reports 100 percent', 'data-used="100"' in render('FejesMover.page'))
    free_bytes = False
    check('Unreadable free space is unavailable', 'free=null' in render('FejesMoverSettings.page'))
    free_bytes = 10 * 1073741824
    def post(**changes):
        data = {'ms_csrf':'test-token', 'source_hash':hashlib.sha256(script.read_bytes()).hexdigest(), 'KUSZOB_GIB':'3', 'UJRA_PROBALKOZAS_MP':'10'}
        data.update(changes)
        return render('FejesMoverSettings.page', data)
    check('Optional settings GET renders', 'Beállítások mentése' in render('FejesMoverSettings.page'))
    rejected = post(ms_csrf='wrong')
    check('Invalid CSRF cannot modify script', 'Lejárt munkamenet' in rejected and script.read_text() == original)
    rejected = post(source_hash='0'*64)
    check('Conflicting source hash cannot modify script', 'közben megváltozott' in rejected and script.read_text() == original)
    rejected = post(KUSZOB_GIB='-1')
    check('Invalid range cannot modify script', 'Érvénytelen érték' in rejected and script.read_text() == original)
    (lab / 'mover.pid').write_text('4242')
    rejected = post()
    check('Present Mover PID blocks settings changes', 'Futó Mover mellett' in rejected and script.read_text() == original)
    (lab / 'mover.pid').unlink()
    saved = post()
    assert 'Sikeresen mentve' in saved, re.findall(r'role="alert">(.*?)</div>', saved)
    expected = original.replace('KUSZOB_GIB=2', 'KUSZOB_GIB=3').replace('UJRA_PROBALKOZAS_MP=5', 'UJRA_PROBALKOZAS_MP=10')
    backups = list((lab / 'backups').glob('*.sh'))
    check('Valid settings save is verified', 'Sikeresen mentve' in saved and script.read_text() == expected)
    check('Backup preserves exact original script', len(backups) == 1 and backups[0].read_text() == original)
    unchanged = post()
    check('Unchanged settings do not create a backup', 'Nem történt módosítás' in unchanged and len(list((lab / 'backups').glob('*.sh'))) == 1)
    for language, monitor_title, settings_title, session_error, pause_label, free_warning in [
        ('en','Mover Monitor','Save settings','Session expired. Reload the page.','PAUSED','Free space is already below the threshold.'),
        ('de','Mover-Monitor','Einstellungen speichern','Sitzung abgelaufen. Seite neu laden.','PAUSIERT','Der freie Speicher liegt bereits unter dem Schwellenwert.')]:
        detail = render('FejesMover.page', language=language)
        check(f'{language}: monitor, refresh labels and language selection', monitor_title in detail and pause_label in detail and f'value="{language}" selected' in detail and 'Automatikus frissítés' not in detail)
        handler=re.search(r'onchange="([^"]+)"', detail)[1]
        selection_test="const vm=require('node:vm'),assert=require('node:assert/strict');const context={value:'de',document:{},location:{pathname:'/Tools/FejesMoverSettings',assign(p){this.target=p}}};vm.runInNewContext(HANDLER,context);assert.equal(context.document.cookie,'fejes_mover_lang=de; Path=/; Max-Age=31536000; SameSite=Lax');assert.equal(context.location.target,'/Tools/FejesMoverSettings');".replace('HANDLER',json.dumps(handler))
        selection_result=subprocess.run(['node'],input=selection_test,text=True,capture_output=True)
        check(f'{language}: language selection saves cookie and navigates with GET', selection_result.returncode==0)
        dashboard = json.loads(render('FejesMover.Dashboard.page', language=language).split('TILE=',1)[1])['fejes.mover.monitor']['column2']
        check(f'{language}: dashboard and selector translated', monitor_title.upper() in dashboard and f'value="{language}" selected' in dashboard and 'MOVER FIGYELŐ' not in dashboard)
        script.unlink()
        missing = render('FejesMoverSettings.page', language=language)
        check(f'{language}: missing optional script and selector translated', f'value="{language}" selected' in missing and ('not installed' if language=='en' else 'nicht installiert') in missing)
        script.write_text(original, newline='\n')
        free_bytes=0
        settings=render('FejesMoverSettings.page', language=language)
        check(f'{language}: settings and full-cache warning translated', settings_title in settings and free_warning in settings and 'Beállítások mentése' not in settings)
        data={'ms_csrf':'bad','source_hash':hashlib.sha256(script.read_bytes()).hexdigest(),'KUSZOB_GIB':'3','UJRA_PROBALKOZAS_MP':'10'}
        error=render('FejesMoverSettings.page', data, language)
        check(f'{language}: validation message translated without writes', session_error in error and script.read_text()==original)
        data['ms_csrf']='test-token'
        saved=render('FejesMoverSettings.page', data, language)
        check(f'{language}: localized valid save retains behavior', ('Saved and verified.' if language=='en' else 'Gespeichert und geprüft.') in saved and script.read_text()==expected)
        free_bytes=10*1073741824
    for invalid in ['fr', '<script>alert(1)</script>', ['en']]:
        fallback=render('FejesMover.page', language=invalid)
        check(f'Invalid language {invalid!r} safely falls back to Hungarian', 'Automatikus frissítés' in fallback and 'value="hu" selected' in fallback)
    (lab / 'syslog').write_text('Oct 17 mover: Mover figyelő\n', encoding='utf-8')
    check('Runtime log contents remain untranslated', 'mover: Mover figyelő' in render('FejesMover.page', language='en'))
for label in checks:
    print('PASS:', label)
print(f'{len(checks)} application fixture checks passed. Actual Unraid WebGUI/Mover/reboot remain untested.')

assert len(checked_js) == 4, checked_js
print('PASS: JavaScript syntax in rendered output of all four exercised page types (Node --check).')
