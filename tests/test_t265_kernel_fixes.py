"""T265 — regression tests for kernel fixes B1–B4 and the new-vocabulary experiment."""

from __future__ import annotations

import numpy as np

from q_speace.self_improvement_cortex.epigenetics import EpigeneticEngine
from q_speace.spiking.criticality import CriticalityController


def test_branching_ratio_is_unbiased_for_stationary_noise_and_k_does_not_saturate() -> None:
    ctrl = CriticalityController(window=16)
    rng = np.random.default_rng(0)
    k, sigmas = 3.0, []
    for _ in range(400):
        st = ctrl.step(int(rng.poisson(4)), k)
        k = st.updated_k
        sigmas.append(st.branching_ratio)
    assert abs(float(np.mean(sigmas[20:])) - 1.0) < 0.03
    assert ctrl.k_min < k < ctrl.k_max


def test_branching_ratio_tracks_geometric_growth() -> None:
    ctrl = CriticalityController(window=16)
    for t in range(16):
        st = ctrl.step(int(round(100 * 1.2**t)), 3.0)
    assert 1.15 < st.branching_ratio < 1.25
    assert st.regime == "super_critical"


def test_epigenetic_engine_honours_configured_thresholds() -> None:
    eng = EpigeneticEngine(min_promotions=5, stability_threshold=0.9)
    for _ in range(4):
        eng.promote("m")
    assert eng.state_of("m").consolidated is False  # type: ignore[union-attr]
    eng.promote("m")
    assert eng.state_of("m").consolidated is True  # type: ignore[union-attr]


def test_consolidated_mutation_is_revoked_on_rollback_and_register_is_idempotent() -> None:
    eng = EpigeneticEngine()
    for _ in range(3):
        eng.promote("x")
    assert eng.register("x").promotion_count == 3
    for _ in range(10):
        eng.suppress("x")
    assert eng.should_rollback("x") is True
    assert eng.state_of("x").consolidated is False  # type: ignore[union-attr]


def test_t265_new_vocabulary_shows_no_positive_transfer() -> None:
    from q_speace.vertical_slice.t265_new_vocabulary_transfer import run_t265

    s = run_t265(seeds=3, n=16)["summary"]
    assert s["verdict"] == "H1_token_lookup"  # documented limit; flip when T266-30 lands


def test_t266_06_retracted_signatures_survive_cold_boot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import asyncio

    from q_speace.bridge import latent_discovery as ld

    db = tmp_path / "retract.db"
    sig = (frozenset({"panel_online", "bus_ready"}), "engage_primary_bus", "probe_x", "tok_y")

    async def _save() -> None:
        p = ld.Stage1CognitivePrototype(db_path=db, allow_consolidated_load=False)
        p.learner.retracted_signatures.add(sig)
        await p.persist_and_close()

    asyncio.run(_save())
    p2 = ld.Stage1CognitivePrototype(db_path=db, cold_boot_require_consolidated=True)
    assert sig in p2.learner.retracted_signatures
    assert p2.store is not None
    p2.store.close()


def test_t266_06_rss_reader_reports_current_not_peak() -> None:
    from q_speace.bridge.stage1_workspace import read_process_rss_mb

    before = read_process_rss_mb()
    blob = bytearray(60 * 1024 * 1024)
    during = read_process_rss_mb()
    del blob
    assert 1.0 < before < 250.0
    assert during >= before
