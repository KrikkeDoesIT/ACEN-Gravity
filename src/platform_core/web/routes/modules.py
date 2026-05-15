"""Module pages — per-module dashboards built on archetype templates.

Per D-0018 / `UI_DESIGN_DIRECTION.md` §4.3, each of the four POC modules
has its own page archetype:

  - AD          → Posture (status cards + control coverage + priority findings)
  - BloodHound  → Attack-path (ranked paths + PathStepList drawer)
  - Silverfort  → Coverage (CoverageMatrix + coverage-gap priority list)
  - Entra       → License-aware tenant config (license-aware status cards +
                  findings + Opportunity card)

The shared frame (header, side-nav, finding drawer, publish modal) is
identical across all four — this module assembles a per-module template
on top of that frame.

Customer roles only see modules where they have visible findings (a
practical scope: avoid empty module pages for customer roles in POC V1).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.db import _session_factory
from platform_core.evidence.models import Evidence
from platform_core.findings.models import CustomerVisibility, Finding, Severity
from platform_core.identity.models import Identity
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer
from platform_core.module_registry import get_module
from platform_core.web.session import Persona, get_user
from platform_core.web.templating import templates

router = APIRouter()


# Module → template + archetype name. Adding a module is additive.
_ARCHETYPE_TEMPLATE: dict[str, tuple[str, str]] = {
    "ad":         ("module_ad.html",         "posture"),
    "bloodhound": ("module_bloodhound.html", "attack_path"),
    "silverfort": ("module_silverfort.html", "coverage"),
    "entra":      ("module_entra.html",      "license_aware"),
}

_CUSTOMER_VISIBLE: frozenset[str] = frozenset(
    {
        CustomerVisibility.CUSTOMER_SUMMARY.value,
        CustomerVisibility.CUSTOMER_FULL.value,
    }
)

_SEV_ORDER = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
    Severity.INFO.value: 4,
}


@router.get("/modules/{module_id}", response_class=HTMLResponse, response_model=None)
def module_page(request: Request, module_id: str) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    module = get_module(module_id)
    if module is None or module_id not in _ARCHETYPE_TEMPLATE:
        raise HTTPException(status_code=404, detail="Module not found")

    template_name, archetype = _ARCHETYPE_TEMPLATE[module_id]

    Session = _session_factory()
    with Session() as session:
        run = session.query(AssessmentRun).order_by(AssessmentRun.created_at.desc()).first()
        customer = (
            session.query(Customer).order_by(Customer.created_at.desc()).first() if run else None
        )

        if run is None:
            return templates.TemplateResponse(
                request=request,
                name=template_name,
                context={
                    "page_title": module.title,
                    "user": user,
                    "persona": user.persona,
                    "persona_label": user.role_label,
                    "module": module,
                    "archetype": archetype,
                    "customer": None,
                    "run": None,
                    "findings": [],
                    "severity_counts": dict.fromkeys((s.value for s in Severity), 0),
                    "evidence": [],
                    "page_data": {},
                },
            )

        findings_q = session.query(Finding).filter(
            Finding.assessment_run_id == run.id,
            Finding.module_id == module_id,
        )
        if user.persona != Persona.CONSULTANT:
            findings_q = findings_q.filter(Finding.customer_visibility.in_(_CUSTOMER_VISIBLE))
        findings = findings_q.all()
        findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 99), -f.risk_score))

        # Module's evidence for this run (used by per-archetype renderers).
        evidence_rows = (
            session.query(Evidence)
            .filter(Evidence.assessment_run_id == run.id, Evidence.module_id == module_id)
            .order_by(Evidence.created_at.desc())
            .all()
        )

        finding_rows = [_snapshot_finding(f) for f in findings]
        severity_counts = _severity_counts(finding_rows)

        page_data = _build_page_data(
            archetype=archetype,
            module_id=module_id,
            session=session,
            run_id=run.id,
            customer_id=customer.id if customer else None,
            finding_rows=finding_rows,
            evidence_rows=evidence_rows,
        )

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "page_title": module.title,
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "module": module,
            "archetype": archetype,
            "customer": customer,
            "run": run,
            "findings": finding_rows,
            "severity_counts": severity_counts,
            "evidence": evidence_rows,
            "page_data": page_data,
        },
    )


def _snapshot_finding(f: Finding) -> dict:
    return {
        "id": f.id,
        "title": f.title,
        "module_id": f.module_id,
        "category": f.category,
        "severity": f.severity,
        "risk_score": f.risk_score,
        "state": f.state,
        "customer_visibility": f.customer_visibility,
        "summary_internal": f.summary_internal,
        "summary_customer": f.summary_customer,
        "payload": f.payload or {},
    }


def _severity_counts(finding_rows: Iterable[dict]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for r in finding_rows:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1
    return counts


def _build_page_data(
    *,
    archetype: str,
    module_id: str,
    session,
    run_id: str,
    customer_id: str | None,
    finding_rows: list[dict],
    evidence_rows: list[Evidence],
) -> dict:
    """Build the archetype-specific extras the template needs."""
    if archetype == "attack_path":
        return _build_attack_path_data(finding_rows)
    if archetype == "coverage":
        return _build_coverage_data(session=session, customer_id=customer_id, evidence_rows=evidence_rows)
    if archetype == "posture":
        return _build_posture_data(finding_rows)
    if archetype == "license_aware":
        return _build_license_aware_data(finding_rows)
    return {}


def _build_attack_path_data(finding_rows: list[dict]) -> dict:
    """BloodHound — ranked paths + category distribution."""
    paths = [
        {
            "finding_id": f["id"],
            "title": f["title"],
            "severity": f["severity"],
            "risk_score": f["risk_score"],
            "category": f["payload"].get("category", f["category"]),
            "length": f["payload"].get("length", 0),
            "source_label": (f["payload"].get("steps") or [{}])[0].get("from_label", "?"),
            "target_label": (f["payload"].get("steps") or [{}])[-1].get("to_label", "?"),
            "steps": f["payload"].get("steps", []),
        }
        for f in finding_rows
    ]
    category_counts = Counter(p["category"] for p in paths)
    return {
        "paths": paths,
        "category_counts": dict(category_counts),
        "top_category": category_counts.most_common(1)[0][0] if category_counts else None,
    }


def _build_coverage_data(
    *, session, customer_id: str | None, evidence_rows: list[Evidence]
) -> dict:
    """Silverfort — assemble the policy × target coverage matrix from the
    most recent SF evidence row plus the customer's privileged Identity rows."""
    if customer_id is None or not evidence_rows:
        return {"policies": [], "targets": [], "matrix": [], "connector_status": "pending"}

    sf_ev = evidence_rows[0]  # most recent first
    payload = sf_ev.payload or {}
    policies = payload.get("policies", [])
    covered_sids: set[str] = set(payload.get("covered_sids", []))
    uncovered_sids: set[str] = set(payload.get("uncovered_tier0_sids", []))

    # Targets = Tier 0 user/service-account identities.
    target_identities = (
        session.query(Identity)
        .filter(
            Identity.customer_id == customer_id,
            Identity.is_tier0.is_(True),
            Identity.canonical_kind.in_(("user", "service_account")),
        )
        .all()
    )

    targets = [
        {"sid": t.sid, "label": t.canonical_label, "kind": t.canonical_kind}
        for t in target_identities
    ]

    # For each (target, policy) cell, decide a status: covered / excluded / na.
    matrix = []
    for t in targets:
        row = {"target": t, "cells": []}
        for p in policies:
            if not p.get("enabled"):
                row["cells"].append({"policy_id": p["id"], "status": "na"})
                continue
            excluded = t["sid"] in (p.get("excluded_user_sids") or [])
            in_targets = t["sid"] in (p.get("target_user_sids") or [])
            in_groups = any(
                g.rsplit("-", 1)[-1] in {"512", "519", "518", "516", "517"}
                for g in (p.get("target_group_sids") or [])
            )
            if excluded:
                status = "excluded"
            elif in_targets or in_groups:
                status = "covered"
            else:
                status = "na"
            row["cells"].append({"policy_id": p["id"], "status": status})
        row["overall"] = "uncovered" if t["sid"] in uncovered_sids else "covered" if t["sid"] in covered_sids else "na"
        matrix.append(row)

    return {
        "policies": policies,
        "targets": targets,
        "matrix": matrix,
        "covered_count": len(covered_sids),
        "uncovered_count": len(uncovered_sids),
        # Connector status — always "pending" in POC per D-0006 (manual mode).
        "connector_status": "pending",
        "tenant_name": payload.get("tenant", {}).get("name") or "Silverfort",
    }


def _build_posture_data(finding_rows: list[dict]) -> dict:
    """AD — group findings by AD-control category (privileged / kerberos / ...).
    For the slice we only have one AD finding (SF-AD-001 is in the SF module),
    so this is mostly a placeholder for the full posture archetype.
    """
    category_groups: dict[str, list[dict]] = {}
    for f in finding_rows:
        cat = f["category"].split(".")[0] if "." in f["category"] else f["category"]
        category_groups.setdefault(cat, []).append(f)
    return {"by_category": category_groups}


def _build_license_aware_data(finding_rows: list[dict]) -> dict:
    """Entra — placeholder until the Entra parser lands (Chunk E)."""
    return {"capabilities": [], "licensed_sample": []}
