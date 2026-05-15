"""Reports — list of assessment runs + HTML preview per run.

Two variants are rendered from the same template:

  - **Internal Detailed** (consultant) — every finding, all blocks, technical
    detail, internal summaries.
  - **Customer Summary** (customer roles) — only findings whose
    `customer_visibility` ∈ {`customer_summary`, `customer_full`}; technical
    detail block rendered only for `customer_full`.

PDF rendering is a stretch goal — HTML is enough for Stage 9 (T-9010 / Chunk C).
The `Report` row pattern (immutable rendered snapshots) lands at MVP.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.db import _session_factory
from platform_core.findings.models import CustomerVisibility, Finding, Severity
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer, Engagement
from platform_core.web.session import Persona, get_user
from platform_core.web.templating import templates

router = APIRouter()


# Visibility filter per persona.
_CUSTOMER_VISIBLE: frozenset[str] = frozenset(
    {
        CustomerVisibility.CUSTOMER_SUMMARY.value,
        CustomerVisibility.CUSTOMER_FULL.value,
    }
)

_SEV_ORDER: dict[str, int] = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
    Severity.INFO.value: 4,
}


@router.get("/reports", response_class=HTMLResponse, response_model=None)
def list_reports(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    Session = _session_factory()
    with Session() as session:
        # For the slice, "reports" = one per assessment run. Group by run with
        # customer + engagement breadcrumbs.
        runs = (
            session.query(AssessmentRun)
            .order_by(AssessmentRun.created_at.desc())
            .all()
        )
        rows = []
        for run in runs:
            engagement = session.get(Engagement, run.engagement_id)
            customer = session.get(Customer, engagement.customer_id) if engagement else None
            findings = session.query(Finding).filter(Finding.assessment_run_id == run.id)
            if user.persona != Persona.CONSULTANT:
                findings = findings.filter(Finding.customer_visibility.in_(_CUSTOMER_VISIBLE))
            findings_list = findings.all()
            n_total = len(findings_list)
            n_critical = sum(1 for f in findings_list if f.severity == Severity.CRITICAL.value)
            n_high = sum(1 for f in findings_list if f.severity == Severity.HIGH.value)

            rows.append(
                {
                    "run_id": run.id,
                    "run_name": run.name,
                    "engagement_name": engagement.name if engagement else "(unknown)",
                    "customer_name": customer.name if customer else "(unknown)",
                    "customer_slug": customer.slug if customer else "",
                    "created_at": run.created_at,
                    "findings_total": n_total,
                    "findings_critical": n_critical,
                    "findings_high": n_high,
                    "variant": "internal" if user.persona == Persona.CONSULTANT else "customer",
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="reports_list.html",
        context={
            "page_title": "Reports",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "rows": rows,
        },
    )


@router.get("/reports/{run_id}", response_class=HTMLResponse, response_model=None)
def report_preview(request: Request, run_id: str) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    Session = _session_factory()
    with Session() as session:
        run = session.get(AssessmentRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Assessment run not found")
        engagement = session.get(Engagement, run.engagement_id)
        customer = session.get(Customer, engagement.customer_id) if engagement else None

        findings_q = session.query(Finding).filter(Finding.assessment_run_id == run.id)
        if user.persona != Persona.CONSULTANT:
            findings_q = findings_q.filter(Finding.customer_visibility.in_(_CUSTOMER_VISIBLE))
        findings = findings_q.all()
        # Sort: severity, then risk_score desc, then title.
        findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 99), -f.risk_score, f.title))

        # Snapshot for the template (so we don't touch a closed session).
        finding_rows = [_snapshot_finding(f, persona=user.persona) for f in findings]

        # Group by module for the per-module sections.
        by_module: dict[str, list[dict]] = {}
        for row in finding_rows:
            by_module.setdefault(row["module_id"], []).append(row)

        # Highlight the headline finding: the highest-severity correlation
        # finding if any, otherwise the highest-severity finding overall.
        headline = next(
            (r for r in finding_rows if r["module_id"] == "correlation" and r["severity"] == "critical"),
            finding_rows[0] if finding_rows else None,
        )

        # Severity distribution for the report's executive header.
        severity_counts = {sev.value: 0 for sev in Severity}
        for r in finding_rows:
            severity_counts[r["severity"]] = severity_counts.get(r["severity"], 0) + 1

        variant = "internal" if user.persona == Persona.CONSULTANT else "customer"

    return templates.TemplateResponse(
        request=request,
        name="report_preview.html",
        context={
            "page_title": f"Report · {customer.name if customer else 'Report'}",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "variant": variant,
            "customer": customer,
            "engagement": engagement,
            "run": run,
            "findings": finding_rows,
            "by_module": by_module,
            "headline": headline,
            "severity_counts": severity_counts,
        },
    )


def _snapshot_finding(f: Finding, *, persona: Persona) -> dict:
    """Serialise a Finding into a render-safe dict.

    Customer roles never see `summary_internal`; they only see
    `technical_detail` when `customer_visibility == customer_full`.
    """
    show_technical = (
        persona == Persona.CONSULTANT
        or f.customer_visibility == CustomerVisibility.CUSTOMER_FULL.value
    )
    return {
        "id": f.id,
        "title": f.title,
        "module_id": f.module_id,
        "category": f.category,
        "severity": f.severity,
        "risk_score": f.risk_score,
        "state": f.state,
        "customer_visibility": f.customer_visibility,
        "license_status": f.license_status,
        "summary_internal": f.summary_internal if persona == Persona.CONSULTANT else None,
        "summary_customer": f.summary_customer,
        "technical_detail": f.technical_detail if show_technical else None,
        "remediation": f.remediation,
        "payload": f.payload or {},
        "created_at": f.created_at,
    }
