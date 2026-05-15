"""Chunk C tests — Silverfort coverage + cross-module correlation + report preview.

End-to-end demo story validation:
  AD evidence → BH path → SF coverage gap → cross-module correlation Finding
  → published → customer-summary report renders the headline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contoso"
SVC_BACKUP_SID = "S-1-5-21-1234567890-1234567890-1234567890-1202"
DOMAIN_ADMINS_SID = "S-1-5-21-1234567890-1234567890-1234567890-512"


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
# Silverfort parser
# ---------------------------------------------------------------------------


def test_silverfort_parser_identifies_uncovered_tier0() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.evidence.models import Evidence

    session: Session = _session_factory()()
    try:
        sf_ev = (
            session.query(Evidence)
            .filter(Evidence.module_id == "silverfort")
            .order_by(Evidence.created_at.desc())
            .first()
        )
        assert sf_ev is not None
        # svc-backup is the only uncovered Tier 0 in the fixture.
        uncovered = sf_ev.payload.get("uncovered_tier0_sids", [])
        assert SVC_BACKUP_SID in uncovered
        # And only that one.
        assert len(uncovered) == 1
    finally:
        session.close()


def test_sf_ad_001_finding_emitted_when_tier0_uncovered() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        sf_findings = (
            session.query(Finding)
            .filter(
                Finding.module_id == "silverfort",
                Finding.category == "sf.ad.tier0_coverage_gap",
            )
            .all()
        )
        assert len(sf_findings) == 1
        f = sf_findings[0]
        assert f.severity == "high"
        assert "svc-backup" in f.summary_internal
        assert SVC_BACKUP_SID in f.payload["uncovered_tier0_sids"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


def test_correlation_findings_match_path_target_and_pivot_through_gap() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        corr_findings = (
            session.query(Finding)
            .filter(Finding.module_id == "correlation")
            .all()
        )
        # Two cases: paths landing on svc-backup AND paths to DA pivoting through svc-backup.
        # Both fire CORR-BH-SF-001. With the Contoso fixture this yields exactly 5.
        assert len(corr_findings) >= 2

        # Every correlation finding must reference the SF gap (svc-backup) somewhere
        # on the path.
        for c in corr_findings:
            assert SVC_BACKUP_SID in c.payload.get("gap_sids", [])
            assert c.payload.get("rule_id") == "CORR-BH-SF-001"

        # The headline (most severe) must be CRITICAL — paths to Domain Admins
        # pivoting through svc-backup.
        critical = [c for c in corr_findings if c.severity == "critical"]
        assert critical, "Expected at least one CRITICAL correlation (pivot-through-gap)"
        headline = max(critical, key=lambda f: f.risk_score)
        assert headline.payload["bh_target_sid"] == DOMAIN_ADMINS_SID
        assert headline.payload["gap_is_target"] is False
        # Pretty-printed labels.
        assert "Domain Admins" in headline.title
        assert "svc-backup" in headline.title
    finally:
        session.close()


def test_correlation_idempotent_on_reload() -> None:
    _load_contoso()
    _load_contoso()

    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        # Two assessment runs were created (CLI deliberately starts a new run).
        # Each run has its own correlation findings — but no duplicates inside
        # the same run.
        from platform_core.models.core import AssessmentRun

        runs = session.query(AssessmentRun).all()
        assert len(runs) == 2
        per_run = {
            run.id: session.query(Finding)
            .filter(Finding.assessment_run_id == run.id, Finding.module_id == "correlation")
            .count()
            for run in runs
        }
        # Each run should have the same number of correlations (deterministic).
        counts = set(per_run.values())
        assert len(counts) == 1, f"Per-run correlation counts differ: {per_run}"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Reports list
# ---------------------------------------------------------------------------


def test_reports_list_consultant_sees_internal_variant() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/reports")
    assert r.status_code == 200
    body = r.text
    assert "Contoso Corp" in body
    assert "Internal detailed" in body or "internal detailed" in body.lower()


def test_reports_list_customer_executive_sees_customer_summary_variant() -> None:
    _load_contoso()
    c = _client()
    _login(c, "customer_executive")
    r = c.get("/reports")
    assert r.status_code == 200
    body = r.text
    assert "Customer summary" in body or "customer summary" in body.lower()


# ---------------------------------------------------------------------------
# Report preview
# ---------------------------------------------------------------------------


def _run_id() -> str:
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun

    session: Session = _session_factory()()
    try:
        run = session.query(AssessmentRun).order_by(AssessmentRun.created_at.desc()).first()
        assert run is not None
        return run.id
    finally:
        session.close()


def test_report_preview_consultant_shows_internal_summary_and_technical_detail() -> None:
    _load_contoso()
    rid = _run_id()
    c = _client()
    _login(c, "consultant")
    r = c.get(f"/reports/{rid}")
    assert r.status_code == 200
    body = r.text
    # Headline finding region renders the path with gap markers.
    assert "Internal Detailed Report" in body or "INTERNAL DETAILED REPORT" in body.upper()
    assert "svc-backup" in body
    assert "Domain Admins" in body
    # Technical detail block included via <details> for internal report.
    assert "Technical detail" in body or "TECHNICAL DETAIL" in body.upper()
    # ACL abuse path label rendered.
    assert "GenericAll" in body


def test_report_preview_customer_executive_hides_internal_summary() -> None:
    _load_contoso()
    rid = _run_id()

    # Publish a finding so the customer executive has something to see.
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session = _session_factory()()
    try:
        # Publish the headline correlation.
        headline = (
            session.query(Finding)
            .filter(Finding.module_id == "correlation", Finding.severity == "critical")
            .order_by(Finding.risk_score.desc())
            .first()
        )
        assert headline is not None
        fid = headline.id
    finally:
        session.close()

    c = _client()
    _login(c, "consultant")
    rp = c.post(
        f"/findings/{fid}/publish",
        data={"visibility": "customer_summary"},
        follow_redirects=False,
    )
    assert rp.status_code == 303

    # Customer executive sees the report.
    c2 = _client()
    _login(c2, "customer_executive")
    r = c2.get(f"/reports/{rid}")
    assert r.status_code == 200
    body = r.text
    assert "Customer Summary" in body or "CUSTOMER SUMMARY" in body.upper()
    # Headline rendered for customer.
    assert "Critical correlation" in body
    # Internal summary block is NOT rendered for customer roles.
    assert "Summary — internal" not in body
    # Customer-framed text is.
    assert "An attack path" in body  # phrase from CORR template's summary_customer


def test_report_preview_customer_full_includes_technical_detail() -> None:
    _load_contoso()
    rid = _run_id()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session = _session_factory()()
    try:
        headline = (
            session.query(Finding)
            .filter(Finding.module_id == "correlation", Finding.severity == "critical")
            .order_by(Finding.risk_score.desc())
            .first()
        )
        fid = headline.id
    finally:
        session.close()

    c = _client()
    _login(c, "consultant")
    c.post(f"/findings/{fid}/publish", data={"visibility": "customer_full"}, follow_redirects=False)

    c2 = _client()
    _login(c2, "customer_executive")
    r = c2.get(f"/reports/{rid}")
    assert r.status_code == 200
    body = r.text
    # customer_full → technical detail visible for that finding.
    assert "Technical detail" in body or "TECHNICAL DETAIL" in body.upper()
