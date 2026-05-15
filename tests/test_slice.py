"""Integration tests for the Stage 9 vertical slice (Chunk A).

Loads the Contoso Corp fixture into an isolated SQLite database, runs the
full pipeline (AD parser → BloodHound parser → path detection → Finding
generation) and asserts the expected headline path is detected.

Also exercises the `/findings` and `/findings/{id}` UI routes per persona.
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
    """Point DATABASE_URL at a per-test SQLite file and rebuild the schema."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    # Force settings + engine cache to rebuild against the new URL.
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
    """Invoke the same code path the CLI uses, against the isolated DB."""
    from platform_core.cli import demo_load

    demo_load(fixture_path=FIXTURE_ROOT)


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------


def test_pipeline_loads_customer_engagement_run() -> None:
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun, Customer, Engagement

    _load_contoso()
    session: Session = _session_factory()()
    try:
        customer = session.query(Customer).filter(Customer.slug == "contoso").one()
        assert customer.name == "Contoso Corp"
        eng = session.query(Engagement).filter(Engagement.customer_id == customer.id).one()
        assert "Identity Security Review" in eng.name
        run = session.query(AssessmentRun).filter(AssessmentRun.engagement_id == eng.id).one()
        assert run is not None
    finally:
        session.close()


def test_ad_parser_creates_tier0_identities() -> None:
    from platform_core.db import _session_factory
    from platform_core.identity.models import Identity

    _load_contoso()
    session: Session = _session_factory()()
    try:
        domain_admins = (
            session.query(Identity)
            .filter(Identity.sid == "S-1-5-21-1234567890-1234567890-1234567890-512")
            .one()
        )
        assert domain_admins.is_tier0 is True
        assert domain_admins.is_privileged is True
        assert domain_admins.canonical_kind == "group"

        svc_backup = (
            session.query(Identity)
            .filter(Identity.sid == "S-1-5-21-1234567890-1234567890-1234567890-1202")
            .one()
        )
        assert svc_backup.is_tier0 is True
        # Service-account flagging via the `is_service_account` member attribute
        assert svc_backup.canonical_kind == "service_account"
    finally:
        session.close()


def test_bloodhound_finds_acl_abuse_path_to_tier0() -> None:
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding, Severity

    _load_contoso()
    session: Session = _session_factory()()
    try:
        # The headline finding: contractor.john reaches Domain Admins via ACL abuse.
        headline = (
            session.query(Finding)
            .filter(Finding.category == "bh.acl_abuse")
            .order_by(Finding.risk_score.desc())
            .first()
        )
        assert headline is not None, "Expected at least one ACL-abuse path finding"
        assert headline.severity in {Severity.CRITICAL.value, Severity.HIGH.value}
        assert headline.risk_score >= 60

        payload = headline.payload
        assert payload["category"] == "acl_abuse"
        # The path must include a GenericAll edge (the abuse).
        assert any(step["edge_type"] == "GenericAll" for step in payload["steps"])
        # The target SID is a well-known Tier 0 RID (512 = Domain Admins,
        # or the privileged user 1202).
        target_rid = payload["target_sid"].rsplit("-", 1)[-1]
        assert target_rid in {"512", "1202"}
    finally:
        session.close()


def test_pipeline_idempotent_on_reload() -> None:
    """Second load should not duplicate customer/engagement; new run + findings only."""
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun, Customer, Engagement

    _load_contoso()
    _load_contoso()

    session: Session = _session_factory()()
    try:
        assert session.query(Customer).count() == 1
        assert session.query(Engagement).count() == 1
        # New AssessmentRun on each load (deliberate — we want fresh findings).
        assert session.query(AssessmentRun).count() == 2
    finally:
        session.close()


# ---------------------------------------------------------------------------
# UI tests
# ---------------------------------------------------------------------------


def _client() -> TestClient:
    from platform_core.app import create_app

    return TestClient(create_app())


def test_findings_list_redirects_when_no_persona() -> None:
    r = _client().get("/findings", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_findings_list_for_consultant_shows_all_findings() -> None:
    _load_contoso()
    c = _client()
    c.post("/login", data={"persona": "consultant"})
    r = c.get("/findings")
    assert r.status_code == 200
    body = r.text
    assert "ACL abuse" in body
    assert "DOMAIN ADMINS" in body or "contractor.john" in body
    # Severity badges rendered
    assert "HIGH" in body.upper() or "CRITICAL" in body.upper()


def test_findings_list_for_customer_executive_filters_internal_only() -> None:
    _load_contoso()
    c = _client()
    c.post("/login", data={"persona": "customer_executive"})
    r = c.get("/findings")
    assert r.status_code == 200
    body = r.text
    # All synthetic findings default to internal_only, so executives see none.
    assert "No findings yet" in body or "0 findings" in body


def test_finding_detail_renders_path_steps_for_consultant() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        finding = session.query(Finding).order_by(Finding.risk_score.desc()).first()
        assert finding is not None
        finding_id = finding.id
    finally:
        session.close()

    c = _client()
    c.post("/login", data={"persona": "consultant"})
    r = c.get(f"/findings/{finding_id}")
    assert r.status_code == 200
    body = r.text
    # Path-step list renders the GenericAll edge label
    assert "GenericAll" in body
    # Remediation block is shown
    assert "Remediation" in body
    # Properties sidebar is shown
    assert "License status" in body


def test_finding_detail_404_for_customer_role_on_internal_only() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        finding = session.query(Finding).first()
        assert finding is not None
        # Sanity: default visibility is internal_only.
        assert finding.customer_visibility == "internal_only"
        finding_id = finding.id
    finally:
        session.close()

    c = _client()
    c.post("/login", data={"persona": "customer_executive"})
    r = c.get(f"/findings/{finding_id}")
    assert r.status_code == 404
