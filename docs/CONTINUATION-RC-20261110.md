# FejesMover release-candidate continuation

Updated 2026-11-10, owner-authorized work restricted to FejesMover-Test VM. Production NAS unchanged.

## Current candidate

Installed boot/runtime version: 2026.11.10.3. Package source commit dfc9f6b19ca28d6fa63b7ed1c86bc7dbd794f081. Later branch commits only change acceptance scripts. Draft PR #37 contains the candidate; do not merge/release as stable until remaining gates pass.

Local validation: 169 Python cases and package reproducibility/XML/PHP lint/isolated lifecycle passed. Seven JavaScript suites passed before the subsequent Python-only profile fix.

Actual guest results:
- .3 installation succeeded.
- Fresh private 16 MiB torrent and honest inventory prepared around 21:08–21:12 guest time on Nov 10; no age/time overrides.
- Real API outage: isolated fm-qbit stopped, installed runner deferred with zero movement, intact source SHA256, no inspection latch, container restarted.
- File Integrity 2025.11.14 installed from official unraid/dynamix plugin.
- Protection setup completed using upstream File Integrity handler. Real watcher and gated monthly schedule (day 1, 03:17) configured. Real cache scrub completed without errors (16.38 MiB at that time).
- Readiness report showed all nine guards pass: backup, capacity, cooldown, integrity, mount, mover, namespace, open_files, parity.
- Installed runner then returned nothing_eligible, candidate_count=0, skipped protected_content=1, moved_files/bytes=0, active_file_started=false, requires_inspection=false. This is no-move evidence; not full positive guarded acceptance.

## Persistent VM state

`/mnt/disk1/fm-acceptance/guarded/current.json`: new guarded torrent and baseline (private). Do not replace or rerun prepare.

`/mnt/disk1/fm-acceptance/current.json`: earlier successful component/peer-transfer test; preserve separately.

Guarded directory also holds boot-before-guarded.tgz, timestamped boot-before-protection archives and private API/run reports. Files are private, not GitHub artifacts.

Docker persistence now corrected: enabled=yes, existing /mnt/disk1/system/docker/docker.img, size=4 GiB. Existing image attachment verified before setting; no second image created. fm-qbit and fm-peer have unless-stopped restart policies. Both running at last readiness report. Reboot survival is NOT verified yet.

Current VM checkout: /tmp/fm-rc, detached; volatile. Original /tmp/fm and /tmp/fm-seed also exist. Save updated source archive to the array before reboot. Current installed helpers live under /boot/config/plugins/fejes.mover.monitor/tools.

## Authentication finding

The test client's successful login can return an empty HTTP 200 body. Authentication was wrongly reported as rejected although a cookie-authenticated app/version returned v5.3.0. Latest lab helper verifies authenticated version instead of relying on body text and scopes temporary-password lookup to the current container startup. Credentials/authentication remain enabled and are never published. Latest fixed harness must be fetched before reboot/testing.

## Next gates

1. Fetch latest PR #37 branch and run testlab/integrity_deferral.py. It explicitly suspends/resumes a real lab Bunker process to make presence-deferral deterministic; label this narrowly, not a mid-native scan-race test. Execution not yet certified in this checkpoint.
2. Persist updated harness archive, then verify controlled VM reboot and restore the checkout if needed. Check array, plugins, Docker, authenticated APIs, integrity watcher/cron and source evidence after boot. No production reboot.
3. On or after genuine one-day readiness, run testlab/guarded_acceptance.py status and read private forecast for the actual latest age-ready time. Do not fake timestamps or re-prepare.
4. Run the installed guarded runner only after all real guards pass and source/torrent are genuinely eligible. Verify destination hash/metadata, source absence, same torrent path/recheck, then real peer transfer again using a harness adapted for guarded_moved state (existing component transfer expects component_moved; do not call component move).
5. Record results and publish stable only once the claimed scope passes. Broad compatibility, production VPN/tracker credit and power-loss tests remain unverified.

Agreed future direction is separately recorded on main in docs/DEVELOPMENT-DIRECTION.md: stable Unraid 7 first, Docker UI plus restricted host helper next, then tested Unraid 8 support.
