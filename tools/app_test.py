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
        '/var/local/emhttp/var.ini': str(lab / 'var.ini'),
        '/var/run/mover.pid': str(lab / 'mover.pid'),
        '/var/run/fejes-mover-settings.lock': str(lab / 'settings.lock'),
        '/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script': str(lab / 'automation/script'),
        '/boot/config/plugins/fejes.mover.monitor/backups': str(lab / 'backups'),
        '/var/log/syslog': str(lab / 'syslog'),
        '/tmp/user.scripts/tmpScripts/Filmek_Mover_Threshold/log.txt': str(lab / 'script.log'),
        '/mnt/cache': str(lab / 'cache'),
        '/proc/': str(lab / 'proc') + '/',
    }
    (lab / 'var.ini').write_text('csrf_token="test-token"\n')
    (lab / 'syslog').write_text('Oct 17 mover: <script>alert("test")</script>\n')
    (lab / 'automation').mkdir()
    script = lab / 'automation/script'
    mounted = True
    free_bytes = 10 * 1073741824
    total_bytes = 100 * 1073741824
    def render(name, post=None):
        source = (ROOT / 'src' / name).read_text(encoding='utf-8').split('---\n', 1)[1]
        source = source.replace('<?php', '<?php namespace Fixture; use \\RuntimeException; use \\Throwable;', 1)
        source = source.replace('namespace Fixture;', 'namespace Fixture; function disk_total_space($p){return '+json.dumps(total_bytes).lower()+';} function disk_free_space($p){return '+json.dumps(free_bytes).lower()+';}', 1)
        if os.name == 'nt':
            source = source.replace('/bin/bash -n ', 'bash -n ')
        (lab / 'mountinfo').write_text('1 0 0:1 / '+(lab / 'cache').as_posix()+' rw - btrfs /dev/test rw\n' if mounted else '1 0 0:1 / / rw - rootfs rootfs rw\n')
        source = source.replace('/proc/self/mountinfo', (lab / 'mountinfo').as_posix())
        for old, new in paths.items():
            source = source.replace(old, new.replace('\\', '/'))
        page = lab / name
        page.write_text(source, encoding='utf-8', newline='\n')
        encoded = base64.b64encode(json.dumps(post or {}).encode()).decode()
        wrapper = lab / 'run.php'
        wrapper.write_text('<?php $_SERVER["REQUEST_METHOD"]=' + json.dumps('POST' if post is not None else 'GET') + '; $_POST=json_decode(base64_decode(' + json.dumps(encoded) + '),true); include ' + json.dumps(str(page)) + '; if(isset($mytiles)) echo "TILE=".json_encode($mytiles);')
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
    dashboard = render('FejesMover.Dashboard.page')
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
    preview_script = re.findall(r'<script>(.*?)</script>', full, re.S)[0]
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
for label in checks:
    print('PASS:', label)
print(f'{len(checks)} application fixture checks passed. Actual Unraid WebGUI/Mover/reboot remain untested.')

assert len(checked_js) == 3, checked_js
print('PASS: JavaScript syntax in rendered output of all three page types (Node --check).')
