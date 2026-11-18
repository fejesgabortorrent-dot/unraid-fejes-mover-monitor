#!/usr/bin/env python3
"""Opt-in per-torrent qBittorrent coordination; never moves media.

This module is NOT called by the production mover. The caller must supply a
reviewed transport and perform file/namespace/peer checks separately.
"""
import time

STOPPED_STATES = frozenset({"stoppedUP", "pausedUP"})
COMPLETE_SEED_STATES = frozenset({"uploading", "stalledUP", "queuedUP", "forcedUP"})
WAIT_ATTEMPTS = 10


class CoordinationError(RuntimeError):
    pass


class RestorationUnverified(CoordinationError):
    """A failed stop may have changed a torrent and restoration is unproven."""


def _hashes(records):
    if not isinstance(records, list):
        raise CoordinationError("invalid torrent snapshot")
    hashes = [r.get("hash") for r in records if isinstance(r, dict)]
    if len(hashes) != len(records) or len(set(hashes)) != len(hashes):
        raise CoordinationError("torrent ownership changed")
    return sorted(hashes)


def _complete(record):
    return (isinstance(record, dict) and type(record.get("progress")) in (int, float)
            and record["progress"] == 1 and record.get("dlspeed") == 0
            and record.get("state") in COMPLETE_SEED_STATES | STOPPED_STATES)


class SeedCoordinator:
    """Adapter contract: snapshot(hashes), stop(hashes), start(hashes).

    Caller provides explicit timeouts to transport methods. stop/start are
    torrent-specific, never global; no filesystem movement is done here.
    """

    def __init__(self, transport, sleep=time.sleep, journal=None):
        self.transport = transport
        self.sleep = sleep
        self.journal = journal or (lambda state: None)

    def _verify(self, hashes, states):
        records = self.transport.snapshot(hashes)
        if _hashes(records) != sorted(hashes):
            raise CoordinationError("owners changed")
        if not all(_complete(r) and r["state"] in states for r in records):
            raise CoordinationError("torrent state not verified")
        return records

    def prepare(self, hashes):
        """Stop all verified complete owners and confirm quiescence.

        If stop fails, caller must not move any files. A restoration attempt
        targets only torrents that were observed running at preflight.
        """
        if not hashes or len(set(hashes)) != len(hashes):
            raise CoordinationError("invalid owner hashes")
        current = self._verify(hashes, COMPLETE_SEED_STATES | STOPPED_STATES)
        originally_running = sorted(r["hash"] for r in current
                                    if r["state"] in COMPLETE_SEED_STATES)
        token = {"owners": sorted(hashes), "resume": originally_running,
                 "quiesced": False}
        # Durable intent precedes even the first stop request. Process loss
        # must leave enough information for manual scoped restoration.
        self.journal(dict(token, phase="before_stop"))
        try:
            if originally_running:
                self.transport.stop(originally_running)
            for _ in range(WAIT_ATTEMPTS):
                try:
                    self._verify(hashes, STOPPED_STATES)
                    token["quiesced"] = True
                    self.journal(dict(token, phase="stopped"))
                    return token
                except CoordinationError:
                    self.sleep(1)
            raise CoordinationError("stop confirmation timeout")
        except Exception as exc:
            # A failed POST can still have stopped some torrents. Never silently
            # downgrade an unverified restoration to a routine deferral.
            if originally_running:
                try:
                    self.transport.start(originally_running)
                    self._verify(hashes, COMPLETE_SEED_STATES | STOPPED_STATES)
                    resumed = self.transport.snapshot(hashes)
                    if not all(r["state"] in COMPLETE_SEED_STATES
                               for r in resumed if r["hash"] in originally_running):
                        raise RestorationUnverified("owners remained stopped")
                    self.journal(dict(token, phase="stop_failed_restored"))
                except Exception as restore_error:
                    raise RestorationUnverified("stop failed and restore unverified") from restore_error
            raise CoordinationError("quiescence failed; movement forbidden") from exc

    def restore(self, token):
        """Best-effort state restoration, including after a failed file operation.

        The client must verify restored upload/peer continuity independently.
        """
        if not isinstance(token, dict) or token.get("quiesced") is not True:
            raise CoordinationError("invalid restoration token")
        owners, resume = token.get("owners"), token.get("resume")
        if (not isinstance(owners, list) or not isinstance(resume, list)
                or len(set(owners)) != len(owners)
                or any(h not in owners for h in resume)):
            raise CoordinationError("restoration owner mismatch")
        self._verify(owners, STOPPED_STATES)
        self.journal(dict(token, phase="before_restore"))
        if resume:
            self.transport.start(resume)
        for _ in range(WAIT_ATTEMPTS):
            records = self.transport.snapshot(owners)
            if (_hashes(records) == sorted(owners)
                    and all(_complete(r) for r in records)
                    and all(r["state"] in COMPLETE_SEED_STATES
                            for r in records if r["hash"] in resume)):
                self.journal(dict(token, phase="restored"))
                return {"restored": True, "peer_upload_verified": False}
            self.sleep(1)
        raise CoordinationError("resume confirmation timeout")
