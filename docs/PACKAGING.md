# Self-contained PLG packaging

The release candidate embeds all three `src/*.page` files in `fejes.mover.monitor.plg`. It does not require a GitHub Release archive or files from the author's NAS.

Rebuild with `python3 tools/build.py` and verify with `python3 tools/check.py` (requires PHP CLI). All pages are linted before activation. Removal deletes only the three owned runtime pages and preserves local configuration and backups.

`src/` is the authoritative source; the older `plugin/` files are historical prototypes and are not used by the build.

This is a candidate, not an approved production release. See [release status](RELEASE-STATUS.md) for validation and remaining Unraid tests.
