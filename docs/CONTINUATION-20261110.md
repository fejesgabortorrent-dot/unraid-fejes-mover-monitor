# Continuation checkpoint — 2026-11-10, after successful peer transfer

## Current outcome

**The bounded real-torrent component test passed. The full guarded Mover is NOT certified yet.** User authorized unattended continuation, GitHub evidence recording and this continuation save. Production NAS was not changed. Do not merge or release merely to resume.

Main result: [SEED-COMPONENT-RESULT-20261110.md](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/blob/main/docs/SEED-COMPONENT-RESULT-20261110.md).
Draft PR: [#36](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/pull/36), branch `test/seed-lab-20261110`.
Executed harness revision: `fa24fac08d26810e5863453712f91035a26ef40d`.
Installed plugin: main `2026.10.31.2`, original tested source `26f62660f4831adb5ddcbae498f569f69b74c684`.

## Verified evidence

- Main: 154 Linux fixture tests passed. Actual guest install and `tools/check.py` passed; guest 33 mover / 10 torrent / 1 recovery fixture tests passed.
- PR #35 at `524b79b9e9093ca5a80bd3ad3a3ea6d04d758810`: 147 fixture tests, isolated package lifecycle and seven JS suites passed separately. It is still unmerged and was not installed.
- Earlier independent 4 MiB native component move passed.
- New 16 MiB private torrent was 100%/`stalledUP` before movement.
- The real native execution component moved 16,777,216 bytes to the guest array, preserving checksum/metadata; cache source was absent.
- Real qBittorrent recheck after movement: 100%/`stalledUP`; logical content path preserved.
- A separate internal peer downloaded 16,777,216 bytes; seeder uploaded 16,777,216 bytes.
- Original/array/peer SHA-256: `0d829db777be51fc3bb4e0eba46312f6a6d567111d3fad59eb60074ba16c7b86`.
- Final private JSON status: `peer_transfer_verified`, `seed_verified=true` scoped ONLY to this component test.

**Boundary:** `fresh_candidate()` was simulated in the test Python process. New torrents cannot meet the production one-day age floor immediately. The full age/eligibility/maintenance/integrity/batch path was not exercised by this move. Runtime helper files and persistent Advanced-mode configuration were not patched. No tracker credit, production VPN, broad compatibility, guest reboot or full release certification is claimed.

## Durable guest state

Only operate on hostname `FejesMover-Test`, Unraid 7.3.4, 2 vCPU/4 GiB.
Expected virtual disk serials: `FMTESTPARITY24`, `FMTESTDATA16`, `FMTESTCACHE08`.
Test share `fejesmover`: cache to array. Python 3.11.15 installed.

- Private final result: `/mnt/disk1/fm-acceptance/current.json`.
- Local source archive: `/mnt/disk1/fm-acceptance/source-checkpoint.tgz` (verify before relying on it).
- Earlier result: `/mnt/disk1/fejesmover-component-result.json`.
- Pre-install boot config backup: `/mnt/disk1/fejesmover-boot-before.tgz`.
- Virtual Docker image: `/mnt/disk1/system/docker/docker.img`, 4 GiB, mounted at `/var/lib/docker`.
- Docker daemon was started using `/etc/rc.d/rc.docker start`.
- **Docker auto-mount/start is not configured or verified after reboot.** Last read `/boot/config/docker.cfg` still had original disabled/default 20 GiB settings; GUI edits were not applied. Preserve/verify current state before deliberately rebooting. Do not let default settings create a second image.
- Internal-only network `fm-lab`; containers `fm-qbit` and `fm-peer`, 512 MiB each; no published host ports.
- Seeder: `/mnt/user/fejesmover:/data`; receiver: distinct `/mnt/disk1/fm-peer:/data`.
- Configs: `/mnt/disk1/appdata/fm-qbit`, `/mnt/disk1/appdata/fm-peer`.
- qBittorrent v5.3.0, image manifest digest `sha256:3d4c4545d51a690a0df15a2ff99038823a88a9822df8e794526447b9afbd7384`.
- Worktrees `/tmp/fm-seed` and `/tmp/fm` are volatile. Recreate from GitHub after a reboot if needed.
- Authentication stayed enabled. Harness uses generated temporary credentials and local session cookies. Do not publish container logs, cookies or credentials. Sessions may need reauthentication after container restart; no passwords were changed.

## Harness / diagnostics

`python3 /tmp/fm-seed/testlab/seed_acceptance.py status` reads saved status.
Actions already completed: `prepare` (recovered with `verify-prepared`), `move-component`, `transfer`.

Do not rerun `prepare` or move the saved run again merely to resume. A new test run must use fresh unique data. Existing test data, torrents and both containers were retained.

The initial add response differed from historical `Ok.`, although the torrent was already complete; fixed by querying authoritative state. The initial immediate byte-count check was incomplete, and re-adding a duplicate was rejected; fixed by resuming the existing peer and polling counters for a bounded interval. Final successful counters and SHA were verified after those fixes. Earlier failures remain in the PR discussion.

## Next independent work

1. Review the saved evidence and choose the next unverified gate; do not repeat already-passed checks without a reason.
2. Reconcile PR #35 with current main while preserving newer profile/directory behavior; rerun targeted/full tests before deployment.
3. Prepare and test the full guarded execution path with real torrent snapshots, integrity listeners, legacy launcher and age eligibility. Observe a naturally aged test torrent if real elapsed-age acceptance is required; do not manufacture timestamps or silently bypass guards.
4. Test per-torrent exclusions, API failures, open files, integrity/parity/backup conflicts and interrupted-operation recovery on the VM.
5. Deliberately configure/review guest Docker persistence before actual guest reboot/update/remove/restore acceptance.
6. Keep Beta/RC1. Verify CA's independent index refresh; repository metadata publication is not catalog approval. Unraid 8 remains separate.

## Browser recovery

Use the installed Browser extension, a fresh open-tabs listing and the existing `QEMU (FejesMover-Test) - noVNC` tab. Never use the production NAS terminal. The guest Firefox terminal is visually `http://localhost/webterminal/ttyd/`.

Bulk input can truncate shifted characters. Small lowercase chunks plus explicit Shift+physical-key presses for capitals/colon/underscore were reliable. NoVNC clipboard paste produced stale content; inspect before execution. To cancel a partial command: fresh DOM, open noVNC Extra keys if needed, toggle its Ctrl button, type `c`, untoggle Ctrl. Browser calls sometimes timed out after the guest operation succeeded; inspect before retrying mutations.

## End-of-day handoff — 2026-11-10

The owner requested a final continuation save and stopping work for today, with approximately 19% of the session credit remaining. No new test was run after the successful 16 MiB component/peer result recorded above. The proposed real-preflight/API-failure test was discussed but NOT executed; do not mark it passed.

Resume next time from the unverified full preflight/API-failure gate, after freshly checking the disposable guest. Preserve the proven component results and avoid repeating the successful move on the same saved run. The source archive on the guest data disk was previously verified with gzip exit code 0; it was not recreated or reread during this closing save. Docker/container uptime and current VM state were not freshly inspected at close. No merge, release or production operation was performed during this closing save.
