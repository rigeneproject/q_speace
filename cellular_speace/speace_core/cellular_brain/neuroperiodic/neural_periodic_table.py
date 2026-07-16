from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_core.cellular_brain.neuroperiodic.neural_element import (
    CATALOG,
    ElementBlock,
    ElementGroup,
    ElementPeriod,
    NeuralElement,
    ValenceState,
    build_element,
    get_element_by_cell_type,
)


class PeriodVisualization(BaseModel):
    """ASCII/Unicode visualization of a single period row."""
    period: ElementPeriod
    elements: Dict[ElementGroup, str] = Field(default_factory=dict)


class NeuralPeriodicTable(BaseModel):
    """The Neural Periodic Table — organizing principle for all neural elements.

    Maps each neuron type to a position in a 2D grid where:
      - Rows (Periods) = hierarchical processing depth
      - Columns (Groups) = functional family
      - Cell color/pattern = Block (neurotransmitter system)

    Provides property prediction, element discovery, and
    compatibility rules between elements.
    """
    elements: Dict[int, NeuralElement] = Field(default_factory=dict)
    by_symbol: Dict[str, int] = Field(default_factory=dict)
    by_cell_type: Dict[str, int] = Field(default_factory=dict)
    periods: Dict[ElementPeriod, List[NeuralElement]] = Field(default_factory=dict)
    groups: Dict[ElementGroup, List[NeuralElement]] = Field(default_factory=dict)
    blocks: Dict[ElementBlock, List[NeuralElement]] = Field(default_factory=dict)

    # Periodic trends as mathematical functions
    trend_functions: Dict[str, Callable] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def register(self, element: NeuralElement) -> None:
        z = element.atomic_number
        self.elements[z] = element
        self.by_symbol[element.symbol] = z
        for ct in element.cell_types:
            self.by_cell_type[ct] = z
        self.periods.setdefault(element.period, []).append(element)
        self.groups.setdefault(element.group, []).append(element)
        self.blocks.setdefault(element.block, []).append(element)

    def get_by_z(self, z: int) -> Optional[NeuralElement]:
        return self.elements.get(z)

    def get_by_symbol(self, symbol: str) -> Optional[NeuralElement]:
        z = self.by_symbol.get(symbol)
        return self.elements.get(z) if z else None

    def get_by_cell_type(self, cell_type: str) -> Optional[NeuralElement]:
        z = self.by_cell_type.get(cell_type)
        return self.elements.get(z) if z else None

    def get_period(self, period: ElementPeriod) -> List[NeuralElement]:
        return self.periods.get(period, [])

    def get_group(self, group: ElementGroup) -> List[NeuralElement]:
        return self.groups.get(group, [])

    def get_block(self, block: ElementBlock) -> List[NeuralElement]:
        return self.blocks.get(block, [])

    # ------------------------------------------------------------------
    # Periodic trends
    # ------------------------------------------------------------------

    def _default_electronegativity_trend(self, p: ElementPeriod, g: ElementGroup) -> float:
        """Electronegativity increases across a period, decreases down a group."""
        base = g.value / 18.0
        period_factor = 1.0 - ((p.value - 1) / 6.0) * 0.3
        return min(1.0, base * period_factor + 0.1)

    def _default_ionization_trend(self, p: ElementPeriod, g: ElementGroup) -> float:
        """Ionization energy increases across a period, decreases down a group."""
        base = (g.value / 18.0) * 0.5 + 0.3
        period_factor = 1.0 + ((p.value - 1) / 6.0) * 0.2
        return min(1.0, base * period_factor)

    def _default_radius_trend(self, p: ElementPeriod, g: ElementGroup) -> float:
        """Atomic radius decreases across a period, increases down a group."""
        base = 1.0 - (g.value / 18.0) * 0.4
        period_factor = 1.0 + ((p.value - 1) / 6.0) * 0.3
        return min(1.0, max(0.0, base * period_factor))

    def predict_property(self, period: ElementPeriod, group: ElementGroup,
                         property_name: str = "electronegativity") -> float:
        """Predict a property based on position in the table."""
        key = f"{property_name}_trend"
        fn = self.trend_functions.get(key)
        if fn:
            return fn(period, group)
        if property_name == "electronegativity":
            return self._default_electronegativity_trend(period, group)
        if property_name == "ionization_energy":
            return self._default_ionization_trend(period, group)
        if property_name == "atomic_radius":
            return self._default_radius_trend(period, group)
        return 0.5

    def find_similar(self, element: NeuralElement, n: int = 5) -> List[NeuralElement]:
        """Find the n most similar elements based on periodic properties."""
        candidates = [
            e for e in self.elements.values()
            if e.atomic_number != element.atomic_number
        ]
        def _similarity(other: NeuralElement) -> float:
            score = 0.0
            score += 1.0 - abs(element.electronegativity - other.electronegativity)
            score += 1.0 - abs(element.ionization_energy - other.ionization_energy)
            score += 1.0 - abs(element.atomic_radius - other.atomic_radius)
            score += 1.0 - abs(element.mass - other.mass)
            score += 0.5 if element.block == other.block else 0.0
            score += 0.3 if element.group == other.group else 0.0
            score += 0.2 if element.period == other.period else 0.0
            return score / 5.0
        candidates.sort(key=_similarity, reverse=True)
        return candidates[:n]

    def predict_connection(self, source: NeuralElement,
                           target: NeuralElement) -> Dict[str, float]:
        """Predict the properties of a connection between two elements."""
        base = source.compatibility_score(target)
        strength = base * (1.0 - abs(source.ionization_energy - target.ionization_energy))
        polarity = 0.5 + 0.5 * (source.electronegativity - target.electronegativity)
        plasticity = 0.5 + 0.5 * (1.0 - abs(source.mass - target.mass))
        return {
            "compatibility": base,
            "strength": max(0.0, min(1.0, strength)),
            "polarity": max(0.0, min(1.0, polarity)),
            "plasticity": max(0.0, min(1.0, plasticity)),
            "reciprocal": target.compatibility_score(source),
        }

    def suggest_network(self, elements: List[NeuralElement],
                        density: float = 0.3) -> List[Tuple[int, int, float]]:
        """Suggest a network topology between a list of elements.

        Returns list of (source_z, target_z, connection_strength).
        """
        import random
        connections = []
        n = len(elements)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if random.random() > density:
                    continue
                src = elements[i]
                tgt = elements[j]
                pred = self.predict_connection(src, tgt)
                if pred["compatibility"] > 0.4:
                    connections.append(
                        (src.atomic_number, tgt.atomic_number, pred["strength"])
                    )
        return connections

    def to_periodic_grid(self) -> Dict[str, Any]:
        """Return the table as a grid (for visualization/monitoring)."""
        grid = {}
        for period in ElementPeriod:
            period_data = {}
            for group in ElementGroup:
                elements_in_cell = [
                    e for e in self.elements.values()
                    if e.period == period and e.group == group
                ]
                if elements_in_cell:
                    period_data[str(group.value)] = [
                        e.to_dict() for e in elements_in_cell
                    ]
            if period_data:
                grid[str(period.value)] = period_data
        return grid

    def count(self) -> int:
        return len(self.elements)

    def missing_blocks(self) -> List[Tuple[ElementPeriod, ElementGroup, ElementBlock]]:
        """Detect empty positions in the table (undiscovered elements)."""
        filled = {(e.period, e.group, e.block) for e in self.elements.values()}
        all_combinations = []
        for p in ElementPeriod:
            for g in ElementGroup:
                for b in ElementBlock:
                    all_combinations.append((p, g, b))
        return [c for c in all_combinations if c not in filled]


