# Installable candidate 2026.11.10.1

Status: test candidate; not certified for production.

Based on main 0b9874a8bf27602a4d53e3987083176b52a5a6f3, with the preflight safety work from PR #35 reconciled with the current profile and directory-unit protections.

The runner records native intent only immediately before native execution, preserves unresolved prior reports, and retains private per-file destination, signature and SHA256 evidence. Directory grouping and batch limits remain enforced. Fixture tests block accidental live service/native commands.

Validation on 2026-11-10:
- 167 Python unittest cases passed, including preflight boundaries and abrupt-exit recovery.
- Package check passed: reproducible manifest/checksums, XML, PHP lint, isolated install/update/rejection/remove.
- All seven JavaScript test suites passed.
- Local PHP 8.4.27 CLI used for package/UI fixture checks; this is not the guest PHP runtime.

Outstanding gates: install this exact candidate in FejesMover-Test; genuine guarded-run age/integrity/API-failure acceptance; VM lifecycle/reboot checks. Prior real torrent peer-transfer evidence applies only to the documented component test, not to this candidate's full guarded runner. Do not reboot the lab before deliberately correcting its Docker persistence configuration; the last checkpoint used a manually mounted 4 GiB image while docker.cfg retained disabled/default settings.

Candidate update channel is the dedicated fix/installable-preflight-rc branch. The Community Applications main listing has not been changed by this candidate.
