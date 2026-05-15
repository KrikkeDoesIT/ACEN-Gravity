"""Home / overview shell.

POC Stage 8.1: renders the empty ACEN shell with the chosen persona's nav.
No data, no findings, no scores — those land in Stage 9 with the vertical slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.web.session import get_user
from platform_core.web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
def home(request: Request) -> HTMLResponse | RedirectResponse:
    user = get_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "page_title": "Overview",
            "user": user,
            "persona": user.persona,
            "persona_label": user.role_label,
        },
    )
