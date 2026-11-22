"""Async httpx client for the SpikingBrain sidecar (T205).

Talks to the FastAPI server in ``spiking_brain_server/``. The contract is:

- POST ``/think``   body: {prompt, coherence_phi, n_tokens, history?}
                     returns: {text, confidence, belief, spikes, plasticity}
- GET  ``/health``  returns: {ready, model, vram_mb, ...}

The client reuses :func:`q_speace.spiking.dynamic_spikes` server-side
contract: ``spikes`` is a dict with keys ``spikes``, ``vth``, ``num_spikes``,
``sparsity``, ``rate``. ``belief`` and ``plasticity`` are plain float
lists.

The class implements the same public surface as :class:`StubSpikingBrain`
so callers can swap them via :func:`make_spiking_brain`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, cast

import httpx
import numpy as np

from ..spiking.encoder import SpikeEncodingResult
from .interface import LifecycleState, SpikingBrainUnavailableError
from .types import ThinkResult


class HTTPSpikingBrainClient:
    """Async client for the SpikingBrain FastAPI sidecar.

    Args:
        endpoint: base URL of the sidecar, e.g. ``http://localhost:8001``.
            No trailing slash.
        timeout_s: total timeout per request (default 30 s).
        n_classes: expected ILF belief vector size; used for parsing.
    """

    _default_timeout: float = 30.0
    supports_async: bool = True
    supports_streaming: bool = False
    supports_tool: bool = False
    supports_retrieval: bool = False

    def __init__(
        self,
        endpoint: str,
        timeout_s: float = 30.0,
        n_classes: int = 3,
    ) -> None:
        endpoint = endpoint.rstrip("/")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must start with http:// or https://")
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.n_classes = n_classes
        self._client: httpx.AsyncClient | None = None
        self._lifecycle: LifecycleState = LifecycleState.LOAD
        # Per-instance identifier (matches legacy ``.backend`` format).
        self._backend_name = endpoint

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def backend(self) -> str:
        """Backward-compatible alias for ``backend_name``."""
        return self._backend_name

    @property
    def memory(self) -> None:  # type: ignore[override]
        return None

    def lifecycle_state(self) -> LifecycleState:
        return self._lifecycle

    async def load(self) -> None:
        """Verify connectivity to the sidecar (no model load — sidecar owns that).

        Transitions LOAD → READY on successful /health; remains LOAD
        (and may raise SpikingBrainUnavailableError) otherwise.
        """
        try:
            cli = await self._ensure_client()
            resp = await cli.get(f"{self.endpoint}/health")
            resp.raise_for_status()
        except Exception as exc:
            raise SpikingBrainUnavailableError(
                f"sidecar at {self.endpoint} not reachable: {exc}"
            ) from exc
        self._lifecycle = LifecycleState.READY

    async def shutdown(self) -> None:
        await self.aclose()
        self._lifecycle = LifecycleState.SHUTDOWN

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_s)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> HTTPSpikingBrainClient:
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        await self.aclose()

    async def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        """Call /think on the sidecar and translate the JSON into a ThinkResult."""
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a str")
        cli = await self._ensure_client()
        history_payload = None
        if history is not None:
            history_payload = [
                {
                    "text": h.text,
                    "confidence": h.confidence,
                    "belief": h.belief.tolist(),
                }
                for h in history[-8:]  # cap to last 8 turns
            ]
        resp = await cli.post(
            f"{self.endpoint}/think",
            json={
                "prompt": prompt,
                "coherence_phi": float(coherence_phi),
                "n_tokens": int(n_tokens),
                "history": history_payload,
            },
        )
        resp.raise_for_status()
        body = cast(dict[str, Any], resp.json())
        return _parse_think_result(body, default_n_classes=self.n_classes)

    async def health(self) -> dict[str, Any]:
        cli = await self._ensure_client()
        resp = await cli.get(f"{self.endpoint}/health")
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())


def _parse_think_result(body: Any, default_n_classes: int) -> ThinkResult:
    """Convert the JSON dict from /think into a ThinkResult.

    Defensive against missing keys, non-dict payloads, and unexpected shapes.
    """
    if not isinstance(body, dict):
        raise ValueError(
            f"sidecar /think response must be a JSON object (got {type(body).__name__})"
        )
    text = str(body.get("text", ""))
    confidence = float(body.get("confidence", 0.0))
    if not math.isfinite(confidence):
        raise ValueError(f"sidecar returned non-finite confidence: {confidence!r}")
    n_tokens = int(body.get("n_tokens", 0))
    latency = float(body.get("latency_s", 0.0))
    if not math.isfinite(latency):
        latency = 0.0
    metadata = dict(body.get("metadata", {}) or {})
    # T-SPB-2 fix: ensure n_tokens_in is always present even on older
    # sidecars that didn't write it. Default to 0 (caller can detect).
    metadata.setdefault("n_tokens_in", 0)

    belief = np.asarray(body.get("belief", [1.0] * default_n_classes), dtype=float)
    if belief.ndim != 1:
        belief = belief.ravel()

    spikes_dict = body.get("spikes", {}) or {}
    spikes = SpikeEncodingResult(
        spikes=np.asarray(spikes_dict.get("spikes", []), dtype=float),
        vth=np.asarray(spikes_dict.get("vth", [1.0]), dtype=float),
        num_spikes=int(spikes_dict.get("num_spikes", 0)),
        sparsity=float(spikes_dict.get("sparsity", 1.0)),
        rate=float(spikes_dict.get("rate", 0.0)),
    )

    plasticity = np.asarray(body.get("plasticity", [0.0] * belief.size), dtype=float)
    if plasticity.size != belief.size:
        # Pad / truncate to match belief shape (paranoia).
        padded = np.zeros(belief.size, dtype=float)
        n = min(plasticity.size, belief.size)
        padded[:n] = plasticity[:n]
        plasticity = padded

    return ThinkResult(
        text=text,
        confidence=confidence,
        belief=belief,
        spikes=spikes,
        plasticity=plasticity,
        n_tokens=n_tokens,
        latency_s=latency,
        metadata=metadata,
    )
