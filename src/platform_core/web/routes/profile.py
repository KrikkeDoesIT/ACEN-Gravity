"""User profile page (stub).

POC Stage 8.1: simple placeholder that renders the current synthetic user's
details. Real user management lands at MVP (Q-0043 — Entra ID authentication).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.web.session import get_user
from platform_core.web.templating import templates

router = APIRouter()


@router.get("/profile", response_class=HTMLResponse, response_model=None)
def profile(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "page_title": "My profile",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
        },
    )
