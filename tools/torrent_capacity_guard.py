#!/usr/bin/env python3
"""Fail-closed torrent pause/resume policy for cache pressure.

This module deliberately contains no credentials, shell calls, or live API
mutations.  The caller supplies a qBittorrent adapter and persists the returned
state.  Only torrents paused by this policy may be resumed later.
"""
from dataclasses import dataclass


DOWNLOAD_STATES = {
    "allocating", "checkingDL", "downloading", "stalledDL", "queuedDL",
    "forcedDL", "stoppedDL", "pausedDL", "metaDL", "forcedMetaDL",
}
KNOWN_STATES = DOWNLOAD_STATES | {
    "uploading", "stalledUP", "queuedUP", "forcedUP", "stoppedUP", "pausedUP",
}


@dataclass(frozen=True)
class CapacityDecision:
    action: str
    warning: str
    hashes: tuple
    reason: str


def _hash(item):
    value = item.get("hash")
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("invalid torrent hash")
    return value


def plan(torrents, free_bytes, pause_below_bytes, resume_at_bytes, owned_paused=()):
    """Return an idempotent pause/resume plan without changing qBittorrent."""
    if not isinstance(torrents, list) or not isinstance(free_bytes, int):
        raise ValueError("invalid capacity snapshot")
    if not isinstance(pause_below_bytes, int) or not isinstance(resume_at_bytes, int):
        raise ValueError("invalid thresholds")
    if pause_below_bytes < 0 or resume_at_bytes < pause_below_bytes:
        raise ValueError("invalid threshold ordering")
    owned = tuple(dict.fromkeys(owned_paused))
    if any(not isinstance(value, str) for value in owned):
        raise ValueError("invalid owned pause state")
    downloading = []
    for item in torrents:
        if not isinstance(item, dict):
            raise ValueError("invalid torrent snapshot")
        state = item.get("state")
        if state not in KNOWN_STATES:
            raise ValueError("unknown torrent state")
        if state in DOWNLOAD_STATES:
            downloading.append(_hash(item))
    if free_bytes < pause_below_bytes:
        return CapacityDecision(
            "pause", "Alacsony szabad kapacitás – torrentletöltések szüneteltetve.",
            tuple(downloading), "capacity_below_pause_threshold")
    if free_bytes >= resume_at_bytes:
        return CapacityDecision(
            "resume", "A felszabadult hely elérte a biztonságos szintet – korábban automatikusan szüneteltetett letöltések folytatása.",
            owned, "capacity_recovered")
    return CapacityDecision("none", "", (), "capacity_hysteresis")


def apply(adapter, decision):
    """Apply one decision through an injected adapter and return successful IDs."""
    if decision.action == "none":
        return ()
    if not hasattr(adapter, "pause") or not hasattr(adapter, "resume"):
        raise ValueError("adapter must expose pause/resume")
    changed = []
    operation = adapter.pause if decision.action == "pause" else adapter.resume
    for torrent_hash in decision.hashes:
        operation(torrent_hash)
        changed.append(torrent_hash)
    return tuple(changed)
