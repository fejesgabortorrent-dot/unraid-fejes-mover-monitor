# Real torrent continuity / peer-transfer component result — 2026-11-10

**PASS for the bounded component test below. Full guarded-runner acceptance remains open.**

## Scope and revision

- Disposable Unraid 7.3.4 test VM only; production NAS untouched.
- Harness: draft PR [#36](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/pull/36), executed revision `fa24fac08d26810e5863453712f91035a26ef40d`.
- Runtime movement source is the main `2026.10.31.2` executor, carried unchanged on that branch.
- Two LinuxServer qBittorrent `v5.3.0` containers, each limited to 512 MiB, on an internal-only Docker network with no published host ports.
- Image manifest digest: `sha256:3d4c4545d51a690a0df15a2ff99038823a88a9822df8e794526447b9afbd7384`.
- Private, randomly generated single-file torrent, no public tracker or web seed. Seeder reads the logical Unraid user-share path; receiver has a distinct guest data directory.
- WebUI authentication stayed enabled. Generated temporary credentials and session cookies were used locally and are excluded from this report.

## Observed results

| Evidence | Observed value |
| --- | --- |
| Test payload | 16,777,216 bytes (16 MiB) |
| Before movement | Torrent 100%, `stalledUP` |
| Native executor result | `moved`, 16,777,216 bytes |
| Physical cache source absent | true |
| Executor checksum/metadata checks | Passed |
| qBittorrent recheck after movement | 100%, `stalledUP` |
| Logical container content path preserved | true |
| Receiving peer completion | 100% |
| Receiving peer downloaded bytes | 16,777,216 |
| Seeder uploaded bytes | 16,777,216 |
| Receiver hash matches original payload | true |
| Saved final status | `peer_transfer_verified` |

SHA-256 of the original payload, the array copy and the receiving peer's copy:

`0d829db777be51fc3bb4e0eba46312f6a6d567111d3fad59eb60074ba16c7b86`

## Essential acceptance boundary

The harness used the real Docker-exec torrent API, checked that the test torrent was complete and idle, verified its bind-mount namespace, invoked the real native movement engine and its checksum/metadata checks, then performed a real qBittorrent recheck and transfer to the second client.

The executor's `fresh_candidate()` was **simulated in that Python process**. The newly created torrent cannot satisfy the production one-day age floor in an immediate test. That function also covers additional protections; this test does not replace their acceptance. No installed runtime file or persistent Advanced-mode configuration was patched by that in-memory override.

This proves that **this test torrent remained valid and uploadable after this component move**. It does not certify the full guarded batch runner, real elapsed age eligibility, integrity coordination, crash/power-loss recovery, tracker credit, reboot persistence, production VPN behavior, broad hardware support or Unraid 8.

## Test-harness corrections during the run

1. The current API returned a successful add with a response body differing from the historical `Ok.` expectation. The torrent list already showed 100% completion. The harness now uses authoritative torrent state and can recover an existing prepared run.
2. The first immediate transfer check lacked complete counter evidence. A duplicate add on retry was also rejected. The harness now resumes an existing peer torrent, waits a bounded interval for counters and retains diagnostic observations. It reports success only after the full byte counts and content hash match.

The initial failures are preserved in PR #36 discussion; they were not relabelled as successful tests.

## Saved continuation

The guest data disk retains the private structured result and a source archive. The public continuation checkpoint is [on the test branch](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/blob/test/seed-lab-20261110/docs/CONTINUATION-20261110.md). Docker auto-mount/start after guest reboot is not configured or certified; the checkpoint explains recovery. The PR remains draft and unmerged; Beta/RC1 remains in effect.
