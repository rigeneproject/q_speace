"""AGI readiness assessment for SPEACE.

This package provides tools to measure how close SPEACE is to exhibiting
Artificial General Intelligence (AGI) across a set of observable dimensions.
"""

from speace_core.cellular_brain.agi_readiness.agi_readiness_score import (
    AGIReadinessDimension,
    AGIReadinessScore,
    AGIReadinessReport,
)

__all__ = ["AGIReadinessDimension", "AGIReadinessScore", "AGIReadinessReport"]
