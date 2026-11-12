# Reboot recovery — current candidate operating limit

This documents recovery with manual revalidation. Unattended reboot-to-ready
operation and physical power-loss recovery are not certified.

## Observed behavior

The FejesMover-Test guest retained its plugin, profile, torrent data and Docker
configuration across a controlled reboot. Its existing policy required manual
array startup. Btrfs then reported no scrub history. The Mover blocked until a
fresh, real scrub of the small disposable cache completed without errors.

The current guard requires `btrfs scrub status <configured pool>` to report both
`Status: finished` and `no errors found`. Missing history is not a successful
health check. This condition can prevent movement after reboot even when files
and containers are otherwise available.

## Operator recovery sequence

1. Confirm the intended server and pool. Wait for normal array/pool startup and
   any maintenance to finish. Do not reboot the production NAS to reproduce a
   disposable-guest test.
2. Confirm that the installed version, selective profile, existing Docker image,
   torrent clients and their authenticated API are present. Preserve the current
   torrent, inventory and any inspection report; do not prepare replacement data.
3. Read the actual scrub result, for example `btrfs scrub status /mnt/cache` for
   the reviewed cache profile. If it is absent, active or unhealthy, keep movement
   blocked. Investigate errors; do not interpret a missing result as corruption.
4. Where a new scrub is appropriate, complete a real pool scrub through the
   normal Unraid controls and inspect its result. The earlier quick test was on
   a tiny VM pool, not a duration estimate for a production SSD pool.
5. Request a fresh Mover observation. Every guard must pass. Recheck actual file
   and torrent age; a forecast is not authorization to move.
6. For the isolated acceptance workflow only, run the installed guarded runner
   after genuine eligibility, then verify destination content, source absence,
   unchanged logical torrent path, client recheck and real peer download.

Never edit scrub output, backdate first observations, weaken a guard or clear an
inspection requirement just to make recovery look automatic. A native/partial
movement failure still requires examination of its preserved evidence.

## Remaining release gate

The documented limitation is now explicit. Full age-qualified positive movement
and post-move peer proof remain separate outstanding acceptance gates. Any future
automatic recovery implementation must collect trustworthy pool health evidence
and receive its own guest tests before an unattended recovery claim is made.
