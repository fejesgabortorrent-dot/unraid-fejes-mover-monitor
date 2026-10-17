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
    nodes = plugin.findall('FILE')
    for node in nodes:
        if 'Name' in node.attrib:
            target = sandbox / Path(node.attrib['Name']).name
            target.write_text(node.findtext('INLINE'))
            assert target.read_bytes() == (root / 'src' / target.name).read_bytes()
    def script(method):
        node = next(n for n in nodes if n.attrib.get('Run') == '/bin/bash' and n.attrib.get('Method', '') == method)
        text = node.findtext('INLINE')
        text = text.replace('/tmp/fejes-mover-monitor-' + plugin.attrib['version'], str(sandbox))
        text = text.replace('/usr/local/emhttp/plugins/fejes.mover.monitor', str(destination))
        subprocess.run(['bash', '-n'], input=text, text=True, check=True)
        return subprocess.run(['bash'], input=text, text=True, capture_output=True)
    assert script('').returncode == 0, 'Clean install failed'
    installed = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert script('').returncode == 0, 'Repeated install failed'
    assert installed == {p.name: p.read_bytes() for p in destination.iterdir()}
    page = sandbox / 'FejesMover.page'
    page.write_text('<?php function broken( {')
    assert script('').returncode != 0, 'Invalid PHP must be rejected'
    assert installed == {p.name: p.read_bytes() for p in destination.iterdir()}, 'Failed lint changed installation'
    unrelated = destination / 'preserved-local-config.txt'
    unrelated.write_text('preserve')
    assert script('remove').returncode == 0, 'Uninstall failed'
    assert list(destination.iterdir()) == [unrelated], 'Uninstall removed unrelated data'
print('PASS: reproducible manifest, checksums, XML, PHP lint, isolated install/update/rejection/remove')
print('Unraid WebGUI, reboot persistence and live Mover behavior remain untested.')
