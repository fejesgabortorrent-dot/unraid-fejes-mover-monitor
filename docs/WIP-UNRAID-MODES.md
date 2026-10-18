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

Pending before treating this as a beta:

- Adapt application fixtures and the local browser demo to stage the shared PHP
  runtime, pool definitions and plugin configuration in temporary directories.
- Add mode tests: observer/demo direct POST rejection, advanced acknowledgment,
  invalid/traversal/unknown pool rejection, custom/unmounted pool readings, corrupt
  configuration fail-closed behavior, conflicting edits, and concurrent mode/save.
- Check all setup text and language selection; review demo mode data isolation.
- Test preflight rejection and preservation on unsupported/missing Unraid hosts.
- Run every existing test and the new regression tests on Linux CI.
- Refresh README, release status, package metadata, screenshots and release notes.

The previous tested candidate remains on `fix/review-cache-refresh-checksums`.
No live NAS changes, merge, Community Applications submission or release publishing
were performed as part of this work-in-progress snapshot.
