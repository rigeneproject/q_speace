"""T-HOME-02 — PhysioDriveAdapter: PSN signals as drive modulation sources.

Routes validated PSN physiological streams into
``GlobalHomeostaticDrive.update_drive`` as *secondary* inputs with limited
weight. Design invariants (T-HOME-02 spec §4):

- the adapter only READS from the PSN and WRITES to ``update_drive``; there
  is no direct signal→actuator path;
- signals not registered in the PSN ontologia are rejected: no unvalidated
  input reaches regulation;
- stale/missing data uses the configured hold policy — no errors, no
  discontinuous jumps;
- with no PSN sources the drive behaviour is identical to pre-T-HOME-02.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PhysioMapping:
    """A PSN signal → drive mapping with bounded influence."""

    signal_id: str
    drive_name: str
    transform: str = "identity"  # identity | complement
    weight: float = 0.2  # blend weight toward the PSN-derived value
    max_age_ticks: int = 10
    stale_policy: str = "hold"  # hold | decay_to_setpoint


# Default mappings: secondary, limited-weight inputs that preserve the
# orchestrator's own mean_energy mapping untouched. No default mapping
# targets 'survival' (that source stays mean_energy unless explicitly
# decoupled via T-HOME-02.4 configuration).
DEFAULT_PHYSIO_MAPPINGS: list[PhysioMapping] = [
    PhysioMapping(signal_id="energy", drive_name="efficiency", transform="identity", weight=0.2),
    PhysioMapping(signal_id="stress", drive_name="exploration", transform="identity", weight=0.2),
]


class PhysioDriveAdapter:
    """Adapter between a PhysiologicalSignalBus and GlobalHomeostaticDrive."""

    def __init__(
        self,
        psn: Any,
        drive: Any,
        mappings: list[PhysioMapping] | None = None,
    ) -> None:
        self._psn = psn
        self._drive = drive
        self._mappings = list(mappings or DEFAULT_PHYSIO_MAPPINGS)
        # signal_id → (last value, tick when seen)
        self._last_seen: dict[str, tuple] = {}
        # signal_id → last blended value applied to the drive (hold idempotence)
        self._last_applied: dict[str, float] = {}
        self.last_sync: dict[str, Any] = {}

    # ------------------------------------------------------------------ #

    def _registered(self, signal_id: str) -> bool:
        physiome = getattr(self._psn, "physiome", None)
        if physiome is None:
            return False
        try:
            return bool(physiome.is_signal_registered(signal_id))
        except Exception:
            return False

    def _read_stream(self, signal_id: str) -> float | None:
        try:
            return self._psn.read_stream(signal_id)
        except Exception:
            return None

    def _drive_current(self, name: str) -> float:
        getter = getattr(self._drive, "get_drive_value", None)
        if getter is not None:
            return float(getter(name))
        # Fallback for drives without the accessor (tests with stubs).
        drives = getattr(self._drive, "_drives", {})
        return float(drives[name].current_value)

    def _drive_setpoint(self, name: str) -> float | None:
        getter = getattr(self._drive, "get_drive_setpoint", None)
        if getter is not None:
            try:
                return float(getter(name))
            except Exception:
                return None
        drives = getattr(self._drive, "_drives", None)
        if drives and name in drives:
            return float(drives[name].setpoint)
        return None

    def _drive_registered(self, name: str) -> bool:
        try:
            return name in self._drive.list_drives()
        except Exception:
            return False

    # ------------------------------------------------------------------ #

    def sync(self, current_tick: int) -> dict[str, Any]:
        """Read PSN streams and fold them into the drive (weighted blend).

        Returns a metrics report: applied / stale / rejected entries.
        """
        report: dict[str, Any] = {
            "tick": int(current_tick),
            "applied": {},
            "stale": [],
            "rejected": [],
        }

        for mapping in self._mappings:
            if not self._registered(mapping.signal_id):
                report["rejected"].append(
                    {"signal": mapping.signal_id, "reason": "unregistered_in_physiome"}
                )
                continue
            if not self._drive_registered(mapping.drive_name):
                report["rejected"].append(
                    {"signal": mapping.signal_id, "reason": f"drive_not_registered:{mapping.drive_name}"}
                )
                continue

            value = self._read_stream(mapping.signal_id)
            if value is not None:
                self._last_seen[mapping.signal_id] = (float(value), int(current_tick))
            else:
                if mapping.signal_id not in self._last_seen:
                    # Never seen: do not touch the drive at all.
                    report["stale"].append(
                        {"signal": mapping.signal_id, "policy": "no_data_ever"}
                    )
                    continue
                last_value, last_tick = self._last_seen[mapping.signal_id]
                age = int(current_tick) - last_tick
                if age <= mapping.max_age_ticks:
                    # Idempotent hold: re-apply the last blended value so the
                    # drive does not drift while the signal is stale.
                    if mapping.signal_id in self._last_applied:
                        self._drive.update_drive(
                            mapping.drive_name, self._last_applied[mapping.signal_id]
                        )
                    report["stale"].append(
                        {"signal": mapping.signal_id, "age": age, "policy": "hold"}
                    )
                    continue
                elif mapping.stale_policy == "decay_to_setpoint":
                    setpoint = self._drive_setpoint(mapping.drive_name)
                    if setpoint is not None:
                        blended = (1.0 - mapping.weight) * self._drive_current(
                            mapping.drive_name
                        ) + mapping.weight * float(setpoint)
                        self._drive.update_drive(mapping.drive_name, blended)
                        report["stale"].append(
                            {
                                "signal": mapping.signal_id,
                                "age": age,
                                "policy": "decay_to_setpoint",
                            }
                        )
                        continue
                    # No setpoint knowledge: fall back to idempotent hold.
                    if mapping.signal_id in self._last_applied:
                        self._drive.update_drive(
                            mapping.drive_name, self._last_applied[mapping.signal_id]
                        )
                    report["stale"].append(
                        {"signal": mapping.signal_id, "age": age, "policy": "hold"}
                    )
                    continue
                else:
                    # Documented hold policy (default): idempotent re-apply.
                    if mapping.signal_id in self._last_applied:
                        self._drive.update_drive(
                            mapping.drive_name, self._last_applied[mapping.signal_id]
                        )
                    report["stale"].append(
                        {"signal": mapping.signal_id, "age": age, "policy": "hold"}
                    )
                    continue

            transformed = (
                1.0 - float(value) if mapping.transform == "complement" else float(value)
            )
            # Clamp the contribution: a single out-of-scale signal must not
            # saturate the objective function.
            transformed = max(0.0, min(1.0, transformed))
            current = self._drive_current(mapping.drive_name)
            blended = (1.0 - mapping.weight) * current + mapping.weight * transformed
            self._drive.update_drive(mapping.drive_name, blended)
            self._last_applied[mapping.signal_id] = blended
            report["applied"][mapping.drive_name] = {
                "signal": mapping.signal_id,
                "value": blended,
                "weight": mapping.weight,
            }

        self.last_sync = report
        return report
