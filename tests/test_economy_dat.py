"""Tests for the q_speace_economy DAT module (T6.4)."""

from __future__ import annotations

import math

import pytest

from q_speace.economy.dat import DAT, half_life_for_target_lifespan, rate_to_half_life


def test_dat_value_at_mint_time() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=1000.0)
    assert d.value_at(1000.0) == 100.0


def test_dat_value_at_half_life() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=1000.0)
    assert d.value_at(1000.0 + 3600.0) == pytest.approx(50.0, abs=1e-9)


def test_dat_value_after_two_half_lives() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=1000.0)
    assert d.value_at(1000.0 + 2 * 3600.0) == pytest.approx(25.0, abs=1e-9)


def test_dat_value_long_ago_approaches_zero() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=0.0)
    assert d.value_at(1e9) < 1e-200


def test_dat_fraction_remaining_in_unit_interval() -> None:
    d = DAT(amount=100.0, bound_to="x", decay_half_life=10.0, mint_time=0.0)
    assert d.fraction_remaining(0.0) == pytest.approx(1.0)
    assert d.fraction_remaining(10.0) == pytest.approx(0.5)
    assert 0.0 < d.fraction_remaining(5.0) < 1.0


def test_dat_rejects_pre_mint_time() -> None:
    d = DAT(amount=1.0, bound_to="x", decay_half_life=1.0, mint_time=100.0)
    with pytest.raises(ValueError):
        d.value_at(50.0)


def test_dat_constructor_validates() -> None:
    with pytest.raises(ValueError):
        DAT(amount=0.0, bound_to="x", decay_half_life=1.0, mint_time=0.0)
    with pytest.raises(ValueError):
        DAT(amount=1.0, bound_to="", decay_half_life=1.0, mint_time=0.0)
    with pytest.raises(ValueError):
        DAT(amount=1.0, bound_to="x", decay_half_life=0.0, mint_time=0.0)
    with pytest.raises(ValueError):
        DAT(amount=1.0, bound_to="x", decay_half_life=1.0, mint_time=-1.0)


def test_dat_spend_success_reduces_amount() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=0.0)
    receipt = d.spend(amount=20.0, target="exergy", t=0.0)
    assert receipt.spent == 20.0
    # Remaining amount = 80.0
    assert d.amount == pytest.approx(80.0, abs=1e-9)
    assert d.mint_time == 0.0


def test_dat_spend_with_decay_then_new_mint() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=3600.0, mint_time=0.0)
    # Half-life elapsed, value = 50.0
    receipt = d.spend(amount=10.0, target="exergy", t=3600.0)
    assert receipt.spent == 10.0
    # Remaining 40.0 at new mint time t=3600
    assert d.amount == pytest.approx(40.0, abs=1e-9)
    assert d.mint_time == 3600.0
    # 1 more half-life → 20.0
    assert d.value_at(3600.0 + 3600.0) == pytest.approx(20.0, abs=1e-9)


def test_dat_spend_bound_violation() -> None:
    d = DAT(amount=100.0, bound_to="exergy", decay_half_life=1.0, mint_time=0.0)
    with pytest.raises(ValueError, match="bound violation"):
        d.spend(amount=1.0, target="entropy", t=0.0)


def test_dat_spend_overspend() -> None:
    d = DAT(amount=10.0, bound_to="exergy", decay_half_life=1.0, mint_time=0.0)
    with pytest.raises(ValueError, match="over-spend"):
        d.spend(amount=20.0, target="exergy", t=0.0)


def test_dat_spend_rejects_non_positive_amount() -> None:
    d = DAT(amount=1.0, bound_to="x", decay_half_life=1.0, mint_time=0.0)
    with pytest.raises(ValueError):
        d.spend(amount=0.0, target="x", t=0.0)
    with pytest.raises(ValueError):
        d.spend(amount=-1.0, target="x", t=0.0)


def test_half_life_for_target_lifespan() -> None:
    assert half_life_for_target_lifespan(3600.0) == 3600.0


def test_half_life_for_target_lifespan_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        half_life_for_target_lifespan(0.0)


def test_rate_to_half_life() -> None:
    rate = math.log(2.0) / 3600.0  # 1 hour half-life
    assert rate_to_half_life(rate) == pytest.approx(3600.0, abs=1e-9)


def test_rate_to_half_life_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        rate_to_half_life(0.0)
    with pytest.raises(ValueError):
        rate_to_half_life(-1.0)
