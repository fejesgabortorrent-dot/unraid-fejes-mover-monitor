# Persistent diagnostics and interrupted-coordinator recovery — 2026-11-18

Version 2026.11.18.1 retains the opt-in 75% / 65% completed-download mode and
adds durable private run events, a localized movement-page log and terminal
hangup protection. The supported UI start launches a detached session. Direct
worker execution now also ignores terminal hangup; no maintenance protection is
disabled.

## Observed incident and recovery

The production 17.1 worker disappeared after all 12 native file moves were
verified and its torrent restoration was journaled. The final post-resume
verification did not complete, leaving a sticky inspection latch and a PID file
for a process that no longer existed. No final outcome or captured terminal log
was available. Loss of the diagnostic terminal is a possible cause, not a
proven signal diagnosis.

The exact original private authorization, preparation hashes, rollback archive
and complete native ledger were retained. Recovery checked all 12 physical
array destinations and user-share hashes twice, verified no retained cache
sources, unchanged ownership/namespace and four complete torrent API members.
It then backed up the original report and exact absent coordinator PID before
clearing the latch and stale PID. No media movement or torrent restart occurred
during recovery. The torrent was directly observed complete and seed-ready;
production peer traffic was not certified by this incident.

## Isolated verification

- Thirteen recovery policy tests passed on the disposable Unraid 7.3.4 guest.
- A synthetic restored/full ledger over previously verified 32 MiB test files
  and an actually exited owned child exercised read-only inspection, real
  physical/logical hashes, current torrent evidence, backup and PID cleanup.
  No files were moved again; original guest state and November 10 acceptance
  were preserved. This is not a native-I/O crash or power-loss test.
- The installed 18.1 scheduler moved a fresh 32 MiB two-file private torrent,
  verified it and restored seed readiness. The durable journal recorded all
  preparation, stop, native, restore, hash-check and completion phases, and
  the localized movement page displayed them. Original disabled automation,
  selection settings and cron were restored.
- A dedicated test sends an actual SIGHUP only to its own test process and
  verifies the worker dispatch survives.
- Full GitHub Actions run 217 passed on the final runtime/UI commit b1e8c9f.

The full event journal remains on the owner's evidence disk. Only the latest
40 safe events are shown in the application, without media filenames, torrent
hashes or credentials. A missing process without a final event is explicitly
shown as requiring inspection. Native intent is never automatically replayed
or unlocked after process loss.

## Scope and remaining limits

The [November 17 acceptance](ACCEPTANCE-20261117.md) and its limits still apply:
one complete unit per invocation, at most 32 GiB and 128 files, all existing
guards and a reviewed profile. Physical power loss and interruption during
native I/O remain uncertified. Direct HDD downloading of oversized incomplete
torrents is not implemented. The planned dual-handle minimum/maximum control
is a later UI improvement; both limits are already configurable numerically.
