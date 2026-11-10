# Continuation checkpoint — 2026-11-10

Work is incomplete; no stable/seed certification is claimed. Resume only on the disposable `FejesMover-Test` guest, never the production NAS. User authorized continuing unattended and requested this checkpoint. Do not merge or release the test branch merely to resume.

## Saved public records

- Main validation record: `docs/UNRAID-VM-VALIDATION-20261110.md`, linked from release status and CA source overview. CA indexing refresh remains unverified; Beta remains true.
- Acceptance issue #34 has the bounded results.
- Draft PR #36, branch `test/seed-lab-20261110`, adds `testlab/seed_acceptance.py` (initial commit `b8ee4404fae8550349e6e16d4dcc7c8c65ab694a`). No production/runtime changes.
- PR #35 is the separately tested, unmerged preflight-latch fix. It is not in installed main.

## Proven before this checkpoint

Main `26f62660f4831adb5ddcbae498f569f69b74c684`: 154 development fixture tests passed. PR #35 `524b79b9e9093ca5a80bd3ad3a3ea6d04d758810`: 147 tests, isolated package lifecycle and seven JS suites passed. Actual guest installation of main package `2026.10.31.2` succeeded. Guest `tools/check.py` and 33 mover / 10 torrent / 1 recovery fixture tests passed.

A 4 MiB component test called source `selective_mover.execute_file` with `fresh_candidate` simulated in process. Real native move and checksum/metadata checks passed, physical cache source disappeared, destination SHA matched. This does NOT certify full guards or live seed behavior. Private result lives on the guest data disk as `fejesmover-component-result.json`.

## Guest runtime and durable state

- Unraid 7.3.4, 2 vCPU, 4 GiB; virtual disks serials `FMTESTPARITY24`, `FMTESTDATA16`, `FMTESTCACHE08`.
- Dedicated test share: `fejesmover`, cache to array. Python 3.11.15 installed through the official Python-for-Unraid plugin source. Boot configuration backup retained on the guest data disk.
- Newly created 4 GiB Docker image at `/mnt/disk1/system/docker/docker.img`, mounted by `mount_image` on `/var/lib/docker`; daemon started through `/etc/rc.d/rc.docker start`.
- Important: `/boot/config/docker.cfg` was still the original disabled/default configuration when last read. GUI edits were NOT applied. Thus automatic image mounting/start after reboot is NOT configured or verified. Do not reboot until this is deliberately handled.
- Internal-only Docker network `fm-lab`. No published host ports.
- Seeder `fm-qbit`, data bind `/mnt/user/fejesmover:/data`, config under guest disk1 appdata, memory limit 512 MiB.
- Image digest observed: `sha256:3d4c4545d51a690a0df15a2ff99038823a88a9822df8e794526447b9afbd7384`.
- Harness worktree `/tmp/fm-seed`; original checkout `/tmp/fm`. These are volatile; recreate by fetching the test branch after reboot if needed.
- `prepare` was run via `python3 /tmp/fm-seed/testlab/seed_acceptance.py prepare`.
- It created/validated the second `fm-peer` container, authenticated to both clients without disabling authentication, created a private random 16 MiB torrent, and saved `/mnt/disk1/fm-acceptance/current.json`.
- It then reported `Seeder rejected test torrent` based on an unexpected API response. No move or peer transfer has yet occurred. Inspect real torrent list and the response before deciding whether the torrent actually failed to add.
- Credentials/cookies are deliberately not included here. The harness obtains temporary credentials from local container logs and keeps sessions only inside the test containers. Never publish those logs or cookies.

## Immediate next steps

1. Inspect the guest terminal fresh; a partial command may be at its prompt after input/clipboard issues. Cancel it safely rather than appending commands blindly.
2. Verify both containers and their internal-only network/no-port configuration. Read the synthetic torrent list using authenticated local Docker-exec curl, or import the harness and use its API helper. Do not disable authentication.
3. Diagnose the prepare reply. Avoid creating duplicate runs until `current.json` and qBittorrent state are understood. Improve response handling if the current qBittorrent version uses a new success response.
4. Once the real test torrent is verified 100% complete and idle, run `move-component` only for the saved fresh run. This still simulates fresh_candidate because a new torrent cannot satisfy the production one-day floor; it must remain explicitly component-only acceptance.
5. Run `transfer` after the real post-move qBittorrent recheck. Require the second peer to download the entire payload, matching SHA-256, and seeder upload byte evidence. Record actual results and limitations on #36/#34.
6. Full guarded batch/integrity/age acceptance, reconciling #35 with main, actual guest lifecycle/reboot/remove/restore, tracker credit and Unraid 8 remain open.

## Browser operation notes

Use the installed Browser extension only. Find the existing `QEMU (FejesMover-Test) - noVNC` user tab by a fresh open-tabs listing. Do not substitute the production NAS terminal. Guest terminal URL visually is `http://localhost/webterminal/ttyd/` inside the VNC canvas.

Normal bulk typing can lose shifted characters (colon, underscore, capitals) or truncate; explicit Shift+physical-key presses and small chunks were reliable. NoVNC clipboard paste yielded stale content; do not paste or execute it without inspecting the command. For cancelling a partial command, open noVNC Extra keys, toggle its Ctrl button, type `c`, then untoggle Ctrl. Fresh DOM snapshots are necessary before toggling the toolbar. Browser calls occasionally time out even when the guest operation succeeds; inspect state before retrying mutations.
