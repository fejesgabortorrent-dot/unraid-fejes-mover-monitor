#!/usr/bin/env python3
"""Reviewed native-mover callback bridge for isolated VM acceptance only.

Connects active_seed_runner.move_unit to the *existing* selective_mover
execute_file signature through dependency injection. There is no executable
entry point and this is NOT wired to the PLG or production run(). The host
adapter MUST hold the same mover/integrity/configuration locks throughout
stop -> native move -> resume, and persist(report) MUST atomically fsync.
"""
import re

from active_seed_runner import UnitInspectionRequired

SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def move_verified_unit(*, expected_paths, inventory, days, execute_file,
                       persist, test_vm_authorized=False):
    """Run only an exact verified file unit with durable per-file intent/ledger.

    Caller must supply trusted full-unit membership and an already validated
    inventory. If any native intent is ambiguous, fail without reattempting.
    Returns a verification result for active_seed_runner.run_unit.
    """
    if test_vm_authorized is not True:
        return {"verified": False, "reason": "vm_test_not_authorized"}
    if (not isinstance(expected_paths, (list, tuple)) or not expected_paths
            or len(expected_paths) != len(set(expected_paths))
            or any(type(p) is not str or not p.startswith("/mnt/user/")
                   or "\n" in p or "\r" in p or "\x00" in p
                   or ".." in p.split("/") for p in expected_paths)
            or not isinstance(inventory, dict)
            or set(expected_paths) != set(inventory)
            or type(days) is not int or days not in (1, 7, 14, 30)):
        return {"verified": False, "reason": "unit_inventory_unverified"}
    if not callable(execute_file) or not callable(persist):
        return {"verified": False, "reason": "native_adapter_missing"}
    for path in expected_paths:
        item = inventory[path]
        if (not isinstance(item, dict)
                or not isinstance(item.get("signature"), list)
                or len(item["signature"]) != 5
                or any(type(n) is not int or n < 0 for n in item["signature"])
                or type(item.get("first_seen")) not in (int, float)
                or item["first_seen"] < 0):
            return {"verified": False, "reason": "invalid_inventory_signature"}
    state = {"version": 1, "state": "checking", "requires_inspection": False,
             "active_file_started": False, "verified_files": [],
             "scope_paths": list(expected_paths)}
    persist(state)
    for path in expected_paths:
        state.update(state="checking", active_file=path,
                     active_file_started=False,
                     requires_inspection=bool(state["verified_files"]))
        persist(state)
        intent = [False]
        def before_native(source_sha256):
            if type(source_sha256) is not str or not SHA256.fullmatch(source_sha256):
                raise UnitInspectionRequired("native checksum intent invalid")
            intent[0] = True
            state.update(state="native_intent", active_file_started=True,
                         requires_inspection=True, active_sha256=source_sha256)
            persist(state)  # MUST finish its durable write before native invocation.
        try:
            result = execute_file(path, inventory[path], days, before_native)
            if not isinstance(result, dict):
                raise UnitInspectionRequired("native result invalid")
            # Persist admission/skip evidence before raising on a partial unit.
            # Never include arbitrary transport output or credential-bearing text.
            state['native_outcome'] = {key: result[key] for key in
                ('state', 'reason', 'admission_reason') if isinstance(result.get(key), str)}
            if result.get("state") != "moved" or intent != [True]:
                persist(state)
                if intent[0]:
                    raise UnitInspectionRequired("native outcome ambiguous")
                if state["verified_files"]:
                    raise UnitInspectionRequired("unit partially moved")
                state.update(state="deferred", requires_inspection=False,
                             active_file_started=False)
                persist(state)
                return {"verified": False, "reason": "pre_native_skip"}
            if (type(result.get("bytes")) is not int
                    or result["bytes"] != inventory[path]["signature"][2]
                    or not isinstance(result.get("sha256"), str)
                    or result["sha256"].lower() != state["active_sha256"].lower()
                    or not isinstance(result.get("destination"), str)
                    or not result["destination"].startswith("/mnt/disk")
                    or result["destination"] in
                    {item["destination"] for item in state["verified_files"]}):
                raise UnitInspectionRequired("native destination evidence invalid")
            state["verified_files"].append(
                {"source": path, "bytes": result["bytes"],
                 "sha256": result["sha256"], "destination": result["destination"]})
            # Keep native evidence latched until the host verifies actual
            # post-resume peer continuity, including after process loss.
            state.update(state="checking", active_file_started=False,
                         requires_inspection=True)
            state.pop("active_sha256", None)
            state.pop("active_file", None)
            persist(state)
        except Exception as error:
            state.update(state="inspection_required",
                         requires_inspection=True, failure_type=type(error).__name__)
            persist(state)
            raise UnitInspectionRequired("verified native unit incomplete") from error
    state.update(state="native_verified", active_file_started=False,
                 requires_inspection=True)
    persist(state)
    return {"verified": True, "files": len(state["verified_files"]),
            "bytes": sum(row["bytes"] for row in state["verified_files"])}
