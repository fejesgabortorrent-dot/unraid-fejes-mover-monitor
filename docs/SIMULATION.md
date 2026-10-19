# FejesMover: USB-free simulation

Run on Linux with Python 3.10+, Bash, flock, awk and GNU grep. No root,
Docker, USB device, Unraid license or third-party Python package is needed.

```bash
python3 tools/simulate.py --output /tmp/fejes-demo-report
```

Choose a new output directory on each run. Open its `index.html` in a browser
for the Hungarian scenario table and expandable logs. `results.json` contains
machine-readable evidence. A nonzero exit means a scenario failed.

[Example report](simulation-example/index.html) · [Example JSON](simulation-example/results.json)

## What really runs

The production `rewrite_launcher()` validates and instruments the reviewed
threshold script. Bash executes that script. The unchanged production
`torrent_preflight.assess()` evaluates synthetic torrent records. The ready
scenario moves an actual generated 120 KiB file between two temporary folders.
Every scenario checks the payload checksum, attempt timestamp, torrent-gate
invocation, expected move decision and process exit code.

Only environmental boundaries are synthetic: free-space output, cache mount
status, torrent API snapshot, backup PID marker, parity status and Mover PID.
The Mover executable is replaced with a tiny file-moving fixture. Every
production path in the launcher is redirected into a fresh temporary directory;
the runner rejects a launcher containing known production paths after rewriting.
Temporary data is removed automatically. Reports are the only retained files.

## Scenarios

1. Low space and completed torrents: moves the file and records the attempt.
2. Sufficient space: leaves the file in cache and skips the torrent gate.
3. Exactly 300 GiB free: does not move.
4. Active download: defers without writing an attempt timestamp.
5. Nearly complete stalled download: defers.
6. Completed torrent still checking: defers.
7. Unavailable API: fails closed.
8. Live backup PID: defers before the torrent gate.
9. Active parity operation: defers before the torrent gate.
10. Existing Mover PID: defers.
11. Active cooldown: preserves the existing timestamp.
12. Unmounted cache: rejects execution before the gate or move.

GitHub Actions runs the simulation on pushes and pull requests and uploads the
HTML/JSON as `fejes-mover-simulation` artifacts. The checked-in example is one
local run, not evidence that a GitHub Actions run has completed.

## Limits

This does not verify the real Unraid Mover, WebGUI integration, Docker/API
transport, disk filesystems, reboot persistence or physical hardware. It does
not simulate File Integrity/Bunker. Existing unit and package lifecycle tests
remain separate. Live Unraid acceptance is still required before release.
