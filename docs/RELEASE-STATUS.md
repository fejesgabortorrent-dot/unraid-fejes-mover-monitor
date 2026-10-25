# Release Candidate 1 — 2026.10.25.2

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

Prior bounded owner movement acceptance is documented in
[OWNER-MOVEMENT-20261024.md](OWNER-MOVEMENT-20261024.md). A read-only host preview
also confirmed protected integrity/cooldown deferral. New RC1 ordering is tested
in isolation; a fresh native RC1 run remains pending until all live guards pass.
No successful live RC1 transfer is claimed from simulation or preview.

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
