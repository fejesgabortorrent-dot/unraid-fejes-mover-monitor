# Release candidate status — 2026-10-18

Version 2026.10.17.1 is a self-contained PLG. All three runtime pages are compiled from Hungarian templates under `src/` and the English/German translation catalog by `tools/localize.py` and `tools/build.py`. No missing GitHub Release archive is referenced. The older files under `plugin/` are historical development files, not the build source.

The interface supports Magyar / English (US) / Deutsch. On 2026-10-18 the exact file tree of GitHub revision `543300a61d7052bc9ed0df45b7b277005a4b45fd` was retested in a fresh disposable filesystem: 41 application checks, rendered JavaScript syntax, refresh race/state checks, package reproducibility, checksums, XML, PHP lint, clean/repeated installation, invalid-PHP rejection, uninstall preservation and stale-artifact rejection passed. This was a Windows-hosted PHP/Git Bash fixture run, not a live Unraid acceptance test.

The existing clean Codex review applies to earlier revision `7078273`, before the language feature. It must not be described as a review of the latest revision. A GitHub Actions workflow now runs the isolated tests for PR updates and main-branch pushes; its run status must be checked separately.

Community Applications status: **not submitted**. No acceptance is claimed.

## Verification

Run `python3 tools/check.py` with Python 3 and PHP CLI. It checks deterministic generation, all published checksums, XML metadata and PHP syntax. It stages the PLG inline pages into a temporary directory and runs the install and remove scripts against that directory. It checks repeat installation, rejection of invalid PHP before activation, and preservation of unrelated files on removal.

These are isolated filesystem tests, not an Unraid acceptance test. They do not emulate Unraid's plugin manager or WebGUI.

## Remaining Unraid acceptance tests

Use a disposable licensed Unraid 7.x system and test disks. Do not use production disks or the production USB flash device.

- Install through the actual Unraid plugin manager and inspect PHP/system logs.
- Confirm Tools routes, dashboard integration, automatic refresh and session expiration.
- Check idle, running and stale PID states; verify observed file descriptors during real Mover activity.
- Verify unavailable `cache` is shown honestly, and test systems without the optional legacy script.
- Verify settings CSRF rejection, conflicting edits, backups and recovery with a disposable legacy script fixture. Confirm the script uses minutes for `UJRA_PROBALKOZAS_MP` before enabling this editor.
- Verify update, reboot persistence, uninstall and rollback.
- Record actual results and Unraid version before merging/publishing the candidate.

## Community Applications preparation

Checked against the official submission help on 2026-10-17:

- https://ca.unraid.net/submit/help
- https://ca.unraid.net/submit/help/repository-xml
- https://ca.unraid.net/submit/help/repository-info-xml

The candidate contains an MIT license, non-empty root `ca_profile.xml`, icon, plugin wrapper with `PluginURL`, support/project links, and an overview that discloses the three interface languages and the `cache`-only pool limit. Plugin submissions require manual review. After the acceptance tests, run Validate and Scan at https://ca.unraid.net/submit/new, review the listing, and submit. A GitHub merge alone is not a CA submission.
