#!/usr/bin/env python3
"""VM-only connection to the existing Unraid native selective mover.

NO CLI, scheduler, PLG wiring or default enablement. The host must be an
explicitly marked disposable FejesMover-Test guest; the production FejesNAS
MUST NOT carry this marker. Never use this module to bypass an inspection
latch or for an unreviewed production migration.
"""
import fcntl
import os
from pathlib import Path

from active_seed_native import move_verified_unit
from active_seed_runner import run_unit, UnitInspectionRequired
from active_seed_policy import GLOBAL_GUARDS
from selective_preview import atomic_json, read_json

MARKER_CONTENT = "FEJESMOVER_DISPOSABLE_TEST_VM_V1"
LOCK_NAMES = ("fejes-mover-launch.lock", "fejes-integrity-cron.lock",
              "fejes-selective-inventory.lock", "fejes-mover-config.lock")


def verified_vm_marker(path):
    """The marker alone is not a production authorization token."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return path.read_text(encoding="utf-8").strip() == MARKER_CONTENT
    except OSError:
        return False


def run_vm_trial(*, marker, report_path, initial_evidence, fresh_evidence,
                 transport, inventory, days, verify_files, verify_peer,
                 sleep, native_module=None, completed_seed=False):
    """Wire the real execute_file protocol behind locks and a durable journal.

    Callbacks are provided by a disposable-guest harness:
      initial_evidence/fresh_evidence -> complete authenticated owner snapshot,
          full host inventory and guards; every guard must pass.
      verify_files/verify_peer -> hashes/path/completeness/actual peer upload.
    The caller MUST NOT use production paths as report_path. No call to this
    function is made from FejesMover's scheduled worker.
    """
    if not verified_vm_marker(marker):
        return {"state": "blocked", "reason": "disposable_vm_marker_missing"}
    path = Path(report_path)
    if (path.is_symlink() or path.parent.is_symlink()
            or not path.parent.is_dir() or path.name != "active-seed-vm-last.json"):
        return {"state": "blocked", "reason": "invalid_vm_report_path"}
    if any(not callable(x) for x in
           (initial_evidence, fresh_evidence, verify_files, verify_peer)):
        return {"state": "blocked", "reason": "unverified_callbacks"}
    # This import is intentionally lazy: it loads Unraid's native engine only
    # inside an explicitly selected VM trial, never during plugin import.
    if native_module is None:
        import selective_mover as native_module
    native = native_module
    locks = []
    own_pid = False
    report = {"version": 1, "state": "checking", "requires_inspection": True}
    last_durable = [None]
    coordination = [None]
    try:
        for name in LOCK_NAMES:
            handle = open("/var/run/" + name, "a")
            locks.append(handle)
            fcntl.flock(handle, (fcntl.LOCK_SH if name ==
                         "fejes-mover-config.lock" else fcntl.LOCK_EX) |
                        fcntl.LOCK_NB)
        # Prior reports are sticky, including unknown or interrupted runs.
        # A separate inspected recovery procedure is required before another
        # trial; do not overwrite previous evidence.
        if path.exists():
            return {"state": "blocked", "reason": "prior_vm_report_requires_review"}
        previous = read_json(native.LAST, {})
        if native.needs_inspection(previous):
            return {"state": "blocked", "reason": "production_inspection_latch"}
        if native.PID.exists():
            return {"state": "deferred", "reason": "mover_already_running"}
        fd = os.open(native.PID, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, str(os.getpid()).encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        own_pid = True

        def guard_snapshot(provider):
            values = provider()
            if not isinstance(values, dict):
                raise ValueError("host evidence invalid")
            measured = native.guards(owned=True)
            required_native = ("backup", "parity", "integrity", "mount",
                               "mover", "cooldown", "capacity",
                               "open_files", "namespace")
            if (not isinstance(measured, dict)
                    or any(measured.get(k) != "pass" for k in required_native)):
                raise ValueError("native guards unavailable")
            guards = values.get("guards")
            if not isinstance(guards, dict):
                raise ValueError("host guards unavailable")
            for guard in GLOBAL_GUARDS:
                if guards.get(guard) != "pass":
                    raise ValueError("host guard not passed")
            for guard, state in measured.items():
                if state != "pass":
                    raise ValueError("native guard not passed")
            # Prevent the injected provider from manufacturing a passing
            # native-guard result after Unraid reports a different state.
            for guard in measured:
                if guards.get(guard) != "pass":
                    raise ValueError("guard mismatch")
            return values

        snapshot = guard_snapshot(initial_evidence)
        expected = snapshot.get("expected_paths")
        if (not isinstance(expected, list) or any(type(p) is not str for p in expected)
                or len(expected) != len(set(expected)) or not isinstance(inventory, dict)
                or set(expected) != set(inventory)):
            return {"state": "deferred", "reason": "unit_inventory_unverified"}

        def persist(state):
            # Preserve full per-file ledger across transitions, including errors.
            # Keep the post-peer audit gate sticky until final success.
            state = dict(state)
            if coordination[0] is not None:
                state['coordination'] = dict(coordination[0])
                state['requires_inspection'] = True
            atomic_json(path, state)
            last_durable[0] = dict(state)

        def journal(value):
            coordination[0] = dict(value)
            persist(last_durable[0] or report)

        def move():
            return move_verified_unit(
                expected_paths=expected, inventory=inventory, days=days,
                execute_file=(native.execute_completed_seed_file if completed_seed
                              else native.execute_file), persist=persist,
                test_vm_authorized=True)

        def preflight():
            fresh = guard_snapshot(fresh_evidence)
            if fresh.get("expected_paths") != expected:
                raise ValueError("host inventory changed")
            return fresh

        persist(report)
        try:
            outcome = run_unit(
                snapshot=snapshot, transport=transport, preflight=preflight,
                move_unit=move, verify_files=verify_files,
                verify_peer=verify_peer, sleep=sleep,
                vm_test_authorized=True, journal=journal)
            report = dict(last_durable[0] or report)
            if outcome.get("state") == "completed":
                coordination[0] = None
                report.update(state="completed", requires_inspection=False,
                              peer_upload_verified=True)
            else:
                report.update(state="deferred", requires_inspection=True,
                              reason=outcome.get("reason", "unverified"))
            persist(report)
            return outcome
        except Exception:
            failure = dict(last_durable[0] or report)
            failure.update(state="inspection_required", requires_inspection=True)
            persist(failure)
            raise
    finally:
        if own_pid and native.PID.exists():
            try:
                if native.PID.read_text() == str(os.getpid()):
                    native.PID.unlink()
            except OSError:
                pass
        for handle in reversed(locks):
            handle.close()
