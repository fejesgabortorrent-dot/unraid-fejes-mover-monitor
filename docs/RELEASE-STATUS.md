# Release Candidate 1 — current build 2026.10.25.3

RC1 is a prerelease for the documented Unraid 7.x owner-tested scope. See
[RC1 release notes](RC1.md) and [selection/execution rules](SELECTIVE-MOVEMENT.md).

The package provides monitoring, optional age-filtered native movement, per-content
torrent exclusions, checksum/metadata verification and explicit maintenance
blocking. RC1 fixes small-file domination of the eight-file batch by ordering
larger eligible files first inside the existing ratio-priority groups. Low or
unknown ratios never exclude an otherwise eligible file. File/byte caps, age,
cooldown, maintenance and source/target guards are unchanged.

## Verification

CI checks reproducible package/checksums, isolated install/update/rejection/remove,
selection and executor behavior, three-language authenticated UI, configuration
recovery, interruption blocking, depth/navigation, sorting and refresh failures.
Ordering regressions cover tiny sidecars preceding large media, ratio precedence,
missing sizes, deterministic ties and remaining byte-budget handling.

## Verified RC1 owner movement — 2026-10-25

The installed RC1 appearance build 2026.10.25.3 completed three scheduled native
cache-to-array batches: **24 files, 94,199,156,410 bytes (94.20 GB)**.

| Batch start (CET) | Files | Verified moved bytes |
| --- | ---: | ---: |
| 08:45 | 8 | 34,348,423,383 |
| 10:15 | 8 | 30,728,214,699 |
| 11:30 | 8 | 29,122,518,328 |

All three reports were `completed`, with `requires_inspection=false`,
`active_file_started=false`, and all four torrent-continuity checks true:
same torrents, unchanged paths, completed content still complete, and completed
content in seed states. The executor verifies SHA-256 and metadata before
counting a moved file. These checks do not prove peer upload or tracker credit.

After the first completed batch, the owner-authorized retry interval changed
from 360 to 60 minutes through the authenticated settings page. The backup,
exact one-line change, shell syntax and read-back were verified; threshold,
cron, age, ratio and batch limits remained unchanged. This is an owner setting,
not a new installation default. The 24–48-hour observation is still in progress;
RC1 remains a prerelease, not a stable or broad-compatibility certification.

## Known limits

- Execution remains cache/Filmek to the array using reviewed existing automation;
  Observer is the default and installation creates no schedule or transfer.
- Files above the saved byte limit remain in cache. Eight-file and cooldown
  limits may still constrain release rate; RC1 promises no transfer ETA or
  guarantee against cache filling while writes exceed eligible movement.
- Actual peer upload of moved content, tracker seed credit, reverse movement,
  physical power-loss recovery, NAS reboot persistence and broad compatibility
  remain unverified. Backup restore acceptance is separate from a successful job.
- The catalog refreshes independently. GitHub publication and accessible image
  URLs do not by themselves prove current Community Applications gallery content.

## Delivery

The validated main-branch build publishes the first RC1 prerelease and a versioned
manifest, full source checksums, source ZIP and asset checksum list. Publishing is
restricted to a successful main-branch push for this RC version; pull-request
validation has read-only repository permissions. Existing published assets are
not overwritten. Store metadata keeps the Beta flag for the candidate.
