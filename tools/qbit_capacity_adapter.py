#!/usr/bin/env python3
"""Small qBittorrent pause/resume adapter with injected transport.

The adapter never stores credentials and never logs response bodies. The
production caller must provide a short-lived authenticated cookie/session and
must keep the adapter behind the mover coordination lock.
"""
import re
import urllib.parse
import urllib.request


class QbitCapacityAdapter:
    def __init__(self, base_url, session_cookie, transport=None):
        if not isinstance(base_url, str) or not re.match(r"^https?://[^/]+/?$", base_url):
            raise ValueError("invalid qBittorrent base URL")
        if not isinstance(session_cookie, str) or not session_cookie.strip():
            raise ValueError("authenticated session cookie required")
        self.base_url = base_url.rstrip("/")
        self._cookie = session_cookie
        self._transport = transport or self._default_transport

    def _default_transport(self, url, data):
        request = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Cookie": self._cookie,
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("qBittorrent API rejected request")

    def _change(self, endpoint, torrent_hash):
        if not isinstance(torrent_hash, str) or not re.fullmatch(r"[A-Za-z0-9]{8,128}", torrent_hash):
            raise ValueError("invalid torrent hash")
        data = urllib.parse.urlencode({"hashes": torrent_hash}).encode("ascii")
        self._transport(self.base_url + endpoint, data)

    def pause(self, torrent_hash):
        self._change("/api/v2/torrents/pause", torrent_hash)

    def resume(self, torrent_hash):
        self._change("/api/v2/torrents/resume", torrent_hash)
