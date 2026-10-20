"""Constants for the AACM self-improvement loop (T-AACM-LOOP_SPEC).

Separated from ``constants.py`` so the AACM *control layer* (shipped
in production) and the AACM *loop* (development-time only, behind
explicit invocation) cannot accidentally share mutable configuration.

BCEL: these are *thresholds* and *budget caps*, not agent goals. They
are dimensionless or SI, and overridable per-instance. Defaults
reflect a conservative bounded-loop regime.
"""

from __future__ import annotations

# --- Loop budget ---
MAX_ITERATIONS: int = 50
MAX_WALL_CLOCK_S: float = 3600.0
AUTO_INFRA_INTERVAL: int = 5  # every N iterations, refresh infra (R8)


# --- R6: reputation ---
REPUTATION_HALF_LIFE_S: float = 7.0 * 24.0 * 3600.0  # 7 days
MIN_REPUTATION: float = 0.05
REPUTATION_LOW_THRESHOLD: float = 0.2  # below this, require K+1 evidence


# --- R5: fallback eligibility ---
FALLBACK_RESIDUAL_CONFIDENCE_MIN: float = 0.4


# --- R7 + R10: adversarial gate threshold modulation by Ω ---
ADVERSARIAL_THRESHOLD_BASE: float = 0.70
ADVERSARIAL_THRESHOLD_LOW_OMEGA: float = 0.85  # omega < OMEGA_MIN
ADVERSARIAL_THRESHOLD_HIGH_OMEGA: float = 0.60  # omega >= 0.50
OMEGA_HIGH_THRESHOLD: float = 0.50


# --- R10: extra-evidence rule when Ω is low or failures recur ---
CONSECUTIVE_FAILURES_FOR_EXTRA_K: int = 3
OMEGA_LOW_FOR_EXTRA_K: float = 0.30


# --- Validation set ---
VALIDATION_SET_MIN_SIZE: int = 10
VALIDATION_SET_MIN_PER_TASK_TYPE: int = 2
VALIDATION_SET_SCHEMA_VERSION: str = "aacm.vs.1"


# --- Convergence detection ---
CONVERGENCE_WINDOW: int = 5
VALIDATION_OVERFIT_THRESHOLD: float = 0.95
VALIDATION_OVERFIT_STREAK: int = 3


# --- Checkpoint schema extension for loop state ---
LOOP_CHECKPOINT_SCHEMA_VERSION: str = "aacm.cp.1+loop.1"


# --- Hard prohibitions (paths the loop may NEVER modify) ---
# These three are loaded directly by loop._assert_path_not_prohibited.
# Kept here (not in loop.py) only because loop.py itself is the
# LOOP_HARD_PROHIBITIONS set; we need a separate anchor for tests.
LOOP_HARD_PROHIBITION_PATHS: frozenset[str] = frozenset(
    {
        "q_speace/aacm/loop.py",
        "q_speace/aacm/controller.py",
        "q_speace/aacm/constants.py",
        "q_speace/aacm/loop_constants.py",
    }
)


# --- Evidence kinds (mirror of primitives._EVIDENCE_KINDS) ---
# Kept as a tuple here so the loop can validate without importing
# the primitives module (avoids circular imports in tests).
EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "code",
        "test",
        "doc",
        "external_audit",
        "metric",
        "log",
    }
)


# --- D3: cap on replacement_diff size ---
# Beyond this, a single proposal is too large to review in one PR
# and the loop should reject it. Counts non-header, non-blank lines.
MAX_DIFF_LINES: int = 500
