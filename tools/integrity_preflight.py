#!/usr/bin/env python3
"""Run an existing generated Bunker schedule with live torrent exclusions."""
import argparse
import pathlib
import re
import shlex
import subprocess
import sys

from torrent_preflight import assess, read_snapshot

TOKEN = "/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/bunker -Vqj "
MARKER = "# This is an auto-generated file, do not change manually!"
MEDIA_ROOT = re.compile(r"^/mnt/(?:user|user0|disk[0-9]+)/")


def folder_pattern(name):
    # Bunker interpolates -F entries into a sed ERE with / delimiters and comma IFS.
    # Accept only the plain basenames supported by this integration, not patterns.
    if not name or not re.fullmatch(r"[A-Za-z0-9._+ -]+", name):
        raise ValueError("Folder exclusion cannot safely be represented")
    return re.escape(name).replace(r"\ ", " ")


def config_exclusions(source):
    result = {}
    for key in ("exclude", "folders", "files"):
        values = re.findall(r'^' + key + r'="([^"\n]*)"\s*$', source, re.M)
        if len(values) != 1:
            raise ValueError("Missing or ambiguous exclusion configuration")
        result[key] = values[0]
    if result["files"]:
        raise ValueError("Custom file masks need separate integration review")
    return result


def prepare_script(source, config, protected_paths, is_dir):
    if MARKER not in source or not source.startswith("#!/bin/bash\n"):
        raise ValueError("Not the reviewed generated schedule format")
    count = source.count(TOKEN)
    if count < 1 or count > 64:
        raise ValueError("Cannot locate Bunker schedule invocations")
    # Accept only full-disk scheduled verify commands. Any changed format defers.
    for line in source.splitlines():
        if "bunker" in line:
            if (line.count(TOKEN) != 1 or not line.startswith("[[ ")
                    or not re.search(r" /mnt/disk[0-9]+ >/dev/null &$", line)
                    or re.search(r"(?:^|\s)-(?:E|F)(?:\s|$)", line)):
                raise ValueError("Unreviewed Bunker invocation format")
    settings = config_exclusions(config)
    folders = set(filter(None, settings["folders"].split(",")))
    for path in protected_paths:
        if not MEDIA_ROOT.match(path) or not is_dir(path):
            raise ValueError("Unfinished content is not a known array/user directory")
        folders.add(pathlib.PurePosixPath(path).name)
    args = []
    if folders:
        args += ["-F", ",".join(folder_pattern(f) for f in sorted(folders))]
    shares = list(filter(None, settings["exclude"].split(",")))
    if shares:
        args += ["-E", ",".join(folder_pattern(s) for s in shares)]
    if args:
        source = source.replace(TOKEN, TOKEN + shlex.join(args) + " ")
    return source, len(folders)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="binhex-qbittorrentvpn")
    parser.add_argument("--config", default="/boot/config/plugins/dynamix.file.integrity/dynamix.file.integrity.cfg")
    parser.add_argument("--script", default="/boot/config/plugins/dynamix.file.integrity/integrity-check.sh")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.container or args.container.startswith("-"):
        parser.error("invalid container name")
    try:
        torrents, mounts = read_snapshot(args.container, 5)
        decision = assess(torrents, mounts)
        script, count = prepare_script(
            pathlib.Path(args.script).read_text(), pathlib.Path(args.config).read_text(),
            decision["protected_paths"], lambda p: pathlib.Path(p).is_dir())
        subprocess.run(["bash", "-n"], input=script, text=True,
                       capture_output=True, check=True, timeout=5)
    except (ValueError, TypeError, AttributeError, KeyError, OSError, subprocess.SubprocessError):
        print("File Integrity deferred: torrent state, exclusions or schedule cannot be verified.")
        return 20
    print(f"File Integrity preflight: {count} folder exclusion(s).", flush=True)
    if args.check_only:
        print("Check only; no hashing or configuration change performed.")
        return 0
    # Original parity guard, disk rotation, nice/ionice and notifications are retained.
    # No /Items DELETE, torrent API writes, checksum updates or source-file edits.
    try:
        return subprocess.run(["bash"], input=script, text=True).returncode
    except OSError:
        print("File Integrity schedule could not be started.")
        return 20


if __name__ == "__main__":
    sys.exit(main())
