"""Findings list + detail routes (Stage 9 slice).

Consultants see all findings; customer roles see only those marked
`customer_summary` or `customer_full` (per `SECURITY_AND_GDPR.md` §17).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from platform_core.db import _session_factory
from platform_core.findings.models import CustomerVisibility, Finding
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer, Engagement
from platform_core.web.session import Persona, get_user
from platform_core.web.templating import templates

router = APIRouter()


def _visible_findings_query(session: Session, persona: Persona):
    q = session.query(Finding).order_by(Finding.risk_score.desc(), Finding.created_at.desc())
    if persona != Persona.CONSULTANT:
        q = q.filter(
            Finding.customer_visibility.in_(
                [
                    CustomerVisibility.CUSTOMER_SUMMARY.value,
                    CustomerVisibility.CUSTOMER_FULL.value,
                ]
            )
        )
    return q


@router.get("/findings", response_class=HTMLResponse, response_model=None)
def list_findings(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    Session = _session_factory()
    with Session() as session:
        findings = _visible_findings_query(session, user.persona).all()
        # Snapshot the data we need now so the template doesn't touch a closed session.
        rows = [
            {
                "id": f.id,
                "title": f.title,
                "module_id": f.module_id,
                "category": f.category,
                "severity": f.severity,
                "risk_score": f.risk_score,
                "state": f.state,
                "customer_visibility": f.customer_visibility,
                "license_status": f.license_status,
                "summary_internal": f.summary_internal,
                "summary_customer": f.summary_customer,
                "created_at": f.created_at,
            }
            for f in findings
        ]
        # Customer-or-engagement summary for the page header.
        customer = session.query(Customer).order_by(Customer.created_at.asc()).first()
        engagement = (
            session.query(Engagement).order_by(Engagement.created_at.desc()).first()
            if customer
            else None
        )
        run = (
            session.query(AssessmentRun).order_by(AssessmentRun.created_at.desc()).first()
            if engagement
            else None
        )

    return templates.TemplateResponse(
        request=request,
        name="findings_list.html",
        context={
            "page_title": "Findings",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "findings": rows,
            "customer": customer,
            "engagement": engagement,
            "run": run,
        },
    )


@router.get("/findings/{finding_id}", response_class=HTMLResponse, response_model=None)
def finding_detail(request: Request, finding_id: str) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    Session = _session_factory()
    with Session() as session:
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise HTTPException(status_code=404, detail="Finding not found")

        # Customer-visibility gate for non-consultant roles.
        if user.persona != Persona.CONSULTANT and finding.customer_visibility == (
            CustomerVisibility.INTERNAL_ONLY.value
        ):
            raise HTTPException(status_code=404, detail="Finding not visible to this role")

        snapshot = {
            "id": finding.id,
            "title": finding.title,
            "module_id": finding.module_id,
            "category": finding.category,
            "severity": finding.severity,
            "risk_score": finding.risk_score,
            "state": finding.state,
            "customer_visibility": finding.customer_visibility,
            "license_status": finding.license_status,
            "summary_internal": finding.summary_internal,
            "summary_customer": finding.summary_customer,
            "technical_detail": finding.technical_detail,
            "remediation": finding.remediation,
            "payload": finding.payload or {},
            "identity_refs": finding.identity_refs or [],
            "created_at": finding.created_at,
        }

    # Per-role rendering: customer roles see the customer-framed summary
    # only; technical detail is rendered only for customer_full.
    show_technical = (
        user.persona == Persona.CONSULTANT
        or finding.customer_visibility == CustomerVisibility.CUSTOMER_FULL.value
    )

    return templates.TemplateResponse(
        request=request,
        name="finding_detail.html",
        context={
            "page_title": snapshot["title"],
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "finding": snapshot,
            "show_technical": show_technical,
        },
    )
