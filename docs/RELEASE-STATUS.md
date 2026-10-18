# Release candidate status — 2026-10-18

This candidate replaces the earlier archive-based packaging proposal with a self-contained PLG. All four runtime pages now have a source file under `src/`, embedded exactly by `tools/build.py`. Five protection helpers are embedded from `tools/` and installed alongside the pages. No missing GitHub Release archive is referenced. The older files under `plugin/` are historical development files, not the build source.

Community Applications status: **not submitted**. No acceptance is claimed.

## Verification

Run `python3 tools/check.py` with Python 3 and PHP CLI. It checks deterministic generation, all published checksums, XML metadata and PHP syntax. It stages the PLG inline pages into a temporary directory and runs the install and remove scripts against that directory. It checks repeat installation, rejection of invalid Python/PHP before activation, helper retention, and preservation of unrelated files on removal.

Current isolated validation: 38 Python unit tests, 20 application fixture checks, PHP lint on four pages, JavaScript syntax checks on the three scripted page types, and the packaging lifecycle check. Shared protection diagnostics and the CSRF-protected wiring action are covered. Offline cron removal, reload rollback, active cron verification, conservative capacity estimates, and guarded launch rejection/concurrency are covered.

This is an isolated Linux packaging test, not an Unraid acceptance test. It does not emulate Unraid's plugin manager or WebGUI.

The [USB-free simulation](SIMULATION.md) additionally executes the real reviewed
launcher and torrent assessor through 12 scenarios, with checksummed synthetic
file movement and timestamp assertions. GitHub Actions now runs the unit,
application, package lifecycle and simulation checks on pushes and pull requests.
The workflow retains the generated simulation HTML/JSON for review.

## Remaining Unraid acceptance tests

Use a disposable licensed Unraid 7.x system and test disks. Do not use production disks or the production USB flash device.

- Install through the actual Unraid plugin manager and inspect PHP/system logs.
- Confirm Tools routes, dashboard integration, automatic refresh and session expiration.
- Check idle, running and stale PID states; verify observed file descriptors during real Mover activity.
- Verify unavailable `cache` is shown honestly, and test systems without the optional legacy script.
- Verify settings CSRF rejection, conflicting edits, backups and recovery with a disposable legacy script fixture. Confirm the script uses minutes for `UJRA_PROBALKOZAS_MP` before enabling this editor.
- Verify the shared protection page and Python/Docker/API dependencies on Unraid.
- The current live legacy launcher was reviewed on 2026-10-18. Test `wire_mover_gate.py` in check-only mode, then apply on the NAS and verify the existing User Scripts path calls the modified file. No live gate installation is claimed yet.
- Test static watcher exclusion cleanup and large-download cache pressure; these are not automated by this candidate.
- Verify update, reboot persistence, uninstall and rollback, including restoration of the original File Integrity cron command.
- Record actual results and Unraid version before merging/publishing the candidate.

## Community Applications preparation

Checked against the official submission help on 2026-10-17:

- https://ca.unraid.net/submit/help
- https://ca.unraid.net/submit/help/repository-xml
- https://ca.unraid.net/submit/help/repository-info-xml

The candidate contains an MIT license, non-empty root `ca_profile.xml`, icon, plugin wrapper with `PluginURL`, support/project links, and an overview that discloses the Hungarian interface and the `cache`-only pool limit. Plugin submissions require manual review. After the acceptance tests, run Validate and Scan at https://ca.unraid.net/submit/new, review the listing, and submit. A GitHub merge alone is not a CA submission.
