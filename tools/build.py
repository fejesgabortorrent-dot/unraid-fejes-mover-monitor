from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
from localize import compile_page
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/main'
PROJECT='https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor'
version='2026.10.23.997'
files=sorted([*(ROOT/'src').glob('*.page'),*(ROOT/'src').glob('*.php')])
helpers=[ROOT/'tools'/name for name in ('torrent_preflight.py','integrity_preflight.py','wire_integrity_cron.py','fejes_service.py','wire_mover_gate.py','selection_policy.py','selective_preview.py','selective_mover.py','wire_selective.py')]

def cdata(s):
    return '<![CDATA['+s.replace(']]>',']]]]><![CDATA[>')+']]>'
parts=[f'''<?xml version="1.0" encoding="UTF-8"?>
<PLUGIN name="fejes.mover.monitor" author="FejesNAS" version="{version}" launch="Tools/FejesMover" min="7.0.0" icon="fa-exchange" pluginURL="{BASE}/fejes.mover.monitor.plg" support="{PROJECT}/issues">
<CHANGES>
### 2026.10.23.997
- Add a browser-persisted Follow Unraid / Light / Dark appearance selector scoped to plugin surfaces.
- Keep host Unraid styling and all movement settings unchanged.
### 2026.10.23.996
- Group monitoring, queue filters, settings and confirmed manual actions into separate sections.
- Add summary cards, filename search, status/video filters and expandable full paths.
### 2026.10.23.995
- Keep long filenames and blocker explanations inside fixed table columns under Unraid themes.
### 2026.10.23.994
- Add a private per-file waiting table with size, earliest age date, countdown and blockers.
- Include verified cache arrival and quiet torrent completion in age forecasts; avoid promising start or finish times.
- Keep table GET refreshes read-only and use timestamped snapshots; movement guards and schedules are unchanged.
### 2026.10.23.993
- Preserve every batch-limit skip in the final selective movement report.
- Distinguish files larger than the fixed 16 GiB limit from files deferred by this batch.
- Report zero-movement runs explicitly; preserve all movement guards and limits.
### 2026.10.23.992
- Add opt-in age-filtered native movement for cache/Filmek, excluding young, incomplete, active and open content.
- Keep Observer default and preserve existing schedules on install. Authenticated Advanced mode supports manual start.
- Verify SHA256, metadata and torrent continuity after movement; stop for inspection after movement errors.
- Owner NAS tests passed on self-created files; production media movement and broad compatibility remain unverified.
### 2026.10.19.93 (beta)
- Show the active quarter-hour automation schedule and direct settings access.
### 2026.10.19.92 (beta)
- Reject missing PHP ctype before activating any runtime file.
### 2026.10.19.91 (beta)
- Namespace protection notices to avoid overlapping Unraid alert icons.
### 2026.10.19.9 (beta)
- Complete protection-page translations and translate the native page heading.
### 2026.10.19.8 (beta)
- Show protected content basenames only in explicitly requested private dry-run UI.
### 2026.10.19.7 (beta)
- Fail dry-run readiness closed when the required legacy share is unavailable.
### 2026.10.19.6 (beta)
- Add a read-only dry-run button with seven visible start conditions.
### 2026.10.19.5 (beta)
- Use the FM icon as favicon on Fejes Mover Tools pages.
### 2026.10.19.4 (beta)
- Increase FM icon background and drive contrast.
### 2026.10.19.3 (beta)
- Embed the FM Fejes Mover icon in the Dashboard header.
### 2026.10.19.2 (beta)
- Combine protection diagnostics with observer/demo modes and current navigation.
- Require advanced cache mode and explicit consent for integrity schedule wiring.
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
for f in helpers:
    parts.append(f'<FILE Name="/tmp/fejes-mover-monitor-{version}/{f.name}"><INLINE>'+cdata(f.read_text(encoding='utf-8'))+'</INLINE></FILE>')
script=f'''#!/bin/bash
set -euo pipefail
src=/tmp/fejes-mover-monitor-{version}
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
test -f /etc/unraid-version && test -d /usr/local/emhttp && test -d /boot/config || {{ echo 'Requires Unraid 7.x WebGUI and boot configuration.' >&2; exit 1; }}
php -r '$v=parse_ini_file("/etc/unraid-version")["version"]??""; exit(PHP_VERSION_ID>=80000 && function_exists("ctype_digit") && preg_match("/^7[.]/",$v)?0:1);' || {{ echo 'Unsupported Unraid/PHP version (requires Unraid 7.x, PHP 8+ and ctype).' >&2; exit 1; }}
tools=/boot/config/plugins/fejes.mover.monitor/tools
command -v python3 >/dev/null || exit 1
for name in {' '.join(f.name for f in helpers)}; do
  python3 -c 'import sys; compile(open(sys.argv[1], "rb").read(), sys.argv[1], "exec")' "$src/$name"
done
for name in {' '.join(f.name for f in files)}; do
  php -l "$src/$name" >/dev/null
 done
install -d -m 0755 "$dst"
install -d -m 0700 "$tools"
for name in {' '.join(f.name for f in helpers)}; do
  if [[ -f "$tools/$name" ]] && ! cmp -s "$src/$name" "$tools/$name"; then
    backup=$(mktemp "$tools/$name.before-XXXXXXXX")
    cp -p -- "$tools/$name" "$backup"
  fi
  install -m 0700 "$src/$name" "$tools/$name"
done
for name in {' '.join(f.name for f in files)}; do
  install -m 0644 "$src/$name" "$dst/$name"
 done
printf '%s\\n' 'Fejes Mover Monitor installed. Open Tools / Mover figyelo.'
'''
parts.append('<FILE Run="/bin/bash"><INLINE>'+cdata(script)+'</INLINE></FILE>')
remove=f'''#!/bin/bash
set -euo pipefail
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
# Keep shared helpers and external schedule wiring intact.
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
(ROOT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in [ROOT/'fejes.mover.monitor.plg',*files,*helpers,ROOT/'src/translations.json',ROOT/'icon.svg',ROOT/'icon.png']), encoding='utf-8', newline='\n')
print('Built self-contained manifest; XML parsed successfully.')
