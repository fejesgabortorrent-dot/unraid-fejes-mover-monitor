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

## PR #4 review corrections — 2026-10-18

All four findings from review of `125075b` have been addressed:

- Every page requires the shared helper through the absolute installed plugin
  path, rather than `__DIR__`. Tests now evaluate page bodies from a separate
  layout directory to model Unraid WebGUI execution.
- The monitor mode/pool banner lives inside the replaced monitor fragment.
  Dashboard polling updates the incoming banner with the readings in the same
  synchronous update and keeps simulated status explicitly labeled DEMO.
- Malformed configuration still disables automation editing, but setup may save
  a fully validated replacement under its exclusive lock. Actual lock/read
  failures continue to block the save.
- Non-cache pools do not load or compare the cache-only legacy script threshold.

Local validation after these fixes: **41 application checks + 31 mode safety
checks passed**, together with rendered JavaScript syntax, pause/dashboard state
tests, package/XML/PHP checks, reproducibility, isolated installer checks and
stale-artifact rejection. The application fixtures and browser demo now stage
the shared helper and configuration. This does not establish live Unraid
acceptance or release readiness.

Pending before treating this as a beta:

- Exercise the updated browser demo end-to-end after the current review fixes.
- Extend mode tests with concurrent mode/save locking and additional error paths.
- Check all setup text and language selection; review demo mode data isolation.
- Extend preflight tests to missing Unraid host markers (6.x/8.x already checked).
- Run every existing test and the new regression tests on Linux CI.
- Refresh README, release status, package metadata, screenshots and release notes.

The previous tested candidate remains on `fix/review-cache-refresh-checksums`.
No live NAS changes, merge, Community Applications submission or release publishing
were performed as part of this work-in-progress snapshot.
