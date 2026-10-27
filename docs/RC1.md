# RC1 — Fejes Mover Monitor

Original prerelease: 2026.10.25.2. Current usability build: 2026.10.25.4.

First release candidate for Unraid 7.x. This is a prerelease for evaluation,
not a general compatibility or reboot/power-loss certification.

## What RC1 includes

- Hungarian, English and German monitoring, a compact dashboard, raised/flat
  appearance and independent Follow Unraid / Light / Dark themes.
- Back / Forward / Home navigation, queue search, filters and bidirectional
  display sorting; small-screen file cards.
- Opt-in selective native cache/Filmek-to-array movement. Young, incomplete,
  active, open or unstable content remains excluded. Eligibility uses modification,
  verified cache arrival and torrent completion age.
- Existing ratio-priority groups are retained; larger eligible files go first
  within each group. This avoids spending all eight slots on small sidecars.
  Files that do not fit the remaining byte budget are deferred, with independent
  smaller files still able to use the remainder.
- At most eight files and the saved 16 / 32 / 64 / 128 GiB limit per batch.
  Installation does not change the limit, age, cooldown, schedule or mode.
- Native execution, SHA-256, metadata/xattr and client-continuity verification;
  durable execution intent and inspection blocking after an uncertain outcome.
- Explicit integrity/cooldown deferral, truthful stale-data feedback and the
  Unraid form-name compatibility fix.

## Supported scope

Observer monitoring is the default. Execution is limited to the reviewed
Advanced/cache configuration and existing threshold-script integration described
in SELECTIVE-MOVEMENT.md. There is no global Mover launch, recursive copy/delete,
target overwrite or automatic bypass of maintenance checks.

## Evidence and remaining limits

Validation completed locally: 120 Python tests, 64 application fixtures, 31 mode
checks and the JavaScript refresh/theme/navigation/sort suites.

The package is reproducibly built, with checksum, isolated install/update/remove,
policy, UI, language, interruption, guard and ordering regressions checked in CI.
## Acceptance limits

RC1 remains a prerelease. File verification and client continuity do not prove tracker credit, peer upload, power-loss recovery or reboot persistence. Keep backups and perform environment-specific acceptance checks.

## Install and rollback

Use the normal plugin installer URL from README.md or the versioned manifest in
this GitHub prerelease. Check the asset hashes in RC1-SHA256SUMS; SHA256SUMS covers
the manifest and packaged source files. The source ZIP is the tested release tree.

An existing installation preserves its saved configuration. Before replacing an
owner installation, retain the current manifest/runtime backup and configuration
checksums. If a movement report requires inspection, investigate source, target,
user-share view and torrent state before another launch; do not clear it blindly.

## Store availability

The Community Applications template identifies this as RC1 and retains the Beta
flag because it is a prerelease. The catalog may update later than GitHub; new
screenshots and metadata are not claimed visible until checked in the catalog.
