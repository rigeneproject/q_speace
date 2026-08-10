"""T207 import-level tests; no GPU or model download required."""

from __future__ import annotations


def test_instruction_server_imports_without_runtime_model() -> None:
    from spiking_brain_server.instruction_server import app

    assert app.title == "Q-SPEACE instruction chat sidecar"
    assert {route.path for route in app.routes} >= {"/health", "/think"}


def test_token_confidence_distinguishes_sharp_from_uniform_logits() -> None:
    import numpy as np

    from spiking_brain_server.instruction_server import token_confidence

    sharp = token_confidence([np.array([8.0, 0.0])], coherence=1.0)
    uniform = token_confidence([np.array([0.0, 0.0])], coherence=1.0)
    assert sharp > uniform
