"""Cross-module correlation orchestrator.

Per `MODULE_ARCHITECTURE.md` §11: correlation findings live in core (owner
`module_id="correlation"`), never in a single module. Modules contribute
their normalized data via Evidence + Identity rows; this orchestrator reads
the run's combined view and emits correlation findings.

Slice scope (Chunk C): one correlation rule — `CORR-BH-SF-001` —
"BloodHound critical path target lacks Silverfort coverage". Severity
bumped one rung above the contributing BH finding (HIGH → CRITICAL).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from platform_core.evidence.models import Evidence
from platform_core.findings.models import (
    CustomerVisibility,
    Finding,
    FindingState,
    LicenseStatus,
    Severity,
)
from platform_core.identity.models import Identity

CORRELATION_ENGINE_VERSION = "0.1.0"

# Severity bump: a path target lacking SF coverage is more dangerous than the
# BH-path alone, because Silverfort would have been the compensating control.
_BUMP: dict[str, str] = {
    Severity.LOW.value: Severity.MEDIUM.value,
    Severity.MEDIUM.value: Severity.HIGH.value,
    Severity.HIGH.value: Severity.CRITICAL.value,
    Severity.CRITICAL.value: Severity.CRITICAL.value,
    Severity.INFO.value: Severity.LOW.value,
}


@dataclass(frozen=True)
class CorrelationResult:
    correlations_created: int
    correlation_finding_ids: list[str]


def run_correlations(
    *,
    session: Session,
    assessment_run_id: str,
) -> CorrelationResult:
    """Run every correlation rule for the given run.

    For the slice, only CORR-BH-SF-001 is implemented. Adding rules is
    additive — register a new function below.
    """
    created: list[str] = []
    created.extend(_corr_bh_sf_001(session=session, assessment_run_id=assessment_run_id))
    return CorrelationResult(correlations_created=len(created), correlation_finding_ids=created)


def _corr_bh_sf_001(*, session: Session, assessment_run_id: str) -> list[str]:
    """CORR-BH-SF-001 — BloodHound path target lacks Silverfort coverage.

    For every BH finding whose path target SID is in the Silverfort
    uncovered-Tier-0 set for the same run, emit a correlation finding.
    Idempotent: if a correlation already exists for the same (run, BH source,
    BH target), it is replaced.
    """
    sf_evidence = (
        session.query(Evidence)
        .filter(
            Evidence.assessment_run_id == assessment_run_id,
            Evidence.module_id == "silverfort",
            Evidence.evidence_type == "silverfort-export",
        )
        .order_by(Evidence.created_at.desc())
        .first()
    )
    if sf_evidence is None:
        return []
    uncovered: set[str] = set(sf_evidence.payload.get("uncovered_tier0_sids", []))
    if not uncovered:
        return []

    bh_findings = (
        session.query(Finding)
        .filter(
            Finding.assessment_run_id == assessment_run_id,
            Finding.module_id == "bloodhound",
        )
        .all()
    )

    # Pre-fetch every Identity row referenced by any BH finding (target or step)
    # plus the uncovered set, so we can pretty-print SIDs as labels.
    sids_to_resolve: set[str] = set(uncovered)
    for bh_f in bh_findings:
        p = bh_f.payload or {}
        if p.get("target_sid"):
            sids_to_resolve.add(p["target_sid"])
        for step in p.get("steps", []):
            for k in ("from_sid", "to_sid"):
                if step.get(k):
                    sids_to_resolve.add(step[k])
    identity_by_sid: dict[str, Identity] = {
        i.sid: i
        for i in session.query(Identity).filter(Identity.sid.in_(sids_to_resolve)).all()
        if i.sid is not None
    }

    created: list[str] = []
    for bh in bh_findings:
        payload = bh.payload or {}
        target_sid = payload.get("target_sid")
        source_sid = payload.get("source_sid")
        steps = payload.get("steps", [])

        # Match when ANY identity on the path is in the SF coverage gap —
        # either the final target or an intermediate pivot. The demo headline
        # is the through-gap path (e.g., contractor.john → … → svc-backup →
        # Domain Admins), where the gap account is the bridge to Tier 0.
        path_sids = {target_sid, *[s.get("to_sid") for s in steps], *[s.get("from_sid") for s in steps]}
        path_sids.discard(None)
        path_sids.discard(source_sid)  # source is the attacker entry, not a "gap" pivot
        gap_sids_on_path = sorted(path_sids & uncovered)
        if not gap_sids_on_path:
            continue

        # Idempotency: delete any existing CORR finding for this (run, source, target).
        existing = (
            session.query(Finding)
            .filter(
                Finding.assessment_run_id == assessment_run_id,
                Finding.module_id == "correlation",
                Finding.category == "correlation.bh_sf_001",
            )
            .all()
        )
        for prev in existing:
            prev_payload = prev.payload or {}
            if (
                prev_payload.get("bh_source_sid") == source_sid
                and prev_payload.get("bh_target_sid") == target_sid
            ):
                session.delete(prev)

        target_identity = identity_by_sid.get(target_sid)
        target_label = target_identity.canonical_label if target_identity else target_sid
        gap_labels = [
            (identity_by_sid[s].canonical_label if s in identity_by_sid else s)
            for s in gap_sids_on_path
        ]

        bumped_severity = _BUMP.get(bh.severity, Severity.HIGH.value)
        bumped_score = min(100, int((bh.risk_score or 70) * 1.15))

        # Gather identity_refs from both contributors.
        identity_refs = list(
            dict.fromkeys(
                (bh.identity_refs or [])
                + ([target_identity.id] if target_identity else [])
                + [identity_by_sid[s].id for s in gap_sids_on_path if s in identity_by_sid]
            )
        )

        path_steps = steps
        path_summary = " → ".join(
            f"{s.get('from_label')} ─{s.get('edge_type')}→ {s.get('to_label')}" for s in path_steps
        )

        gap_phrase = ", ".join(f"`{lbl}`" for lbl in gap_labels)
        # Did the gap account also reach Tier 0 as the final target, OR is it
        # a pivot on the way to Tier 0?
        gap_is_target = target_sid in gap_sids_on_path
        if gap_is_target:
            title = (
                f"Critical correlation: BloodHound path reaches `{target_label}` "
                "AND that account is excluded from Silverfort coverage"
            )
        else:
            title = (
                f"Critical correlation: BloodHound path to Tier 0 (`{target_label}`) "
                f"pivots through {gap_phrase}, which is excluded from Silverfort coverage"
            )

        source_label = path_steps[0].get("from_label", "?") if path_steps else "?"
        summary_internal = (
            f"The attack path from `{source_label}` to `{target_label}` "
            f"{'lands on' if gap_is_target else 'pivots through'} {gap_phrase}, "
            "which is excluded from every enabled Silverfort policy. Silverfort would "
            "therefore not interrupt this attack at the gap account. "
            f"BH risk score: {bh.risk_score}; correlation risk: {bumped_score}. "
            f"Path summary: {path_summary}."
        )
        summary_customer = (
            "An attack path "
            f"{'reaches' if gap_is_target else 'passes through'} a privileged service "
            "account that is intentionally excluded from your Silverfort policies. The "
            "combination — an exploitable path AND a missing safety net at the bridge "
            "account — makes this the most urgent finding in this assessment."
        )
        technical_detail = (
            f"BloodHound finding id: {bh.id}\n"
            f"Silverfort evidence id: {sf_evidence.id}\n"
            f"Gap identity / identities on the path: {', '.join(gap_labels)}\n"
            f"Final path target: {target_label}\n\n"
            f"Path steps:\n"
            + "\n".join(
                f"  {i + 1}. {s.get('from_label')} ({s.get('from_kind')}) "
                f"─{s.get('edge_type')}→ {s.get('to_label')} ({s.get('to_kind')})"
                f"{'   ← SF GAP' if s.get('to_sid') in gap_sids_on_path else ''}"
                for i, s in enumerate(path_steps)
            )
        )
        remediation = (
            "Close the gap on one of the two sides:\n"
            "  • Silverfort side: remove the exclusion for this account, OR replace it "
            "with a `restrict_source` policy pinning the account to its expected source "
            "host(s).\n"
            "  • AD side: remove the abusable ACE that enables the attack path "
            "(see the linked BloodHound finding for the exact step).\n"
            "Both fixes together close the path and restore the compensating control."
        )

        corr = Finding(
            assessment_run_id=assessment_run_id,
            module_id="correlation",
            category="correlation.bh_sf_001",
            title=title,
            severity=bumped_severity,
            risk_score=bumped_score,
            license_status=LicenseStatus.LICENSED_ENABLED.value,
            state=FindingState.NEW.value,
            customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
            summary_internal=summary_internal,
            summary_customer=summary_customer,
            technical_detail=technical_detail,
            remediation=remediation,
            payload={
                "rule_id": "CORR-BH-SF-001",
                "template_id": "corr-bh-sf-001",
                "engine_version": CORRELATION_ENGINE_VERSION,
                "bh_finding_id": bh.id,
                "bh_source_sid": source_sid,
                "bh_target_sid": target_sid,
                "bh_path_length": payload.get("length"),
                "bh_steps": path_steps,
                "sf_evidence_id": sf_evidence.id,
                "target_label": target_label,
                "gap_sids": gap_sids_on_path,
                "gap_labels": gap_labels,
                "gap_is_target": gap_is_target,
            },
            identity_refs=identity_refs,
        )
        session.add(corr)
        session.flush()
        created.append(corr.id)
    return created
