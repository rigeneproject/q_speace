"""T172 — Information Value Module for SPEACE.

Closes the gap identified in the context-engineering gap analysis:
"informational value as a thermodynamic function of order ↔ exploration".

The package implements three modules:

- :class:`PerceivedEntropyModule` — aggregates prediction_error, novelty,
  informational_entropy, signal_diversity into a single perceived entropy
  signal ``H_local(t) ∈ [0, 1]``. Maps to DNA principle
  ``destructive_entropy_reduction`` (S_ent) and ``generative_variability_preservation``
  (V_gen) without modifying them.

- :class:`InformationalValueFunction` — implements the inverted-U value
  function ``V(novelty, predictability, compressibility) ∈ [-1, +1]`` with a
  sweet spot at the boundary between order and chaos. Maps to the
  *emergent* relationship between S_ent and V_gen.

- :class:`ExplorationPolicy` — deterministic ``π(a|s, V)`` that proposes
  (does NOT execute) actions through the existing
  ``EmbodiedActionActuator`` governance. Maps to the missing
  ``motivational_dopaminergic_loop`` BCEL equivalence.

These modules are designed to be **observers + proposers**, never direct
mutators of DNA, BCEL catalog or safety-critical state. They comply with
``AGENTS.md`` §3 ownership gates.
"""

from speace_core.cellular_brain.information_value.perceived_entropy import (
    PerceivedEntropyModule,
    PerceivedEntropySnapshot,
)
from speace_core.cellular_brain.information_value.value_function import (
    InformationalValueFunction,
    ValueBreakdown,
)
from speace_core.cellular_brain.information_value.exploration_policy import (
    ExplorationPolicy,
    ActionProposal,
    ProposalKind,
)

__all__ = [
    "PerceivedEntropyModule",
    "PerceivedEntropySnapshot",
    "InformationalValueFunction",
    "ValueBreakdown",
    "ExplorationPolicy",
    "ActionProposal",
    "ProposalKind",
]
