# Guarded acceptance — 2026-11-12

Observed through the owner's connected browser in FejesMover-Test, hostname verified. Guest time approximately 15:30–15:31 CET. Installed candidate 2026.11.11.2; existing /tmp/fm-new test helpers used. No preparation, age override, guard bypass or production move.

## Positive acceptance

- Existing guarded checkpoint reported seeding_before_move, progress=1, stalledUP, source_on_cache=true. Completion epoch 1794341297; genuine readiness 1794427697; observed now 1794493809.
- Ran `python3 testlab/guarded_acceptance.py run` against the installed runner. Finished epoch 1794493839.7544482.
- One 16777216-byte test file moved from cache to disk1; baseline SHA256 matched destination, source absence verified by harness. No blockers or inspection latch.
- Torrent continuity: same_torrents, completed_still_complete, completed_in_seed_states and paths_unchanged all true.
- Ran `python3 testlab/guarded_transfer.py`. It verified completed full-runner evidence, destination hash and source absence, preserved logical path, and performed torrent recheck before peer transfer.
- Final output: PASS: peer downloaded all test bytes after movement; SHA-256 matched; seeder upload counted.

Private checkpoint and detailed evidence remain in the guest guarded acceptance directory. No credentials or private API logs are published here.

## Release scope and qualification

The previously pending positive full-runner move plus recheck/peer-transfer gate has passed for this isolated Unraid 7 test VM. Existing automated candidate validation is recorded in CONTINUATION-RC-20261110.md (183 cases and package/lifecycle checks).

After reboot, btrfs scrub history was unavailable and the guard blocked until a fresh real scrub passed. Recovery therefore requires manual revalidation; unattended reboot-to-ready is not claimed. Public tracker credit, production VPN, power-loss, broad hardware compatibility, Docker edition and Unraid 8 remain unverified or future scope.

This evidence supports review for a scope-limited stable Unraid 7 release. It is not Community Applications acceptance or a stable publication by itself.