class PeriodicTableBuilder:
    """Builds and populates the NeuralPeriodicTable from catalog and genome data."""

    @classmethod
    def build_default(cls) -> NeuralPeriodicTable:
        table = NeuralPeriodicTable()
        for z in sorted(CATALOG.keys()):
            element = build_element(z)
            table.register(element)
        cls._add_affinities(table)
        return table

    @classmethod
    def _add_affinities(cls, table: NeuralPeriodicTable) -> None:
        # Define cross-element affinities based on biological pairing
        affinities = {
            "Ph": {"Sc": 0.9, "Cc": 0.85, "In": 0.3},
            "Hc": {"Au": 0.9, "We": 0.7, "In": 0.3},
            "Au": {"We": 0.9, "Br": 0.8, "Hp": 0.5},
            "We": {"Br": 0.85, "Sp": 0.8, "Pf": 0.6},
            "Br": {"Mo": 0.85, "Sp": 0.7, "Pf": 0.6},
            "Sp": {"Pf": 0.8, "Dm": 0.7, "Hp": 0.6},
            "Hp": {"En": 0.9, "Dg": 0.9, "Dm": 0.7, "Pf": 0.6},
            "Pf": {"Lb": 0.8, "Dm": 0.7, "Mo": 0.7, "Cb": 0.6, "In": 0.5},
            "Lb": {"Pf": 0.8, "Hp": 0.7, "Dp": 0.9, "Sr": 0.8},
            "Dm": {"Pf": 0.7, "Hp": 0.6, "Lb": 0.6},
            "Mo": {"Cb": 0.9, "Bs": 0.6, "In": 0.4},
            "Cb": {"Mo": 0.9, "Bs": 0.5, "In": 0.5},
            "Bs": {"As": 0.8, "Dp": 0.7, "Sr": 0.7},
            "In": {"Pf": 0.8, "Mo": 0.7, "Hp": 0.7, "Sc": 0.6},
            "Dp": {"Lb": 0.9, "Pf": 0.8, "Hp": 0.7},
            "Sr": {"Lb": 0.8, "Dm": 0.7, "Bs": 0.7},
            "As": {"Bs": 0.8, "In": 0.6, "Mg": 0.5},
            "Mg": {"As": 0.6, "Ol": 0.4, "In": 0.5},
            "Ol": {"Mo": 0.7, "Pf": 0.6, "Hp": 0.5},
        }
        for symbol, targets in affinities.items():
            element = table.get_by_symbol(symbol)
            if element:
                element.affinity_strengths.update(targets)
