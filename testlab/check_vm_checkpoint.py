#!/usr/bin/env python3
"""Read-only FejesMover-Test acceptance checkpoint inspection.

This does not start Docker, torrents, Mover or a VM, and never rewrites a
result. Run inside the disposable guest only, not on the FejesNAS host.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

HOST = "FejesMover-Test"
BASE = Path("/mnt/disk1/fm-acceptance")
REPORT = BASE / "current.json"
EXPECTED_SERIALS = {"FMTESTPARITY24", "FMTESTDATA16", "FMTESTCACHE08"}
CONTAINERS = ("fm-qbit", "fm-peer")


def command(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=12)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    if os.uname().nodename != HOST:
        print("BLOCKED: this check is only allowed in FejesMover-Test", file=sys.stderr)
        return 2
    print("host: " + HOST)
    serials = set((command("lsblk", "-dn", "-o", "SERIAL") or "").splitlines())
    disks_ok = EXPECTED_SERIALS.issubset({x.strip() for x in serials})
    print("disposable_disks_verified: " + str(disks_ok).lower())
    if not disks_ok:
        print("BLOCKED: guest disk identity could not be verified", file=sys.stderr)
        return 2
    for mount in ("/mnt/cache", "/mnt/disk1", "/mnt/user"):
        print("mounted_" + mount.rsplit("/", 1)[-1] + ": " +
              str(os.path.ismount(mount)).lower())
    if REPORT.is_symlink() or BASE.is_symlink():
        print("BLOCKED: report path is a symlink", file=sys.stderr)
        return 2
    if REPORT.is_file():
        try:
            data = json.loads(REPORT.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("result not an object")
        except (OSError, ValueError) as exc:
            print("saved_result_error: " + type(exc).__name__)
        else:
            # Print selected non-secret fields only: never dump credentials or
            # arbitrary diagnostics stored in the checkpoint JSON.
            for key in ("state", "seed_verified", "peer_transfer_verified",
                        "moved_bytes", "seeder_uploaded_bytes",
                        "receiver_downloaded_bytes", "requires_inspection"):
                if key in data and type(data[key]) in (str, int, bool, float):
                    print("saved_" + key + ": " + str(data[key]))
            print("saved_result_present: true")
    else:
        print("saved_result_present: false")
    for name in CONTAINERS:
        raw = command("docker", "inspect", "--format",
                      "{{.State.Running}}|{{.HostConfig.NetworkMode}}", name)
        if raw is None:
            print(name + ": unavailable")
        else:
            print(name + ": " + raw.replace("\n", " ")[:120])
    print("read_only_check_complete: true")
    print("NOTE: this is a checkpoint check, not PR #48 live seed acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
