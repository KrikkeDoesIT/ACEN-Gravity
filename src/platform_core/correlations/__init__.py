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

    Rule registry (additive — add a function and call it here):
      - CORR-BH-SF-001 (Chunk C) — BH path target / pivot in SF coverage gap.
      - CORR-AD-ENTRA-001 (Chunk E) — AD privileged identity ↔ Entra Tier 0
        role assignee (hybrid admin bridge).
      - CORR-BH-ENTRA-001 (Chunk E) — BH critical path target is a hybrid
        admin (compounds BH + Entra context).
    """
    created: list[str] = []
    created.extend(_corr_bh_sf_001(session=session, assessment_run_id=assessment_run_id))
    created.extend(_corr_ad_entra_001(session=session, assessment_run_id=assessment_run_id))
    created.extend(_corr_bh_entra_001(session=session, assessment_run_id=assessment_run_id))
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


# --- CORR-AD-ENTRA-001 --------------------------------------------------------


def _corr_ad_entra_001(*, session: Session, assessment_run_id: str) -> list[str]:
    """CORR-AD-ENTRA-001 — AD privileged identity is also an Entra Tier 0
    role assignee. The "hybrid admin bridge" — compromise on either side
    compromises both.

    Reads the Entra evidence row's `hybrid_admin_records` (computed by the
    Entra parser) and emits ONE correlation finding per AD principal whose
    AD `is_tier0` is true. Idempotent on (run, ad_identity_id).
    """
    entra_evidence = (
        session.query(Evidence)
        .filter(
            Evidence.assessment_run_id == assessment_run_id,
            Evidence.module_id == "entra",
            Evidence.evidence_type == "entra-graph-bundle",
        )
        .order_by(Evidence.created_at.desc())
        .first()
    )
    if entra_evidence is None:
        return []
    hybrid_records = (entra_evidence.payload or {}).get("hybrid_admin_records", [])
    if not hybrid_records:
        return []

    created: list[str] = []
    for record in hybrid_records:
        if not record.get("is_ad_tier0"):
            continue

        # Idempotency.
        existing = (
            session.query(Finding)
            .filter(
                Finding.assessment_run_id == assessment_run_id,
                Finding.module_id == "correlation",
                Finding.category == "correlation.ad_entra_001",
            )
            .all()
        )
        for prev in existing:
            prev_payload = prev.payload or {}
            if prev_payload.get("ad_identity_id") == record.get("ad_identity_id"):
                session.delete(prev)

        identity_refs = [record["ad_identity_id"]] if record.get("ad_identity_id") else []

        title = (
            f"Hybrid admin bridge: AD Tier 0 `{record['ad_sam_account_name']}` "
            f"is also Entra `{record['entra_display_name'] or record['entra_upn']}`"
        )
        summary_internal = (
            f"The AD account `{record['ad_sam_account_name']}` (SID {record['ad_sid']}) is "
            f"a Domain Admin (Tier 0) AND synced to Entra (`{record['entra_upn']}`) where it "
            "holds Tier 0 directory-role assignments. The accounts share a credential lifecycle. "
            "Compromise of the AD account compromises the cloud admin role and vice versa."
        )
        summary_customer = (
            "A single identity is highly privileged in both Active Directory and Microsoft "
            "Entra. Anyone who compromises either side automatically controls the other. "
            "This 'hybrid admin bridge' is a top-tier risk in hybrid identity environments."
        )
        technical_detail = (
            f"AD identity id:        {record['ad_identity_id']}\n"
            f"AD sAMAccountName:     {record['ad_sam_account_name']}\n"
            f"AD SID:                {record['ad_sid']}\n"
            f"Entra principal id:    {record['entra_principal_id']}\n"
            f"Entra UPN:             {record['entra_upn']}\n"
            f"Entra display name:    {record['entra_display_name']}\n"
            f"Tier 0 (AD):           {record['is_ad_tier0']}"
        )
        remediation = (
            "1. Where business permits, move the cloud-side privileged role to a "
            "cloud-only admin account (no on-prem counterpart).\n"
            "2. For unavoidable hybrid admins, apply Tier 0 hardening on BOTH sides: "
            "PAW + restricted logon + strong password on the AD side; PIM-eligible role "
            "assignment + phishing-resistant MFA on the Entra side.\n"
            "3. Exclude admin accounts from Entra Connect sync where the role can be "
            "fulfilled by a cloud-only identity."
        )

        finding = Finding(
            assessment_run_id=assessment_run_id,
            module_id="correlation",
            category="correlation.ad_entra_001",
            title=title,
            severity=Severity.HIGH.value,
            risk_score=78,
            license_status=LicenseStatus.LICENSED_ENABLED.value,
            state=FindingState.NEW.value,
            customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
            summary_internal=summary_internal,
            summary_customer=summary_customer,
            technical_detail=technical_detail,
            remediation=remediation,
            payload={
                "rule_id": "CORR-AD-ENTRA-001",
                "template_id": "corr-ad-entra-001",
                "engine_version": CORRELATION_ENGINE_VERSION,
                "ad_identity_id": record["ad_identity_id"],
                "ad_sid": record["ad_sid"],
                "ad_sam_account_name": record["ad_sam_account_name"],
                "entra_principal_id": record["entra_principal_id"],
                "entra_upn": record["entra_upn"],
                "entra_display_name": record["entra_display_name"],
            },
            identity_refs=identity_refs,
        )
        session.add(finding)
        session.flush()
        created.append(finding.id)

    return created


# --- CORR-BH-ENTRA-001 --------------------------------------------------------


def _corr_bh_entra_001(*, session: Session, assessment_run_id: str) -> list[str]:
    """CORR-BH-ENTRA-001 — BloodHound critical path target is a hybrid admin.

    For each BH finding whose target SID matches an AD identity that is also
    an Entra Tier 0 role assignee, emit a correlation finding. This is the
    full-stack story: BH path lands on the bridge, and the bridge is also a
    cloud admin, so the blast radius spans both planes.
    """
    entra_evidence = (
        session.query(Evidence)
        .filter(
            Evidence.assessment_run_id == assessment_run_id,
            Evidence.module_id == "entra",
            Evidence.evidence_type == "entra-graph-bundle",
        )
        .order_by(Evidence.created_at.desc())
        .first()
    )
    if entra_evidence is None:
        return []
    hybrid_records = (entra_evidence.payload or {}).get("hybrid_admin_records", [])
    hybrid_by_sid = {r["ad_sid"]: r for r in hybrid_records if r.get("ad_sid")}
    if not hybrid_by_sid:
        return []

    bh_findings = (
        session.query(Finding)
        .filter(
            Finding.assessment_run_id == assessment_run_id,
            Finding.module_id == "bloodhound",
        )
        .all()
    )

    created: list[str] = []
    for bh in bh_findings:
        payload = bh.payload or {}
        target_sid = payload.get("target_sid")
        if not target_sid or target_sid not in hybrid_by_sid:
            continue
        record = hybrid_by_sid[target_sid]
        source_sid = payload.get("source_sid")
        steps = payload.get("steps", [])

        # Idempotency.
        existing = (
            session.query(Finding)
            .filter(
                Finding.assessment_run_id == assessment_run_id,
                Finding.module_id == "correlation",
                Finding.category == "correlation.bh_entra_001",
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

        bumped = (
            Severity.CRITICAL.value
            if bh.severity in {Severity.HIGH.value, Severity.MEDIUM.value}
            else bh.severity
        )
        bumped_risk = min(100, int((bh.risk_score or 70) * 1.2))

        identity_refs = list(
            dict.fromkeys(
                (bh.identity_refs or [])
                + ([record["ad_identity_id"]] if record.get("ad_identity_id") else [])
            )
        )

        path_summary = " -> ".join(
            f"{s.get('from_label')} -{s.get('edge_type')}-> {s.get('to_label')}" for s in steps
        )

        title = (
            f"Critical: BloodHound path reaches hybrid admin `{record['ad_sam_account_name']}` "
            f"(also Entra `{record['entra_upn']}`)"
        )
        summary_internal = (
            f"BloodHound found a {len(steps)}-hop path ending at `{record['ad_sam_account_name']}`, "
            "which is BOTH an AD Tier 0 account AND an Entra Tier 0 role assignee "
            f"(`{record['entra_upn']}`). Compromise of this account compromises both on-prem AD and "
            f"the Entra tenant. Path: {path_summary}."
        )
        summary_customer = (
            "An on-prem attack path reaches an account that is highly privileged in both your "
            "on-premises Active Directory AND your Microsoft Entra tenant. The blast radius of "
            "this attack spans both environments."
        )
        technical_detail = (
            f"BloodHound finding id: {bh.id}\n"
            f"AD identity:           {record['ad_sam_account_name']} (SID {record['ad_sid']})\n"
            f"Entra UPN:             {record['entra_upn']}\n"
            f"Entra principal id:    {record['entra_principal_id']}\n\n"
            "Path steps:\n"
            + "\n".join(
                f"  {i + 1}. {s.get('from_label')} ({s.get('from_kind')}) "
                f"-{s.get('edge_type')}-> {s.get('to_label')} ({s.get('to_kind')})"
                for i, s in enumerate(steps)
            )
        )
        remediation = (
            "Address both ends of the bridge:\n"
            "  - AD side: remove the abusable step in the BloodHound path "
            "(see the linked BH finding).\n"
            "  - Entra side: move the Tier 0 role from the hybrid account to a "
            "cloud-only privileged identity, or apply PIM-eligible assignment with "
            "phishing-resistant MFA so the cloud role cannot be silently abused even if "
            "the AD account is compromised."
        )

        corr = Finding(
            assessment_run_id=assessment_run_id,
            module_id="correlation",
            category="correlation.bh_entra_001",
            title=title,
            severity=bumped,
            risk_score=bumped_risk,
            license_status=LicenseStatus.LICENSED_ENABLED.value,
            state=FindingState.NEW.value,
            customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
            summary_internal=summary_internal,
            summary_customer=summary_customer,
            technical_detail=technical_detail,
            remediation=remediation,
            payload={
                "rule_id": "CORR-BH-ENTRA-001",
                "template_id": "corr-bh-entra-001",
                "engine_version": CORRELATION_ENGINE_VERSION,
                "bh_finding_id": bh.id,
                "bh_source_sid": source_sid,
                "bh_target_sid": target_sid,
                "bh_steps": steps,
                "ad_identity_id": record["ad_identity_id"],
                "ad_sam_account_name": record["ad_sam_account_name"],
                "entra_principal_id": record["entra_principal_id"],
                "entra_upn": record["entra_upn"],
            },
            identity_refs=identity_refs,
        )
        session.add(corr)
        session.flush()
        created.append(corr.id)

    return created
