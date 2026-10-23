# Experimental beta — 2026.10.23.992

Unraid 7.x / PHP 8+. Observer remains the default. Installation and mode changes do not start movement or create a schedule. Community Applications listing was observed on the owner's NAS; listing does not certify broad compatibility.

## Direct owner-NAS evidence (Unraid 7.3.3)

- A 256 MiB own file moved through the native Unraid engine, cache to physical disk2, outside Emby. Before/after SHA-256 matched. User-share access, permissions, ownership, mtime and test/checksum xattrs were preserved. The native engine retained the file while it was actually open.
- Separate selective executor tests moved a 64 MiB eligible fixture while retaining a young fixture, synthetic active-torrent fixture and actually open fixture. Synthetic age/torrent inputs existed only in the isolated test adapter. Production inventory and torrent API state were not falsified.
- Real before/after snapshots retained the same 366 torrent identities/paths and all 364 completed torrent seed states. Upload counters increased during the initial native test. This does not claim that production torrent files moved.
- The actual browser monitor showed the running selective process, open file, position, cache and logs. The fixture checksum read was deliberately slowed for observation; no sustained copy-speed or ETA measurement is claimed.
- Every installed inline runtime/helper matched the manifest. Owner mode/pool, age setting and cron bytes remained unchanged. Existing 15-minute dispatch was explicitly delegated to the selective executor with a verified backup. Threshold remained 300 GiB and cooldown 360 minutes.
- Invoking the installed dispatcher and authenticated UI returned nothing_eligible: 437 files, 98 protected and 339 too young, zero moved. These counts are a time-specific owner snapshot.

## Release validation

Python policy/native invocation/dispatch guards, authenticated selective UI requests in all three languages, existing PHP page fixtures, 31 mode guards, stale-artifact rejection, JavaScript refresh behavior, reproducible XML/checksums and isolated install/reinstall/rejection/remove are checked. CI runs these from committed public source and never performs production movement.

## Remaining limits

Production-media/torrent-file movement, live NAS reboot persistence and broad hardware/configuration compatibility remain unverified. The accepted movement tests used self-created files outside Emby. Selective execution is fixed to cache/Filmek to Array with user-share torrent bindings and an 8-file/16-GiB batch limit. Age includes first observation; old mtime alone does not make a new cache file eligible. Unknown state stops execution.

See [selective movement and recovery](SELECTIVE-MOVEMENT.md) for retained-helper uninstall semantics and explicit restoration of external wiring. Older archive-prototype and acceptance notes are historical; this status describes the current build.
