# Integration candidate — 2026-10-19

Plugin version: `2026.10.19.92` (experimental beta). Combines protection PR #3,
mode/navigation PR #6 and the separate owner download-counter tool from PR #5.
No automatic main-branch merge or new stable release.

Validation on Unraid 7.3.3 in an isolated temporary filesystem:

- 45 protection/dry-run unit tests, 59 PHP application fixtures, 31 mode guards.
- 12 synthetic movement/deferral scenarios; no live media movement.
- Reproducible XML/checksums, PHP/Python lint, install/reinstall, invalid-runtime
  rejection, invalid-code rejection and uninstall with retained helpers.
- JavaScript pause/refresh and dashboard unavailable/full-cache checks.

Default remains Observer. Demo diagnostics never invoke Docker. Integrity
wiring requires Advanced cache mode, a mounted pool and separate consent.
GET pages never invoke protection commands. Installation creates no schedule.
Uninstall retains helpers, configuration and external protection integrations.
See the protection guide for explicit manual restoration procedures.

Protection diagnostics and the monitor/settings/setup are available in HU, US English and German.

Live plugin-manager install/remove/reinstall passed on the owner NAS in
Observer/cache mode. All 11 installed files matched the manifest; settings,
existing helper hashes, the legacy launcher and configured/active cron remained
unchanged. Read-only diagnostics confirmed the existing File Integrity gate.
The legacy Mover torrent gate remains uninstalled. No real Mover or hashing
was started. Rendered WebGUI acceptance, reboot persistence and real guarded
Mover operation remain pending.
This document records only the completed isolated checks. Community Applications
submission and broad hardware/configuration compatibility remain pending.

The dry-run button was verified through the real NAS WebGUI. It shows seven
read-only conditions and never executes the launcher. Seven dry-run unit tests
cover readiness, simultaneous blockers, missing share, unknown state and no writes.
The owner separately enabled the torrent gate after the first lifecycle test;
the subsequent dry-run update preserved that launcher and both cron files.

Protected file/folder basenames are now opt-in for the authenticated dry-run UI.
Default status and CLI dry-run output remain redacted; full paths and real NAS
filenames are not published in this repository. Live browser verification
confirmed the private list is displayed. Multi-file torrents may show a folder.

The full protection page now has English/German explanatory translations.
Live navigation verified language retention through monitor, settings, setup,
Dashboard and protection for both English and German; Hungarian was restored.
Native plugin page headings follow the selected plugin language.

The notice CSS collision was fixed with plugin-specific class names; the live
package/app tests passed and 2026.10.19.92 was installed. Browser visual
confirmation of this small fix remained blocked by the origin approval gate.
The separate Alpine VM passed real guest reboots after install and removal,
with restored tmpfs runtime, preserved settings/helpers and unchanged NAS
boot ID/protected files. Missing PHP ctype was caught and is now rejected
before activation. See LINUX-VM-ACCEPTANCE.md and its JSON report.
