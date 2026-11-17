#!/usr/bin/env python3
"""Isolated, opt-in integration of seed policy, coordinator and move adapter.

Not wired into selective_mover.run() or the PLG. For disposable VM acceptance
only until native movement, crash recovery, real peer upload and pause/restore
have been verified. A caller supplies both a trusted inventory and a reviewed
native unit move callback; this module does not delete or move files itself.
"""
from active_seed_policy import assess_unit, validate_transition
from seed_coordination import SeedCoordinator, CoordinationError, RestorationUnverified


class UnitInspectionRequired(RuntimeError):
    """Potentially moved bytes or uncertain restore; never retry automatically."""


def run_unit(*, snapshot, transport, preflight, move_unit, verify_files,
             verify_peer, sleep, vm_test_authorized=False, journal=None):
    """Coordinate one complete torrent-owned unit.

    snapshot is a fresh evidence bundle from a trusted adapter. After stop,
    preflight must repeat all host guards and ownership/namespace/write checks.
    move_unit may invoke only the reviewed, exact-scope native mover and must
    write its own durable before-native intent and per-file verification ledger.
    After either move success or failure, previously running torrents are
    restored. Final success also requires a real peer-upload confirmation.
    """
    if vm_test_authorized is not True:
        return {"state": "blocked", "reason": "vm_test_not_authorized"}
    try:
        initial = assess_unit(**snapshot)
    except (ValueError, TypeError, KeyError):
        return {"state": "deferred", "reason": "invalid_snapshot"}
    if initial["decision"] != "coordination_required":
        return {"state": "deferred", "reason": initial["reason"]}
    hashes = initial["owner_hashes"]
    coordinator = SeedCoordinator(transport, sleep=sleep, journal=journal)
    token = None
    native_started = False
    native_result = None
    operation_error = None
    try:
        token = coordinator.prepare(hashes)
        # Re-read all guards under the same mover and integrity locks before
        # starting ANY native move. Never trust a pre-stop inventory.
        fresh = preflight()
        valid = assess_unit(**fresh)
        if (valid["decision"] != "coordination_required"
                or valid["owner_hashes"] != hashes
                or fresh["expected_paths"] != snapshot["expected_paths"]):
            return {"state": "deferred", "reason": "conditions_changed"}
        native_started = True
        native_result = move_unit()
        if not isinstance(native_result, dict) or native_result.get("verified") is not True:
            raise UnitInspectionRequired("native unit not fully verified")
    except Exception as exc:
        operation_error = exc
    finally:
        if token is not None:
            try:
                coordinator.restore(token)
            except Exception as exc:
                # A real host adapter must retain the durable operation ledger
                # and inspection latch; no automated retry after uncertain restore.
                raise UnitInspectionRequired("torrent restoration unverified") from exc
    if operation_error is not None:
        if isinstance(operation_error, RestorationUnverified):
            raise UnitInspectionRequired("quiescence restoration unverified") from operation_error
        if native_started:
            raise UnitInspectionRequired("native outcome requires inspection") from operation_error
        return {"state": "deferred", "reason": "pre_native_coordination_failed"}
    if token is None:
        return {"state": "deferred", "reason": "stop_unverified"}
    try:
        evidence = verify_files()
        peer = verify_peer(hashes)
        result = validate_transition(
            initial, {"owner_hashes": hashes},
            files_verified=evidence.get("hashes_match"),
            logical_paths_unchanged=evidence.get("logical_paths_unchanged"),
            complete=evidence.get("all_complete"),
            resumed=evidence.get("resumed"),
            peer_upload_verified=peer is True)
    except Exception as exc:
        raise UnitInspectionRequired("post-move verification unavailable") from exc
    if not result["verified"]:
        raise UnitInspectionRequired("peer or file continuity not verified")
    return {"state": "completed", "peer_upload_verified": True,
            "native_verified": True}
