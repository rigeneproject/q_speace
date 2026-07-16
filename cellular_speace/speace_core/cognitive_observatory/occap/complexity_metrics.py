import math
from collections import defaultdict
from typing import Dict, Optional, Tuple

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class ComplexityMetrics:
    """Computes the 5-dimensional complexity vector C = [C_s, C_f, C_r, C_i, C_t].

    C_s = structural complexity (systems × organs × tissues × cells)
    C_f = functional complexity (signals × molecules × receptors)
    C_r = regulatory complexity (policies × setpoints × routes)
    C_i = informational complexity (signal ontology depth)
    C_t = temporal complexity (stream variance over history)

    Baseline (C_s, C_f, C_r, C_i) is computed once from the Physiome.
    C_t is updated every call from PSN stream history.
    """

    def __init__(self, psn: PhysiologicalSignalBus):
        self.psn = psn
        self._baseline: Optional[Dict[str, float]] = None

    MAX_REF_PRODUCT = 200000  # Reference product for log2 normalization
    # Current SPEACE: 6×13×19×22 = 32604 → log2(32605)/log2(200001) ≈ 0.85
    # 10× larger: 326040 → log2(326041)/log2(200001) ≈ 1.04 (exceeds 1.0)
    # 100× larger: 3260400 → log2(3260401)/log2(200001) ≈ 1.23

    def _compute_baseline(self) -> Dict[str, float]:
        phys = self.psn.physiome

        # C_s — structural
        n_systems = max(len(phys.systems or {}), 1)
        n_organs = max(len(phys.organs or {}), 1)
        n_tissues = max(len(phys.tissues_by_id or {}), 1)
        n_cells = max(len(phys.cells or {}), 1)
        C_s = self._log2_normalize(n_systems * n_organs * n_tissues * n_cells)

        # C_f — functional
        n_constitutional = max(len(phys.constitutional_signals or {}), 1)
        n_epigenetic = max(len(phys.epigenetic_signals or {}), 1)
        n_signals = n_constitutional + n_epigenetic
        n_molecules = max(len(phys.molecules or {}), 1)
        receptors = phys.receptors or {}
        n_receptors = sum(len(recs) for recs in receptors.values())
        C_f = self._log2_normalize(n_signals * n_molecules * max(n_receptors, 1))

        # C_r — regulatory
        n_policies = max(len(phys.policies or {}), 1)
        n_setpoints = max(len(phys.homeostatic_setpoints or {}), 1)
        routing = phys.routing or {}
        n_routes = max(
            len(routing.get("neural", {})) + len(routing.get("endocrine", {})),
            1,
        )
        C_r = self._log2_normalize(n_policies * n_setpoints * n_routes)

        # C_i — informational
        C_i = min(1.0, (n_constitutional + 0.5 * n_epigenetic) / 40.0)

        return {"C_s": C_s, "C_f": C_f, "C_r": C_r, "C_i": C_i}

    def compute(self, tick: int) -> Tuple[float, float, float, float, float]:
        if self._baseline is None:
            self._baseline = self._compute_baseline()

        # C_t — temporal complexity from stream variance
        history = self.psn.history
        if len(history) < 5:
            C_t = 0.5
        else:
            recent = history[-min(len(history), 200):]
            stream_values: Dict[str, list] = defaultdict(list)
            for snap in recent:
                for sid, val in snap.streams.items():
                    stream_values[sid].append(val)
            if stream_values:
                cvs = []
                for vals in stream_values.values():
                    if len(vals) > 1:
                        mean = sum(vals) / len(vals)
                        if abs(mean) > 1e-6:
                            var = sum((v - mean) ** 2 for v in vals) / len(vals)
                            cv = math.sqrt(var) / abs(mean)
                            cvs.append(min(1.0, cv))
                C_t = sum(cvs) / len(cvs) if cvs else 0.5
            else:
                C_t = 0.5

        return (
            round(self._baseline["C_s"], 4),
            round(self._baseline["C_f"], 4),
            round(self._baseline["C_r"], 4),
            round(self._baseline["C_i"], 4),
            round(C_t, 4),
        )

    @staticmethod
    def _log2_normalize(product: int) -> float:
        if product <= 1:
            return 0.0
        return min(2.0, math.log2(product + 1) / math.log2(ComplexityMetrics.MAX_REF_PRODUCT + 1))
