"""Score engine.

Aggregates control outcomes (one per Finding category) into:

- Current License Score      — only over license-eligible controls
- Target Posture Score       — over all evaluable controls, treating
                                not_licensed / requires_add_on /
                                available_in_higher_tier as failures
- Opportunity                 — points dropped by factoring in unlicensed
                                gaps, i.e. `Current − Target` (always ≥ 0
                                with the §7.3 target_factor mapping). This
                                matches LICENSE_MODEL §1's commercial framing
                                ("close X points of risk"); the §7.4 formula
                                is written `Target − Current`, which has the
                                same magnitude but inverted sign — flagged
                                in REVIEW_NOTES for resolution at Cycle 2.

Per LICENSE_MODEL.md §7. POC uses unit weight per control and an
unweighted average across modules. Correlation findings are excluded
from per-module aggregation (they are cross-module derivatives, not
control outcomes).

Pass factor by severity (POC mapping):

  info, low     → 1.0   (control passes / minor)
  medium        → 0.5   (partial)
  high, critical → 0.0  (fail)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from platform_core.findings.models import Finding, LicenseStatus, Severity

_CURRENT_ELIGIBLE: frozenset[str] = frozenset(
    {
        LicenseStatus.LICENSED_ENABLED.value,
        LicenseStatus.LICENSED_DISABLED.value,
        LicenseStatus.LICENSED_MISCONFIGURED.value,
    }
)

# Target ignores `not_applicable` and `unknown` (LICENSE_MODEL §7.3).
_TARGET_EXCLUDED: frozenset[str] = frozenset(
    {
        LicenseStatus.NOT_APPLICABLE.value,
        LicenseStatus.UNKNOWN.value,
    }
)

# In Target scoring, these license statuses are counted as outright failures
# (LICENSE_MODEL §7.3): the customer would close the gap by buying / enabling
# the capability.
_TARGET_FORCE_FAIL: frozenset[str] = frozenset(
    {
        LicenseStatus.NOT_LICENSED.value,
        LicenseStatus.REQUIRES_ADD_ON.value,
        LicenseStatus.AVAILABLE_IN_HIGHER_TIER.value,
    }
)

_PASS_FACTOR_BY_SEVERITY: dict[str, float] = {
    Severity.INFO.value: 1.0,
    Severity.LOW.value: 1.0,
    Severity.MEDIUM.value: 0.5,
    Severity.HIGH.value: 0.0,
    Severity.CRITICAL.value: 0.0,
}


@dataclass(frozen=True)
class ModuleScores:
    """Score breakdown for a single module."""

    module_id: str
    current: float | None  # 0–100 or None if no eligible controls
    target: float | None
    opportunity: float | None  # target − current; None when either is None
    eligible_for_current: int
    eligible_for_target: int
    findings_total: int
    severity_counts: dict[str, int]
    license_status_counts: dict[str, int]

    @property
    def has_data(self) -> bool:
        return self.findings_total > 0


@dataclass(frozen=True)
class EngagementScores:
    """Engagement-wide rollup + per-module breakdown."""

    current: float | None
    target: float | None
    opportunity: float | None
    severity_counts: dict[str, int]  # across all non-correlation findings
    license_status_counts: dict[str, int]
    modules: dict[str, ModuleScores] = field(default_factory=dict)
    correlation_count: int = 0
    critical_correlation_count: int = 0

    def for_module(self, module_id: str) -> ModuleScores | None:
        return self.modules.get(module_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_scores(session: Session, assessment_run_id: str) -> EngagementScores:
    """Compute scores for the given assessment run.

    Reads all findings for the run, groups non-correlation findings by
    (module_id, category) — keeping the most severe per group — and applies
    the LICENSE_MODEL §7 formulas.
    """
    findings: list[Finding] = (
        session.query(Finding)
        .filter(Finding.assessment_run_id == assessment_run_id)
        .all()
    )

    correlation_total = sum(1 for f in findings if f.module_id == "correlation")
    correlation_critical = sum(
        1
        for f in findings
        if f.module_id == "correlation" and f.severity == Severity.CRITICAL.value
    )

    scoreable = [f for f in findings if f.module_id != "correlation"]

    by_module: dict[str, list[Finding]] = {}
    for f in scoreable:
        by_module.setdefault(f.module_id, []).append(f)

    module_scores: dict[str, ModuleScores] = {}
    current_values: list[float] = []
    target_values: list[float] = []

    for module_id, module_findings in by_module.items():
        m = _score_module(module_id, module_findings)
        module_scores[module_id] = m
        if m.current is not None:
            current_values.append(m.current)
        if m.target is not None:
            target_values.append(m.target)

    eng_current = _avg(current_values)
    eng_target = _avg(target_values)
    eng_opportunity = (
        eng_current - eng_target if eng_current is not None and eng_target is not None else None
    )

    return EngagementScores(
        current=eng_current,
        target=eng_target,
        opportunity=eng_opportunity,
        severity_counts=_count(scoreable, lambda f: f.severity),
        license_status_counts=_count(scoreable, lambda f: f.license_status),
        modules=module_scores,
        correlation_count=correlation_total,
        critical_correlation_count=correlation_critical,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _score_module(module_id: str, findings: list[Finding]) -> ModuleScores:
    current_num = 0.0
    current_den = 0.0
    target_num = 0.0
    target_den = 0.0
    eligible_current = 0
    eligible_target = 0

    for f in findings:
        pass_factor = _PASS_FACTOR_BY_SEVERITY.get(f.severity, 0.0)
        weight = 1.0  # POC: equal weights

        if f.license_status in _CURRENT_ELIGIBLE:
            current_num += weight * pass_factor
            current_den += weight
            eligible_current += 1

        if f.license_status not in _TARGET_EXCLUDED:
            target_factor = 0.0 if f.license_status in _TARGET_FORCE_FAIL else pass_factor
            target_num += weight * target_factor
            target_den += weight
            eligible_target += 1

    current = (current_num / current_den * 100.0) if current_den > 0 else None
    target = (target_num / target_den * 100.0) if target_den > 0 else None
    # Opportunity = points lost by counting unlicensed/disabled gaps as
    # failures. Current − Target ≥ 0 always (Target denominator includes
    # the same controls plus the not_licensed/requires_add_on/higher_tier
    # ones, all scored as fail).
    opportunity = (
        current - target if current is not None and target is not None else None
    )

    return ModuleScores(
        module_id=module_id,
        current=_round1(current),
        target=_round1(target),
        opportunity=_round1(opportunity),
        eligible_for_current=eligible_current,
        eligible_for_target=eligible_target,
        findings_total=len(findings),
        severity_counts=_count(findings, lambda f: f.severity),
        license_status_counts=_count(findings, lambda f: f.license_status),
    )


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return _round1(sum(values) / len(values))


def _round1(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)


def _count(findings: list[Finding], key) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        k = key(f)
        out[k] = out.get(k, 0) + 1
    return out
