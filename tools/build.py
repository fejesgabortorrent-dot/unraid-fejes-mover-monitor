from pathlib import Path
import hashlib
import xml.etree.ElementTree as ET
from localize import compile_page
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/main'
PROJECT='https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor'
version='2026.11.14.3'
files=sorted([*(ROOT/'src').glob('*.page'),*(ROOT/'src').glob('*.php')])
helpers=[ROOT/'tools'/name for name in ('torrent_preflight.py','torrent_capacity_guard.py','qbit_capacity_adapter.py','integrity_preflight.py','wire_integrity_cron.py','fejes_service.py','wire_mover_gate.py','selection_policy.py','selective_profile.py','selective_preview.py','selective_mover.py','wire_selective.py','managed_schedule.py')]

def cdata(s):
    return '<![CDATA['+s.replace(']]>',']]]]><![CDATA[>')+']]>'
parts=[f'''<?xml version="1.0" encoding="UTF-8"?>
<PLUGIN name="fejes.mover.monitor" author="FejesNAS" version="{version}" launch="Tools/FejesMover" min="7.0.0" icon="fa-exchange" pluginURL="{BASE}/fejes.mover.monitor.plg" support="{PROJECT}/issues">
<CHANGES>
### 2026.11.14.3 (managed scheduler cron refresh compatibility)
- Run Unraid's cron refresh helper through Bash so CRLF shebangs do not defer the managed schedule.
- Use the main branch as the plugin update channel.
### 2026.11.14.2 (managed scheduler install recovery)
- Keep plugin installation available when optional cron restoration is deferred; leave automated movement guarded.
### 2026.11.14.1 (managed scheduler development candidate)
- Add an opt-in plugin-managed schedule with validated profile binding and fail-closed settings.
- Add the multilingual automation page and exact active-schedule status; keep the stable channel unchanged.
- Development candidate; isolated VM installation and reboot recovery passed on 2026-11-14.
### 2026.11.13.1 (maintenance recovery update)
- Defer integrity scan races after fully verified files when torrent continuity is verified.
- Preserve cooldown and evidence; uncertain movement and historical latches remain protected.
### 2026.11.12.1 (stable UI update)
- Show the locally installed version on every Mover view, including the profile and dashboard card.
- Report unavailable version data explicitly; never infer installation state from Community Applications.
### 2026.11.11.2 (stable for documented Unraid 7 scope)
- Full guarded movement, destination SHA-256, source absence, torrent recheck and isolated peer transfer passed on 2026-11-12.
- After reboot, missing scrub history requires a fresh successful scrub; unattended recovery is not claimed.
- Earlier candidate notes below describe historical validation status.
- Bound blocker details to five per waiting row; excluded or directly blocked rows do not repeat group causes.
### 2026.11.11.1 (test release candidate)
- Keep independent root files separate; preserve folder, exact-name sidecar and torrent-owner units.
- Show concrete unit blockers and separate open-file/stability observations.
- Full guarded positive acceptance remains pending.
### 2026.11.10.3 (test release candidate)
- Use the validated selective profile for scheduled integrity torrent preflight.
### 2026.11.10.2 (test release candidate)
- Normalize physical pool paths without duplicating the configured share name.
### 2026.11.10.1 (test release candidate)
- Preserve inspection evidence and distinguish preflight deferral from native movement intent.
- Retain profile, directory unit and batch protections.
- Add private per-file checksum evidence; full VM acceptance remains pending.
### 2026.10.28.4 (unpublished combined candidate)
- Add a guarded multilingual profile editor for selective scope configuration.
- Defer a fresh integrity-scan conflict before the first native move without creating an inspection latch.
- Retain inspection for partial batches, interrupted runs and existing unresolved failures.
- Use shared contrast-checked semantic palettes and consistent hover/focus feedback across all pages.
### 2026.10.28.3 (RC1 appearance hotfix)
- Repair mixed light/dark surfaces and low-contrast text without changing any movement helper or inspection state.
### 2026.10.27.4 (RC1 reliability and controls)
- Keep the shared appearance when following the Unraid theme.
- Align flag-only language, settings and detail controls with keyboard labels.
- Explain unavailable torrent queries and retain private native process failure evidence.
### 2026.10.26.6 (RC1 support strip)
- Add a shared grey PayPal strip with white border and optional coffee, beer, pizza and custom support links.
### 2026.10.26.5 (RC1 dashboard and diagnostics update)
- Use a non-submitting button for Back to top; never open a new tab.
- Keep navigation accessible while scrolling and align controls across all plugin pages.
- Add a report summary and accessible hover/touch help to the dashboard.
- Show unsaved numeric settings and invalid-range feedback.
- Preserve private failure details; keep movement guards and schedules unchanged.
### 2026.10.25.4 (RC1 usability update)
- Add accessible dismissible help bubbles, a user guide and project history to the selective interface.
- Reduce explanatory clutter while keeping manual-action and safety warnings visible.
### 2026.10.25.3 (RC1 appearance update)
- Refine flat controls, hover and focus feedback, and dashboard appearance selector spacing.
- Presentation only; movement rules, schedules and safety checks are unchanged.
### 2026.10.25.2 (RC1)
- First release candidate: larger eligible files first within the existing ratio-priority groups.
- Keep the 8-file cap, selected byte cap, age, active/open-content checks and maintenance guards.
- Document the supported owner-tested scope and remaining acceptance limits.
- Older experimental beta notes are retained in Git history.
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
# Restore only previously configured opt-in scheduling; absent settings stay off.
if command -v update_cron >/dev/null; then
  # Schedule restoration is best-effort during plugin installation. A failed
  # refresh must not roll back the monitoring UI; the executor remains guarded
  # by the saved opt-in settings and the next explicit save can retry it.
  if ! python3 "$tools/managed_schedule.py" sync; then
    printf '%s\\n' 'WARNING: managed schedule sync was deferred; no automated move was enabled.' >&2
  fi
fi
printf '%s\\n' 'Fejes Mover Monitor installed. Open Tools / Mover figyelo.'
'''
parts.append('<FILE Run="/bin/bash"><INLINE>'+cdata(script)+'</INLINE></FILE>')
remove=f'''#!/bin/bash
set -euo pipefail
dst=/usr/local/emhttp/plugins/fejes.mover.monitor
# Disable this plugin's own cron entry before removing its runtime.
if command -v update_cron >/dev/null; then
  python3 /boot/config/plugins/fejes.mover.monitor/tools/managed_schedule.py remove-cron
fi
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
