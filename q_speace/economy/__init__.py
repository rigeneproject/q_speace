"""q_speace_economy — SPEACE-aligned multi-domain economic primitives (T6.*).

Implements the formal apparatus described in ``docs/q_speace_economy.md``
(v0.3+): the cognitive 5-tuple ``J_c``, the multi-domain ``V`` vector, the
12-dimensional ``CME`` registry, the ``DAT`` (Dynamic Allocation Token) with
exponential decay, the ``VTEC`` (Value-of-Total-Exergy-Considered) controller
(projected gradient ascent under 6 hard constraints), the ``kl_barycentre``
aggregator (iterative Bregman projection), and the ``elasticity_test`` for
admission control.

Submodules are intentionally **numpy-only** — no scipy/cvxpy/pymanopt — to
respect the AGENTS.md invariant and to keep the package importable on the
Windows control process (no GPU required for primitives; VTEC runs in
< 1 ms per call on toy graphs).

BCEL: the 5-tuple ``J_c`` is *not* a joule-equivalent of consciousness. It is
a structured measurement tuple whose components are independently measurable
physical quantities (energy, entropy, information, regenerative capacity,
catalytic cost). Any claim of "metabolic intentionality" deriving from
``J_c`` is **accidental**: the math survives, the analogy does not.

Public surface (this ``__init__`` is the curated entry point; deeper
symbols are reached via explicit submodule imports):

- :func:`J_c.from_telemetry` — build the 5-tuple from per-agent telemetry
- :class:`V` — multi-domain value vector (4 or 5 components)
- :class:`CME` — 12-dimensional Capital-Multi-vector Extension
- :class:`DAT` — Dynamic Allocation Token (exponential decay, bound to use)
- :func:`vtec_allocate` — projected gradient allocation under constraints
- :func:`kl_barycentre.aggregate` — KL-barycentre of N distributions
- :func:`elasticity_test` — REJECT/ACCEPT gate for external standards

The MCP server (``q_speace.economy.mcp_server``) exposes these primitives as
JSON-RPC tools for external agents.
"""

from __future__ import annotations

from .primitives import CME, J_c, V

__all__ = [
    "J_c",
    "V",
    "CME",
]
