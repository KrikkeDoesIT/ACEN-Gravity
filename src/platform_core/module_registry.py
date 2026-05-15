"""Module registry.

Stage 8.1 stub. The full ModuleManifest dataclass per MODULE_ARCHITECTURE.md §6
will be filled in during Stage 9 when modules start declaring evidence types,
controls, and correlations. For now, this only knows which module ids exist so
the UI side-nav can render them, plus each module's brand category colour
(per UI_DESIGN_DIRECTION.md §2.1 supporting palette / module category map).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleStub:
    """Minimal stand-in for ModuleManifest until Stage 9 fills the full shape."""

    id: str
    title: str
    nav_label: str
    icon: str  # icon token (matched in templates)
    accent: str  # Tailwind colour class fragment (e.g. "brand-turquoise", "support-violet")


# Registration order = side-nav order.
# Accent tokens follow the module category map in UI_DESIGN_DIRECTION.md §2.1.
MODULES: tuple[ModuleStub, ...] = (
    ModuleStub(
        id="ad",
        title="Active Directory",
        nav_label="AD",
        icon="server",
        accent="brand-turquoise",
    ),
    ModuleStub(
        id="bloodhound",
        title="BloodHound",
        nav_label="BloodHound",
        icon="route",
        accent="support-rose",
    ),
    ModuleStub(
        id="silverfort",
        title="Silverfort",
        nav_label="Silverfort",
        icon="shield",
        accent="support-violet",
    ),
    ModuleStub(
        id="entra",
        title="Microsoft Entra",
        nav_label="Entra",
        icon="cloud",
        accent="support-sky",
    ),
)


def list_modules() -> tuple[ModuleStub, ...]:
    return MODULES


def get_module(module_id: str) -> ModuleStub | None:
    for m in MODULES:
        if m.id == module_id:
            return m
    return None
