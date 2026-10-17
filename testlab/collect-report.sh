#!/bin/bash
set -euo pipefail
[[ -f /etc/unraid-version && "$(hostname -s)" == FejesMover-Test ]] || { echo 'Run only inside FejesMover-Test.' >&2; exit 1; }
printf 'FejesMover test report\nUTC: '; date -u +%FT%TZ
cat /etc/unraid-version
printf '\nRuntime pages\n'
for name in FejesMover.page FejesMover.Dashboard.page FejesMoverSettings.page; do
 file=/usr/local/emhttp/plugins/fejes.mover.monitor/$name
 if [[ -f "$file" ]]; then sha256sum "$file"; php -l "$file"; else printf 'MISSING %s\n' "$name"; fi
done
printf '\nCache mount\n'; findmnt -n -o TARGET,FSTYPE /mnt/cache || true
printf '\nMover PID presence: '; if [[ -f /var/run/mover.pid ]]; then echo present; else echo absent; fi
printf '\nThis report does not prove WebGUI, reboot, uninstall or Mover functionality.\n'
