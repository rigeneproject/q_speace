"""Small instruction-tuned chat sidecar for Q-SPEACE (T207).

Heavy ML dependencies are imported only at startup, so this module remains
importable on the Windows control process. The service has no access to ILF
or SIA state; it only returns an untrusted response over HTTP.
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from q_speace.spiking import SpikePlasticity, dynamic_spikes

MODEL_ID = os.environ.get("Q_SPEACE_INSTRUCT_MODEL", "Qwen/Qwen2.5-3B-Instruct")
MODEL_PATH = os.environ.get("Q_SPEACE_INSTRUCT_MODEL_PATH", MODEL_ID)
PORT = int(os.environ.get("Q_SPEACE_INSTRUCT_PORT", "8002"))
MAX_NEW_TOKENS = int(os.environ.get("Q_SPEACE_INSTRUCT_MAX_NEW_TOKENS", "128"))

model_obj: Any | None = None
tokenizer_obj: Any | None = None
model_ready = False
model_lock = asyncio.Lock()
plasticity = SpikePlasticity(num_units=3, decay=0.9, seed=0)


class ThinkRequest(BaseModel):
    prompt: str
    coherence_phi: float = 1.0
    n_tokens: int = 64
    history: list[dict[str, Any]] | None = None


class ThinkResponse(BaseModel):
    text: str
    confidence: float
    belief: list[float]
    spikes: dict[str, Any]
    plasticity: list[float]
    n_tokens: int
    latency_s: float
    metadata: dict[str, Any] = Field(default_factory=dict)


def _load_model() -> None:
    global model_obj, tokenizer_obj, model_ready
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")
    tokenizer_obj = AutoTokenizer.from_pretrained(MODEL_PATH)
    model_obj = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        device_map="auto",
        quantization_config=quant,
        torch_dtype=torch.bfloat16,
    )
    model_obj.eval()
    model_ready = True


def _messages(req: ThinkRequest) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise, helpful language interface for Q-SPEACE. "
                "State uncertainty plainly. Do not claim consciousness or agency."
            ),
        }
    ]
    for item in (req.history or [])[-4:]:
        text = str(item.get("text", "")).strip()
        if text:
            messages.append({"role": "assistant", "content": text})
    messages.append({"role": "user", "content": req.prompt})
    return messages


def token_confidence(score_rows: list[np.ndarray], coherence: float) -> float:
    """Mean greedy-token probability, attenuated by the ILF coherence gate.

    This is a measurable model-output statistic, unlike a hash-derived
    pseudo-confidence. It is still only a forecast and requires labelled
    Brier/ECE evaluation before being trusted as calibrated.
    """
    if not score_rows:
        return 0.0
    probabilities: list[float] = []
    for scores in score_rows:
        shifted = scores - np.max(scores)
        probs = np.exp(shifted)
        probabilities.append(float(np.max(probs) / np.sum(probs)))
    return float(np.clip(np.mean(probabilities) * (0.5 + 0.5 * coherence), 0.0, 1.0))


def _belief(confidence: float, coherence: float) -> np.ndarray:
    """Expose a normalised three-class control vector, not semantic truth."""
    raw = np.array([confidence, 1.0 - confidence, coherence], dtype=float)
    return raw / raw.sum()


def _think_sync(req: ThinkRequest) -> ThinkResponse:
    if model_obj is None or tokenizer_obj is None:
        raise RuntimeError("model not loaded")
    import torch

    coherence = float(np.clip(req.coherence_phi, 0.0, 1.0))
    inputs = tokenizer_obj.apply_chat_template(
        _messages(req), add_generation_prompt=True, return_tensors="pt"
    ).to(model_obj.device)
    prompt_len = int(inputs.shape[-1])
    started = time.monotonic()
    with torch.no_grad():
        output = model_obj.generate(
            inputs,
            max_new_tokens=max(1, min(req.n_tokens, MAX_NEW_TOKENS)),
            do_sample=False,
            repetition_penalty=1.05,
            return_dict_in_generate=True,
            output_scores=True,
        )
    generated = output.sequences[0][prompt_len:]
    text = tokenizer_obj.decode(generated, skip_special_tokens=True).strip()
    score_rows = [scores[0].float().cpu().numpy() for scores in output.scores]
    confidence = token_confidence(score_rows, coherence)
    belief = _belief(confidence, coherence)
    spikes = dynamic_spikes(belief, k=3.0, coherence_phi=coherence, beta=0.1)
    plasticity.update(spikes.spikes)
    return ThinkResponse(
        text=text,
        confidence=confidence,
        belief=belief.tolist(),
        spikes={
            "spikes": spikes.spikes.tolist(),
            "vth": spikes.vth.tolist(),
            "num_spikes": spikes.num_spikes,
            "sparsity": spikes.sparsity,
            "rate": spikes.rate,
        },
        plasticity=plasticity.coefficients().tolist(),
        n_tokens=int(generated.shape[-1]),
        latency_s=time.monotonic() - started,
        metadata={
            "backend": "hf-instruct-nf4",
            "model": MODEL_ID,
            "confidence_source": "mean-greedy-token-probability",
            "n_tokens_in": prompt_len,
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model_ready
    try:
        await asyncio.to_thread(_load_model)
    except Exception:
        model_ready = False
    yield


app = FastAPI(title="Q-SPEACE instruction chat sidecar", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ready": model_ready, "model": MODEL_ID, "backend": "hf-instruct-nf4"}


@app.post("/think", response_model=ThinkResponse)
async def think(req: ThinkRequest) -> ThinkResponse:
    if not model_ready:
        raise HTTPException(status_code=503, detail="instruction model not ready")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is empty")
    async with model_lock:
        return await asyncio.to_thread(_think_sync, req)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    main()
