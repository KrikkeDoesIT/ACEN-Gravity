"""Persona session helpers for the POC role-switcher.

There is no real authentication in POC V1 (A-0013). The chosen persona is stored
in a signed Starlette session cookie. The audit log captures every role switch
once the AuditLog model lands (Stage 9).

The `User` dataclass synthesises display fields (name, email, role label,
initials) from the persona so the UI can render a real-looking user profile
even though no auth/IDP exists yet. Real users come at MVP (Q-0043).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from fastapi import Request


class Persona(StrEnum):
    CONSULTANT = "consultant"
    CUSTOMER_EXECUTIVE = "customer_executive"
    CUSTOMER_IT_LEAD = "customer_it_lead"


PERSONA_LABELS: Final[dict[Persona, str]] = {
    Persona.CONSULTANT: "ACEN Consultant",
    Persona.CUSTOMER_EXECUTIVE: "Customer Executive",
    Persona.CUSTOMER_IT_LEAD: "Customer IT Lead",
}


# Side-nav visibility per persona. Consultants see everything; customer roles
# see a compressed nav (per UI_DESIGN_DIRECTION.md §3.1 SideNav).
NAV_VISIBLE_FOR: Final[dict[Persona, frozenset[str]]] = {
    Persona.CONSULTANT: frozenset(
        {"overview", "ad", "bloodhound", "silverfort", "entra", "findings", "reports", "audit"}
    ),
    Persona.CUSTOMER_EXECUTIVE: frozenset({"overview", "findings", "reports"}),
    Persona.CUSTOMER_IT_LEAD: frozenset({"overview", "findings", "reports"}),
}


SESSION_KEY: Final[str] = "persona"


@dataclass(frozen=True)
class User:
    """Synthetic user profile derived from the chosen persona.

    POC V1 has no real users (A-0013). These display fields make the UI feel
    real during the demo. Real `User` model + Entra ID auth lands at MVP.
    """

    persona: Persona
    display_name: str
    email: str
    role_label: str
    accent: str  # Tailwind colour class fragment used in chrome

    @property
    def initials(self) -> str:
        parts = [p for p in self.display_name.replace(".", "").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()


# Persona → synthetic user profile. Email domains use `.example` (RFC 2606) to
# mark these as fake. Consultant uses Kristof's name; customer personas are
# fictional (per D-0011 — synthetic data only).
USERS: Final[dict[Persona, User]] = {
    Persona.CONSULTANT: User(
        persona=Persona.CONSULTANT,
        display_name="Kristof Laerenbergh",
        email="kristof.laerenbergh@acen.example",
        role_label="ACEN Consultant",
        accent="brand-turquoise",
    ),
    Persona.CUSTOMER_EXECUTIVE: User(
        persona=Persona.CUSTOMER_EXECUTIVE,
        display_name="Alexandra Chen",
        email="a.chen@contoso.example",
        role_label="Customer · Executive",
        accent="support-violet",
    ),
    Persona.CUSTOMER_IT_LEAD: User(
        persona=Persona.CUSTOMER_IT_LEAD,
        display_name="Marcus Webb",
        email="m.webb@contoso.example",
        role_label="Customer · IT Lead",
        accent="support-sky",
    ),
}


def get_persona(request: Request) -> Persona | None:
    raw = request.session.get(SESSION_KEY)
    if raw is None:
        return None
    try:
        return Persona(raw)
    except ValueError:
        return None


def get_user(request: Request) -> User | None:
    persona = get_persona(request)
    if persona is None:
        return None
    return USERS[persona]


def set_persona(request: Request, persona: Persona) -> None:
    request.session[SESSION_KEY] = persona.value


def clear_persona(request: Request) -> None:
    request.session.pop(SESSION_KEY, None)


def is_nav_visible(persona: Persona | None, nav_id: str) -> bool:
    if persona is None:
        return False
    return nav_id in NAV_VISIBLE_FOR[persona]
