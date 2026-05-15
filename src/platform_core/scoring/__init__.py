"""Scoring engine — Current License Score, Target Posture Score, Opportunity.

Implements LICENSE_MODEL.md §7 against the Finding table. Deterministic,
session-pure, no I/O outside SQLAlchemy.
"""

from platform_core.scoring.engine import (
    EngagementScores,
    ModuleScores,
    compute_scores,
)

__all__ = ["EngagementScores", "ModuleScores", "compute_scores"]
