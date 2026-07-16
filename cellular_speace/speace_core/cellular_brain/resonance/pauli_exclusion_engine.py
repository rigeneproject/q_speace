from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.resonance.frequency_oscillator import FrequencyBand


@dataclass
class CognitiveQuantumNumbers:
    region_id: str
    frequency_band: str
    function_type: str
    encoding_dimension: int = 0

    def to_tuple(self) -> Tuple[str, str, str, int]:
        return (self.region_id, self.frequency_band, self.function_type, self.encoding_dimension)

    def to_signature(self) -> str:
        raw = f"{self.region_id}:{self.frequency_band}:{self.function_type}:{self.encoding_dimension}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]


class PauliExclusionEngine(BaseModel):
    engine_id: str
    occupied_states: Dict[str, CognitiveQuantumNumbers] = Field(default_factory=dict)
    exclusion_violations: int = 0
    max_violations_before_action: int = 3

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def try_occupy(
        self,
        agent_id: str,
        quantum_numbers: CognitiveQuantumNumbers,
    ) -> bool:
        signature = quantum_numbers.to_signature()
        for existing_id, existing_qn in self.occupied_states.items():
            if existing_qn.to_signature() == signature and existing_id != agent_id:
                return False
        self.occupied_states[agent_id] = quantum_numbers
        return True

    def release(self, agent_id: str) -> None:
        self.occupied_states.pop(agent_id, None)

    def find_collisions(
        self,
        agent_id: str,
        quantum_numbers: CognitiveQuantumNumbers,
    ) -> List[str]:
        signature = quantum_numbers.to_signature()
        colliders: List[str] = []
        for existing_id, existing_qn in self.occupied_states.items():
            if existing_qn.to_signature() == signature and existing_id != agent_id:
                colliders.append(existing_id)
        return colliders

    def find_available_state(
        self,
        agent_id: str,
        preferred_qn: CognitiveQuantumNumbers,
        all_bands: Optional[List[str]] = None,
        all_functions: Optional[List[str]] = None,
    ) -> Optional[CognitiveQuantumNumbers]:
        if self.try_occupy(agent_id, preferred_qn):
            return preferred_qn

        bands = all_bands or [b.value for b in FrequencyBand]
        functions = all_functions or [
            "sensory", "motor", "associative", "executive",
            "memory", "language", "emotional", "regulatory",
        ]

        for band in bands:
            for func in functions:
                for dim in range(3):
                    candidate = CognitiveQuantumNumbers(
                        region_id=preferred_qn.region_id,
                        frequency_band=band,
                        function_type=func,
                        encoding_dimension=dim,
                    )
                    if self.try_occupy(agent_id, candidate):
                        return candidate
        return None

    def detect_collision_risk(
        self, agent_id: str, quantum_numbers: CognitiveQuantumNumbers
    ) -> float:
        collisions = self.find_collisions(agent_id, quantum_numbers)
        if not collisions:
            return 0.0
        return min(1.0, len(collisions) / max(1, len(self.occupied_states)))

    def force_differentiation(
        self,
        agent_id: str,
        quantum_numbers: CognitiveQuantumNumbers,
    ) -> CognitiveQuantumNumbers:
        result = self.find_available_state(agent_id, quantum_numbers)
        if result is not None:
            return result

        if quantum_numbers.encoding_dimension < 5:
            return CognitiveQuantumNumbers(
                region_id=quantum_numbers.region_id,
                frequency_band=quantum_numbers.frequency_band,
                function_type=quantum_numbers.function_type,
                encoding_dimension=quantum_numbers.encoding_dimension + 1,
            )

        import random
        bands = [b.value for b in FrequencyBand]
        return CognitiveQuantumNumbers(
            region_id=quantum_numbers.region_id,
            frequency_band=random.choice(bands),
            function_type=quantum_numbers.function_type,
            encoding_dimension=0,
        )

    def get_occupancy_count(self) -> int:
        return len(self.occupied_states)

    def get_unique_state_count(self) -> int:
        signatures: Set[str] = {qn.to_signature() for qn in self.occupied_states.values()}
        return len(signatures)

    def reset(self) -> None:
        self.occupied_states.clear()
        self.exclusion_violations = 0
