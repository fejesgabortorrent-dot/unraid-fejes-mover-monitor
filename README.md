# Fejes Mover Monitor

Hungarian-language Mover dashboard and file monitor for Unraid 7.x.

**Release candidate. Not submitted to Community Applications. Clean install, update, reboot and uninstall still require validation on a disposable Unraid system.**

## Features

- Dashboard tile with Mover process status and cache usage.
- Tools page showing open files belonging to the Mover process tree.
- Recent Mover-related syslog lines, escaped before display.
- Polling only while the page is visible, with timeouts and stale-data notices.
- Optional settings page for an existing `Filmek_Mover_Threshold` User Scripts automation.

## Requirements and limits

- Unraid 7.0+ and its bundled PHP 8; the original local version was used on Unraid 7.3.3.
- This first version monitors a pool named **cache** at `/mnt/cache`. Arbitrarily named pools and multi-pool selection are not supported yet.
- The interface is in Hungarian. English translation is not included yet.
- Mover activity is inferred from `/var/run/mover.pid` and `/proc`. Custom Mover implementations may not be detected.
- File positions are observations, not verified transfer progress. No transfer ETA or total progress is claimed.
- The cache-to-array diagram is illustrative. Actual movement direction is controlled by each share's Unraid settings.
- The optional threshold panel requires the pre-existing script at `/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script`. It is not distributed here. Without it, monitoring still works and settings explain that the optional automation is unavailable.
- The settings panel changes only `KUSZOB_GIB` and `UJRA_PROBALKOZAS_MP`, after CSRF, version, range, lock and shell-syntax checks. It saves a backup first. The legacy UI interprets `UJRA_PROBALKOZAS_MP` as minutes; check your script's semantics before using this panel with a different script.
- The plugin does not install a scheduler, start Mover, move files or provide backup/parity guards itself. Those remain the responsibility of Unraid and any existing automation.

## Planned installation after Unraid acceptance testing

Do not install this candidate on a production NAS yet.

In Unraid, open **Plugins → Install Plugin**, then enter:

```
https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/main/fejes.mover.monitor.plg
```

The manifest contains the runtime pages. It does not rely on files from the author's NAS. The installer checks PHP syntax before activating them.

Open **Tools → Mover figyelő** or the dashboard tile. Plugin updates use the manifest URL above.

## Uninstall

Remove `fejes.mover.monitor` through Unraid's Plugins page. Its three runtime pages are removed. Existing local automation scripts and `/boot/config/plugins/fejes.mover.monitor/backups` are preserved.

## Privacy and support

No telemetry, credentials, server logs or user files are shipped in this repository. Live file paths and syslog excerpts are shown only inside the authenticated Unraid interface. Redact personal filenames before posting screenshots.

Report problems at [GitHub Issues](https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/issues). Include your Unraid version, pool name and reproduction steps. Do not attach credentials or full private logs.

## Optional torrent preflight for an external Mover launcher

`python3 tools/torrent_preflight.py` performs a read-only qBittorrent check.
It returns 0 only when every reported torrent is complete and in a known seed
state; unfinished, stopped downloads, checks and moves return 10. API failures,
unknown states and invalid snapshots return 20. Both nonzero results mean defer.
The optional `--json` report includes host paths and must be kept private.

This standalone tool is **not installed by the PLG** and does not change the
legacy launcher, Unraid Mover or Dynamix File Integrity. It cannot enforce
per-file Mover exclusions or prevent a torrent starting after its snapshot.
See [torrent / Mover / File Integrity integration notes](docs/TORRENT-INTEGRITY-HU.md)
before wiring it into an existing script. The live launcher must be reviewed
first; it is not included in this repository.

Run its isolated tests with `python3 tools/torrent_preflight_test.py`.

## Build

```
python3 tools/build.py
python3 tools/check.py
sha256sum -c SHA256SUMS
```

This rebuilds the self-contained `.plg` manifest and checksums from `src/`. Before publishing changes, run PHP lint on all page files, validate the XML, and test install/update/remove on an appropriate Unraid system.

## License

MIT. Copyright 2026 FejesNAS contributors.

## Release readiness

See [release status and remaining acceptance tests](docs/RELEASE-STATUS.md). Earlier packaging and testing notes describe the previous archive-based prototype; this candidate uses the self-contained manifest and `src/` files.

## Optional support

Fejes Mover Monitor is free and open source. If you find it useful, you can [support FejesNAS development via PayPal](https://paypal.me/FejesG). Support is voluntary and does not unlock features or guarantee support or development timelines.

A Fejes Mover Monitor ingyenes és nyílt forráskódú. Ha hasznosnak találod, [támogathatod a FejesNAS fejlesztéseit PayPalon](https://paypal.me/FejesG). A támogatás önkéntes.

