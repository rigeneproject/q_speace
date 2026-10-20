"""Constants for the AACM model (T-AACM-SPEC §1.3).

All values are dimensionless or in SI units, with conservative defaults
that are overridable per-instance. The defaults reflect the *failure
mode* regime described in §8 of the spec: a single-agent deployment
with weak cross-validation.
"""

from __future__ import annotations

# Vincolo D: distribuzione minima del controllo.
OMEGA_MIN: float = 0.10

# Regola 7: numero minimo di canali indipendenti di legittimazione.
LEGITIMATION_K_MIN: int = 2

# Regola 10: periodicità del checkpoint (in step).
CHECKPOINT_INTERVAL_STEPS: int = 5

# Regola 1: soglia di betweenness oltre cui un nodo è "centrale".
CENTRALITY_HIT_THRESHOLD: float = 0.6

# Regola 2: finestra di fail-fast (fallimenti consecutivi prima del
# switch tattico).
FAIL_FAST_WINDOW: int = 2

# Regola 7: tempo di decadimento della legittimità non rinnovata.
DECAY_HALF_LIFE_S: float = 3600.0
