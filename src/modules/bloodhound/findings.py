"""Deterministic template-based Finding generator for BloodHound paths.

D-0005: explanations are template substitutions, not LLM output. The template
id is stored on the finding so any explanation can be reproduced.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from modules.bloodhound.analyzer import AttackPath
from platform_core.findings.models import (
    CustomerVisibility,
    Finding,
    FindingState,
    LicenseStatus,
    Severity,
)


@dataclass(frozen=True)
class FindingResult:
    finding_id: str
    title: str
    severity: str
    category: str


def severity_for(risk_score: int) -> Severity:
    """Bands per REVIEW_NOTES item 6 (defaults — confirm at Cycle 3)."""
    if risk_score >= 85:
        return Severity.CRITICAL
    if risk_score >= 65:
        return Severity.HIGH
    if risk_score >= 45:
        return Severity.MEDIUM
    if risk_score >= 25:
        return Severity.LOW
    return Severity.INFO


# Template-based explanations per path category. Each template uses
# {placeholder} substitution from the path payload. Template ids are stable
# so an explanation can be regenerated identically.
TEMPLATES: dict[str, dict] = {
    "acl_abuse": {
        "template_id": "bh-acl-abuse-to-tier0",
        "title": "ACL abuse path from {source_label} reaches Tier 0 ({target_label})",
        "summary_internal": (
            "BloodHound detected a {length}-hop attack path from "
            "`{source_label}` ({source_kind}) to the Tier 0 target "
            "`{target_label}` via an ACL abuse step. The path traverses "
            "{step_summary}. Risk score: {risk_score}/100."
        ),
        "summary_customer": (
            "A non-privileged account can reach the highest-privileged "
            "group in your environment by abusing permissions it should not "
            "have on a privileged service account. This represents a "
            "high-impact privilege escalation path that should be remediated "
            "promptly."
        ),
        "technical_detail": (
            "Path category: ACL abuse. "
            "The intermediate principal has explicit rights "
            "(e.g., GenericAll / WriteDacl) over a privileged target. "
            "Steps: {step_list}"
        ),
        "remediation": (
            "1. Remove the ACL grant that enables the abuse (look for the "
            "GenericAll/WriteDacl/WriteOwner/GenericWrite ACE in the path).\n"
            "2. Audit other ACEs on privileged service accounts using the same "
            "pattern.\n"
            "3. Consider moving the privileged service account to a "
            "protected OU and applying AdminSDHolder-style ACL hygiene.\n"
            "4. Validate with a follow-up SharpHound collection that the "
            "path no longer exists."
        ),
    },
    "group_nesting_priv_esc": {
        "template_id": "bh-group-nesting-to-tier0",
        "title": "Group nesting reaches Tier 0 from {source_label}",
        "summary_internal": (
            "BloodHound detected a {length}-hop group-nesting path from "
            "`{source_label}` to Tier 0 (`{target_label}`). Steps: {step_summary}."
        ),
        "summary_customer": (
            "An account inherits privileged access through nested group "
            "memberships, ending up effectively administering the domain."
        ),
        "technical_detail": "Steps: {step_list}",
        "remediation": (
            "Audit the nested group chain and remove unnecessary nestings; "
            "do not nest privileged groups inside operational groups."
        ),
    },
    "delegation": {
        "template_id": "bh-delegation-to-tier0",
        "title": "Delegation path reaches Tier 0 from {source_label}",
        "summary_internal": (
            "BloodHound detected a {length}-hop delegation path from "
            "`{source_label}` to Tier 0 (`{target_label}`). Steps: {step_summary}."
        ),
        "summary_customer": (
            "Delegation settings allow an account to act on behalf of a "
            "privileged identity. This shortcut to Tier 0 should be removed."
        ),
        "technical_detail": "Steps: {step_list}",
        "remediation": (
            "Restrict the delegation scope; prefer Resource-Based "
            "Constrained Delegation; never allow unconstrained delegation "
            "on accounts that can reach Tier 0."
        ),
    },
    "dcsync": {
        "template_id": "bh-dcsync-to-tier0",
        "title": "DCSync capability gives {source_label} Tier 0 control",
        "summary_internal": (
            "BloodHound detected DCSync rights granted to `{source_label}`, "
            "giving it the ability to replicate secrets from Active Directory."
        ),
        "summary_customer": (
            "An account has the ability to replicate authentication secrets "
            "from the domain controller — equivalent to Domain Admin."
        ),
        "technical_detail": "Steps: {step_list}",
        "remediation": (
            "Remove DS-Replication-Get-Changes-All / DS-Replication-Get-Changes "
            "rights from non-DC, non-Tier-0 principals."
        ),
    },
    "privilege_escalation": {
        "template_id": "bh-privilege-escalation-to-tier0",
        "title": "Privilege escalation path reaches Tier 0 from {source_label}",
        "summary_internal": (
            "BloodHound detected a {length}-hop privilege escalation path "
            "from `{source_label}` to Tier 0 (`{target_label}`). Steps: {step_summary}."
        ),
        "summary_customer": (
            "An attack path exists that allows escalation to the highest "
            "privileges in your domain."
        ),
        "technical_detail": "Steps: {step_list}",
        "remediation": (
            "Audit and remove the highest-severity step in the chain; the "
            "specific edge type indicates the underlying misconfiguration."
        ),
    },
}


def _render(template: str, *, path: AttackPath) -> str:
    first = path.steps[0]
    last = path.steps[-1]
    step_summary = " → ".join(
        f"{s.from_label} ─{s.edge_type}→ {s.to_label}" for s in path.steps
    )
    step_list = "\n".join(
        f"  {i + 1}. {s.from_label} ({s.from_kind}) ─{s.edge_type}→ {s.to_label} ({s.to_kind})"
        for i, s in enumerate(path.steps)
    )
    return template.format(
        source_label=first.from_label,
        source_kind=first.from_kind,
        target_label=last.to_label,
        target_kind=last.to_kind,
        length=path.length,
        risk_score=path.risk_score,
        step_summary=step_summary,
        step_list=step_list,
    )


def generate_finding(
    *,
    path: AttackPath,
    session: Session,
    assessment_run_id: str,
    identity_refs: list[str],
) -> FindingResult:
    """Persist one Finding for the given path. Idempotent on (run, source, target)."""
    tmpl = TEMPLATES.get(path.category, TEMPLATES["privilege_escalation"])
    severity = severity_for(path.risk_score)

    # Idempotency: clear any prior finding for this run+source+target.
    existing = (
        session.query(Finding)
        .filter(
            Finding.assessment_run_id == assessment_run_id,
            Finding.module_id == "bloodhound",
            Finding.category == f"bh.{path.category}",
        )
        .all()
    )
    for f in existing:
        payload_source = f.payload.get("source_sid") if isinstance(f.payload, dict) else None
        payload_target = f.payload.get("target_sid") if isinstance(f.payload, dict) else None
        if payload_source == path.source_sid and payload_target == path.target_sid:
            session.delete(f)

    payload = path.as_dict() | {
        "template_id": tmpl["template_id"],
        "analyzer_version": "0.1.0",
    }

    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="bloodhound",
        category=f"bh.{path.category}",
        title=tmpl["title"].format(
            source_label=path.source_label,
            target_label=path.target_label,
        ),
        severity=severity.value,
        risk_score=path.risk_score,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=_render(tmpl["summary_internal"], path=path),
        summary_customer=_render(tmpl["summary_customer"], path=path),
        technical_detail=_render(tmpl["technical_detail"], path=path),
        remediation=tmpl["remediation"],
        payload=payload,
        identity_refs=identity_refs,
    )
    session.add(finding)
    session.flush()

    return FindingResult(
        finding_id=finding.id,
        title=finding.title,
        severity=finding.severity,
        category=finding.category,
    )
