from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
from localize import compile_page
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/main'
PROJECT='https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor'
version='2026.10.19.1'
files=sorted([*(ROOT/'src').glob('*.page'),*(ROOT/'src').glob('*.php')])
def cdata(s):
    return '<![CDATA['+s.replace(']]>',']]]]><![CDATA[>')+']]>'
parts=[f'''<?xml version="1.0" encoding="UTF-8"?>
<PLUGIN name="fejes.mover.monitor" author="FejesNAS" version="{version}" launch="Tools/FejesMover" min="7.0.0" icon="fa-exchange" pluginURL="{BASE}/fejes.mover.monitor.plg" support="{PROJECT}/issues">
<CHANGES>
### 2026.10.19.1 (beta)
- Add inline country flags to the HU, US English and German language selectors.
### 2026.10.18.3 (beta)
- Add the same Dashboard return button to mode/pool setup and every settings state.
### 2026.10.18.2 (beta)
- Add a visible return button from the detailed monitor to its Dashboard card.
### 2026.10.18.1 (beta)
- Unraid 7.x preflight; observer mode by default, demo and explicit advanced opt-in.
- Select a configured Unraid pool for observation; legacy script editor remains cache-only.
- Persist plugin mode/pool independently; never start Mover from the setup page.
### 2026.10.17.1
- Hungarian, US English and German interfaces with a persistent language selector.
- Correct unavailable/full cache readings, mounted-cache checks and refresh pause state.
- Reject stale checksum manifests during package validation.
### 2026.10.17
- First self-contained public package; Hungarian UI, cache pool required.
- Optional legacy threshold settings, retained only on systems with the existing script.
- Installer validates PHP before activation and preserves local backup files.
</CHANGES>''']
for f in files:
    text=f.read_text(encoding='utf-8')
    parts.append(f'<FILE Name="/tmp/fejes-mover-monitor-{version}/{f.name}"><INLINE>'+cdata(compile_page(text) if f.suffix=='.page' else text)+'</INLINE></FILE>')
script=f'''#!/bin/bash
set -euo pipefail
src=/tmp/fejes-mover-monitor-{version}
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
test -f /etc/unraid-version && test -d /usr/local/emhttp && test -d /boot/config || {{ echo 'Requires Unraid 7.x WebGUI and boot configuration.' >&2; exit 1; }}
php -r '$v=parse_ini_file("/etc/unraid-version")["version"]??""; exit(PHP_VERSION_ID>=80000 && preg_match("/^7[.]/",$v)?0:1);' || {{ echo 'Unsupported Unraid/PHP version (requires Unraid 7.x, PHP 8+).' >&2; exit 1; }}
for name in {' '.join(f.name for f in files)}; do
  php -l "$src/$name" >/dev/null
 done
install -d -m 0755 "$dst"
for name in {' '.join(f.name for f in files)}; do
  install -m 0644 "$src/$name" "$dst/$name"
 done
printf '%s\\n' 'Fejes Mover Monitor installed. Open Tools / Mover figyelo.'
'''
parts.append('<FILE Run="/bin/bash"><INLINE>'+cdata(script)+'</INLINE></FILE>')
remove=f'''#!/bin/bash
set -euo pipefail
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
# Remove only runtime files owned by this plugin. Preserve settings and backups.
for name in {' '.join(f.name for f in files)}; do
  rm -f -- "$dst/$name"
done
rmdir "$dst" 2>/dev/null || true
printf '%s\\n' 'Fejes Mover Monitor removed; local configuration and backups preserved.'
'''
parts.append('<FILE Run="/bin/bash" Method="remove"><INLINE>'+cdata(remove)+'</INLINE></FILE>')
parts.append('</PLUGIN>\n')
manifest='\n'.join(parts)
ET.fromstring(manifest)
(ROOT/'fejes.mover.monitor.plg').write_text(manifest, encoding='utf-8', newline='\n')
(ROOT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in [ROOT/'fejes.mover.monitor.plg',*files,ROOT/'src/translations.json']), encoding='utf-8', newline='\n')
print('Built self-contained manifest; XML parsed successfully.')
