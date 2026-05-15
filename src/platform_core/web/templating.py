"""Jinja2 template environment shared across routes."""

from __future__ import annotations

from fastapi.templating import Jinja2Templates

from platform_core.module_registry import list_modules
from platform_core.settings import get_settings
from platform_core.web.session import PERSONA_LABELS, USERS, Persona, is_nav_visible


def _current_context() -> dict:
    """Look up the latest Customer / Engagement / Run for the header strip.

    POC: there is only one customer / engagement / run per database, so
    "latest" == "selected". When MVP introduces customer/engagement
    pickers, this helper is replaced by a session-stored selection.

    Returns a dict with `customer`, `engagement`, `run` (any of which
    may be None when the database is empty).
    """
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun, Customer, Engagement

    Session = _session_factory()
    with Session() as session:
        customer = session.query(Customer).order_by(Customer.created_at.desc()).first()
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
        return {
            "customer": _snapshot(customer, ("id", "name", "slug")),
            "engagement": _snapshot(engagement, ("id", "name", "slug")),
            "run": _snapshot(run, ("id", "name")),
        }


def _snapshot(obj, fields: tuple[str, ...]) -> dict | None:
    """Detach a small dict from a model instance so the template can render
    safely after the session closes."""
    if obj is None:
        return None
    return {field: getattr(obj, field) for field in fields}


def _build_templates() -> Jinja2Templates:
    settings = get_settings()
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    env = templates.env
    env.globals["modules"] = list_modules()
    env.globals["persona_labels"] = PERSONA_LABELS
    env.globals["Persona"] = Persona
    env.globals["users"] = USERS
    env.globals["is_nav_visible"] = is_nav_visible
    env.globals["app_env"] = settings.app_env
    env.globals["current_context"] = _current_context
    return templates


templates = _build_templates()
