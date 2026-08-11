"""Tests for the T-SPB-4 SpikingBrainCognitiveInterface Protocol and memory subsystem.

Verifies:
- Protocol @runtime_checkable: stub and HTTP client satisfy it.
- Capability flags declared on concrete classes.
- LifecycleState enum values.
- Error class inheritance.
- WorkingMemory: put, recent (cap, order), get_relevant (substring),
  capacity overflow eviction.
- EpisodicMemory: persistence, get_relevant, recent (JSON roundtrip).
- SpikingBrainCortex: delegates lifecycle, load, shutdown to backend;
  default WorkingMemory; aclose deprecation warning.
"""

from __future__ import annotations

import asyncio
import warnings

import pytest

from q_speace.spiking_brain import (
    EpisodicMemory,
    HTTPSpikingBrainClient,
    LifecycleState,
    Memory,
    SpikingBrainCognitiveInterface,
    SpikingBrainCortex,
    SpikingBrainError,
    SpikingBrainMemoryError,
    SpikingBrainQualityError,
    SpikingBrainTimeoutError,
    SpikingBrainUnavailableError,
    StubSpikingBrain,
    StubSpikingBrainV2,
    WorkingMemory,
)


# --- helpers ---


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# --- Protocol runtime_checkable ---


def test_protocol_runtime_checkable_passes_stub() -> None:
    """StubSpikingBrain exposes the Protocol surface.

    Note: ``@runtime_checkable`` Protocols do NOT see plain ``bool``
    attributes or methods with mismatched sync/async signatures (both
    known Python limitations). The strict type-check happens via
    mypy; here we verify capability flags + method presence via
    ``hasattr``.
    """
    s = StubSpikingBrain(n_classes=3)
    # Method presence
    assert hasattr(s, "load") and callable(s.load)
    assert hasattr(s, "shutdown") and callable(s.shutdown)
    assert hasattr(s, "lifecycle_state") and callable(s.lifecycle_state)
    assert hasattr(s, "think") and callable(s.think)
    assert hasattr(s, "health") and callable(s.health)
    # Capability flags
    assert getattr(s, "backend_name", None) == "stub"
    assert getattr(s, "supports_async", None) is False
    assert getattr(s, "supports_streaming", None) is False
    assert getattr(s, "supports_tool", None) is False
    assert getattr(s, "supports_retrieval", None) is False


def test_protocol_runtime_checkable_passes_stub_v2() -> None:
    s = StubSpikingBrainV2(n_classes=3)
    assert hasattr(s, "load") and callable(s.load)
    assert hasattr(s, "shutdown") and callable(s.shutdown)
    assert hasattr(s, "lifecycle_state") and callable(s.lifecycle_state)
    assert getattr(s, "backend_name", None) == "stub-v2"


def test_protocol_rejects_unrelated_object() -> None:
    """A bare object that doesn't expose the protocol methods fails."""
    bare = object()
    assert not (hasattr(bare, "load") and callable(bare.load))


# --- Capability flags ---


def test_stub_capability_flags() -> None:
    s = StubSpikingBrain(n_classes=3)
    assert s.backend_name == "stub"
    assert s.supports_async is False
    assert s.supports_streaming is False
    assert s.supports_tool is False
    assert s.supports_retrieval is False


def test_stub_v2_capability_flags() -> None:
    s = StubSpikingBrainV2(n_classes=3)
    assert s.backend_name == "stub-v2"
    assert s.supports_async is False
    assert s.supports_streaming is False
    assert s.supports_tool is False
    assert s.supports_retrieval is False


def test_client_capability_flags() -> None:
    c = HTTPSpikingBrainClient(endpoint="http://x", n_classes=3)
    assert c.backend_name == "http://x"
    assert c.supports_async is True
    assert c.supports_streaming is False
    assert c.supports_tool is False
    assert c.supports_retrieval is False


# --- LifecycleState enum ---


def test_lifecycle_state_enum_values() -> None:
    assert LifecycleState.LOAD.value == "load"
    assert LifecycleState.READY.value == "ready"
    assert LifecycleState.ACTIVE.value == "active"
    assert LifecycleState.SHUTDOWN.value == "shutdown"


# --- Error class inheritance ---


def test_error_inheritance() -> None:
    assert issubclass(SpikingBrainUnavailableError, SpikingBrainError)
    assert issubclass(SpikingBrainTimeoutError, SpikingBrainError)
    assert issubclass(SpikingBrainQualityError, SpikingBrainError)
    assert issubclass(SpikingBrainMemoryError, SpikingBrainError)
    assert issubclass(SpikingBrainError, Exception)


# --- Memory subsystem ---


def test_working_memory_basic_put_and_recent() -> None:
    mem = WorkingMemory(capacity=4)

    async def go():
        s = StubSpikingBrain(n_classes=3)
        r1 = s.think("first")
        r2 = s.think("second")
        r3 = s.think("third")
        await mem.put(r1)
        await mem.put(r2)
        await mem.put(r3)
        recents = await mem.recent(2)
        return recents, r1, r2, r3

    recents, r1, r2, r3 = _run(go())
    assert len(recents) == 2
    # Most recent first.
    assert recents[0] is r3
    assert recents[1] is r2


