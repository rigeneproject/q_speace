"""Attack simulator for the q_speace_economy (T6.21 §4.10.1).

The 5 conditions of a successful weak-to-strong takeover are described
in ``docs/q_speace_economy.md`` §4.10.1:

1. **salience injection** — the attacker raises the perceived reward
   of one action so the controller over-allocates to it;
2. **induction of λ** — the attacker biases the discount rate so the
   controller prefers short-term over long-term outcomes;
3. **exit cost asymmetry** — the attacker makes the controller's
   allocation sticky (high switching cost) so it cannot escape the
   sub-optimal attractor;
4. **monopoly of measurement** — the attacker controls the only
   external standard, so the elasticity test cannot find a referee;
5. **reference elasticity** — the attacker rides the threshold
   elasticity: small perturbations in the external standard flip the
   ACCEPT/REJECT gate repeatedly.

This module ships a detector per condition. Each detector returns the
set of triggered flags for a given state.

BCEL: the detectors are *functional*: they are deterministic checks on
measurable state vectors. They do not label any agent as "malicious";
they flag structural conditions that **would** enable a takeover if
exploited.
"""

from __future__ import annotations
