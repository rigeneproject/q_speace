"""SpikingBrainCognitiveInterface — formal Protocol for SpikingBrain backends.

T-SPB-4. Replaces the duck-typed contract previously embedded in
:class:`SpikingBrainCortex`. Every backend (stub, HTTP client, future
SpB2.0) MUST implement this Protocol. Static type-check compliance is
the goal; ``@runtime_checkable`` allows the test suite to assert
conformity without forcing an explicit subclass relationship.

Capability flags (declared as attributes on the concrete class):

    backend_name: str    — short identifier ("stub", "http:...", "local-7b")
    supports_async: bool — whether think() may return a coroutine
    supports_streaming: bool — whether think_stream() is implemented
    supports_tool: bool  — whether think() can interleave tool calls
    supports_retrieval: bool — whether memory.get_relevant() is honored

Lifecycle:

    LOAD      → backend is being constructed (weights loading, HTTP handshake)
    READY     → backend is ready for think() calls
    ACTIVE    → at least one think() call is in flight (advisory)
    SHUTDOWN  → backend has been closed; no more calls

Errors:

    SpikingBrainError               — base class
    SpikingBrainUnavailableError    — backend not in READY state
    SpikingBrainTimeoutError        — think() exceeded timeout
    SpikingBrainQualityError        — confidence below threshold
    SpikingBrainMemoryError         — memory subsystem failure

The Protocol is intentionally ``@runtime_checkable`` so
``isinstance(x, SpikingBrainCognitiveInterface)`` works in tests even
without subclassing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from enum import Enum
from typing import Protocol, runtime_checkable

from .memory import Memory
from .types import ThinkResult


class LifecycleState(str, Enum):
    """Backend lifecycle states (T-SPB-4)."""

    LOAD = "load"
    READY = "ready"
    ACTIVE = "active"
    SHUTDOWN = "shutdown"


class SpikingBrainError(Exception):
    """Base class for all SpikingBrain backend errors.

    Catch this to handle any SpikingBrain-specific failure; catch
    subclasses for granular handling.
    """


class SpikingBrainUnavailableError(SpikingBrainError):
    """Backend is not in READY state (still LOAD-ing or already SHUTDOWN)."""


class SpikingBrainTimeoutError(SpikingBrainError):
    """think() exceeded the configured timeout."""


class SpikingBrainQualityError(SpikingBrainError):
    """Result confidence below the caller's quality threshold.

    Distinct from SpikingBrainError because the model *did* respond,
    but the response wasn't usable per the caller's policy.
    """


class SpikingBrainMemoryError(SpikingBrainError):
    """Memory subsystem failure (read/write/retrieval)."""


@runtime_checkable
class SpikingBrainCognitiveInterface(Protocol):
    """Formal contract every SpikingBrain backend MUST implement.

    The Protocol declares the surface that
    :class:`q_speace.spiking_brain.SpikingBrainCortex` consumes. Concrete
    classes (StubSpikingBrain, HTTPSpikingBrainClient, future
    LocalSpB7B) do NOT need to inherit — they only need to expose the
    attributes listed here.
    """

    backend_name: str
    supports_async: bool
    supports_streaming: bool
    supports_tool: bool
    supports_retrieval: bool

    def lifecycle_state(self) -> LifecycleState:
        """Return the current lifecycle state."""
        ...

    async def load(self) -> None:
        """Initialize the backend (load weights, open connections).

        Transitions LOAD → READY. Idempotent (calling on a READY
        backend is a no-op). Raises
        :class:`SpikingBrainUnavailableError` if the backend cannot
        reach READY.
        """
        ...

    async def shutdown(self) -> None:
        """Release resources. Transitions any state → SHUTDOWN.

        Idempotent. After shutdown, ``think()`` raises
        :class:`SpikingBrainUnavailableError`.
        """
        ...

    async def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        """Run one cognitive step. Returns the language-agnostic result."""
        ...

    async def think_stream(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> AsyncIterator[ThinkResult]:
        """Streaming variant. Required iff ``supports_streaming is True``.

        Each yielded ThinkResult has the text accumulated so far.
        Backends that don't support streaming must NOT yield anything
        even if this method is defined; ``supports_streaming=False`` is
        the authoritative answer for the cortex.
        """
        ...

    async def health(self) -> dict[str, object]:
        """Return a health snapshot (ready, model, vram_mb, ...)."""
        ...

    @property
    def memory(self) -> Memory | None:
        """Optional memory subsystem. None means stateless backend."""
        ...
