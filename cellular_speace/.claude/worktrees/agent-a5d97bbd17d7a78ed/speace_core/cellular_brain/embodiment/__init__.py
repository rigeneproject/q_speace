"""Embodiment layer — the body senses and muscles of SPEACE."""

from speace_core.cellular_brain.embodiment.body_registry import BodyRegistry
from speace_core.cellular_brain.embodiment.body_router import BodyRouter
from speace_core.cellular_brain.embodiment.cross_body_sensorimotor_coordinator import (
    CrossBodySensorimotorCoordinator,
)
from speace_core.cellular_brain.embodiment.cyber_physical_sensor_array import (
    CyberPhysicalSensorArray,
)
from speace_core.cellular_brain.embodiment.embodied_action_actuator import (
    EmbodiedActionActuator,
)
from speace_core.cellular_brain.embodiment.embodiment_monitor import (
    EmbodimentMonitor,
)
from speace_core.cellular_brain.embodiment.physical_environment_model import (
    PhysicalEnvironmentModel,
)

__all__ = [
    "BodyRegistry",
    "BodyRouter",
    "CrossBodySensorimotorCoordinator",
    "CyberPhysicalSensorArray",
    "EmbodiedActionActuator",
    "PhysicalEnvironmentModel",
    "EmbodimentMonitor",
]
