"""Exercise PHP pages against disposable local fixtures, never the host NAS."""
from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if not shutil.which('php'):
    raise SystemExit('PHP CLI required')
checks = []
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
    def render(name, post=None):
        source = (ROOT / 'src' / name).read_text()
        for old, new in paths.items():
            source = source.replace(old, new)
        page = lab / name
        page.write_text(source)
        encoded = base64.b64encode(json.dumps(post or {}).encode()).decode()
        wrapper = lab / 'run.php'
        wrapper.write_text('<?php $_SERVER["REQUEST_METHOD"]=' + json.dumps('POST' if post is not None else 'GET') + '; $_POST=json_decode(base64_decode(' + json.dumps(encoded) + '),true); include ' + json.dumps(str(page)) + '; if(isset($mytiles)) echo "TILE=".json_encode($mytiles);')
        result = subprocess.run(['php', '-d', 'display_errors=stderr', '-d', 'error_reporting=32767', str(wrapper)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert not result.stderr.strip(), result.stderr
        return result.stdout
    def check(label, condition):
        assert condition, label
        checks.append(label)
    page = render('FejesMover.page')
    check('Idle detail page renders without PHP warnings', '● Nem fut' in page)
    check('Missing cache shows unavailable capacity', '<span>—</span>' in page)
    check('Syslog HTML is escaped', '&lt;script&gt;' in page and '<script>alert("test")</script>' not in page)
    settings = render('FejesMoverSettings.page')
    check('Missing optional automation is handled', 'A script nincs telepítve' in settings)
    dashboard = render('FejesMover.Dashboard.page')
    check('Dashboard tile renders without PHP warnings', 'TILE=' in dashboard and 'MOVER FIGYEL' in dashboard)
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
    (lab / 'cache').mkdir()
    original = '#!/bin/bash\nKUSZOB_GIB=2\nUJRA_PROBALKOZAS_MP=5\n# fixture only; never executed\n'
    script.write_text(original)
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
    expected = original.replace('KUSZOB_GIB=2', 'KUSZOB_GIB=3').replace('UJRA_PROBALKOZAS_MP=5', 'UJRA_PROBALKOZAS_MP=10')
    backups = list((lab / 'backups').glob('*.sh'))
    check('Valid settings save is verified', 'Sikeresen mentve' in saved and script.read_text() == expected)
    check('Backup preserves exact original script', len(backups) == 1 and backups[0].read_text() == original)
    unchanged = post()
    check('Unchanged settings do not create a backup', 'Nem történt módosítás' in unchanged and len(list((lab / 'backups').glob('*.sh'))) == 1)
for label in checks:
    print('PASS:', label)
print(f'{len(checks)} application fixture checks passed. Actual Unraid WebGUI/Mover/reboot remain untested.')
