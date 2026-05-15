"""Persona picker (stand-in for authentication in POC V1, per A-0013).

Real Entra ID auth is an MVP concern (Q-0043). The role switcher here is
explicitly labelled as a POC stand-in and produces an audit-log entry every
time a persona is chosen (audit hook lands in Stage 9).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.web.session import (
    PERSONA_LABELS,
    Persona,
    clear_persona,
    get_persona,
    set_persona,
)
from platform_core.web.templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def show_login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "page_title": "Sign in",
            "personas": list(Persona),
            "labels": PERSONA_LABELS,
            "current_persona": get_persona(request),
        },
    )


@router.post("/login")
def submit_login(request: Request, persona: str = Form(...)) -> RedirectResponse:
    try:
        chosen = Persona(persona)
    except ValueError:
        return RedirectResponse(url="/login?error=unknown_persona", status_code=303)
    set_persona(request, chosen)
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    clear_persona(request)
    return RedirectResponse(url="/login", status_code=303)
