# Unraid test plan — Universal Mover Monitor

Status: **NOT YET TESTED ON UNRAID**. Do not install the development package on a production NAS.

## Functional
- [ ] Confirm Tools page loads in Unraid 7.0 and newer.
- [ ] Confirm dashboard tile appears without affecting other tiles.
- [ ] Check Mover idle, active, and stale PID states.
- [ ] Check pool detection with zero, one, and multiple pools; use non-`cache` pool names.
- [ ] Check missing /var/log/syslog and inaccessible /proc data.
- [ ] Confirm refresh stops when tab is hidden and handles session expiry.
- [ ] Confirm output escapes paths and log lines.
- [ ] Confirm no Mover operation, script modification, or background job is started.

## Packaging
- [ ] Publish versioned source archive and SHA-256.
- [ ] Replace all placeholder URLs in .plg with working release links.
- [ ] Verify clean install, reboot persistence, update, uninstall, and rollback.
- [ ] Check Unraid Community Applications submission requirements and prepare metadata.
- [ ] Submit only after successful test results.

## Compatibility note
The FejesNAS-specific `Filmek_Mover_Threshold` script is not required by the universal edition.
