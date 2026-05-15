"""Findings list + detail routes (Stage 9 slice).

Chunks:
  A — list / detail / role-aware visibility filter.
  B — state transitions, visibility changes, publish action, audit log writes
      (this file). Only the consultant persona may perform mutations.

Consultants see all findings; customer roles see only those marked
`customer_summary` or `customer_full` (per `SECURITY_AND_GDPR.md` §17).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from platform_core.audit.models import AuditEvent
from platform_core.db import _session_factory
from platform_core.findings.models import CustomerVisibility, Finding, FindingState
from platform_core.findings.workflow import (
    ALLOWED_TRANSITIONS,
    TransitionError,
    publish_finding,
    set_visibility,
    transition_state,
)
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer, Engagement
from platform_core.web.session import Persona, get_user
from platform_core.web.templating import templates

router = APIRouter()

_FLASH_KEY = "_flash"


def _set_flash(request: Request, kind: str, message: str) -> None:
    request.session[_FLASH_KEY] = {"kind": kind, "message": message}


def _pop_flash(request: Request) -> dict | None:
    return request.session.pop(_FLASH_KEY, None)


def _ensure_consultant(request: Request) -> Persona:
    """Returns the persona only if it's the consultant; otherwise raises 403."""
    user = get_user(request)
    if user is None or user.persona != Persona.CONSULTANT:
        raise HTTPException(status_code=403, detail="Consultant role required")
    return user.persona


def _engagement_ids_for(finding: Finding, session: Session) -> tuple[str | None, str | None, str | None]:
    run = session.get(AssessmentRun, finding.assessment_run_id)
    if run is None:
        return (None, None, finding.assessment_run_id)
    engagement = session.get(Engagement, run.engagement_id)
    if engagement is None:
        return (None, run.engagement_id, run.id)
    return (engagement.customer_id, engagement.id, run.id)


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
            "flash": _pop_flash(request),
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

    # Possible next state transitions for the action panel.
    allowed_states = sorted(ALLOWED_TRANSITIONS.get(snapshot["state"], frozenset()))

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
            "allowed_states": allowed_states,
            "flash": _pop_flash(request),
        },
    )


# ---------------------------------------------------------------------------
# Mutation endpoints — consultant only
# ---------------------------------------------------------------------------


@router.post("/findings/{finding_id}/state", response_model=None)
def change_state(
    request: Request,
    finding_id: str,
    new_state: str = Form(...),
) -> RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    _ensure_consultant(request)

    Session = _session_factory()
    with Session() as session, session.begin():
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise HTTPException(status_code=404, detail="Finding not found")

        customer_id, engagement_id, run_id = _engagement_ids_for(finding, session)
        try:
            transition_state(
                session=session,
                finding=finding,
                new_state=new_state,
                actor_role=user.persona.value,
                actor_label=user.display_name,
                customer_id=customer_id,
                engagement_id=engagement_id,
                run_id=run_id,
            )
            _set_flash(request, "ok", f"State updated to “{new_state}”.")
        except TransitionError as err:
            _set_flash(request, "error", err.message)

    return RedirectResponse(url=f"/findings/{finding_id}", status_code=303)


@router.post("/findings/{finding_id}/visibility", response_model=None)
def change_visibility(
    request: Request,
    finding_id: str,
    new_visibility: str = Form(...),
) -> RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    _ensure_consultant(request)

    Session = _session_factory()
    with Session() as session, session.begin():
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise HTTPException(status_code=404, detail="Finding not found")

        customer_id, engagement_id, run_id = _engagement_ids_for(finding, session)
        try:
            set_visibility(
                session=session,
                finding=finding,
                new_visibility=new_visibility,
                actor_role=user.persona.value,
                actor_label=user.display_name,
                customer_id=customer_id,
                engagement_id=engagement_id,
                run_id=run_id,
            )
            _set_flash(request, "ok", f"Visibility set to “{new_visibility}”.")
        except TransitionError as err:
            _set_flash(request, "error", err.message)

    return RedirectResponse(url=f"/findings/{finding_id}", status_code=303)


@router.post("/findings/{finding_id}/publish", response_model=None)
def publish(
    request: Request,
    finding_id: str,
    visibility: str = Form(CustomerVisibility.CUSTOMER_SUMMARY.value),
) -> RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    _ensure_consultant(request)

    Session = _session_factory()
    with Session() as session, session.begin():
        finding = session.get(Finding, finding_id)
        if finding is None:
            raise HTTPException(status_code=404, detail="Finding not found")

        # A finding must be triaged before it can be published (forward state
        # machine: new → triaged → published). Auto-triage if it's `new` so a
        # consultant can publish directly with one click.
        if finding.state == FindingState.NEW.value:
            customer_id, engagement_id, run_id = _engagement_ids_for(finding, session)
            transition_state(
                session=session,
                finding=finding,
                new_state=FindingState.TRIAGED.value,
                actor_role=user.persona.value,
                actor_label=user.display_name,
                customer_id=customer_id,
                engagement_id=engagement_id,
                run_id=run_id,
            )

        customer_id, engagement_id, run_id = _engagement_ids_for(finding, session)
        try:
            publish_finding(
                session=session,
                finding=finding,
                visibility=visibility,
                actor_role=user.persona.value,
                actor_label=user.display_name,
                customer_id=customer_id,
                engagement_id=engagement_id,
                run_id=run_id,
            )
            _set_flash(
                request,
                "ok",
                f"Published with visibility “{visibility}”. Customer roles can now see this finding.",
            )
        except TransitionError as err:
            _set_flash(request, "error", err.message)

    return RedirectResponse(url=f"/findings/{finding_id}", status_code=303)


# ---------------------------------------------------------------------------
# Audit log view (consultant only)
# ---------------------------------------------------------------------------


@router.get("/audit", response_class=HTMLResponse, response_model=None)
def audit_log(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if user.persona != Persona.CONSULTANT:
        raise HTTPException(status_code=403, detail="Audit log is consultant-only")

    Session = _session_factory()
    with Session() as session:
        events = (
            session.query(AuditEvent)
            .order_by(AuditEvent.created_at.desc())
            .limit(200)
            .all()
        )
        rows = [
            {
                "created_at": e.created_at,
                "actor_role": e.actor_role,
                "actor_label": e.actor_label,
                "event_type": e.event_type,
                "severity": e.severity,
                "target_kind": e.target_kind,
                "target_id": e.target_id,
                "payload": e.payload or {},
            }
            for e in events
        ]

    return templates.TemplateResponse(
        request=request,
        name="audit_log.html",
        context={
            "page_title": "Audit log",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "events": rows,
            "flash": _pop_flash(request),
        },
    )
