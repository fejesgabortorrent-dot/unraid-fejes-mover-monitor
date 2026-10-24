# Owner outbound acceptance — 2026-10-24

Unraid 7.3.3; experimental beta 2026.10.24.2. Authenticated owner test used the
existing selective executor, saved 1-day age, 32-GiB batch and ratio target 1.0.
The existing 15-minute automation remained installed; its cooldown remains six
hours. No NAS reboot or reverse movement was performed.

The completed worker report records:

- state: completed; requires_inspection: false; blockers: empty
- moved_files: 8; moved_bytes: 9587259657 (8.929 GiB)
- candidate_count: 384; deferred by file-count cap: 376
- protected content: 17; too young: 50
- same_torrents: true
- completed_still_complete: true
- completed_in_seed_states: true
- paths_unchanged: true

The executor's successful per-file completion requires SHA256 checks at the
physical target and user-share path, metadata/xattr verification and source
absence. The monitor visibly observed target and user-share verification reads.
Cache free space increased from approximately 173.4 to 182.2 GiB while other NAS
activity continued; the worker byte count is the authoritative movement amount.

This is production-content outbound movement and client-state continuity evidence
for this bounded owner run. It is not proof of a peer downloading these files
after movement, tracker seed-time credit, reverse-executor safety, crash recovery,
NAS reboot persistence or general hardware compatibility. No private filenames,
torrent hashes, tracker URLs, credentials or raw server logs are published here.
