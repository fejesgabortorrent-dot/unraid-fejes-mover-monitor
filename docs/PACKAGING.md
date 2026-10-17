# Packaging and installer design (draft)

**No installable release has been published.** The repository currently contains development source only.

Target repository: https://github.com/fejesgabortorrent-dot/unraid-fejes-mover-monitor

## Proposed release artifacts
- `fejes-mover-monitor-<version>.tar.gz` with `fejes.mover.monitor/FejesMover.page` and `fejes.mover.monitor/FejesMover.Dashboard.page`
- `fejes.mover.monitor.plg` with a GitHub Releases URL to that exact archive and the archive's SHA-256

## Installation safeguards
1. Download over HTTPS; verify the pinned SHA-256 before extracting.
2. Validate archive member paths and PHP syntax before copying to `/usr/local/emhttp/plugins/fejes.mover.monitor/`.
3. Install both pages with mode 0644; preserve a working installation on failure.
4. Avoid deleting any FejesNAS-specific settings page during a preview install. Design migration and uninstall separately.
5. Confirm that the Tools navigation route and dashboard integration work on Unraid 7.
6. Verify clean installation, upgrades, rollback, and uninstall on a **test** NAS.

## Known development caveats
- Dashboard and detail-page pool selection and process detection require real Unraid validation.
- The repository pages are a development preview, not a signed or approved release.
- Community Applications acceptance is subject to its maintainers.
