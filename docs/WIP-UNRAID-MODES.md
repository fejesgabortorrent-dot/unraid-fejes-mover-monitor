# Unraid mode selection — work in progress

Saved at the user request on 2026-10-18 to preserve the current development state.
**Not an installable or validated beta. Do not merge or deploy this branch yet.**

Target: Unraid 7.x only. The intended modes are demo (synthetic display and no
automation writes), observer (default, live read-only monitoring), and advanced
(explicit opt-in to the existing cache-only legacy script editor). Pool selection
must come from configured Unraid pools, never arbitrary browser-supplied paths.

Current source adds a shared runtime configuration reader, an authenticated mode
and pool setup page, mode guards in the existing monitor/dashboard/settings pages,
Hungarian/US English/German setup translations, and Unraid/PHP installer preflight.
Mode configuration uses a plugin-owned JSON file, CSRF validation, a configuration
hash, process locking and an atomic write. Advanced script editing intentionally
remains cache-only because the external script is not rewritten by pool selection.

## Safety test results — 2026-10-18

`python tools/mode_test.py`: **24 checks passed** in disposable local fixtures.
Covered observer/demo direct POST rejection, explicit advanced acknowledgment,
CSRF and conflicting configuration hashes, unknown mode/pool and path traversal,
cache-only advanced editing, synthetic demo output without live log/disk readings,
custom/unmounted pool measurement, five malformed configuration cases, advanced
save with backup, revoked advanced access, and English/German setup rendering.

The tests found an undefined escaping helper in the demo monitor branch; fixed by
initializing it before mode branching. The regenerated PLG/checksums and
`python tools/check.py` also passed, including Unraid 6.x/8.x rejection before
installation/update, source matching, PHP lint, isolated install/reinstall,
invalid-PHP rejection and uninstall preservation. No production paths were used.

The older 41-check application suite and browser demo still need shared-runtime
fixture adaptation. This is partial validation, not a release-ready claim.

Pending before treating this as a beta:

- Adapt application fixtures and the local browser demo to stage the shared PHP
  runtime, pool definitions and plugin configuration in temporary directories.
- Extend mode tests with concurrent mode/save locking and additional error paths.
- Check all setup text and language selection; review demo mode data isolation.
- Extend preflight tests to missing Unraid host markers (6.x/8.x already checked).
- Run every existing test and the new regression tests on Linux CI.
- Refresh README, release status, package metadata, screenshots and release notes.

The previous tested candidate remains on `fix/review-cache-refresh-checksums`.
No live NAS changes, merge, Community Applications submission or release publishing
were performed as part of this work-in-progress snapshot.
