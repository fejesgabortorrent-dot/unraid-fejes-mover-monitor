"""Validate the package and exercise its scripts in a temporary filesystem."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
if not shutil.which('php'):
    raise SystemExit('PHP CLI is required for lint and installer checks')
manifest = root / 'fejes.mover.monitor.plg'
before = manifest.read_bytes()
subprocess.run(['python3', str(root / 'tools/build.py')], check=True)
assert before == manifest.read_bytes(), 'Generated manifest is stale'
for line in (root / 'SHA256SUMS').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
plugin = ET.parse(manifest).getroot()
assert plugin.attrib['min'] == '7.0.0'
profile = ET.parse(root / 'ca_profile.xml').getroot()
assert profile.findtext('Profile', '').strip()
wrapper = ET.parse(root / 'plugins/fejes-mover-monitor.xml').getroot()
assert wrapper.findtext('PluginURL') == plugin.attrib['pluginURL']
for page in sorted((root / 'src').glob('*.page')):
    subprocess.run(['php', '-l', str(page)], check=True)

with tempfile.TemporaryDirectory(prefix='fejes-mover-check-') as directory:
    sandbox = Path(directory)
    destination = sandbox / 'runtime'
    helper_destination = sandbox / 'config/tools'
    nodes = plugin.findall('FILE')
    for node in nodes:
        if 'Name' in node.attrib:
            target = sandbox / Path(node.attrib['Name']).name
            target.write_text(node.findtext('INLINE'))
            folder = 'src' if target.suffix == '.page' else 'tools'
            assert target.read_bytes() == (root / folder / target.name).read_bytes()
    def script(method):
        node = next(n for n in nodes if n.attrib.get('Run') == '/bin/bash' and n.attrib.get('Method', '') == method)
        text = node.findtext('INLINE')
        text = text.replace('/tmp/fejes-mover-monitor-' + plugin.attrib['version'], str(sandbox))
        text = text.replace('/usr/local/emhttp/plugins/fejes.mover.monitor', str(destination))
        text = text.replace('/boot/config/plugins/fejes.mover.monitor/tools', str(helper_destination))
        # Exercise real uninstall code with its cron root redirected away from NAS paths.
        harness = sandbox / 'unwire.py'
        harness.write_text('import sys\nsys.dont_write_bytecode=True\nfrom pathlib import Path\nsys.path.insert(0, '+repr(str(helper_destination))+')\nimport wire_integrity_cron as w\nw.ROOT=Path('+repr(str(sandbox/'absent-integrity'))+')\nw.main(remove=True)\n')
        text = text.replace('python3 "$tools/wire_integrity_cron.py" --remove', 'python3 '+str(harness))
        mover_harness = sandbox / 'unwire-mover.py'
        mover_harness.write_text('import sys\nsys.dont_write_bytecode=True\nfrom pathlib import Path\nsys.path.insert(0, '+repr(str(helper_destination))+')\nimport wire_mover_gate as w\nw.LAUNCHER=Path('+repr(str(sandbox/'absent-launcher'))+')\nw.main(["--remove"])\n')
        text = text.replace('python3 "$tools/wire_mover_gate.py" --remove', 'python3 '+str(mover_harness))
        subprocess.run(['bash', '-n'], input=text, text=True, check=True)
        return subprocess.run(['bash'], input=text, text=True, capture_output=True)
    assert script('').returncode == 0, 'Clean install failed'
    helper_bytes = {p.name:p.read_bytes() for p in helper_destination.iterdir()}
    assert len(helper_bytes) == 5, 'Protection helpers missing'
    assert all((p.stat().st_mode & 0o777) == 0o700 for p in helper_destination.iterdir())
    installed = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert script('').returncode == 0, 'Repeated install failed'
    assert installed == {p.name: p.read_bytes() for p in destination.iterdir()}
    assert helper_bytes == {p.name:p.read_bytes() for p in helper_destination.iterdir()}, 'Repeat install changed helpers'
    helper = sandbox / 'fejes_service.py'
    good_helper = helper.read_text()
    helper.write_text('def broken(:')
    assert script('').returncode != 0, 'Invalid Python must be rejected'
    assert helper_bytes == {p.name:p.read_bytes() for p in helper_destination.iterdir()}, 'Failed Python lint changed helpers'
    helper.write_text(good_helper)
    page = sandbox / 'FejesMover.page'
    page.write_text('<?php function broken( {')
    assert script('').returncode != 0, 'Invalid PHP must be rejected'
    assert installed == {p.name: p.read_bytes() for p in destination.iterdir()}, 'Failed lint changed installation'
    unrelated = destination / 'preserved-local-config.txt'
    unrelated.write_text('preserve')
    assert script('remove').returncode == 0, 'Uninstall failed'
    assert list(destination.iterdir()) == [unrelated], 'Uninstall removed unrelated data'
    assert helper_bytes == {p.name:p.read_bytes() for p in helper_destination.iterdir()}, 'Uninstall removed retained helpers'
print('PASS: reproducible manifest, checksums, XML, PHP lint, isolated install/update/rejection/remove')
print('Unraid WebGUI, reboot persistence and live Mover behavior remain untested.')
