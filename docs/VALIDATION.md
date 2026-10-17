# Candidate validation — 2026-10-17

Executed `python3 tools/check.py` on Ubuntu 24.04 with PHP CLI 8.3.6.

PASS: deterministic manifest rebuild; SHA-256 checks; PLG/profile/wrapper XML; all three runtime page PHP syntax checks; embedded source matches `src/`; isolated clean install; repeated install; invalid PHP rejected without changing installed pages; removal preserves unrelated files.

NOT RUN: actual Unraid plugin-manager install/update/uninstall, reboot, WebGUI rendering, live Mover process detection, optional settings POST behavior and rollback on Unraid. No CA Validate/Scan or submission has been completed.

The test redirects installer paths into a temporary directory. It is packaging evidence only and does not prove Unraid compatibility.
