# Fejes Mover Monitor 0.1.0-beta.1

**Experimental pre-release for Unraid 7.x with PHP 8+. Not production-validated.**
Plugin-manager version: `2026.10.18.1`. UI: Magyar / English (US) / Deutsch.
No live Unraid install, WebGUI acceptance or reboot test has been performed.
Community Applications submission has not been made.

## Install on a test Unraid system

1. Download the release assets and verify the PLG against `SHA256SUMS`.
   The release checksum file applies to the attached installer and this guide;
   the repository checksum file additionally covers the source templates.
2. In Unraid, open **Plugins → Install Plugin** and use the pinned installer:

```
https://raw.githubusercontent.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor/v0.1.0-beta.1/fejes.mover.monitor.plg
```

3. The installer checks for Unraid 7.x WebGUI, boot configuration and PHP 8+ before
   changing runtime pages. Unsupported versions are rejected.
4. Open `/Tools/FejesMoverSetup`. Initial mode is **Observer** and the selected
   pool defaults to `cache`. Start with **Demo** if you want synthetic readings.
5. Select an existing configured pool and Observer for live read-only monitoring.
   Unmounted pools remain unavailable. No Mover is started by changing modes.
6. Advanced mode requires explicit acknowledgment and enables only the optional
   editor for a pre-existing `Filmek_Mover_Threshold` script with the cache pool.
   The plugin does not install that script or create a schedule. Before any real
   use, verify that your script interprets `UJRA_PROBALKOZAS_MP` as minutes.

Open `/Tools/FejesMover` for the monitor and the Unraid Dashboard for its tile.
The 🌐 selector persists the browser language. Language changes discard unsaved
form edits and navigate without submitting settings.

## Updating

Keep a copy of the previously used installer and plugin configuration first.
Updates point at the repository main-branch PLG; use a tagged URL to pin a known
release. Check release notes and checksums before updating. An update preserves
the plugin configuration; it does not reset a previously selected Advanced mode.

## Disable / remove / recover

- To disable automation editing, select Observer (or Demo) in mode setup.
- Remove `fejes.mover.monitor` using **Plugins → Remove**. Owned runtime pages and
  the helper are removed. The plugin-owned settings and legacy-script backups are
  preserved. Removing the plugin does not stop Unraid Mover or any external script.
- Mode settings live in `/boot/config/plugins/fejes.mover.monitor/settings.json`.
  If their JSON is damaged, mode setup can save a validated replacement. Bad
  configuration disables the automation editor; actual lock/read errors block saves.
- If Advanced mode changed your legacy script, removal does not undo that change.
  Backups are under `/boot/config/plugins/fejes.mover.monitor/backups/`. Compare the
  appropriate backup with the current script before restoring; never overwrite
  subsequent edits blindly. Stop and obtain help if the intended original is unclear.
- Reinstall the pinned beta only after inspecting logs and resolving the cause of
  a failure. Do not describe reinstalling an untested earlier build as a safe rollback.

## Verified / still unverified

Passed: 41 isolated application checks, 31 mode safety checks, eval-based page
fixtures, JavaScript syntax and refresh/banner state tests, reproducible package,
checksums, PHP/XML validation, isolated clean/repeated install, invalid PHP and
unsupported OS rejection, uninstall preservation and stale-artifact rejection.
GitHub Ubuntu CI passed for the reviewed implementation. Codex review of
`9168e6b9ceaf53b27c4369f38772f1d855e6a774` reported no findings.

Not verified: live Unraid installation, real Dashboard integration, Mover transfers,
reboot persistence and broad hardware/configuration compatibility. Further browser
walkthrough, concurrency and missing-host-marker coverage remain on the beta backlog.

## Magyar rövid útmutató

Kísérleti béta, **Unraid 7.x-re**, nem általános operációs rendszerekre. A fenti,
verzióhoz rögzített PLG-címet a Plugins → Install Plugin mezőben lehet használni.
Telepítés előtt ellenőrizd a kiadáshoz tartozó checksumot. Első próba: Demó mód;
valós megfigyeléshez Megfigyelő mód és a saját pool kiválasztása.

A Haladó mód külön jóváhagyás után a meglévő, cache-alapú scriptet szerkesztheti.
A módváltás nem indít Movert. Eltávolítás: Plugins → Remove; a beállítások és a
scriptmentések megmaradnak. A korábbi scriptmódosításokat az eltávolítás nem vonja
vissza automatikusan. Az élő Unraid-telepítés és újraindítás még nincs tesztelve.
