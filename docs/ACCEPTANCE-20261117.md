# Completed-download movement acceptance — 2026-11-17

Version 2026.11.17.1 adds an explicit completed-download mode. Completion
replaces age and ratio waiting. The affected torrent is stopped briefly for
verified native cache-to-array movement and restored afterward. Its user-share
path stays unchanged. This does not promise uninterrupted upload during the move.

## Verified scope

- Unraid 7.3.4, one reviewed cache/share/qBittorrent profile.
- Fresh disposable VM torrents, physical and logical SHA-256 checks, source
  absence and restored complete seed state.
- A fresh 32 MiB VM peer test verified actual upload after movement. Earlier
  November 10 test data were preserved, not replayed.
- A separate fresh hybrid test kept one existing array member in place and
  moved only the remaining cache member; all hashes passed.
- API failure and pre-native worker termination tests preserved source data
  and restored the original torrent state. Ambiguous native intent remains
  blocked for inspection.
- The installed 2026.11.17.1 scheduler moved two fresh files (33,554,432 bytes)
  with age=30 days and ratio=100 configured, demonstrating completion-based
  eligibility. Real 2%/1% thresholds were used on the almost-empty 8 GiB test
  cache. Original disabled automation, settings and cron were restored.
- GitHub Actions run 209 passed all checks on runtime commit 5daa16a.

## Deployment

FejesNAS was upgraded from 2026.11.16.5 after a read-back-verified rollback
archive covering 211 files. All 23 installed helpers matched the tested source.
The saved completed-download mode uses 75% start / 65% stop and a 32 GiB cap.
The existing single 15-minute User Scripts schedule was retained; a second
scheduler was not created. Initial measured cache free space was about 214 GiB.
Final production-run evidence is recorded separately before release approval.

## Limits

Each invocation handles one complete unit, at most 32 GiB and 128 files.
Crossing the lower threshold finishes the already-started verified unit, so
usage may fall below the target. A later scheduled invocation continues an
active drain cycle until the lower threshold is reached.

Incomplete torrents and units exceeding the cap remain in cache. Direct-to-HDD
downloading for torrents larger than cache is not implemented. Reverse movement,
public tracker credit, physical power-loss and mid-native-I/O process-loss
recovery are not certified. Existing maintenance, open-file, namespace, lock,
cooldown and inspection protections remain mandatory. Installation does not
enable this mode on other installations.

Private file names, credentials, torrent hashes and production logs are excluded
from published evidence. Full operational proofs and rollback archives stay on
the owner's NAS and in the local project checkpoint.
