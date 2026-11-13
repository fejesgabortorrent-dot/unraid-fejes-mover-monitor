# Unattended operation acceptance

## Maintenance race fix

An integrity scan beginning between files must stop the batch without latching
inspection when no native call is pending, every moved file has verified evidence,
and torrent continuity is still verified. Preserve counters, per-file evidence,
and cooldown. A subsequent scheduled run must perform all guards again.

A missing or changed torrent snapshot, unverified native outcome, partial-unit
error, unreadable report, or existing inspection latch remains fail-closed. This
change does not automatically clear historical inspection reports.

## Remaining general-installation gates

- Replace the dependency on the owner's pre-existing User Scripts launcher with
  a plugin-managed, explicitly enabled scheduler and validated settings.
- Keep Observer as the clean-install default. Never infer movement permission.
- Validate configured pool, share, array direction, torrent namespace and client.
- Exercise clean install, update, removal and reboot on a fresh Unraid VM.
- Verify safe recovery from backup, scrub, parity, API downtime and interrupted
  native movement without weakening integrity or torrent protections.
- Prove real movement, matching checksums and peer transfer on that fresh setup.

Until these gates pass, broad unattended compatibility is not claimed.
