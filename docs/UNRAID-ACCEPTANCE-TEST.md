# v0.1.0 Unraid acceptance test (isolated VM only)

Status: **BLOCKED — no v0.1.0 GitHub Release asset, no verified Unraid VM test.**

Do not install this development build on the production FejesNAS. The current production plugin includes a settings page not included in this build, and GitHub development PHP pages differ from the PHP files in the local test archive.

## Preconditions

1. Create a disposable Unraid 7.3.3 test VM, using a legitimate test license and test disks; never attach production disks or the production flash device.
2. Snapshot the VM and capture `/boot/config/plugins` and `/usr/local/emhttp/plugins` state.
3. Publish a release asset `fejes-mover-monitor-v0.1.0.tar.gz` with the exact checksum recorded in the PLG, or rebuild the PLG/checksum after synchronizing source.
4. Verify the release URL returns the archive and its SHA-256 matches the PLG.
5. Verify `php -l` on both page files; validate PLG XML; inspect the inline installer and uninstall behavior.

## Acceptance tests

- Install from the published .plg on the disposable VM.
- Verify Tools > Mover monitor opens without PHP errors.
- Verify dashboard tile displays while mover is idle and while it runs.
- Verify pools other than `cache` and a missing `/var/run/mover.pid` are handled.
- Verify refresh works without duplicate tiles or JavaScript errors.
- Verify the plugin is read-only: no mover start/stop, file moves, share changes, or scheduling changes.
- Verify reboot persistence and clean uninstall.
- Verify upgrading from an older installation preserves settings only if migration is explicitly supported.
- Verify syslog and web server logs contain no plugin errors.
- Roll back the VM snapshot.

## Current evidence

The Debian isolated installer test passed XML parsing, SHA-256, PHP syntax checks, staging and invalid archive rejection. **This is not an Unraid installation test.** The v0.1.0 release was confirmed missing on 2026-10-17.

Release/Community Applications submission must remain on hold until all acceptance tests are documented as passed.
