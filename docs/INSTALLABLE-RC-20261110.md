# Installable candidate 2026.11.10.3

Status: test candidate; not certified for production.

Based on main 0b9874a8bf27602a4d53e3987083176b52a5a6f3, with the preflight safety work from PR #35 reconciled with the current profile and directory-unit protections.

The runner records native intent only immediately before native execution, preserves unresolved prior reports, and retains private per-file destination, signature and SHA256 evidence. Directory grouping and batch limits remain enforced. Fixture tests block accidental live service/native commands.

Validation on 2026-11-10:
- 168 Python unittest cases passed, including preflight boundaries and abrupt-exit recovery.
- Package check passed: reproducible manifest/checksums, XML, PHP lint, isolated install/update/rejection/remove.
- All seven JavaScript test suites passed.
- Local PHP 8.4.27 CLI used for package/UI fixture checks; this is not the guest PHP runtime.

Outstanding gates: install this exact candidate in FejesMover-Test; genuine guarded-run age/integrity/API-failure acceptance; VM lifecycle/reboot checks. Prior real torrent peer-transfer evidence applies only to the documented component test, not to this candidate's full guarded runner. Do not reboot the lab before deliberately correcting its Docker persistence configuration; the last checkpoint used a manually mounted 4 GiB image while docker.cfg retained disabled/default settings.

The validated release manifest and Community Applications wrapper use the main branch as their update channel. Development candidates should be installed by immutable commit URL and must not redirect updates to a stale feature branch. Community Applications metadata updates only when the validated change reaches main; catalog refresh timing is independent.

## Follow-up

The preceding 2026.11.10.1 candidate installed successfully on FejesMover-Test, and the guest package check passed. Before full guarded-run acceptance, review found physical pool normalization duplicated the share name. Candidate .2 fixes that mapping and adds a regression test covering cache, custom pool, disk, user0 and user views. The full 168-case Python suite and isolated package check pass. The read-only testlab/live_readiness.py diagnostic refuses other hostnames and reports missing live prerequisites without repairing them.

## Actual VM progress

Candidate 2026.11.10.2 installed successfully. Fresh private 16 MiB torrent prepared with genuine one-day age and inventory observations. The installed runner passed a genuine API-outage test: the isolated fm-qbit container was stopped, the runner deferred with zero movement and no inspection latch, source SHA256 remained intact, and the container was restarted. Full age-qualified movement and reboot acceptance remain pending.

Candidate .3 additionally makes the scheduled integrity preflight use the validated profile container instead of a fixed production container name. 169 Python cases and the isolated package check passed. The configure_protection lab script uses upstream File Integrity settings generation and a completed real cache scrub; its execution is tracked separately from code checks.
