# Preflight safety candidate — 2026-10-29

Development branch only; do not deploy or clear an existing inspection latch.
PR #9 remains an older, open draft planner prototype. This fix is based on
current main `9655f4e`, which contains the execution adapter and later UI work.
Read-only owner verification found the installed executor identical to that base
(SHA-256 `1038d722031f7d28798baa24791b56c07208eb1b329b9c9f72a8a95af470b7e0`).
The owner system has an active inspection latch; this change does not resolve it.

## Boundary and recovery

Previously `run()` persisted `active_file_started=true` before calling
`execute_file()`. Both fresh torrent/integrity checks occur inside that call,
before native execution, so a preflight failure looked like uncertain movement.

The v2 report explicitly records read-only preflight with zero moved counters and
`active_file_started=false`. Only after both fresh checks, metadata/checksum
collection, destination checks and the open-file check does a required callback
persist native intent. Failure to persist prevents native invocation. The marker
stays set until execution and verification return. Native failures, uncertain
postchecks and errors after an earlier moved file remain inspection errors.
Old running reports, ambiguous v2 reports and every existing inspection latch
remain blocked. Only an explicit v2 zero-operation preflight report can avoid a
new inspection latch; a stale PID still blocks launch independently.

Known pre-native Docker-exec torrent query failures/timeouts and active integrity
hashing defer the batch. No internal retry, API authentication change, host API
fallback, torrent pause/resume, file deletion or global mover invocation was added.
Unknown preflight failures stop as errors without claiming native movement began.
Every future attempt must acquire the same locks and pass all existing guards.

The UI consumes allowlisted error codes, including preview failures, before
discarding a nonzero worker response. It distinguishes inspection, unavailable
torrent state, integrity waiting, expired session, changed/invalid settings and
save failures in Hungarian, English and German. Unknown causes are explicitly
unknown. Private exception strings, paths and command arguments are not rendered.

## Test isolation and navigation

Run Python checks through `python3 tools/isolated_test.py ...`. It sets disposable
temporary directories and installs an inherited Python audit hook that fails
loudly on production-path writes/mutations or live Docker/logger/native commands.
Executor/diagnostic tests also install the hook when invoked directly, and pass
it to their Python children. The exception derives from BaseException so
diagnostic best-effort handlers cannot silently hide a test leak. This is a
regression tripwire, not an OS sandbox for
arbitrary shell/PHP code. Tests are intended for a development host/CI, never the
production NAS. PHP fixtures explicitly rewrite production locations into their
temporary directories. No test-error log is copied into a release package.

Mobile navigation uses a wrapping two-column destination grid at <=700 px and
normal document flow. All controls remain at least 44 px high. The setup page now
renders the shared navigation in all three language branches. Browser assertions
cover all four full pages, three languages and widths 320/375/430/700/1024 px,
checking destinations, overlap, clipping and horizontal navigation overflow.

## Acceptance boundary

Automated checks cover failures before/after native intent, first/second fresh
checks, sticky old latches, interrupted child processes and test-isolation leaks.
They simulate native movement in disposable filesystems. They do not certify
actual Unraid movement, tracker credit, peer upload, NAS reboot or power loss.

Before any production recovery, retain the old report/log and independently
establish whether native execution began and whether every source/destination
from the affected operation is consistent. Zero counters alone are insufficient.
No unlock, production movement, file deletion, deployment, merge or release is
part of this candidate.

## Local validation

- 19 localized selective interface tests passed, including specific worker errors,
  unknown causes, escaping, CSRF and fixed-command dispatch.
- 29 ratio-priority, waiting-table and torrent-preflight tests passed.
- The Windows isolation write/command regression test passed; the separate
  Linux diagnostic-handler test was skipped locally.
- All seven existing JavaScript behavior checks passed.
- 60 browser page/viewport navigation combinations passed with the installed
  Chrome browser. Fixtures used actual rendered pages and disposable settings.
- Python compilation and PHP syntax checks passed; the generated manifest and
  source payloads were rebuilt locally.
- [GitHub Actions run 40891690001](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/actions/runs/40891690001)
  passed on implementation commit `65d2f8a`: the complete Linux suite including
  interrupted-process checks, isolated package install/update/rejection/remove,
  reproducibility, interface/mode safety and all JavaScript checks. The separate
  Linux Chromium navigation job also passed. Publication was skipped.
- The Windows full installer check could not complete in Git Bash; Linux CI
  supplies the successful package check. Neither environment is a live Unraid
  movement or seed-upload acceptance test.
