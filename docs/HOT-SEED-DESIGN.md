# Hot-seed cache placement — development prototype

The owner requested bidirectional placement within one user share: retain the
client-visible path, keep colder files on the array and consider recently wanted
completed torrents for the cache. This prototype implements only the pure,
read-only decision policy in `tools/hot_seed_policy.py`; it is not packaged,
wired to cron or installed on the owner NAS. It cannot copy or remove files.

## Decision rules

- Fresh, trusted inventory and all existing maintenance guards are mandatory.
- Two monotonic upload observations, 5–60 minutes apart, identify demand; the
  latest observation must be at most 60 seconds old. Default demand is 64 MiB.
- Cumulative share ratio is not a demand signal or proof of tracker compliance.
- Promote only a unique regular array file with complete ownership, a stable
  signature, no symlink/hardlink and a verified user-share container binding.
- The file must now be quiet and closed. Observed demand does not authorize
  interfering with a currently active upload or incomplete torrent.
- Require known movement history and at least 24 hours since the last move.
- Reserve 300 GiB of cache by default; at most 2 files / 32 GiB per promotion
  plan. At current owner free space (~182 GiB), no promotion is appropriate.
- Prioritize recent upload volume; obey both total-byte and file-count limits.
- Missing, stale or reset counters withhold content. Unknown global state or
  duplicate/escaping paths produces no candidates.

## Proposed interface

Add a separate “Seed cache” section, clearly labelled “Preview only” until an
execution adapter is verified. Show current cache reserve, observed upload
window, suggested direction and a per-file reason. Proposed controls: enabled
(default off), reserve GiB, demand MiB/window, residency hours and promotion
batch size. Never treat a filename filter as execution selection. Do not expose
private paths, tracker tokens or raw torrent identifiers in public reports.

## Required before live reverse movement

1. Read-only host adapter: complete ownership and physical location inventory,
   upload samples across a validated daemon generation, immutable file
   signatures and persistent last-move records.
2. Validate reverse native movement semantics on disposable Unraid data. The
   existing executor is explicitly fixed to cache → array; it must not be reused
   by merely replacing source paths or changing the whole Filmek share direction.
3. Coordinate both directions with existing locks and transaction records.
   Preserve old availability through durable copy, checksum/metadata verification
   and recoverable cutover. Handle collisions, crash recovery and source drift.
4. Recheck all owners, open files, capacity and maintenance immediately before
   execution. Verify unchanged client paths and torrent completeness afterwards.
5. Test restart, partial copy, disk-full, concurrent Mover, multi-file torrents,
   hardlinks, tracker/API failure and demand ending during promotion.
6. Verify real peer upload after movement; a seed state alone proves neither
   peer transfer nor tracker-side seed obligation completion.

The current outbound owner test is separate evidence, not reverse-executor
acceptance. Do not describe this development prototype as active tiering.
