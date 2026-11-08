# Release Candidate 1 — published build 2026.10.31.2

RC1 is a prerelease for the documented Unraid 7.x documented scope. See
[RC1 release notes](RC1.md) and [selection/execution rules](SELECTIVE-MOVEMENT.md).

The package provides monitoring, optional age-filtered native movement, per-content
torrent exclusions, checksum/metadata verification and explicit maintenance
blocking. RC1 fixes small-file domination of the eight-file batch by ordering
larger eligible files first inside the existing ratio-priority groups. Low or
unknown ratios never exclude an otherwise eligible file. File/byte caps, age,
cooldown, maintenance and source/target guards are unchanged.

## Current published candidate

Build 2026.10.31.2 preserves the reviewed top-level EMBY directory exclusion during updates and adds the guarded selective-mover profile contract plus the profile settings page. Regression coverage verifies exact-directory boundaries and prevents a promised move date for excluded files. Package lifecycle and 154 isolated Python tests passed on Linux. This build is published on the main branch; NAS installation remains a separate observer-mode-gated action. Movement configuration is still limited to the documented reviewed cache/Filmek setup. General source/share/target setup is not implemented.

## Prior integrity-wait candidate

Build 2026.10.28.4 handles an integrity scan discovered by a fresh per-file guard before the first native move as a deferred operation. A partial batch, an interrupted run and an existing inspection requirement remain blocked. This change does not clear an existing production inspection latch. Support-strip text follows the selected palette; page controls gain pointer-transparent orbit feedback on hover and keyboard focus, with a static reduced-motion fallback.

The candidate passed 135 isolated Python tests and all seven JavaScript suites on Unraid 7.3.4, including package reproducibility and installation lifecycle. This combined candidate has not been installed or published. Appearance-only build 2026.10.28.3 is installed, with all Python runtime helpers and the inspection state retained from 2026.10.27.4; GitHub publication remains at the previously verified build. Unraid 8 is deliberately rejected by the current installer.

## Prior update and operating limits

Build 2026.10.27.4 retains the shared appearance in Follow Unraid mode, aligns flag-only language/settings/detail controls, improves light-theme contrast and reports unavailable torrent queries without exposing command arguments. Native process failure details remain in a private diagnostic log.

The current candidate passed 131 isolated tests, package reproducibility, checksums, PHP syntax, installation lifecycle and targeted JavaScript checks. GitHub CI validates the submitted revision separately. These checks do not establish live reboot persistence or broad hardware compatibility. RC1 remains a prerelease; keep backups and do not infer tracker credit or actual peer upload from continuity checks.

## Verification

CI checks reproducible package/checksums, isolated install/update/rejection/remove,
selection and executor behavior, three-language authenticated UI, configuration
recovery, interruption blocking, depth/navigation, sorting and refresh failures.
Ordering regressions cover tiny sidecars preceding large media, ratio precedence,
missing sizes, deterministic ties and remaining byte-budget handling.

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
