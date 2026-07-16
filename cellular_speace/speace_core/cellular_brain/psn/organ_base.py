from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from typing import TYPE_CHECKING

from speace_core.cellular_brain.psn.models import OrganState, TissueState, TissueStatus
from speace_core.cellular_brain.psn.physiome import Physiome

if TYPE_CHECKING:
    from speace_core.cellular_brain.psn.physiological_signal_bus import (
        PhysiologicalSignalBus,
    )
    from speace_core.cellular_brain.psn.tissue_base import AbstractTissue


class AbstractOrgan(ABC):
    """Base class for all digital organs.

    An organ is composed of one or more tissues. It delegates
    publish/subscribe/sense to its constituent tissues.
    """

    def __init__(
        self,
        organ_id: str,
        system_id: str,
        psn: PhysiologicalSignalBus,
        physiome: Physiome,
    ):
        self.organ_id = organ_id
        self.system_id = system_id
        self.psn = psn
        self.physiome = physiome
        self._tissues: Dict[str, AbstractTissue] = {}

    def add_tissue(self, tissue: AbstractTissue) -> None:
        self._tissues[tissue.tissue_id] = tissue

    @property
    def tissues(self) -> Dict[str, AbstractTissue]:
        return dict(self._tissues)

    def publish_all(self, tick: int) -> None:
        """Publish from all tissues."""
        for tissue in self._tissues.values():
            if tissue.status != TissueStatus.CRISIS:
                tissue.publish(tick)

    def subscribe_all(self) -> None:
        """Subscribe all tissues."""
        for tissue in self._tissues.values():
            tissue.subscribe()

    def sense_all(self, tick: int) -> OrganState:
        """Sense from all tissues, return aggregated organ state."""
        tissue_states = {}
        for tid, tissue in self._tissues.items():
            if tissue.status != TissueStatus.CRISIS:
                tissue_states[tid] = tissue.sense(tick)
            else:
                tissue_states[tid] = TissueState(
                    tissue_id=tid,
                    organ_id=self.organ_id,
                    status=TissueStatus.CRISIS,
                )
        return OrganState(
            organ_id=self.organ_id,
            system_id=self.system_id,
            tissues=tissue_states,
        )