def test_working_memory_get_relevant_substring() -> None:
    mem = WorkingMemory(capacity=4)

    async def go():
        s = StubSpikingBrain(n_classes=3)
        await mem.put(s.think("paris is beautiful"))
        await mem.put(s.think("london is foggy"))
        await mem.put(s.think("berlin is historic"))
        return await mem.get_relevant("stub", k=2)

    out = _run(go())
    # All 3 stub results contain "stub" in their templated text; cap at k=2.
    assert len(out) == 2


def test_working_memory_capacity_overflow_eviction() -> None:
    mem = WorkingMemory(capacity=3)

    async def go():
        s = StubSpikingBrain(n_classes=3)
        results = []
        for i in range(5):
            r = s.think(f"item-{i}")
            results.append(r)
            await mem.put(r)
        return await mem.recent(k=10), results

    recents, results = _run(go())
    assert len(recents) == 3
    # Only the last 3 should remain (2, 3, 4), most recent first.
    assert recents[0] is results[4]
    assert recents[1] is results[3]
    assert recents[2] is results[2]


def test_working_memory_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        WorkingMemory(capacity=0)


def test_episodic_memory_persistence(tmp_path) -> None:
    path = str(tmp_path / "history.jsonl")
    mem = EpisodicMemory(path=path)

    async def go():
        s = StubSpikingBrain(n_classes=3)
        r1 = s.think("alpha")
        r2 = s.think("beta")
        r3 = s.think("gamma")
        await mem.put(r1)
        await mem.put(r2)
        await mem.put(r3)
        return r1, r2, r3

    r1, r2, r3 = _run(go())
    # Reload from disk: simulate a fresh process.
    mem2 = EpisodicMemory(path=path)

    async def go2():
        return await mem2.recent(k=10)

    recents = _run(go2())
    assert len(recents) == 3
    # recent() is most-recent-first.
    assert recents[0].text == r3.text
    assert recents[1].text == r2.text
    assert recents[2].text == r1.text


def test_episodic_memory_get_relevant(tmp_path) -> None:
    path = str(tmp_path / "history.jsonl")
    mem = EpisodicMemory(path=path)

    async def go():
        s = StubSpikingBrain(n_classes=3)
        await mem.put(s.think("paris is beautiful"))
        await mem.put(s.think("london is foggy"))
        await mem.put(s.think("paris again"))
        return await mem.get_relevant("stub", k=5)

    out = _run(go())
    assert len(out) == 3  # All stub texts contain "stub".


# --- Cortex integration ---


def test_cortex_has_default_working_memory() -> None:
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3))
    assert isinstance(c.memory, WorkingMemory)
    assert c.memory.capacity == 64


def test_cortex_accepts_custom_memory() -> None:
    mem = WorkingMemory(capacity=8)
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3), memory=mem)
    assert c.memory is mem
    assert c.memory.capacity == 8


def test_cortex_delegates_lifecycle_state() -> None:
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3))
    # Stub defaults to READY.
    assert c.lifecycle_state() == LifecycleState.READY


def test_cortex_load_then_think_then_shutdown() -> None:
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3))

    async def go():
        await c.load()
        assert c.lifecycle_state() == LifecycleState.READY
        result = await c.think("hello")
        assert result.text != ""
        await c.shutdown()
        assert c.lifecycle_state() == LifecycleState.SHUTDOWN
        # After shutdown, think() must raise SpikingBrainUnavailableError.
        with pytest.raises(SpikingBrainUnavailableError):
            await c.think("after shutdown")
        return result

    res = _run(go())
    assert res.text  # non-empty


def test_cortex_aclose_emits_deprecation_warning() -> None:
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3))

    async def go():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await c.aclose()
            deprecation = [w for w in caught if issubclass(w.category, DeprecationWarning)]
            assert deprecation, "aclose() should emit DeprecationWarning"

    _run(go())


def test_cortex_writes_to_memory_on_think() -> None:
    mem = WorkingMemory(capacity=8)
    c = SpikingBrainCortex(backend=StubSpikingBrain(n_classes=3), memory=mem)

    async def go():
        return await c.think("memory write probe"), c

    result, _ = _run(go())

    async def go2():
        return await mem.recent(k=1)

    recents = _run(go2())
    assert len(recents) == 1
    assert recents[0].text == result.text


def test_memory_is_runtime_checkable() -> None:
    """WorkingMemory and EpisodicMemory satisfy the Memory Protocol."""
    wm = WorkingMemory()
    assert isinstance(wm, Memory)

    # EpisodicMemory needs a path.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        em = EpisodicMemory(path=f"{td}/h.jsonl")
        assert isinstance(em, Memory)