#!/usr/bin/env python3
"""Read-only, conservative qBittorrent gate for an external Mover launcher."""
import argparse
import json
import math
import posixpath
import subprocess
import sys

READY = 0
DEFER = 10
UNAVAILABLE = 20
SEED_STATES = {"uploading", "stalledUP", "queuedUP", "forcedUP", "stoppedUP", "pausedUP"}
BUSY_STATES = {
    "allocating", "checkingDL", "checkingUP", "checkingResumeData", "moving",
    "downloading", "stalledDL", "queuedDL", "forcedDL", "stoppedDL", "pausedDL",
    "metaDL", "forcedMetaDL",
}


def absolute_path(value):
    if (not isinstance(value, str) or not value.startswith("/")
            or "\x00" in value or ".." in value.split("/")):
        raise ValueError("Missing or invalid content/mount path")
    return posixpath.normpath(value)


def host_path(path, mounts):
    path = absolute_path(path)
    matches = []
    for mount in mounts:
        if mount.get("Type") != "bind":
            continue
        dest = absolute_path(mount.get("Destination"))
        source = absolute_path(mount.get("Source"))
        if path == dest or path.startswith(dest.rstrip("/") + "/"):
            matches.append((len(dest), source, posixpath.relpath(path, dest)))
    if not matches:
        raise ValueError("Unfinished content has no known host bind mount")
    _, source, suffix = max(matches)
    return posixpath.normpath(posixpath.join(source, suffix))


def assess(torrents, mounts):
    if not isinstance(torrents, list) or not torrents:
        raise ValueError("Torrent snapshot is empty or invalid")
    if not isinstance(mounts, list):
        raise ValueError("Mount snapshot is invalid")
    protected = set()
    busy = 0
    for torrent in torrents:
        if not isinstance(torrent, dict):
            raise ValueError("Invalid torrent entry")
        progress, state = torrent.get("progress"), torrent.get("state")
        if (isinstance(progress, bool) or not isinstance(progress, (int, float))
                or not math.isfinite(progress) or not 0 <= progress <= 1):
            raise ValueError("Missing or invalid torrent progress")
        if not isinstance(state, str) or state not in SEED_STATES | BUSY_STATES:
            raise ValueError("Unknown, errored or unavailable torrent state")
        if progress < 1 or state in BUSY_STATES:
            busy += 1
            protected.add(host_path(torrent.get("content_path"), mounts))
    return {
        "exit_code": DEFER if busy else READY,
        "decision": "defer" if busy else "no_torrent_blocker",
        "checked_torrents": len(torrents),
        "blocking_torrents": busy,
        "protected_paths": sorted(protected),
    }


def read_snapshot(container, timeout):
    # No shell, credentials, API mutation or direct torrent-state database access.
    inspect = subprocess.run(
        ["docker", "inspect", "--format", "{{json .Mounts}}", container],
        capture_output=True, text=True, check=True, timeout=timeout)
    snapshot = subprocess.run(
        ["docker", "exec", container, "curl", "--fail", "--silent", "--show-error",
         "--connect-timeout", str(timeout), "--max-time", str(timeout),
         "http://127.0.0.1:8080/api/v2/torrents/info"],
        capture_output=True, text=True, check=True, timeout=timeout + 2)
    return json.loads(snapshot.stdout), json.loads(inspect.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="binhex-qbittorrentvpn")
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Include private host paths in JSON")
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.timeout > 30:
        parser.error("timeout must be between 1 and 30 seconds")
    if not args.container or args.container.startswith("-"):
        parser.error("invalid container name")
    try:
        torrents, mounts = read_snapshot(args.container, args.timeout)
        result = assess(torrents, mounts)
    except (ValueError, TypeError, AttributeError, KeyError, OSError,
            subprocess.SubprocessError):
        # Do not echo subprocess output: tracker credentials may occur in API data.
        result = {"exit_code": UNAVAILABLE, "decision": "unavailable",
                  "reason": "Cannot verify qBittorrent state or host paths; defer Mover"}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result["exit_code"] == READY:
        print("No torrent blocker found; other Mover safeguards still apply.")
    elif result["exit_code"] == DEFER:
        print(f"Defer Mover: {result['blocking_torrents']} unfinished or busy torrent(s).")
    else:
        print(result["reason"])
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
