"""Validate the package and exercise its scripts in a temporary filesystem."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import sys
import xml.etree.ElementTree as ET
from localize import compile_page

root = Path(__file__).resolve().parents[1]
if not shutil.which('php'):
    raise SystemExit('PHP CLI is required for lint and installer checks')
manifest = root / 'fejes.mover.monitor.plg'
generated = [manifest, root / 'SHA256SUMS']
before = {p: p.read_bytes() for p in generated}
try:
    subprocess.run([sys.executable, str(root / 'tools/build.py')], check=True)
    for p in generated:
        assert before[p] == p.read_bytes(), f'Generated {p.name} is stale'
finally:
    for p, contents in before.items():
        p.write_bytes(contents)
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
            target.write_text(node.findtext('INLINE'), encoding='utf-8', newline='\n')
            source=(root / 'src' / target.name).read_text(encoding='utf-8')
            assert target.read_text(encoding='utf-8') == (compile_page(source) if target.suffix=='.page' else source)
    (sandbox/'unraid-version').write_text('version="7.3.3"\n')
    (sandbox/'emhttp').mkdir()
    (sandbox/'boot-config').mkdir()
    def script(method):
        node = next(n for n in nodes if n.attrib.get('Run') == '/bin/bash' and n.attrib.get('Method', '') == method)
        text = node.findtext('INLINE')
        text = text.replace('/tmp/fejes-mover-monitor-' + plugin.attrib['version'], sandbox.as_posix())
        text = text.replace('/usr/local/emhttp/plugins/fejes.mover.monitor', destination.as_posix())
        text = text.replace('/etc/unraid-version', (sandbox/'unraid-version').as_posix())
        text = text.replace('/usr/local/emhttp', (sandbox/'emhttp').as_posix())
        text = text.replace('/boot/config', (sandbox/'boot-config').as_posix())
        subprocess.run(['bash', '-n'], input=text, text=True, check=True)
        return subprocess.run(['bash'], input=text, text=True, capture_output=True)
    (sandbox/'unraid-version').write_text('version="6.12.0"\n')
    assert script('').returncode != 0 and not destination.exists(), 'Unsupported OS must fail before install'
    (sandbox/'unraid-version').write_text('version="7.3.3"\n')
    assert script('').returncode == 0, 'Clean install failed'
    installed = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert script('').returncode == 0, 'Repeated install failed'
    assert installed == {p.name: p.read_bytes() for p in destination.iterdir()}
    (sandbox/'unraid-version').write_text('version="8.0.0"\n')
    assert script('').returncode != 0 and installed == {p.name:p.read_bytes() for p in destination.iterdir()}, 'Unsupported update changed runtime'
    (sandbox/'unraid-version').write_text('version="7.3.3"\n')
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
