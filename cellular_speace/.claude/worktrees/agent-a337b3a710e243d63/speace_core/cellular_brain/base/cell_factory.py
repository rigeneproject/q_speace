from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from speace_core.cellular_brain.base.digital_cell import DigitalCell
    from speace_core.dna.models import SharedGenome


class DifferentiationContext:
    def __init__(
        self,
        region: str,
        need: str,
        risk_level: float = 0.0,
        extra: Dict[str, Any] = None,
    ):
        self.region = region
        self.need = need
        self.risk_level = risk_level
        self.extra = extra or {}


class CellFactory:
    def __init__(self, genome: "SharedGenome"):
        self.genome = genome

    def differentiate(
        self,
        cell_id: str,
        context: DifferentiationContext,
    ) -> "DigitalCell":
        from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
        from speace_core.cellular_brain.cells.digital_astrocyte import DigitalAstrocyte
        from speace_core.cellular_brain.cells.digital_microglia import DigitalMicroglia
        from speace_core.cellular_brain.cells.digital_oligodendrocyte import DigitalOligodendrocyte

        role = self._resolve_role(context)
        if role not in self.genome.morphology.allowed_cell_types:
            raise ValueError(f"Role '{role}' not allowed by genome morphology")

        cell: DigitalCell
        if role == "digital_neuron":
            defaults = self.genome.expression_rules.get("digital_neuron", None)
            kwargs: Dict[str, Any] = {"cell_id": cell_id, "role": role}
            if defaults:
                kwargs["threshold"] = defaults.threshold_defaults.get("threshold", 0.5)
                kwargs["plasticity_rate"] = defaults.threshold_defaults.get("plasticity_rate", 0.05)
            cell = DigitalNeuron(**kwargs)
        elif role == "digital_astrocyte":
            cell = DigitalAstrocyte(cell_id=cell_id, role=role)
        elif role == "digital_microglia":
            cell = DigitalMicroglia(cell_id=cell_id, role=role)
        elif role == "digital_oligodendrocyte":
            cell = DigitalOligodendrocyte(cell_id=cell_id, role=role)
        else:
            raise ValueError(f"Unknown role '{role}'")

        cell.bind_genome(self.genome)
        return cell

    def _resolve_role(self, context: DifferentiationContext) -> str:
        if context.risk_level > 0.7:
            return "digital_microglia"
        mapping = {
            ("brain", "memory"): "digital_neuron",
            ("brain", "processing"): "digital_neuron",
            ("brain", "regulation"): "digital_astrocyte",
            ("brain", "optimization"): "digital_oligodendrocyte",
        }
        return mapping.get((context.region, context.need), "digital_neuron")
