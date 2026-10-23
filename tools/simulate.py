#!/usr/bin/env python3
"""Execute the real reviewed launcher and torrent assessor in a temporary lab."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

from wire_mover_gate import rewrite_launcher

REPO = Path(__file__).resolve().parents[1]
SCENARIOS = [
    ('ready', 'Kevés hely, kész torrentek', {}, True, True),
    ('space', 'Elegendő szabad hely', {'free': 633}, False, False),
    ('boundary', 'Pontosan 300 GiB szabad', {'free': 300}, False, False),
    ('download', 'Aktív letöltés', {'state': 'downloading', 'progress': .4}, False, True),
    ('stalled', '99,95%-os megakadt letöltés', {'state': 'stalledDL', 'progress': .9995}, False, True),
    ('checking', '100%-os torrent ellenőrzése', {'state': 'checkingUP'}, False, True),
    ('api', 'Nem elérhető torrent API', {'unavailable': True}, False, True),
    ('backup', 'Appdata-mentés fut', {'backup': True}, False, False),
    ('parity', 'Paritásművelet fut', {'parity': True}, False, False),
    ('mover', 'Mover már fut', {'mover': True}, False, False),
    ('cooldown', 'Újrapróbálkozási várakozás', {'cooldown': True}, False, False),
    ('mount', 'Cache nincs felcsatolva', {'mounted': False}, False, False),
]


def execute(case):
    key, label, options, expected_move, expected_gate = case
    with tempfile.TemporaryDirectory(prefix='fejes-simulation-') as directory:
        root = Path(directory)
        for name in ('bin', 'cache', 'array'):
            (root/name).mkdir()
        payload = b'FejesMover synthetic test file\n' * 4096
        source_file = root/'cache'/'demo.bin'
        destination = root/'array'/'demo.bin'
        source_file.write_bytes(payload)
        (root/'scenario.json').write_text(json.dumps(options))
        if options.get('backup'):
            (root/'backup.pid').write_text(str(os.getpid()))
        if options.get('mover'):
            (root/'mover.pid').write_text(str(os.getpid()))
        previous = str(int(time.time())) + '\n' if options.get('cooldown') else None
        if previous:
            (root/'attempt').write_text(previous)
        (root/'mdstat').write_text('mdResync=' + ('1' if options.get('parity') else '0') + '\n')
        # Only hardware/API boundaries are replaced. assess() runs unchanged.
        gate = root/'gate.py'
        gate.write_text('''import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
from torrent_preflight import assess
root = pathlib.Path(__file__).parent
options = json.loads((root/'scenario.json').read_text())
(root/'gate-called').touch()
if options.get('unavailable'):
    print('SIMULATED API unavailable')
    sys.exit(20)
torrent = {'progress': options.get('progress', 1),
           'state': options.get('state', 'stalledUP'),
           'content_path': '/data/demo.bin'}
result = assess([torrent], [{'Type':'bind', 'Destination':'/data', 'Source':str(root/'cache')}])
print('Real torrent assessor: ' + result['decision'])
sys.exit(result['exit_code'])
''')
        mover = root/'fake_mover.py'
        mover.write_text('''import pathlib, shutil, sys
root = pathlib.Path(__file__).parent
assert sys.argv[1:] == ['start']
shutil.move(str(root/'cache'/'demo.bin'), str(root/'array'/'demo.bin'))
print('SIMULATION: synthetic file moved')
''')
        wrapper = root/'bin'/'python3'
        wrapper.write_text('#!/bin/bash\nif [[ "$1" == "-c" ]]; then exit ' +
                           ('1' if options.get('mounted') is False else '0') +
                           '; fi\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
        wrapper.chmod(0o700)
        df = root/'bin'/'df'
        df.write_text('#!/bin/bash\nprintf "Filesystem 1024-blocks Used Available Capacity Mounted\\nfixture 1000000000 0 ' +
                      str(options.get('free', 100)*1024*1024) + ' 1%% fixture\\n"\n')
        df.chmod(0o700)
        source = rewrite_launcher((REPO/'tests/fixtures/threshold-reviewed.sh').read_text())
        replacements = {
            '/mnt/cache': str(root/'cache'), '/mnt/user/Filmek': str(root/'array'),
            '/var/run/filmek_mover_last_attempt': str(root/'attempt'),
            '/var/run/fejes-mover-launch.lock': str(root/'lock'),
            '/var/run/mover.pid': str(root/'mover.pid'),
            '/tmp/appdata.backup/running': str(root/'backup.pid'),
            '/proc/mdstat': str(root/'mdstat'),
            'python3 /boot/config/plugins/fejes.mover.monitor/tools/torrent_preflight.py':
                shlex.join([sys.executable, str(gate), str(REPO/'tools')]),
            '/usr/local/sbin/mover': shlex.join([sys.executable, str(mover)]),
        }
        for old, new in replacements.items():
            source = source.replace(old, new)
        # No production paths may survive in the executable fixture.
        if any(path in source for path in ('/mnt/', '/boot/', '/var/run/', '/proc/mdstat', '/usr/local/sbin/')):
            raise RuntimeError('Unisolated launcher')
        result = subprocess.run(['bash'], input=source, text=True, capture_output=True,
                                timeout=15, env=dict(os.environ, PATH=str(root/'bin')+':'+os.environ['PATH']))
        moved = destination.is_file() and not source_file.exists()
        intact = hashlib.sha256((destination if moved else source_file).read_bytes()).digest() == hashlib.sha256(payload).digest()
        stamp = (root/'attempt').read_text() if (root/'attempt').exists() else None
        stamp_ok = bool(stamp and stamp.strip().isdigit()) if expected_move else stamp == previous
        gate_called = (root/'gate-called').exists()
        expected_rc = 1 if options.get('mounted') is False else 0
        passed = (moved == expected_move and intact and stamp_ok and
                  gate_called == expected_gate and result.returncode == expected_rc)
        return dict(id=key, scenario=label, passed=passed, moved=moved,
                    checksum_ok=intact, timestamp_ok=stamp_ok, gate_called=gate_called,
                    exit_code=result.returncode, log=result.stdout+result.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory for JSON and HTML reports')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = [execute(case) for case in SCENARIOS]
    report = dict(simulation=True, live_unraid_verified=False, scenarios=rows)
    (args.output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    items = ''.join('<tr><td>'+html.escape(row['scenario'])+'</td><td>'+('PASS' if row['passed'] else 'FAIL')+
                    '</td><td>'+('Áthelyezve' if row['moved'] else 'Halasztva')+
                    '</td><td><details><summary>Napló</summary><pre>'+html.escape(row['log'])+'</pre></details></td></tr>' for row in rows)
    page = '''<!doctype html><html lang="hu"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>FejesMover • Szimuláció</title><style>
body{font:16px system-ui;background:#101820;color:#edf4f6;max-width:1100px;margin:40px auto;padding:20px}
h1{color:#ff983f}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:16px;border-bottom:1px solid #34434d}
pre{white-space:pre-wrap;font-size:12px}p{line-height:1.6}strong{color:#79e2b0}details{max-width:480px}
</style><h1>FejesMover / Szimuláció</h1><p>Valódi védelmi kód, szintetikus NAS-állapotok.
A mozgatás kizárólag ideiglenes tesztfájlokon történik. Ez nem élő Unraid-integrációs teszt.</p>'''
    page += '<p><strong>'+str(sum(row['passed'] for row in rows))+' / '+str(len(rows))+' sikeres forgatókönyv</strong></p>'
    page += '<table><thead><tr><th>Helyzet</th><th>Ellenőrzés</th><th>Tesztfájl</th><th>Bizonyíték</th></tr></thead><tbody>'+items+'</tbody></table></html>'
    (args.output/'index.html').write_text(page)
    for row in rows:
        print(('PASS' if row['passed'] else 'FAIL') + '  ' + row['scenario'])
    print('Report:', args.output/'index.html')
    return 0 if all(row['passed'] for row in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
