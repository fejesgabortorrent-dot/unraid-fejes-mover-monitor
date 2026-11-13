# Managed scheduler development — not released

This branch introduces validated, opt-in automation settings bound to a specific
pool/share/container profile and a scheduler tick that delegates to the existing
guarded executor. Without automation.json, the existing installation retains its
legacy launcher behavior. A present but invalid/disabled managed configuration
cannot silently fall back to legacy authorization.

The dry-run and executor can now read threshold and cooldown from this managed
configuration without a User Scripts launcher. Existing advanced-mode, capacity,
backup, parity, scrub, integrity, torrent and native file verification remain.

Not yet complete: authenticated UI, atomic configuration and cron lifecycle,
legacy schedule migration, install/update/remove/reboot VM acceptance. The cron
preview prints a proposed entry only; no command in this branch installs it.
No claim of unattended general compatibility is made. Keep this branch out of
the stable update channel until these gates pass.
