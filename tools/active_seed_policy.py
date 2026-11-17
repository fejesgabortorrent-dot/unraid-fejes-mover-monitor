#!/usr/bin/env python3
"""Fail-closed, read-only contract for moving completed actively seeding torrents.

This is an isolated development policy. It never invokes qBittorrent, Unraid's
mover, or the filesystem. A host adapter and VM peer-transfer acceptance are
required before connecting it to production execution.
"""
import math

SEED_STATES = frozenset({"uploading", "stalledUP", "queuedUP", "stoppedUP", "pausedUP"})
BLOCKED_STATES = frozenset({"checkingUP", "checkingDL", "moving", "downloading",
                            "stalledDL", "queuedDL", "forcedDL", "error",
                            "missingFiles", "allocating", "metaDL"})
GLOBAL_GUARDS = ("backup", "parity", "integrity", "mount", "mover", "cooldown",
                 "capacity", "open_files", "namespace", "inspection")


def _valid_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def classify_completed_seed(torrent):
    """Classify one fresh qBittorrent record without authorizing movement.

    'active' is permitted for a *coordination plan*, not for direct native move.
    The state must be rechecked at the operation boundary by a host adapter.
    """
    if not isinstance(torrent, dict):
        return "unknown"
    if torrent.get("state") not in SEED_STATES:
        return "blocked" if torrent.get("state") in BLOCKED_STATES else "unknown"
    progress = torrent.get("progress")
    if type(progress) not in (int, float) or not math.isfinite(progress) or progress != 1:
        return "blocked"
    if not all(_valid_number(torrent.get(key)) for key in ("upspeed", "dlspeed", "ratio")):
        return "unknown"
    if torrent["dlspeed"] != 0:
        return "blocked"
    if not isinstance(torrent.get("hash"), str) or len(torrent["hash"]) not in (40, 64):
        return "unknown"
    if any(c not in "0123456789abcdefABCDEF" for c in torrent["hash"]):
        return "unknown"
    if not isinstance(torrent.get("content_path"), str) or not torrent["content_path"].startswith("/"):
        return "unknown"
    if torrent["state"] in {"stoppedUP", "pausedUP"} and torrent["upspeed"] != 0:
        return "blocked"
    if torrent["state"] == "uploading" or torrent["upspeed"] > 0:
        return "active_coordination_required"
    return "idle_coordination_required"


def assess_unit(torrents, guards, *, owner_hashes, expected_paths, verified_paths,
                stable, no_writers, namespace_unchanged):
    """Plan a whole-unit transaction using independently collected evidence.

    owner_hashes are *all* verified qBittorrent owners, not a filtered subset.
    expected_paths must equal the full set of verified unit members; a partial
    unit, unknown overlapping owner, or stale mapping always blocks.
    This function never approves execution while the torrent is uploading.
    """
    result = {"read_only": True, "execute_allowed": False, "decision": "blocked",
              "reason": "unverifiable", "owner_hashes": []}
    if not isinstance(guards, dict) or any(guards.get(g) != "pass" for g in GLOBAL_GUARDS):
        result["reason"] = "guard_not_passed"
        return result
    if any(value is not True for value in (stable, no_writers, namespace_unchanged)):
        result["reason"] = "file_or_namespace_unverified"
        return result
    if not isinstance(expected_paths, (list, tuple)) or not expected_paths:
        result["reason"] = "unit_unverified"
        return result
    if (any(type(p) is not str or not p.startswith("/") or "\\n" in p or "\\r" in p
            for p in expected_paths)
            or len(expected_paths) != len(set(expected_paths))
            or not isinstance(verified_paths, (list, tuple))
            or set(expected_paths) != set(verified_paths)):
        result["reason"] = "partial_or_ambiguous_unit"
        return result
    if not isinstance(torrents, list) or not torrents or not isinstance(owner_hashes, (list, tuple)):
        result["reason"] = "owners_unverified"
        return result
    hashes = [t.get("hash") for t in torrents if isinstance(t, dict)]
    if (len(hashes) != len(torrents) or len(hashes) != len(set(hashes))
            or len(owner_hashes) != len(set(owner_hashes))
            or set(owner_hashes) != set(hashes)):
        result["reason"] = "owners_unverified"
        return result
    classes = [classify_completed_seed(t) for t in torrents]
    if any(c not in {"active_coordination_required", "idle_coordination_required"} for c in classes):
        result["reason"] = "torrent_not_eligible"
        return result
    result.update(decision="coordination_required",
                  reason="pause_recheck_move_resume_required",
                  owner_hashes=sorted(hashes),
                  actively_uploading=any(c == "active_coordination_required" for c in classes))
    return result


def validate_transition(before, after, *, files_verified, logical_paths_unchanged,
                        complete, resumed, peer_upload_verified):
    """Post-operation verification for a future transaction coordinator.

    A completed copy/hash check alone never proves continued real peer upload.
    Preserve a failure/inspection state until all invariants are evidenced.
    """
    if not isinstance(before, dict) or before.get("decision") != "coordination_required":
        return {"verified": False, "reason": "missing_preflight"}
    if not isinstance(after, dict) or after.get("owner_hashes") != before.get("owner_hashes"):
        return {"verified": False, "reason": "owners_changed"}
    flags = (files_verified, logical_paths_unchanged, complete, resumed, peer_upload_verified)
    if any(flag is not True for flag in flags):
        return {"verified": False, "reason": "continuity_unverified"}
    return {"verified": True, "reason": "peer_continuity_verified"}
