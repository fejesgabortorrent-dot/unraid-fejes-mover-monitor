# Selective native movement — 2026.10.23.992

Default installation is Observer and creates no schedule. Selective execution is
an opt-in Advanced/cache feature for `/mnt/cache/Filmek` → the array only.

## Selection

Save 7, 14 or 30 days on Tools → Mover Selective. Age requires unchanged
device/inode/size/mtime/ctime evidence, old mtime, verified cache observation
history and, for torrents, old completion time. First observation starts a new
age window; copied old timestamps do not bypass a recent cache arrival.

Incomplete, checking, moving, downloading and uploading torrent content is
excluded by path, including a torrent folder's descendants. Completed quiet
seeds also need verified zero transfer rates. Open files, symlinks, hard links,
changed files and existing array copies are excluded. Unknown state blocks
execution. An unrelated unfinished torrent does not prevent an independent old
file from moving.

Backup, parity, scrub, disk/mount health, integrity listeners/pipes and verified
integrity schedule wiring remain mandatory. Launch/integrity locks, the existing
free-space threshold and cooldown apply. Each file is checked again after its
source checksum. The native engine also checks open-file use.

The engine receives exactly one physical source filename. No global Mover,
user-share copy, recursive delete or target overwrite is invoked. Target data is
flushed, then SHA-256 is compared with the physical array file and unchanged
user-share path. Ownership, permissions, mtime and existing xattrs are compared.
A movement/post-movement error stops further files and requires inspection before
later movement. No automatic cleanup or deletion is attempted.

Each batch is limited to **8 files / 16 GiB**. Larger files remain in cache and
are reported. File positions in the monitor are observations, not verified ETA.

## Manual and automatic start

Use **Read-only check** before **Move eligible files with verification**. The
latter starts a background worker which rechecks every guard. An accepted start
request is not evidence that any file moved. GET pages only read the last report.

The optional schedule adapter recognizes only the reviewed existing
`Filmek_Mover_Threshold` script. It preserves its schedule, threshold and retry
interval. An early `exec` delegates that script to the selective executor so the
old global Mover body cannot subsequently move young files.

Check only:

```sh
python3 /boot/config/plugins/fejes.mover.monitor/tools/wire_selective.py
```

After explicitly approving the change to your existing automation:

```sh
python3 /boot/config/plugins/fejes.mover.monitor/tools/wire_selective.py --apply
```

The adapter verifies a backup under
`/boot/config/plugins/fejes.mover.monitor/backups/selective-dispatch-before-*.sh`
and does not start movement. Existing scheduled invocations subsequently use the
new executor. Its observation inventory and selective attempt timestamp are
separate from the retained legacy timestamp.

## Disable and remove

UI uninstall retains shared helpers and external wiring. First pause the specific
User Scripts schedule if you want movement disabled. Confirm no Mover/native copy
is running. Review the exact saved dispatcher backup before restoring it, and
preserve the current script too. Restoring that backup restores the **global**
Mover behavior; it is not a substitute for pausing automatic movement. Do not
remove shared helpers or blindly delete PID/lock files. Re-enable a schedule only
after reviewing its resulting behavior.

## Evidence limits

Owner acceptance used a 256 MiB native test and separate 64 MiB selective tests
in `util`, outside Emby. The selective adapter used synthetic age/active-torrent
inputs only for its own fixtures, real native movement, actual open-file
exclusion and real before/after torrent observations. Production inventory and
torrent API state were not falsified.

The live `Filmek` scan correctly moved zero files because none had yet met the
verified observation age. Production-media movement, live NAS reboot persistence
and broad hardware/configuration compatibility remain unverified.


## Ratio priority and larger batches (2026.10.24.1)

In Selective → Settings, choose a ratio target (0 = disabled) and batch limit (16/32/64/128 GiB). Save settings, then refresh the observation. Both settings are private to the NAS and backed up before changes. The ratio is the qBittorrent snapshot value; shared files use the lowest owner ratio, and missing/invalid values show an em dash. Reaching the target prioritizes an already eligible file; it never bypasses age or safety checks, and a lower/unknown ratio never blocks movement. Files without torrents remain movable under the existing rules. This feature does not change tracker obligations or stop/remove torrents.

The batch limit defaults to 16 GiB. A larger value admits larger individual files and increases total work per batch; the 8-file cap, exact native-file invocation, fresh checks, SHA256 and metadata verification remain. Existing schedules are untouched. This candidate has isolated regression validation; production-media acceptance remains outstanding.
