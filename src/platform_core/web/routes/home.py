"""Home / overview shell.

Stage 9 Chunk F: real scores + module breakdown + headline finding from the
most recent assessment run. Customer roles see the same headline numbers but
the published-finding teaser is filtered to customer-visible findings only.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.db import _session_factory
from platform_core.findings.models import CustomerVisibility, Finding, Severity
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer
from platform_core.module_registry import list_modules
from platform_core.scoring import compute_scores
from platform_core.web.session import Persona, get_user
from platform_core.web.templating import templates

router = APIRouter()


_CUSTOMER_VISIBLE: frozenset[str] = frozenset(
    {
        CustomerVisibility.CUSTOMER_SUMMARY.value,
        CustomerVisibility.CUSTOMER_FULL.value,
    }
)

_SEV_RANK = {
    Severity.CRITICAL.value: 0,
    Severity.HIGH.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.LOW.value: 3,
    Severity.INFO.value: 4,
}


@router.get("/", response_class=HTMLResponse, response_model=None)
def home(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    Session = _session_factory()
    with Session() as session:
        run = (
            session.query(AssessmentRun)
            .order_by(AssessmentRun.created_at.desc())
            .first()
        )
        customer = (
            session.query(Customer).order_by(Customer.created_at.desc()).first() if run else None
        )

        if run is None:
            # Empty platform — keep the original Stage 8.1 empty state.
            return templates.TemplateResponse(
                request=request,
                name="home.html",
                context={
                    "page_title": "Overview",
                    "user": user,
                    "persona": user.persona,
                    "persona_label": user.role_label,
                    "modules": list_modules(),
                    "customer": None,
                    "scores": None,
                    "module_strip": [],
                    "headline": None,
                    "totals": None,
                },
            )

        scores = compute_scores(session, run.id)

        # Module strip — one row per registered module, joined with score
        # breakdown if the module produced any findings in this run.
        module_strip = []
        for module in list_modules():
            ms = scores.for_module(module.id)
            module_strip.append(
                {
                    "module": module,
                    "scores": ms,
                    "status": _module_status(ms),
                }
            )

        # Headline finding — most severe / highest risk_score that the user
        # is allowed to see.
        headline_q = session.query(Finding).filter(Finding.assessment_run_id == run.id)
        if user.persona != Persona.CONSULTANT:
            headline_q = headline_q.filter(Finding.customer_visibility.in_(_CUSTOMER_VISIBLE))
        candidate_findings = headline_q.all()
        candidate_findings.sort(
            key=lambda f: (_SEV_RANK.get(f.severity, 99), -f.risk_score)
        )
        headline = candidate_findings[0] if candidate_findings else None

        totals = {
            "findings": sum(scores.severity_counts.values()),
            "by_severity": scores.severity_counts,
            "correlations": scores.correlation_count,
            "critical_correlations": scores.critical_correlation_count,
        }

        headline_snapshot = _snapshot_headline(headline) if headline is not None else None

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "page_title": "Overview",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
            "modules": list_modules(),
            "customer": customer,
            "scores": scores,
            "module_strip": module_strip,
            "headline": headline_snapshot,
            "totals": totals,
        },
    )


def _module_status(ms) -> str:
    """Status label for a module strip card."""
    if ms is None or not ms.has_data:
        return "pending"
    if ms.current is None:
        return "evaluating"
    if any(ms.severity_counts.get(s, 0) > 0 for s in ("critical", "high")):
        return "attention"
    if ms.severity_counts.get("medium", 0) > 0:
        return "watch"
    return "ok"


def _snapshot_headline(f: Finding) -> dict:
    return {
        "id": f.id,
        "title": f.title,
        "module_id": f.module_id,
        "category": f.category,
        "severity": f.severity,
        "risk_score": f.risk_score,
        "license_status": f.license_status,
        "summary_internal": f.summary_internal,
        "summary_customer": f.summary_customer,
        "state": f.state,
        "customer_visibility": f.customer_visibility,
    }
