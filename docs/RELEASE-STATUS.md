# Integration candidate — 2026-10-19

Plugin version: `2026.10.19.5` (experimental beta). Combines protection PR #3,
mode/navigation PR #6 and the separate owner download-counter tool from PR #5.
No automatic main-branch merge or new stable release.

Validation on Unraid 7.3.3 in an isolated temporary filesystem:

- 38 protection unit tests, 50 PHP application fixtures, 31 mode guards.
- 12 synthetic movement/deferral scenarios; no live media movement.
- Reproducible XML/checksums, PHP/Python lint, install/reinstall, invalid-runtime
  rejection, invalid-code rejection and uninstall with retained helpers.
- JavaScript pause/refresh and dashboard unavailable/full-cache checks.

Default remains Observer. Demo diagnostics never invoke Docker. Integrity
wiring requires Advanced cache mode, a mounted pool and separate consent.
GET pages never invoke protection commands. Installation creates no schedule.
Uninstall retains helpers, configuration and external protection integrations.
See the protection guide for explicit manual restoration procedures.

Protection diagnostic explanations are currently Hungarian; the existing
monitor/settings/setup remain available in HU, US English and German.

Live plugin-manager install/remove/reinstall passed on the owner NAS in
Observer/cache mode. All 11 installed files matched the manifest; settings,
existing helper hashes, the legacy launcher and configured/active cron remained
unchanged. Read-only diagnostics confirmed the existing File Integrity gate.
The legacy Mover torrent gate remains uninstalled. No real Mover or hashing
was started. Rendered WebGUI acceptance, reboot persistence and real guarded
Mover operation remain pending.
This document records only the completed isolated checks. Community Applications
submission and broad hardware/configuration compatibility remain pending.
