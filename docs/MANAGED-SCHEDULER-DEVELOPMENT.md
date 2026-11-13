# Managed scheduler development — not released

This branch introduces validated, opt-in automation settings bound to a specific
pool/share/container profile and a scheduler tick that delegates to the existing
guarded executor. Without automation.json, the existing installation retains its
legacy launcher behavior. A present but invalid/disabled managed configuration
cannot silently fall back to legacy authorization.

The dry-run and executor can now read threshold and cooldown from this managed
configuration without a User Scripts launcher. Existing advanced-mode, capacity,
backup, parity, scrub, integrity, torrent and native file verification remain.

Implemented: Hungarian/English/German CSRF-protected settings page, exclusive-lock
configuration writes, private backups, disable-first cron updates, install-time
restoration and removal of only the plugin-owned cron entry. The configure
command installs the opted-in schedule; preview-cron remains read-only.
The monitor verifies the exact active managed cron entry and displays the saved
interval; disabled, invalid, missing and duplicate active entries are distinguished
from a confirmed schedule. Demo mode does not inspect managed automation.

Not yet complete: legacy schedule migration and install/update/remove/reboot VM
acceptance. Existing cache/Btrfs and File Integrity requirements remain in force.
No claim of unattended general compatibility is made. Keep this branch out of
the stable update channel until these gates pass.
