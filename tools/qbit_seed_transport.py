#!/usr/bin/env python3
"""Bounded qBittorrent API v2 transport for isolated seed coordination tests.

NEVER call this from production movement until the owner VM acceptance is done.
No shell, public HTTP, host credential handling or global torrent actions.
The container-local API must already be accessible and authenticated by the
existing Unraid/qBittorrent configuration. Failed requests are errors.
"""
import json
import re
import subprocess

HASH_RE = re.compile(r"^[a-fA-F0-9]{40}(?:[a-fA-F0-9]{24})?$")
CONTAINER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


class TorrentTransportError(RuntimeError):
    pass


class DockerQbitTransport:
    def __init__(self, container="binhex-qbittorrentvpn", timeout=5, runner=subprocess.run):
        if not isinstance(container, str) or not CONTAINER_RE.fullmatch(container):
            raise ValueError("invalid container name")
        if type(timeout) is not int or not 1 <= timeout <= 15:
            raise ValueError("invalid API timeout")
        self.container = container
        self.timeout = timeout
        self.runner = runner

    @staticmethod
    def _hash_args(hashes):
        if (not isinstance(hashes, list) or not hashes
                or len(hashes) != len(set(hashes))
                or any(type(h) is not str or not HASH_RE.fullmatch(h) for h in hashes)):
            raise ValueError("invalid torrent hash list")
        return "|".join(sorted(hashes))

    def _curl(self, route, hashes, mutation=False):
        selected = self._hash_args(hashes)
        if route not in ("info", "stop", "start"):
            raise ValueError("unsupported API route")
        # POST only to selected hashes, never all torrents (hashes=all).
        cmd = ["docker", "exec", self.container, "curl",
               "--fail", "--silent", "--show-error", "--noproxy", "*",
               "--connect-timeout", str(self.timeout),
               "--max-time", str(self.timeout),
               "--request", "POST" if mutation else "GET",
               "--data-urlencode", "hashes=" + selected,
               "http://127.0.0.1:8080/api/v2/torrents/" + route]
        try:
            proc = self.runner(cmd, capture_output=True, text=True,
                               timeout=self.timeout + 3, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise TorrentTransportError("qBittorrent API unavailable") from exc
        if proc.returncode != 0:
            raise TorrentTransportError("qBittorrent API returned failure")
        return proc.stdout

    def snapshot(self, hashes):
        raw = self._curl("info", hashes)
        try:
            result = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise TorrentTransportError("qBittorrent snapshot invalid") from exc
        if not isinstance(result, list):
            raise TorrentTransportError("qBittorrent snapshot invalid")
        # API-side filter must not allow missing or unrelated torrent data.
        wanted = set(hashes)
        if {r.get("hash") for r in result if isinstance(r, dict)} != wanted:
            raise TorrentTransportError("qBittorrent owners changed")
        return result

    def stop(self, hashes):
        self._curl("stop", hashes, mutation=True)

    def start(self, hashes):
        self._curl("start", hashes, mutation=True)
