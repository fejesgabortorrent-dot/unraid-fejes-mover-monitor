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

## Later verified results

The fixed scanner-presence test passed on 2026-11-10 around 21:30 guest time. It held a real Bunker process with SIGSTOP, confirmed movement deferred without a latch or source change, resumed the scanner, and verified successful exit and the actual SHA256 xattr on its isolated 64 MiB test file. This remains a process-presence test, not a mid-native race claim.

Source archive saved to /mnt/disk1/fm-acceptance/guarded/source.tgz from commit 377032426e58fea87da70eeedc98709818df2ce4; gzip -tv reported OK. The test VM has startArray="no", so manual array startup is expected after reboot. A controlled guest reboot was requested and the VM boot splash was observed around 21:35; post-boot verification is pending.

## Reboot result and exact age forecast

The VM completed a controlled reboot. Array manually started under its existing startArray=no policy. Plugin boot/runtime remained 2026.11.10.3; both lab containers returned running, integrity watcher/pipe and profile/launcher remained present, and the 4 GiB Docker persistence was correct. Source restored from the verified archive into /tmp/fm-rc (plain extracted tree, not a git worktree).

Important qualification: btrfs scrub status after reboot reported no stats available, so the existing guard blocked. A fresh real scrub of the 16.38 MiB testcache completed without errors; only then did the installed runner pass all preflight checks again. This proves recovery with manual revalidation, not unattended reboot-to-ready behavior. Document or improve this lifecycle limitation before claiming automatic recovery.

Post-boot guarded run: nothing_eligible, moved_files/bytes=0, skipped protected_content=1, no blockers and no inspection latch. The harness verified the original source SHA256 before calling the installed runner. The real qBittorrent status was progress=1, stalledUP, source still on cache. Private forecast explicitly says too_young with age_ready_at=1794427698.3176904 (2026-11-11T21:08:18.317690+01:00). This is a forecast only: recheck every guard and actual API/file age before starting movement. No timestamp override or protection bypass.

Remaining: genuine age-qualified positive full-runner move plus post-move recheck and peer transfer, then scope-limited release decision. An unattended-reboot claim is still blocked by the scrub-history limitation.

## Resume checkpoint — 2026-11-11 16:25 CET

Reconnected through the production host's VNC solely to FejesMover-Test. Guest hostname confirmed. Guarded status still seeding_before_move, progress=1, stalledUP, source_on_cache=true. No preparation or timestamp changes performed.

Installed guarded runner re-executed at epoch 1794410721: state=nothing_eligible, moved_files=0, moved_bytes=0, protected_content=1, candidate_count=0, blockers=[], requires_inspection=false, active_file_started=false. Source hash was checked by the harness before the run. Private result saved automatically in the guarded evidence directory. Genuine age readiness remains 2026-11-11 21:08:18 CET; recheck actual eligibility and all guards then.

Added testlab/guarded_transfer.py for the remaining positive acceptance. It requires completed full-runner evidence, source absence, array hash and preserved logical torrent path, then performs a real recheck and isolated peer transfer. It does not move files or bypass age guards. Shared transfer helper now accepts an explicit guarded checkpoint and scope description; existing component defaults remain. This new guarded transfer path has NOT yet run in the VM and must not be claimed as successful.

Before the final move, deliver the latest testlab helpers to the guest (the guest /tmp/fm-rc is an extracted tree, not a git checkout). Preserve both existing current.json files. Run guarded_acceptance.py status and run only with genuine eligibility; after successful full movement, use guarded_transfer.py. Do not run the component mover or re-prepare. No stable release yet.

Validation limitation on this resumed workspace: PHP CLI is no longer installed. The attempted full unittest run did not pass (32 errors, missing PHP and PHP-dependent imports); this is not a new successful full-suite claim. No installed plugin code or package was changed in this checkpoint. New lab files passed Python compilation and whitespace checks.


## Grouping correction candidate — 2026-11-11

Candidate package 2026.11.11.1 fixes unrelated root files being grouped by first observation time. Units now preserve top-level folders, exact-name sidecars and shared torrent content ownership; overlapping relationships merge transitively. Selection, forecasts and the actual batch runner use the same grouping inputs. Open/stability, age, integrity, backup, parity, namespace and batch checks remain enforced.

Synthetic regression: 342 independent root files observed together, seven open; only those seven are skipped and 335 remain candidates. This reproduces the reported pattern without publishing real media names. It is not a claim about current production eligibility. Forecast details include actual blocking group members and separate open/stable observations; all displayed names are escaped.

Validation: full discovery passed (182 tests), seven JavaScript suites passed, package reproducibility/checksums/XML/PHP lint and isolated install/update/rejection/remove passed. PHP CLI and ctype were restored in an isolated temporary test runtime. Existing exclusion test was updated so excluded EMBY metadata no longer blocks an unrelated root movie merely by observation time.

The new package is a tested development candidate, not a stable release. Neither production nor test VM installation has been performed for this new version in this checkpoint. Preserve the genuine aged torrent and perform guest update/readiness/positive move/recheck/peer proof next; unattended reboot readiness remains qualified by the scrub-history limitation.


## Installed update and forecast memory correction — 2026-11-11 18:49 CET

Version 2026.11.11.2 installed on both FejesMover-Test and the owner-authorized production NAS. Pinned package source commit df93c07f6d1cf10e377275e06d56afe76bb3294d, SHA256 8d410471cc3f7ad5b8726d2b818f7fce6a5143baa4d10a94d7491868fd50a8f4. Final GitHub validation run 43070988993 succeeded. Earlier failed notifications referred to intermediate per-file commits, including checksums uploaded before the regenerated manifest; do not mistake those for the final run.

Initial .1 production forecast exposed a scale bug: repeated causes for a large excluded metadata group exhausted PHP's 256 MiB memory limit. Replaced with .2 after adding a 1,100-file regression. Cause details are limited to five entries for indirectly blocked rows, with a separate total; directly blocked/excluded rows do not repeat group causes. The oversized forecast was preserved privately in the production rollback directory, not deleted. New production forecast is 579137 bytes and the actual WebGUI renders normally.

Validation for .2: 183 tests passed, reproducible package/checksums/XML/PHP lint/isolated lifecycle passed, GitHub final run succeeded. Earlier .1 grouping/waiting tests also passed inside the guest (24 tests). .2 installed guest runner again returned nothing_eligible, zero files/bytes, protected_content=1, blockers=[], requires_inspection=false, active_file_started=false. Genuine guarded torrent and its age baseline preserved; positive move plus recheck/peer proof still pending after Nov 11 21:08:18 CET. Guest /tmp/fm-new contains extracted .1 source with the peer-proof helper; installed .2 tools are authoritative. Fetch latest source before further development.

Production pre-update backup is on HDD disk5 under biztonsagi_mentesek/fejesmover-before-20261111-1839/plugin-and-config.tgz; gzip integrity checked, runtime and private configuration included. Existing settings.json and selective.json SHA256 remained identical across update. No explicit selective profile existed; reviewed default scope remained cache/Filmek and existing torrent/launcher names. No actual production mover was started during this update, final process check found none. Observe only: all nine guards passed; forecast contained 1579 files (539 too_young, 25 protected_content, 3 busy_or_unverified, 1012 excluded metadata). New first-observation age dates are Nov 12 around 18:40; do not bypass or backdate them. This production forecast does not change the separate guest torrent's Nov 11 readiness.

No stable/public general-acceptance claim yet. Keep the remaining VM positive acceptance and reboot/scrub qualification in scope.
