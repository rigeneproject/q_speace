"""Test for the orchestrator <-> loop integration (T-AACM-LOOP_SPEC §C2).

The orchestrator exposes ``attach_loop`` / ``detach_loop`` /
``attached_loop``. The loop is NOT auto-invoked by the orchestrator;
it is only referenced. This test verifies the wiring without
changing orchestrator behaviour.
"""

from __future__ import annotations

from q_speace.aacm.loop import AACMLoop
from q_speace.orchestrator import QuantumOrchestrator


def test_orchestrator_attach_loop_default_none() -> None:
    """A fresh orchestrator has no loop attached."""
    orch = QuantumOrchestrator()
    assert orch.attached_loop is None


def test_orchestrator_attach_loop_stores_reference() -> None:
    """attach_loop stores the reference; attached_loop returns it."""
    orch = QuantumOrchestrator()
    loop = AACMLoop(omega=0.6, max_iterations=5)
    orch.attach_loop(loop)
    assert orch.attached_loop is loop


def test_orchestrator_detach_loop_returns_previous() -> None:
    """detach_loop returns the previously-attached loop, or None."""
    orch = QuantumOrchestrator()
    assert orch.detach_loop() is None
    loop = AACMLoop(omega=0.6, max_iterations=5)
    orch.attach_loop(loop)
    assert orch.detach_loop() is loop
    assert orch.attached_loop is None


def test_orchestrator_does_not_invoke_attached_loop() -> None:
    """The orchestrator MUST NOT auto-invoke the loop on tick().

    This is a structural invariant: auto-invocation would convert
    the loop from a development tool into a production agent,
    violating T-AACM-LOOP_SPEC §0.
    """
    orch = QuantumOrchestrator(enable_earth=False)

    class _SentinelLoop(AACMLoop):
        invoked = False

        def run(self, *args, **kwargs):  # type: ignore[override]
            _SentinelLoop.invoked = True
            return super().run(*args, **kwargs)

    loop = _SentinelLoop(omega=0.6, max_iterations=1)
    orch.attach_loop(loop)

    # Run a few ticks. The orchestrator must not have called
    # loop.run() implicitly.
    for _ in range(3):
        orch.tick()

    assert _SentinelLoop.invoked is False
    # Detaching still works.
    assert orch.detach_loop() is loop
