"""Jinja2 template environment shared across routes."""

from __future__ import annotations

from fastapi.templating import Jinja2Templates

from platform_core.module_registry import list_modules
from platform_core.settings import get_settings
from platform_core.web.session import PERSONA_LABELS, USERS, Persona, is_nav_visible


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
    return templates


templates = _build_templates()
