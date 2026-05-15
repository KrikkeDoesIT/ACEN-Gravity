"""Chunk D tests — module pages with archetypes.

Each of the four POC modules has its own page on `/modules/{module_id}`. The
shared frame is identical; the body differs per archetype (Posture /
Attack-path / Coverage / License-aware tenant config).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contoso"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    from platform_core import settings as settings_mod
    from platform_core.db import Base, get_engine, reset_for_tests
    from platform_core.models import registry as _registry  # noqa: F401

    settings_mod._settings = None
    reset_for_tests()
    engine = get_engine()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    reset_for_tests()
    settings_mod._settings = None


def _load_contoso() -> None:
    from platform_core.cli import demo_load

    demo_load(fixture_path=FIXTURE_ROOT)


def _client() -> TestClient:
    from platform_core.app import create_app

    return TestClient(create_app())


def _login(c: TestClient, persona: str) -> None:
    r = c.post("/login", data={"persona": persona}, follow_redirects=False)
    assert r.status_code == 303


# ---------------------------------------------------------------------------
# Route plumbing
# ---------------------------------------------------------------------------


def test_module_route_redirects_when_no_persona() -> None:
    r = _client().get("/modules/ad", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_unknown_module_id_is_404() -> None:
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/nonexistent")
    assert r.status_code == 404


def test_module_page_handles_empty_database() -> None:
    """Without `gravity demo load`, module pages render the no-data state."""
    c = _client()
    _login(c, "consultant")
    for module_id in ["ad", "bloodhound", "silverfort", "entra"]:
        r = c.get(f"/modules/{module_id}")
        assert r.status_code == 200, module_id


# ---------------------------------------------------------------------------
# AD — Posture archetype
# ---------------------------------------------------------------------------


def test_ad_module_page_renders_posture_categories_and_privileged_table() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/ad")
    assert r.status_code == 200
    body = r.text
    # Posture categories rendered as status cards.
    assert "Health" in body
    assert "Privileged" in body
    assert "Kerberos" in body
    assert "Delegation" in body
    assert "GPO" in body
    # The privileged-membership table renders the real identities.
    assert "svc-backup" in body
    assert "it.admin.kristof" in body
    assert "Domain Admins" in body
    # Service account is flagged.
    assert "Service account" in body
    # Archetype label rendered.
    assert "Posture archetype" in body


# ---------------------------------------------------------------------------
# BloodHound — Attack-path archetype
# ---------------------------------------------------------------------------


def test_bloodhound_module_page_lists_ranked_paths() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/bloodhound")
    assert r.status_code == 200
    body = r.text
    # Archetype label.
    assert "Attack-path archetype" in body
    # Tier 0 reachable context KPI.
    assert "Tier 0 reachable" in body
    # Path category labels.
    assert "ACL abuse" in body
    # Path step labels render in the preview row.
    assert "GenericAll" in body
    assert "MemberOf" in body
    assert "Domain Admins" in body or "DOMAIN ADMINS" in body
    # Graph size mini-card.
    assert "nodes" in body
    assert "edges" in body


# ---------------------------------------------------------------------------
# Silverfort — Coverage archetype
# ---------------------------------------------------------------------------


def test_silverfort_module_page_renders_coverage_matrix_with_gap() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/silverfort")
    assert r.status_code == 200
    body = r.text
    assert "Coverage archetype" in body
    # Connector pill is always "Pending" in POC (D-0006).
    assert "Pending" in body
    # Coverage matrix renders policy column headers.
    assert "Tier 0" in body
    # The gap row shows "Excluded" (or "Gap" in the Overall column).
    assert "Excluded" in body or "Gap" in body
    # Coverage % computed.
    assert "Tier 0 coverage" in body
    # SF-AD-001 in the coverage-gap finding list.
    assert "Coverage gap" in body or "coverage gap" in body
    # svc-backup is the uncovered identity.
    assert "svc-backup" in body


# ---------------------------------------------------------------------------
# Entra — License-aware tenant config archetype
# ---------------------------------------------------------------------------


def test_entra_module_page_renders_license_aware_cards_with_real_data() -> None:
    """Chunk E populated this page with real data; placeholder copy is gone."""
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/entra")
    assert r.status_code == 200
    body = r.text
    assert "License-aware tenant config" in body
    # Six card titles. Jinja2 HTML-escapes `&` → `&amp;`.
    assert "Licensing &amp; Capability" in body
    assert "Conditional Access" in body
    assert "Privileged Roles" in body
    assert "Authentication Methods" in body
    assert "Apps &amp; Service Principals" in body
    assert "Hybrid Identity" in body


# ---------------------------------------------------------------------------
# Nav wiring
# ---------------------------------------------------------------------------


def test_side_nav_module_links_point_to_module_routes() -> None:
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/ad")
    body = r.text
    # Every module is reachable from the nav.
    for mid in ["ad", "bloodhound", "silverfort", "entra"]:
        assert f'href="/modules/{mid}"' in body


def test_module_nav_active_pill_on_correct_module() -> None:
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/silverfort")
    body = r.text
    # The Silverfort row should carry the active styling marker.
    # We assert by finding the Silverfort link with the active background class.
    # The link uses `bg-support-violet/15` (SF accent) when active.
    assert 'href="/modules/silverfort"' in body
    assert "bg-support-violet/15" in body


# ---------------------------------------------------------------------------
# Role visibility
# ---------------------------------------------------------------------------


def test_module_pages_accessible_to_customer_roles_too() -> None:
    """Module pages are visible to all personas (visibility filter still applies to
    individual findings rendered on those pages, but the chrome itself is shared).
    """
    _load_contoso()
    c = _client()
    _login(c, "customer_executive")
    # Customer roles can hit the pages even if no findings are visible to them.
    for module_id in ["ad", "bloodhound", "silverfort", "entra"]:
        r = c.get(f"/modules/{module_id}")
        assert r.status_code == 200, module_id
