from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/main'
PROJECT='https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor'
version='2026.10.18'
files=sorted((ROOT/'src').glob('*.page'))
helpers=[ROOT/'tools'/name for name in ('torrent_preflight.py','integrity_preflight.py','wire_integrity_cron.py','fejes_service.py','wire_mover_gate.py')]
def cdata(s):
    return '<![CDATA['+s.replace(']]>',']]]]><![CDATA[>')+']]>'
parts=[f'''<?xml version="1.0" encoding="UTF-8"?>
<PLUGIN name="fejes.mover.monitor" author="FejesNAS" version="{version}" launch="Tools/FejesMover" min="7.0.0" icon="fa-exchange" pluginURL="{BASE}/fejes.mover.monitor.plg" support="{PROJECT}/issues">
<CHANGES>
### 2026.10.18
- Bundle torrent, scheduled File Integrity and guarded legacy Mover helpers.
- Add shared protection diagnostics and opt-in integrity schedule wiring.
- Restore integrated File Integrity cron before uninstall; preserve backups.
### 2026.10.17
- First self-contained public package; Hungarian UI, cache pool required.
- Optional legacy threshold settings, retained only on systems with the existing script.
- Installer validates PHP before activation and preserves local backup files.
</CHANGES>''']
for f in files:
    parts.append(f'<FILE Name="/tmp/fejes-mover-monitor-{version}/{f.name}"><INLINE>'+cdata(f.read_text())+'</INLINE></FILE>')
for f in helpers:
    parts.append(f'<FILE Name="/tmp/fejes-mover-monitor-{version}/{f.name}"><INLINE>'+cdata(f.read_text())+'</INLINE></FILE>')
script=f'''#!/bin/bash
set -euo pipefail
src=/tmp/fejes-mover-monitor-{version}
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
tools=/boot/config/plugins/fejes.mover.monitor/tools
command -v python3 >/dev/null || {{ echo 'Python 3 is required by the protection helpers.'; exit 1; }}
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
remove='''#!/bin/bash
set -euo pipefail
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
tools=/boot/config/plugins/fejes.mover.monitor/tools
# Restore the owned cron integration before removing UI. Helpers stay available
# for separately configured launchers and for recovery. No API/hashing required.
if [[ -f "$tools/wire_mover_gate.py" ]]; then
  python3 "$tools/wire_mover_gate.py" --remove
fi
if [[ -f "$tools/wire_integrity_cron.py" ]]; then
  python3 "$tools/wire_integrity_cron.py" --remove
fi
# Remove only runtime files owned by this plugin. Preserve settings and backups.
for name in FejesMover.page FejesMover.Dashboard.page FejesMoverSettings.page FejesMoverProtection.page; do
  rm -f -- "$dst/$name"
done
rmdir "$dst" 2>/dev/null || true
printf '%s\\n' 'Fejes Mover Monitor removed; local configuration and backups preserved.'
'''
parts.append('<FILE Run="/bin/bash" Method="remove"><INLINE>'+cdata(remove)+'</INLINE></FILE>')
parts.append('</PLUGIN>\n')
manifest='\n'.join(parts)
ET.fromstring(manifest)
(ROOT/'fejes.mover.monitor.plg').write_text(manifest)
(ROOT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n' for p in [ROOT/'fejes.mover.monitor.plg',*files,*helpers]))
print('Built self-contained manifest; XML parsed successfully.')
