# Unraid test VM validation — 2026-11-10

Status: **partial acceptance evidence; not a stable-release or Community Applications certification**.

## Revisions and environment

- Main revision tested: `26f62660f4831adb5ddcbae498f569f69b74c684`.
- Package installed in the disposable Unraid test VM: `2026.10.31.2`.
- Guest: Unraid 7.3.4, 2 vCPU, 4 GiB RAM; virtual parity/data/cache disks of 24/16/8 GiB.
- Python 3.11.15 was installed in the guest before plugin testing.
- Guest boot configuration was backed up to the guest data disk before installing the dependencies/plugin.
- All live operations described below were confined to the disposable VM. The production NAS was not modified.

## Executed checks

| Check | Environment | Result and limit |
| --- | --- | --- |
| Main Python suite | Separate Linux development checkout | 154 tests passed. Fixture coverage, not live torrent acceptance. |
| PR #35 Python suite | Separate Linux checkout, revision `524b79b9e9093ca5a80bd3ad3a3ea6d04d758810` | 147 tests passed. This revision was not installed in the guest or merged. |
| PR #35 package/checksum/PHP/install lifecycle checks | Disposable filesystem fixtures | Passed reproducibility, lint, install/reinstall/rejection/removal checks. |
| PR #35 JavaScript suites | Separate Linux checkout | All seven existing suites passed. No new live-browser acceptance claimed. |
| Main package install | Actual Unraid test VM plugin manager | Successful installation. No full advanced-mode deployment or schedule was created. |
| Main `tools/check.py` | Actual Unraid test VM | Passed generated artifacts, checksums, PHP lint and isolated install/update/rejection/remove checks. The lifecycle checks use temporary paths; they are not an actual guest reboot or live uninstall test. |
| Main `selective_mover_test.py` | Actual Unraid test VM | 33 fixture tests passed. |
| Main `torrent_preflight_test.py` | Actual Unraid test VM | 10 fixture tests passed. |
| Main `execution_recovery_test.py` | Actual Unraid test VM | One interrupted-process recovery fixture test passed. |
| Native Unraid Mover baseline | Actual guest cache to guest array | Earlier 1 MiB test file moved; SHA-256 matched and cache source was absent. This tests native Mover, not the full plugin flow. |
| Plugin native execution component | Actual guest cache to guest array | A 4 MiB random test file moved through the source revision's `selective_mover.execute_file()`; real native engine and postchecks were used. See isolation boundary below. |

## Live 4 MiB component result

- Size: `4194304` bytes.
- Returned state: `moved`.
- SHA-256 before and after: `f518d2e3e9e81cf4f5003476f520711b71a3b37b12a7688c2ae3944378301551`.
- Physical cache source absent: `True`.
- Physical guest array destination hash matched: `True`.
- The executor's checksum, file metadata and existing extended-attribute postchecks completed without an exception.
- The executor also verified the unchanged logical user-share path.
- The result was retained as a JSON record on the guest data disk. Private guest addresses, absolute evidence paths and terminal screenshots are not published here.

### Isolation boundary — essential to interpreting this result

This was a **component test**, not an end-to-end run. The imported source module's `SOURCE` was scoped in memory to the dedicated test share, and `fresh_candidate()` was replaced in that Python process with a test callback returning the one test file as eligible. The real native move engine, physical array discovery, file validation, open-file check, checksums and metadata postchecks remained in use.

Therefore this result **does not prove** the production eligibility guards, torrent API path, age rules, integrity coordination, batch runner, persistent native-intent recovery, or live seeding behavior. The overrides ended when the Python process exited; installed helper files and persistent movement configuration were not patched by this component test.

## Outstanding release gates

- [ ] Prepare the guest Docker and a dedicated qBittorrent test workload. Docker was not running at the end of this session.
- [ ] Exercise the full guarded executor with real API snapshots and integrity integration, without mocked preflight.
- [ ] Verify incomplete, checking, moving, uploading and open files stay protected while independent eligible files can move.
- [ ] Verify a completed torrent remains present and valid after movement; run a real recheck and a controlled peer transfer. Tracker credit is a separate claim.
- [ ] Reconcile and revalidate PR #35 against current main. Its passing tests do not mean the fix is present in the installed main package.
- [ ] Complete actual guest install/update/reboot/remove/restore acceptance and failure recovery.
- [ ] Keep Unraid 8 and broader hardware compatibility unverified until separately tested.
- [ ] Verify Community Applications has actually refreshed its indexed listing after metadata publication.

## Catalog wording

Keep `Beta=true` and the RC1 designation. The new evidence supports “successful isolated VM installation and native execution component movement”, **not** “fully certified”, “stable”, or “seed protection proven”. The catalog metadata should point to this record; its independent refresh/approval is not established by a repository write.

Related acceptance tracker: [#34](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/issues/34). Related preflight repair: [#35](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/pull/35).
