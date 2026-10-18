# Experimental beta 0.1.0-beta.1 — 2026-10-18

Plugin version: `2026.10.18.1`. Unraid 7.x / PHP 8+. This is an experimental pre-release, not a production-validated or Community Applications-approved release.

PR #2 and #4 were merged with the owner's explicit approval. The current mode implementation passed Codex review at `9168e6b9ceaf53b27c4369f38772f1d855e6a774` with no findings, and its GitHub Ubuntu CI passed. Local validation includes 41 application checks, 31 mode safety checks, eval-based page execution fixtures, JavaScript syntax/refresh/banner checks, reproducible XML/checksums/PHP and isolated install/reinstall/rejection/uninstall checks.

Default: Observer. Optional Demo uses synthetic display data; Advanced explicitly enables the existing cache-only legacy script editor. One configured pool can be selected for observation. Mode changes do not start Mover.

**Still unverified:** actual Unraid plugin-manager installation and Dashboard integration, live Mover behavior, reboot persistence and broad hardware/configuration compatibility. Concurrent mode/save scenarios, missing-host-marker cases and a complete refreshed browser walkthrough remain on the beta backlog. No live NAS changes were performed in preparing this release.

[Installation, checksums and removal/recovery](BETA-INSTALL.md). Community Applications: **not submitted**. Earlier WIP notes are historical development snapshots, not the release's current validation statement.
