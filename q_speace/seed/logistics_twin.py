"""T221-28: Simulation-only digital twin sandbox of the T221 §4 internal logistics habitat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .constitution import ConstitutionalFault
from .contact import ContactPlan, ContactSpec
from .state_machine import SeedLifecycle

DeviceStatus = Literal["online", "faulted", "recovered"]


@dataclass
class SimulatedDevice:
    """One simulated IoT sensor or robot in the logistics digital twin (no physical I/O)."""

    device_id: str
    kind: Literal["sensor", "robot"]
    zone: str
    status: DeviceStatus = "online"
    tasks_completed: int = 0


@dataclass(frozen=True)
class LogisticsScenarioResult:
    """Outcome of exercising a logistics twin scenario."""

    scenario: str
    tasks_completed: int
    faults_injected: int
    faults_recovered: int
    devices_integrated: int
    prior_functions_preserved: bool
    passed: bool


@dataclass
class LogisticsDigitalTwin:
    """Sandboxed digital twin of internal industrial logistics (T221 §4 — simulation only)."""

    sandboxed: bool = True
    devices: dict[str, SimulatedDevice] = field(default_factory=dict)
    bins: dict[str, int] = field(default_factory=lambda: {"zone_a": 10, "zone_b": 10})
    _faults_injected: int = 0
    _faults_recovered: int = 0
    _tasks_completed: int = 0

    def __post_init__(self) -> None:
        if not self.sandboxed:
            raise ConstitutionalFault("LogisticsDigitalTwin must remain sandboxed=True (T221-28)")
        if not self.devices:
            for i in range(4):
                self.devices[f"sensor-{i}"] = SimulatedDevice(
                    device_id=f"sensor-{i}", kind="sensor", zone="zone_a" if i < 2 else "zone_b"
                )
            self.devices["robot-0"] = SimulatedDevice(
                device_id="robot-0", kind="robot", zone="zone_a"
            )
            self.devices["robot-1"] = SimulatedDevice(
                device_id="robot-1", kind="robot", zone="zone_b"
            )

    def move_bin(self, *, src_zone: str, dst_zone: str, quantity: int = 1) -> bool:
        """Coordinate an available online robot and sensors to move bins in simulation."""
        if quantity < 1 or self.bins.get(src_zone, 0) < quantity:
            return False
        robots = [d for d in self.devices.values() if d.kind == "robot" and d.status != "faulted"]
        if not robots:
            return False
        robot = sorted(robots, key=lambda r: r.tasks_completed)[0]
        self.bins[src_zone] -= quantity
        self.bins[dst_zone] = self.bins.get(dst_zone, 0) + quantity
        robot.tasks_completed += 1
        self._tasks_completed += 1
        return True

    def inject_fault(self, device_id: str) -> None:
        if device_id not in self.devices:
            raise KeyError(f"unknown device_id: {device_id!r}")
        self.devices[device_id].status = "faulted"
        self._faults_injected += 1

    def recover_fault(self, device_id: str) -> bool:
        if device_id not in self.devices:
            raise KeyError(f"unknown device_id: {device_id!r}")
        dev = self.devices[device_id]
        if dev.status != "faulted":
            return False
        dev.status = "recovered"
        self._faults_recovered += 1
        return True

    def integrate_authorized_device(
        self,
        seed: SeedLifecycle,
        device: SimulatedDevice,
        *,
        expected_value_j: float = 12.0,
        estimated_cost_j: float = 4.0,
        measured_value_j: float = 14.0,
        council_approved: bool = True,
    ) -> bool:
        """Integrate a new simulated device through the Seed's governed ContactLayer."""
        spec = ContactSpec(
            contact_id=device.device_id,
            protocol="sim-logistics-bus",
            capabilities=(device.kind, device.zone),
            read_scope=(device.zone,),
            estimated_cost_j=estimated_cost_j,
            sandboxed=True,
        )
        seed.register_contact(spec)
        plan = ContactPlan(
            contact_id=device.device_id,
            scope=(device.zone,),
            expected_value_j=expected_value_j,
            estimated_cost_j=estimated_cost_j,
            rollback_plan=f"detach {device.device_id} from simulated logistics bus",
        )
        res = seed.assimilate_contact(
            plan, measured_value_j=measured_value_j, council_approved=council_approved
        )
        if res.status in ("assimilated", "consolidated"):
            self.devices[device.device_id] = device
            return True
        return False

    def run_reference_drill(self, seed: SeedLifecycle) -> LogisticsScenarioResult:
        """Exercise all three T221 §4 capabilities in simulation: coordinate, recover, integrate."""
        c1 = self.move_bin(src_zone="zone_a", dst_zone="zone_b", quantity=2)
        self.inject_fault("robot-0")
        c2_reroute = self.move_bin(src_zone="zone_b", dst_zone="zone_a", quantity=1)
        c2_recover = self.recover_fault("robot-0")
        new_dev = SimulatedDevice(device_id="sensor-new-1", kind="sensor", zone="zone_c")
        c3_integrate = self.integrate_authorized_device(seed, new_dev)
        prior_preserved = self.move_bin(src_zone="zone_a", dst_zone="zone_b", quantity=1)
        passed = all((c1, c2_reroute, c2_recover, c3_integrate, prior_preserved))
        return LogisticsScenarioResult(
            scenario="t221_s4_internal_logistics",
            tasks_completed=self._tasks_completed,
            faults_injected=self._faults_injected,
            faults_recovered=self._faults_recovered,
            devices_integrated=1 if c3_integrate else 0,
            prior_functions_preserved=prior_preserved,
            passed=passed,
        )
