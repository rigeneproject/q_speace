"""T207 import-level tests; no GPU or model download required."""

from __future__ import annotations

import os

import pytest


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


@pytest.mark.gpu
def test_apply_chat_template_with_local_tokenizer() -> None:
    """Smoke test: load Qwen tokenizer from local path and run apply_chat_template.

    The model is expected to live at the path in Q_SPEACE_INSTRUCT_MODEL_PATH
    (already downloaded at /home/roby/models/qwen2.5-3b-instruct). If the
    path does not exist locally, the test is skipped — no network is touched.
    """

    model_path = os.environ.get(
        "Q_SPEACE_INSTRUCT_MODEL_PATH", "/home/roby/models/qwen2.5-3b-instruct"
    )
    if not os.path.isdir(model_path):
        pytest.skip(f"Qwen tokenizer not available at {model_path}")

    from transformers import AutoTokenizer  # heavy import, gated by skip

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    messages = [{"role": "user", "content": "ping"}]
    out = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
    assert out is not None
    assert int(out.shape[-1]) > 0
