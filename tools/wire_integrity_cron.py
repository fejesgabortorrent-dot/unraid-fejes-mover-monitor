#!/usr/bin/env python3
"""Route the existing File Integrity cron job through its reviewed preflight."""
import datetime
import fcntl
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path("/boot/config/plugins/dynamix.file.integrity")
GUARD = pathlib.Path("/boot/config/plugins/fejes.mover.monitor/tools/integrity_preflight.py")
ORIGINAL = "bash /boot/config/plugins/dynamix.file.integrity/integrity-check.sh"
REPLACEMENT = "python3 " + str(GUARD)


def rewrite_cron(source):
    lines = [line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) != 1:
        raise ValueError("Expected exactly one existing scheduled job")
    line = lines[0]
    fields = line.split(None, 5)
    if len(fields) != 6:
        raise ValueError("Unrecognized cron format")
    command = fields[5]
    if command == REPLACEMENT + " &> /dev/null":
        return source
    if command != ORIGINAL + " &> /dev/null":
        raise ValueError("Unrecognized File Integrity command")
    return source.replace(line, line.replace(ORIGINAL, REPLACEMENT, 1), 1)


def atomic_write(path, text, mode):
    fd, temp = tempfile.mkstemp(prefix=".integrity-cron-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    cron = ROOT / "integrity-check.cron"
    with open("/var/run/fejes-integrity-cron.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = cron.read_text()
        changed = rewrite_cron(source)
        if not GUARD.is_file() or not GUARD.with_name("torrent_preflight.py").is_file():
            raise ValueError("Preflight tools are not installed")
        subprocess.run(["python3", str(GUARD), "--check-only"], check=True)
        if source == changed:
            print("Existing cron job already uses the preflight; no change.")
            return 0
        # Do not use .cron suffix for backups: Unraid must not schedule backups.
        backup = ROOT / ("integrity-cron-before-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
        shutil.copy2(cron, backup)
        if cron.read_text() != source:
            raise ValueError("Cron configuration changed during preparation")
        mode = cron.stat().st_mode & 0o777
        atomic_write(cron, changed, mode)
        try:
            subprocess.run(["/usr/local/sbin/update_cron"], check=True)
        except (OSError, subprocess.SubprocessError):
            atomic_write(cron, source, mode)
            subprocess.run(["/usr/local/sbin/update_cron"], check=True)
            raise
        print("Existing File Integrity schedule now uses the preflight.")
        print("Backup:", backup)
        print("No hashing started. A later plugin settings save can regenerate this cron; recheck/reapply then.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("Cron integration did not complete:", type(exc).__name__)
        sys.exit(20)
