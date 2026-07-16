from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Optional

from speace_core.cellular_brain.psn.models import TissueState, TissueStatus
from speace_core.cellular_brain.psn.physiome import Physiome

if TYPE_CHECKING:
    from speace_core.cellular_brain.psn.physiological_signal_bus import (
        PhysiologicalSignalBus,
    )


class AbstractTissue(ABC):
    """Base class for all digital tissues.

    Each tissue is a functional unit within an organ, composed of
    cell types defined in the Physiome. Tissues are active: they
    publish, subscribe, and sense their environment.
    """

    def __init__(
        self,
        tissue_id: str,
        organ_id: str,
        psn: PhysiologicalSignalBus,
        physiome: Physiome,
    ):
        self.tissue_id = tissue_id
        self.organ_id = organ_id
        self.psn = psn
        self.physiome = physiome
        self._status = TissueStatus.ACTIVE

    @abstractmethod
    def publish(self, tick: int) -> None:
        """Publish molecules to Neural and/or Endocrine bus.

        Called by the parent organ during the tick loop.
        Must call psn.deduct_metabolic_cost(tissue_id, cost) for
        each operation.
        """

    @abstractmethod
    def subscribe(self) -> None:
        """Register callbacks for signals of interest.

        Called once during initialisation.
        """

    @abstractmethod
    def sense(self, tick: int) -> TissueState:
        """Build a local representation of current physiological state.

        This is NOT a passive read. The tissue filters, integrates,
        and contextualises PSN signals using genome-defined parameters.
        Has a metabolic cost.
        """

    @property
    def status(self) -> TissueStatus:
        return self._status

    @status.setter
    def status(self, value: TissueStatus) -> None:
        self._status = value

    def deduct_cost(self, cost: float, operation: str = "") -> bool:
        """Deduct metabolic cost from the tissue's budget."""
        return self.psn.deduct_metabolic_cost(self.tissue_id, cost, operation)
