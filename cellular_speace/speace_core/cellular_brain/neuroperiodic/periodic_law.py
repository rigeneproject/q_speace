"""Periodic Law — mathematical rules governing neural element behavior.

The periodic table is not just a classification — it makes predictions.
These laws derive mathematical trends and interaction rules from
element positions, enabling predictive modeling of neural circuits.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_core.cellular_brain.neuroperiodic.neural_element import (
    ElementBlock,
    ElementGroup,
    ElementPeriod,
    NeuralElement,
    ValenceState,
)
from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
    BondType,
    SynapticBond,
)

# T-DNA — periodic table can be driven by Digital DNA genes
try:
    from speace_core.dna.models import (
        PeriodicTableGeneSet,
        PeriodicTrendGene,
        ValenceRuleGene,
        ReactionRuleGene,
    )
except Exception:  # pragma: no cover
    PeriodicTableGeneSet = None  # type: ignore[misc,assignment]
    PeriodicTrendGene = None  # type: ignore[misc,assignment]
    ValenceRuleGene = None  # type: ignore[misc,assignment]
    ReactionRuleGene = None  # type: ignore[misc,assignment]




def _safe_eval_expression(expression: str, variables: Dict[str, Any]) -> float:
    """Safely evaluate a numeric expression string for periodic trends.

    Only a small whitelist of names is allowed to avoid arbitrary code
    execution. The expression receives the normalized variables ``g`` and
    ``p`` plus standard math helpers.
    """
    safe_names = {
        "abs": abs,
        "max": max,
        "min": min,
        "pow": pow,
        "round": round,
        "sum": sum,
        "math": __import__("math"),
    }
    safe_names.update(variables)
    try:
        return float(eval(expression, {"__builtins__": {}}, safe_names))
    except Exception:
        return 0.0


class PeriodicTrend(BaseModel):
    """A mathematical trend across periods and groups.

    Examples:
      - Electronegativity increases → across period
      - Ionization energy increases → across period
      - Atomic radius decreases → across period
      - Plasticity increases ← across period (deeper = more plastic)
    """
    name: str
    description: str
    across_period: Callable[[float], float]  # f(group_normalized) → property
    down_group: Callable[[float], float]      # f(period_normalized) → property
    noise_amplitude: float = 0.05

    class Config:
        arbitrary_types_allowed = True

    def predict(self, period: ElementPeriod, group: ElementGroup) -> float:
        gp = (group.value - 1) / 17.0
        pp = (period.value - 1) / 6.0
        across = self.across_period(gp)
        down = self.down_group(pp)
        return (across + down) / 2.0


class ValenceRule(BaseModel):
    """Rules for element pairing based on valence electron patterns.

    Analogous to how atoms bond to fill their valence shells.
    """
    name: str
    description: str
    condition: str  # logical expression evaluated against element pair
    result: Dict[str, Any] = Field(default_factory=dict)

    def check(self, source: NeuralElement, target: NeuralElement) -> bool:
        """Evaluate the rule condition against two elements."""
        try:
            return bool(eval(self.condition, {
                "source": source,
                "target": target,
                "ElementBlock": ElementBlock,
                "ElementGroup": ElementGroup,
                "ElementPeriod": ElementPeriod,
                "ValenceState": ValenceState,
            }))
        except Exception:
            return False


class ReactionRule(BaseModel):
    """A neural 'chemical reaction': element + element → computation pattern.

    Analogous to chemical reactions:
      A + B → C (two elements combine to produce a computation)
      A → B + C (one element diverges into two pathways)
      A + catalyst → A' (element is modulated without being consumed)
    """
    name: str
    description: str
    reactants: List[str]
    products: List[str]
    catalyst: Optional[str] = None
    energy_barrier: float = 0.5
    rate_constant: float = 0.1

    def can_react(self, elements: List[NeuralElement],
                  catalyst: Optional[NeuralElement] = None) -> bool:
        """Check if the reaction can occur given available elements."""
        reactant_symbols = {e.symbol for e in elements}
        if not set(self.reactants).issubset(reactant_symbols):
            return False
        if self.catalyst and (catalyst is None or catalyst.symbol != self.catalyst):
            return False
        return True


class PeriodicLaw(BaseModel):
    """Collection of periodic laws governing neural element behavior.

    Provides mathematical functions for:
      1. Property prediction from position
      2. Reaction prediction (which elements combine)
      3. Network formation rules
      4. Periodic trends
      5. Valence/octet rules
    """
    trends: Dict[str, PeriodicTrend] = Field(default_factory=dict)
    valence_rules: List[ValenceRule] = Field(default_factory=list)
    reaction_rules: List[ReactionRule] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # DNA-driven construction
    # ------------------------------------------------------------------

    @classmethod
    def from_genome(cls, genome: Any) -> "PeriodicLaw":
        """Build a PeriodicLaw from Digital DNA periodic-table genes.

        If the genome does not contain usable periodic-table genes, falls
        back to the hard-coded defaults.
        """
        if genome is None or PeriodicTableGeneSet is None:
            return cls.build_default()
        genes = getattr(genome, "periodic_table_genes", None)
        if genes is None:
            genes = getattr(genome, "periodic_table", {}).get("genes")
        if genes is None:
            return cls.build_default()

        if not getattr(genes, "enabled", True):
            return cls.build_default()

        law = cls()

        # Trends
        trend_genes = getattr(genes, "trends", {}) or {}
        if trend_genes:
            for name, gene in trend_genes.items():
                if not isinstance(gene, PeriodicTrendGene):
                    continue
                trend = PeriodicTrend(
                    name=gene.name,
                    description=gene.description,
                    across_period=lambda g, expr=gene.across_period: _safe_eval_expression(expr, {"g": g}),
                    down_group=lambda p, expr=gene.down_group: _safe_eval_expression(expr, {"p": p}),
                    noise_amplitude=gene.noise_amplitude,
                )
                law.trends[name] = trend
        else:
            law.trends = cls.default_trends()

        # Valence rules
        valence_genes = getattr(genes, "valence_rules", []) or []
        if valence_genes:
            for gene in valence_genes:
                if not isinstance(gene, ValenceRuleGene):
                    continue
                law.valence_rules.append(
                    ValenceRule(
                        name=gene.name,
                        description=gene.description,
                        condition=gene.condition,
                        result=gene.result,
                    )
                )
        else:
            law.valence_rules = cls.default_valence_rules()

        # Reaction rules
        reaction_genes = getattr(genes, "reaction_rules", []) or []
        if reaction_genes:
            for gene in reaction_genes:
                if not isinstance(gene, ReactionRuleGene):
                    continue
                law.reaction_rules.append(
                    ReactionRule(
                        name=gene.name,
                        description=gene.description,
                        reactants=gene.reactants,
                        products=gene.products,
                        catalyst=gene.catalyst,
                        energy_barrier=gene.energy_barrier,
                        rate_constant=gene.rate_constant,
                    )
                )
        else:
            law.reaction_rules = cls.default_reaction_rules()

        return law

    @classmethod
    def build_default(cls) -> "PeriodicLaw":
        """Build PeriodicLaw with factory defaults."""
        return cls(
            trends=cls.default_trends(),
            valence_rules=cls.default_valence_rules(),
            reaction_rules=cls.default_reaction_rules(),
        )

    # ------------------------------------------------------------------
    # Periodic trends factory
    # ------------------------------------------------------------------

    @classmethod
    def default_trends(cls) -> Dict[str, PeriodicTrend]:
        return {
            "electronegativity": PeriodicTrend(
                name="Electronegativity",
                description="Inhibition tendency; increases across period, decreases down group",
                across_period=lambda g: min(1.0, 0.15 + g * 0.85),
                down_group=lambda p: max(0.1, 1.0 - p * 0.6),
            ),
            "ionization_energy": PeriodicTrend(
                name="Ionization Energy",
                description="Activation threshold; increases across period, decreases down group",
                across_period=lambda g: min(1.0, 0.2 + g * 0.8),
                down_group=lambda p: max(0.15, 1.0 - p * 0.5),
            ),
            "atomic_radius": PeriodicTrend(
                name="Atomic Radius",
                description="Receptive field size; decreases across period, increases down group",
                across_period=lambda g: max(0.1, 1.0 - g * 0.7),
                down_group=lambda p: min(1.0, 0.2 + p * 0.8),
            ),
            "plasticity": PeriodicTrend(
                name="Neural Plasticity",
                description="Ability to change; peaks in middle periods (association areas)",
                across_period=lambda g: 0.3 + 0.5 * (1.0 - abs(g - 0.5) * 2.0),
                down_group=lambda p: 0.2 + 0.6 * (1.0 - abs(p - 0.4) * 1.5),
            ),
            "metabolic_cost": PeriodicTrend(
                name="Metabolic Cost",
                description="Energy consumption; increases with period depth (larger neurons)",
                across_period=lambda g: 0.2 + g * 0.3,
                down_group=lambda p: 0.2 + p * 0.7,
            ),
            "myelination_potential": PeriodicTrend(
                name="Myelination Potential",
                description="Tendency to be myelinated; higher in stable, repetitive pathways",
                across_period=lambda g: 0.3 + 0.5 * (1.0 - abs(g - 0.4)),
                down_group=lambda p: max(0.1, 0.8 - p * 0.5),
            ),
        }

    # ------------------------------------------------------------------
    # Valence rules factory
    # ------------------------------------------------------------------

    @classmethod
    def default_valence_rules(cls) -> List[ValenceRule]:
        from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
            BondPolarity,
            BondType,
        )
        return [
            ValenceRule(
                name="Octet Rule",
                description="Excitatory neurons preferentially connect to ~7-9 targets",
                condition="source.is_excitatory() and target.is_inhibitory()",
                result={"max_connections": 8, "bond_type": BondType.COVALENT},
            ),
            ValenceRule(
                name="Complementary Valence",
                description="Excitatory→Inhibitory pairs form strong, stable connections",
                condition="source.is_excitatory() and target.is_inhibitory()",
                result={"compatibility_boost": 0.3, "bond_type": BondType.IONIC},
            ),
            ValenceRule(
                name="Like-Valence Repulsion",
                description="Inhibitory→Inhibitory pairs are rare and weak",
                condition="source.is_inhibitory() and target.is_inhibitory()",
                result={"compatibility_penalty": -0.3, "max_strength": 0.3},
            ),
            ValenceRule(
                name="Modulatory Gating",
                description="Modulatory elements gate excitatory→inhibitory pairs",
                condition="source.is_modulatory() or target.is_modulatory()",
                result={"bond_type": BondType.HYDROGEN, "plasticity_boost": 0.2},
            ),
            ValenceRule(
                name="Hierarchical Feedforward",
                description="Lower period → higher period forms feedforward pathways",
                condition="source.period.value < target.period.value",
                result={"polarity": BondPolarity.UNIDIRECTIONAL_FORWARD, "direction_boost": 0.2},
            ),
            ValenceRule(
                name="Hierarchical Feedback",
                description="Higher period → lower period forms feedback pathways",
                condition="source.period.value > target.period.value",
                result={"polarity": BondPolarity.UNIDIRECTIONAL_BACKWARD, "direction_boost": 0.15},
            ),
            ValenceRule(
                name="Same-Group Resonance",
                description="Same-group elements form recurrent/resonant connections",
                condition="source.group == target.group and source.atomic_number != target.atomic_number",
                result={"bond_type": BondType.METALLIC, "polarity": BondPolarity.RECURRENT},
            ),
            ValenceRule(
                name="Glial Inertness",
                description="Glial elements (G-block) do not form strong directed bonds",
                condition="source.block == ElementBlock.G_BLOCK or target.block == ElementBlock.G_BLOCK",
                result={"bond_type": BondType.VAN_DER_WAALS, "max_strength": 0.2},
            ),
            ValenceRule(
                name="Cross-Block Modulation",
                description="D-block elements modulate P-block and S-block connections",
                condition="source.block == ElementBlock.D_BLOCK and target.block in (ElementBlock.P_BLOCK, ElementBlock.S_BLOCK)",
                result={"bond_type": BondType.HYDROGEN, "modulation_factor": 0.3},
            ),
        ]

    # ------------------------------------------------------------------
    # Reaction rules factory
    # ------------------------------------------------------------------

    @classmethod
    def default_reaction_rules(cls) -> List[ReactionRule]:
        return [
            ReactionRule(
                name="Sensory Integration",
                description="Sensory input + feature extraction → feature detection",
                reactants=["Ph", "Sc"], products=["Cc"],
                energy_barrier=0.3, rate_constant=0.5,
            ),
            ReactionRule(
                name="Auditory Comprehension",
                description="Auditory + Wernicke → semantic comprehension",
                reactants=["Hc", "Au", "We"], products=["Sp"],
                energy_barrier=0.4, rate_constant=0.3,
            ),
            ReactionRule(
                name="Memory Formation",
                description="Hippocampal + entorhinal + dentate → memory binding",
                reactants=["Hp", "En", "Dg"], products=["Dm"],
                energy_barrier=0.5, rate_constant=0.2,
            ),
            ReactionRule(
                name="Executive Decision",
                description="Prefrontal + limbic (valence) → executive command",
                reactants=["Pf", "Lb"], products=["Mo"],
                catalyst="Dp", energy_barrier=0.6, rate_constant=0.4,
            ),
            ReactionRule(
                name="Motor Correction",
                description="Motor + cerebellar → refined motor output",
                reactants=["Mo", "Cb"], products=["Mo"],
                energy_barrier=0.35, rate_constant=0.6,
            ),
            ReactionRule(
                name="Inhibitory Gating",
                description="Inhibitory interneuron gates any excitatory signal",
                reactants=["Sc", "In"], products=["null"],
                energy_barrier=0.2, rate_constant=0.7,
            ),
            ReactionRule(
                name="Dopaminergic Facilitation",
                description="Dopamine facilitates prefrontal→motor planning",
                reactants=["Pf", "Mo"], products=["Mo"],
                catalyst="Dp", energy_barrier=0.3, rate_constant=0.5,
            ),
            ReactionRule(
                name="Serotonergic Regulation",
                description="Serotonin modulates limbic→prefrontal valence",
                reactants=["Lb", "Pf"], products=["Pf"],
                catalyst="Sr", energy_barrier=0.4, rate_constant=0.3,
            ),
            ReactionRule(
                name="Default Mode Reflection",
                description="Hippocampal→default mode during offline periods",
                reactants=["Hp", "Dm"], products=["Dm"],
                energy_barrier=0.5, rate_constant=0.2,
            ),
            ReactionRule(
                name="Astrocytic Support",
                description="Astrocyte regulates energy in any active circuit",
                reactants=["Pf", "As"], products=["Pf"],
                energy_barrier=0.1, rate_constant=0.3,
            ),
        ]

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    @classmethod
    def build_default(cls) -> "PeriodicLaw":
        return PeriodicLaw(
            trends=cls.default_trends(),
            valence_rules=cls.default_valence_rules(),
            reaction_rules=cls.default_reaction_rules(),
        )

    def predict_property(self, element: NeuralElement,
                         property_name: str) -> float:
        """Predict a periodic property for any element."""
        trend = self.trends.get(property_name)
        if trend:
            return trend.predict(element.period, element.group)
        return element.metadata.get(property_name, 0.5)

    def get_applicable_rules(self, source: NeuralElement,
                             target: NeuralElement) -> List[ValenceRule]:
        """Get all valence rules that apply to this pair."""
        return [r for r in self.valence_rules if r.check(source, target)]

    def get_applicable_reactions(self, elements: List[NeuralElement],
                                 catalyst: Optional[NeuralElement] = None
                                 ) -> List[ReactionRule]:
        """Get all reactions that can occur with available elements."""
        return [
            r for r in self.reaction_rules
            if r.can_react(elements, catalyst)
        ]

    def apply_bond_rules(self, source: NeuralElement,
                         target: NeuralElement,
                         bond: SynapticBond) -> SynapticBond:
        """Apply all applicable valence rules to modify a bond."""
        rules = self.get_applicable_rules(source, target)
        for rule in rules:
            for key, val in rule.result.items():
                if hasattr(bond, key):
                    current = getattr(bond, key)
                    if isinstance(val, (int, float)) and isinstance(current, (int, float)):
                        setattr(bond, key, current + val)
                    else:
                        setattr(bond, key, val)
        return bond

    def describe_pair(self, source: NeuralElement,
                      target: NeuralElement) -> Dict[str, Any]:
        """Full periodic analysis of an element pair."""
        applicable_rules = self.get_applicable_rules(source, target)
        return {
            "source": source.symbol,
            "target": target.symbol,
            "compatibility": source.compatibility_score(target),
            "reciprocal": target.compatibility_score(source),
            "valence_rules": [r.name for r in applicable_rules],
            "predicted_bond_type": self._predict_bond_type(source, target).value,
        }

    def _predict_bond_type(self, source: NeuralElement,
                           target: NeuralElement) -> BondType:
        """Simplified bond prediction using valence rules."""
        for rule in self.valence_rules:
            if rule.check(source, target):
                bt = rule.result.get("bond_type")
                if bt:
                    try:
                        return BondType(bt)
                    except ValueError:
                        pass
        return BondType.COVALENT


# ------------------------------------------------------------------
# BCEL extension: functional constraints
# ------------------------------------------------------------------

try:
    from speace_core.cellular_brain.neuroperiodic.functional_constraint_law import (
        FunctionalConstraintLaw,
        FunctionalConstraintRegistry,
    )
except Exception:  # pragma: no cover
    FunctionalConstraintLaw = None  # type: ignore[misc,assignment]
    FunctionalConstraintRegistry = None  # type: ignore[misc,assignment]


def _patch_periodic_law() -> None:
    """Attach functional-constraint support to PeriodicLaw if not present."""
    if not hasattr(PeriodicLaw, "add_functional_constraint"):

        def add_functional_constraint(self, data: dict) -> None:
            """Add a functional constraint law from a dictionary payload."""
            if FunctionalConstraintLaw is None:
                return
            law = FunctionalConstraintLaw(**data)
            reg = getattr(self, "_functional_constraints", None)
            if reg is None:
                reg = FunctionalConstraintRegistry()
                self._functional_constraints = reg
            reg.register(law)

        PeriodicLaw.add_functional_constraint = add_functional_constraint

    if not hasattr(PeriodicLaw, "functional_constraints"):

        @property
        def functional_constraints(self) -> list:
            reg = getattr(self, "_functional_constraints", None)
            if reg is None:
                return []
            return list(reg.laws.values())

        PeriodicLaw.functional_constraints = functional_constraints


_patch_periodic_law()
