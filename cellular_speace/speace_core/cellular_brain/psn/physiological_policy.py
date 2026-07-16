from __future__ import annotations
from copy import deepcopy
from typing import Dict, List, Optional, Any, Callable

import math


ModulationFunction = Callable[[float, float, float], float]


def _linear(base: float, min_factor: float, max_factor: float, factor_value: float) -> float:
    """Linear modulation: base * (min_factor + (max_factor - min_factor) * factor_value)."""
    return base * (min_factor + (max_factor - min_factor) * min(1.0, max(0.0, factor_value)))


def _inverse_linear(base: float, min_factor: float, max_factor: float, factor_value: float) -> float:
    """Inverse linear: base * (max_factor - (max_factor - min_factor) * factor_value)."""
    return base * (max_factor - (max_factor - min_factor) * min(1.0, max(0.0, factor_value)))


def _sigmoid(base: float, midpoint: float, steepness: float, factor_value: float) -> float:
    """Sigmoid modulation centred at midpoint."""
    return base * (1.0 / (1.0 + math.exp(-steepness * (factor_value - midpoint))))


def _binary(base: float, factor_value: float, on_value: float = 1.0) -> float:
    """Binary override: on_value if factor_value > 0.5 else base."""
    return on_value if factor_value > 0.5 else base


def _shift(
    distribution: Dict[str, float],
    from_key: str,
    to_key: str,
    gain: float,
    factor_value: float,
) -> Dict[str, float]:
    """Shift a fraction of 'from_key' budget to 'to_key'."""
    result = dict(distribution)
    amount = result.get(from_key, 0.0) * gain * min(1.0, max(0.0, factor_value))
    result[from_key] = max(0.0, result.get(from_key, 0.0) - amount)
    result[to_key] = min(1.0, result.get(to_key, 0.0) + amount)
    return result


_MODULATION_FUNCTIONS: Dict[str, Callable] = {
    "linear": _linear,
    "inverse_linear": _inverse_linear,
    "sigmoid": _sigmoid,
    "binary": _binary,
}


class PolicyEngine:
    """Evaluates physiological policies with contextual modulation.

    Policies define how the organism manages energy, risk, recovery,
    exploration, and social behaviour. Each policy can be modulated
    by physiological state factors (stress, fatigue, threat, etc.).
    """

    def __init__(self, policy_defs: Dict[str, Any]):
        self._policies: Dict[str, Any] = deepcopy(policy_defs)
        self._last_evaluated: Dict[str, float] = {}
        self._current_tick: int = 0

    def set_tick(self, tick: int) -> None:
        self._current_tick = tick

    def get_policy(self, policy_id: str, context: Dict[str, float]) -> Any:
        """Evaluate a policy with current physiological context.

        Returns the current effective value of the policy.
        """
        raw = self._policies.get(policy_id)
        if raw is None:
            return None

        policy_type = raw.get("type", "scalar")
        default = raw.get("default", {})

        if policy_type == "distribution":
            return self._eval_distribution(raw, context)
        elif policy_type == "threshold":
            return self._eval_threshold(raw, context)
        elif policy_type == "scalar":
            return self._eval_scalar(raw, context)
        elif policy_type == "decay_function":
            return self._eval_decay(raw, context)
        else:
            return default

    def _eval_distribution(
        self, raw: Dict[str, Any], context: Dict[str, float]
    ) -> Dict[str, float]:
        result = dict(raw.get("default", {}))
        for mod in raw.get("modulation", []):
            factor_name = mod.get("factor", "")
            factor_value = context.get(factor_name, 0.0)
            if factor_value > 0.01:
                result = _shift(
                    result,
                    mod.get("from", ""),
                    mod.get("to", ""),
                    mod.get("gain", 0.3),
                    factor_value,
                )
        return result

    def _eval_threshold(
        self, raw: Dict[str, Any], context: Dict[str, float]
    ) -> Dict[str, float]:
        result = dict(raw.get("default", {}))
        for mod in raw.get("modulation", []):
            factor_name = mod.get("factor", "")
            factor_value = context.get(factor_name, 0.0)
            if factor_value > 0.01:
                fn_desc = mod.get("function", "")
                parts = fn_desc.replace("(", " ").replace(")", " ").split()
                if len(parts) == 4 and parts[0] == "raise_threshold":
                    key = parts[1]
                    amount = float(parts[2]) * factor_value
                    if key in result:
                        result[key] = min(1.0, result.get(key, 0.0) + amount)
                elif len(parts) == 4 and parts[0] == "lower_threshold":
                    key = parts[1]
                    amount = float(parts[2]) * factor_value
                    if key in result:
                        result[key] = max(0.0, result.get(key, 0.0) - amount)
                elif fn_desc.startswith("raise("):
                    amount = float(fn_desc[6:-1]) * factor_value
                    for k in result:
                        result[k] = min(1.0, result[k] + amount)
                elif fn_desc.startswith("lower("):
                    amount = float(fn_desc[6:-1]) * factor_value
                    for k in result:
                        result[k] = max(0.0, result[k] - amount)
        return result

    def _eval_scalar(
        self, raw: Dict[str, Any], context: Dict[str, float]
    ) -> float:
        base = float(raw.get("default", 1.0))
        for mod in raw.get("modulation", []):
            factor_name = mod.get("factor", "")
            factor_value = context.get(factor_name, 0.0)
            if factor_value > 0.01:
                fn_desc = mod.get("function", "")
                if fn_desc.startswith("linear("):
                    parts = fn_desc[7:-1].split(",")
                    if len(parts) == 3:
                        min_f = float(parts[1].strip())
                        max_f = float(parts[2].strip())
                        base = _linear(base, min_f, max_f, factor_value)
                elif fn_desc.startswith("inverse_linear("):
                    parts = fn_desc[15:-1].split(",")
                    if len(parts) == 3:
                        min_f = float(parts[1].strip())
                        max_f = float(parts[2].strip())
                        base = _inverse_linear(base, min_f, max_f, factor_value)
        return base

    def _eval_decay(
        self, raw: Dict[str, Any], context: Dict[str, float]
    ) -> Dict[str, float]:
        result = dict(raw.get("default", {}))
        for mod in raw.get("modulation", []):
            factor_name = mod.get("factor", "")
            factor_value = context.get(factor_name, 0.0)
            if factor_value > 0.01:
                fn_desc = mod.get("function", "")
                if fn_desc.startswith("reset_to("):
                    parts = fn_desc[8:-1].split(",")
                    if len(parts) >= 1:
                        reset_val = float(parts[0].strip())
                        duration = int(parts[1].split("=")[1]) if len(parts) > 1 else 200
                        result["decay_per_tick"] = reset_val
        return result
