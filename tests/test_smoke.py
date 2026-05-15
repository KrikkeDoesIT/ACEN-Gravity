"""Smoke tests for Stage 8.1 — does the empty shell boot, route, and persona-switch?

No DB, no business logic. Covered:
  - GET /healthz returns 200.
  - GET / when not logged in → redirect to /login.
  - GET /login returns 200 and offers all three personas.
  - POST /login with persona=consultant → redirect to / → home shows full nav.
  - POST /login with persona=customer_executive → home shows compressed nav (no AD/BH/SF/Entra links).
  - POST /login with unknown persona → redirect to /login?error=...
  - POST /logout → redirect to /login.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from platform_core.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_healthz_ok() -> None:
    r = _client().get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root_redirects_to_login_when_no_persona() -> None:
    r = _client().get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_page_lists_all_personas() -> None:
    r = _client().get("/login")
    assert r.status_code == 200
    body = r.text
    assert "Choose a role" in body
    assert 'value="consultant"' in body
    assert 'value="customer_executive"' in body
    assert 'value="customer_it_lead"' in body


def test_consultant_sees_full_side_nav() -> None:
    c = _client()
    r = c.post("/login", data={"persona": "consultant"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Overview" in body
    assert "AD" in body
    assert "BloodHound" in body
    assert "Silverfort" in body
    assert "Entra" in body
    assert "Findings" in body
    assert "Reports" in body
    assert "Audit" in body
    assert "ACEN Consultant" in body


def test_customer_executive_sees_compressed_nav() -> None:
    c = _client()
    c.post("/login", data={"persona": "customer_executive"})
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Overview" in body
    assert "Findings" in body
    assert "Reports" in body
    # Module-level entries should be hidden for customer roles
    # (we look for the side-nav row text, allowing the modules to be mentioned elsewhere)
    nav_segment = body.split('Navigate')[1].split('</nav>')[0]
    assert "AD" not in nav_segment
    assert "BloodHound" not in nav_segment
    assert "Silverfort" not in nav_segment
    assert "Entra" not in nav_segment
    assert "Audit" not in body  # not visible at all for customers


def test_customer_it_lead_sees_compressed_nav() -> None:
    c = _client()
    c.post("/login", data={"persona": "customer_it_lead"})
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Customer · IT Lead" in body  # role label
    assert "Marcus Webb" in body  # synthetic user display name
    # Side-nav Audit row only renders for consultants.
    nav_segment = body.split('Navigate')[1].split('</nav>')[0]
    assert "Audit" not in nav_segment


def test_unknown_persona_redirects_back_to_login() -> None:
    r = _client().post("/login", data={"persona": "nope"}, follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]
    assert "error=" in r.headers["location"]


def test_logout_clears_session_and_redirects_to_login() -> None:
    c = _client()
    c.post("/login", data={"persona": "consultant"})
    r = c.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    # After logout, the root should redirect to login again
    r = c.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_poc_banner_visible_in_development() -> None:
    r = _client().get("/login")
    assert "POC build" in r.text
    assert "synthetic data only" in r.text
