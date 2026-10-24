# Experimental beta — 2026.10.24.2

Candidate .24.1 adds optional ratio priority and an explicit batch size selector. Ratio affects order only after eligibility; low/missing ratios never withhold candidates. Shared ownership uses the minimum ratio, unknown values remain unknown. The private queue gains a ratio column. Existing configs default to priority disabled and 16 GiB. Saves retain config backups and reject concurrent/stale forms. Neither feature overrides age, torrent activity, maintenance or integrity guards. No production media or live reboot acceptance is claimed for this candidate.

The .995 follow-up fixes long filename and status wrapping under the surrounding Unraid theme. Forecast calculations and movement behavior are unchanged.

The .994 follow-up adds a private, timestamped waiting table with per-file size, earliest age eligibility, countdown and blockers. Explicit preview returns a fresh read-only forecast; scheduled inventory observations cache a snapshot. Displayed dates never authorize movement or promise start/finish times. Changing the age setting hides an older forecast until refreshed. Movement safety checks and limits are unchanged.

The .996 interface update adds summary cards, local queue search/status/video filters, expandable full paths and separate settings/manual-action sections. Manual start shows a confirmation explaining that filters do not select the execution scope. Eligibility rules, limits and schedules are unchanged.

Unraid 7.x / PHP 8+. Observer remains the default. Installation and mode changes do not start movement or create a schedule.

## Reporting correction

The .993 follow-up preserves every batch-limit skip in the final selective-run report. A file larger than the fixed 16 GiB limit now has a distinct explanation; it cannot move under the current limit. Files deferred by the current batch are reported separately. A run that moves zero files no longer displays the verified-movement completion state. Movement limits and safety checks are unchanged.

## Validation scope

Regression cases cover oversized files, the exact byte boundary, trailing byte-limit skips, file-count deferrals, independent smaller files and native-retained sources. Authenticated UI fixtures check the new explanations in Hungarian, English and German. These isolated tests use synthetic inputs and mocked execution; they are not additional live-NAS movement evidence.

The project validation also checks policy/native invocation/dispatch guards, existing PHP pages, mode guards, stale-artifact rejection, JavaScript refresh behavior, reproducible package/checksums and isolated install/reinstall/rejection/remove. Public CI never performs production movement.

## Remaining limits

Production-media/torrent-file movement, live NAS reboot persistence and broad hardware/configuration compatibility remain unverified. Earlier owner acceptance tests used self-created files outside media libraries; no production-media movement is claimed. Selective execution is fixed to cache/Filmek to Array with user-share torrent bindings and an 8-file batch limit and explicitly configured 16/32/64/128-GiB cap (default 16 GiB). Age includes first observation; old mtime alone does not make a new cache file eligible. Unknown state stops execution.

See [selective movement and recovery](SELECTIVE-MOVEMENT.md) for retained-helper uninstall semantics and explicit restoration of external wiring. Older archive-prototype and acceptance notes are historical.


Candidate .24.2 adds an explicit one-day age option to avoid a mandatory week of observation on an established cache. Default remains seven days and upgrades preserve saved configuration. The newest of first cache observation, modification and torrent completion still controls eligibility. No active/open/incomplete content or maintenance guard is bypassed.
