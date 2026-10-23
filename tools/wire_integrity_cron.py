#!/usr/bin/env python3
"""Route the existing File Integrity cron job through its reviewed preflight."""
import argparse
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
LOCK = '/var/run/fejes-integrity-cron.lock'


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


def reload_cron():
    # Unraid versions may ship this script without a valid #! interpreter line.
    subprocess.run(["bash", "/usr/local/sbin/update_cron"], check=True)


def main(remove=False):
    cron = ROOT / "integrity-check.cron"
    if remove and not cron.exists():
        return 0
    with open(LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = cron.read_text()
        if remove:
            if REPLACEMENT not in source:
                return 0
            if rewrite_cron(source) != source:
                raise ValueError("Unrecognized integrated cron")
            changed = source.replace(REPLACEMENT, ORIGINAL)
        else:
            changed = rewrite_cron(source)
        if not remove and (not GUARD.is_file() or not GUARD.with_name("torrent_preflight.py").is_file()):
            raise ValueError("Preflight tools are not installed")
        if not remove:
            subprocess.run(["python3", str(GUARD), "--check-only"], check=True)
        if source == changed:
            reload_cron()
            print("Existing cron job already uses the preflight; system cron reloaded.")
            return 0
        # Do not use .cron suffix for backups: Unraid must not schedule backups.
        backup = ROOT / ("integrity-cron-before-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
        shutil.copy2(cron, backup)
        if cron.read_text() != source:
            raise ValueError("Cron configuration changed during preparation")
        mode = cron.stat().st_mode & 0o777
        atomic_write(cron, changed, mode)
        try:
            reload_cron()
        except (OSError, subprocess.SubprocessError):
            atomic_write(cron, source, mode)
            reload_cron()
            raise
        print("Original File Integrity schedule restored." if remove else
              "Existing File Integrity schedule now uses the preflight.")
        print("Backup:", backup)
        print("No hashing started. A later plugin settings save can regenerate this cron; recheck/reapply then.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remove', action='store_true', help='Restore original schedule without API checks')
    args = parser.parse_args()
    try:
        sys.exit(main(remove=args.remove))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("Cron integration did not complete:", type(exc).__name__,
              "errno=" + str(getattr(exc, "errno", None)))
        sys.exit(20)
