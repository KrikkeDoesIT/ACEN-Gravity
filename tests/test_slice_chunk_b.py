"""Chunk B tests — triage → publish → audit-log per state change.

Builds on the Chunk A `isolated_db` fixture: each test gets a clean SQLite
and a freshly loaded Contoso fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def _first_finding_id() -> str:
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        finding = session.query(Finding).order_by(Finding.risk_score.desc()).first()
        assert finding is not None
        return finding.id
    finally:
        session.close()


def _audit_events(event_type: str | None = None) -> list:
    from platform_core.audit.models import AuditEvent
    from platform_core.db import _session_factory

    session: Session = _session_factory()()
    try:
        q = session.query(AuditEvent)
        if event_type:
            q = q.filter(AuditEvent.event_type == event_type)
        return q.order_by(AuditEvent.created_at.asc()).all()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


def test_state_transitions_walk_new_to_published_to_closed() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    # new → triaged
    r = c.post(f"/findings/{fid}/state", data={"new_state": "triaged"}, follow_redirects=False)
    assert r.status_code == 303
    # triaged → published
    r = c.post(f"/findings/{fid}/state", data={"new_state": "published"}, follow_redirects=False)
    assert r.status_code == 303
    # published → closed
    r = c.post(f"/findings/{fid}/state", data={"new_state": "closed"}, follow_redirects=False)
    assert r.status_code == 303

    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session = _session_factory()()
    try:
        f = session.get(Finding, fid)
        assert f.state == "closed"
    finally:
        session.close()


def test_invalid_state_transition_is_rejected_with_flash() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    # new → published is NOT allowed directly (must go via triaged).
    r = c.post(f"/findings/{fid}/state", data={"new_state": "published"}, follow_redirects=True)
    assert r.status_code == 200
    body = r.text
    assert "State transition not allowed" in body

    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session = _session_factory()()
    try:
        f = session.get(Finding, fid)
        assert f.state == "new"  # unchanged
    finally:
        session.close()


def test_only_consultant_can_change_state() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "customer_executive")

    r = c.post(f"/findings/{fid}/state", data={"new_state": "triaged"}, follow_redirects=False)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


def test_visibility_change_audited() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    r = c.post(
        f"/findings/{fid}/visibility",
        data={"new_visibility": "customer_summary"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    events = _audit_events("finding.visibility_change")
    assert len(events) == 1
    payload = events[0].payload
    assert payload["from"] == "internal_only"
    assert payload["to"] == "customer_summary"
    assert events[0].severity == "security"


def test_invalid_visibility_rejected() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    r = c.post(
        f"/findings/{fid}/visibility",
        data={"new_visibility": "nonsense"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "Unknown customer_visibility" in r.text


# ---------------------------------------------------------------------------
# Publish (composite)
# ---------------------------------------------------------------------------


def test_publish_from_new_auto_triages_then_publishes() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    r = c.post(
        f"/findings/{fid}/publish",
        data={"visibility": "customer_summary"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session = _session_factory()()
    try:
        f = session.get(Finding, fid)
        assert f.state == "published"
        assert f.customer_visibility == "customer_summary"
    finally:
        session.close()

    # Audit log: state_change new→triaged, state_change triaged→published,
    # visibility_change internal_only→customer_summary, plus the composite
    # finding.publish event.
    state_changes = _audit_events("finding.state_change")
    transitions = [(e.payload["from"], e.payload["to"]) for e in state_changes]
    assert ("new", "triaged") in transitions
    assert ("triaged", "published") in transitions

    publish_events = _audit_events("finding.publish")
    assert len(publish_events) == 1
    assert publish_events[0].payload["visibility"] == "customer_summary"


def test_publish_blocks_internal_only_visibility() -> None:
    _load_contoso()
    fid = _first_finding_id()
    c = _client()
    _login(c, "consultant")

    r = c.post(
        f"/findings/{fid}/publish",
        data={"visibility": "internal_only"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "Publishing requires" in r.text or "cannot" in r.text.lower()


def test_published_finding_is_visible_to_customer_executive() -> None:
    _load_contoso()
    fid = _first_finding_id()

    # Consultant publishes.
    c = _client()
    _login(c, "consultant")
    r = c.post(
        f"/findings/{fid}/publish",
        data={"visibility": "customer_summary"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    # Customer executive can now see the finding.
    c2 = _client()
    _login(c2, "customer_executive")
    r = c2.get("/findings")
    assert r.status_code == 200
    assert "ACL abuse" in r.text or "Domain Admins" in r.text

    r = c2.get(f"/findings/{fid}")
    assert r.status_code == 200
    # Internal-only summary block must NOT appear for customer roles.
    assert "Summary — internal" not in r.text
    # Customer-framed summary present.
    assert "Summary — customer framing" in r.text


# ---------------------------------------------------------------------------
# Audit log view
# ---------------------------------------------------------------------------


def test_audit_log_visible_to_consultant_only() -> None:
    _load_contoso()
    fid = _first_finding_id()

    c = _client()
    _login(c, "consultant")
    # Do something audit-worthy.
    c.post(f"/findings/{fid}/state", data={"new_state": "triaged"}, follow_redirects=False)

    r = c.get("/audit")
    assert r.status_code == 200
    body = r.text
    assert "finding.state_change" in body
    assert "Audit log" in body

    # Customer executive forbidden.
    c2 = _client()
    _login(c2, "customer_executive")
    r2 = c2.get("/audit")
    assert r2.status_code == 403
