"""Factory for the SpikingBrain backend (T205).

Selects between :class:`StubSpikingBrain` (default, offline) and
:class:`HTTPSpikingBrainClient` based on the ``Q_SPEACE_BRAIN_ENDPOINT``
environment variable. When ``Q_SPEACE_BRAIN_ENDPOINT`` is empty/unset
the factory returns a stub; the stub flavour (v1 vs v2) is selected
via ``Q_SPEACE_BRAIN_MODEL``. The factory never raises if the endpoint
is not reachable — it always returns a stub. Use
:meth:`SpikingBrainCortex.health` to verify connectivity.

Environment variables
---------------------

- ``Q_SPEACE_BRAIN_ENDPOINT``  HTTP base URL of the sidecar (e.g.
  ``http://localhost:8001``). Empty or unset ⇒ stub.
- ``Q_SPEACE_BRAIN_MODEL``     ``v1`` (default) or ``v2``. Selects the
  stub flavour when no endpoint is set. The HTTP backend ignores this
  env var — the sidecar itself decides which model to load. ``v2``
  maps to :class:`StubSpikingBrainV2` which mimics DSSA / MoBA-style
  flatter belief + faster plasticity decay.
- ``Q_SPEACE_BRAIN_TIMEOUT``   Per-request timeout in seconds (default 30).
- ``Q_SPEACE_BRAIN_NCLASSES``  ILF belief vector size (default 3).

Adding a real V2 backend
------------------------

When SpikingBrain2.0 becomes publicly downloadable on HuggingFace
(no public V2 exists as of August 2026 — see the model scan in the
T205 plan file), replace the ``v2`` branch of this factory with a
shim that returns an ``HTTPSpikingBrainClient`` pointed at a sidecar
that has loaded the V2 checkpoint. The stub exists *only* so that
callers can exercise the factory dispatch without a GPU.
"""

from __future__ import annotations

import os

from .client import HTTPSpikingBrainClient
from .stub import StubSpikingBrain, StubSpikingBrainV2

_VALID_MODELS = {"v1", "v2"}


def make_spiking_brain(
    n_classes: int | None = None,
    timeout_s: float | None = None,
    seed: int | None = None,
) -> StubSpikingBrain | StubSpikingBrainV2 | HTTPSpikingBrainClient:
    """Return the appropriate backend.

    The return type is the union of all backends; callers should depend
    on the duck-typed ``SpikingBrainCortex`` contract, not on the class.
    """
    endpoint = os.environ.get("Q_SPEACE_BRAIN_ENDPOINT", "").strip()
    n_classes = n_classes or int(os.environ.get("Q_SPEACE_BRAIN_NCLASSES", "3"))
    timeout_s = timeout_s or float(os.environ.get("Q_SPEACE_BRAIN_TIMEOUT", "30"))
    model = os.environ.get("Q_SPEACE_BRAIN_MODEL", "v1").strip().lower()

    if model not in _VALID_MODELS:
        # Fall back silently to v1; this is the kind of configuration
        # mistake that should not crash the cortex.
        model = "v1"

    if not endpoint:
        if model == "v2":
            return StubSpikingBrainV2(n_classes=n_classes, seed=seed)
        return StubSpikingBrain(n_classes=n_classes, seed=seed)
    return HTTPSpikingBrainClient(endpoint=endpoint, timeout_s=timeout_s, n_classes=n_classes)
