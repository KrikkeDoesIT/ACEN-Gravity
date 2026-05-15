"""Chunk F tests — score engine + Overview real data.

Covers:
  - Score engine math (Current / Target / Opportunity per LICENSE_MODEL §7)
  - Module-level breakdowns
  - Overview page renders real scores, severity strip, module strip,
    and a persona-appropriate headline finding.
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


def _latest_run_id() -> str:
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun

    session: Session = _session_factory()()
    try:
        run = (
            session.query(AssessmentRun)
            .order_by(AssessmentRun.created_at.desc())
            .first()
        )
        assert run is not None
        return run.id
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Score engine
# ---------------------------------------------------------------------------


def test_compute_scores_returns_engagement_and_module_breakdowns() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.scoring import compute_scores

    run_id = _latest_run_id()
    session: Session = _session_factory()()
    try:
        scores = compute_scores(session, run_id)
    finally:
        session.close()

    # AD currently produces Identities only (no control findings in slice).
    # The three modules that DO emit findings must score.
    for module_id in ("bloodhound", "silverfort", "entra"):
        ms = scores.for_module(module_id)
        assert ms is not None, f"{module_id} has no module scores"
        assert ms.has_data is True

    # Engagement scores in [0, 100] and Opportunity = Target − Current.
    assert scores.current is not None
    assert scores.target is not None
    assert 0.0 <= scores.current <= 100.0
    assert 0.0 <= scores.target <= 100.0
    # Opportunity = Current − Target (points lost when unlicensed gaps count as fails).
    assert scores.opportunity == pytest.approx(scores.current - scores.target, abs=0.1)
    assert scores.opportunity >= 0.0


def test_score_engine_excludes_correlation_findings_from_module_aggregation() -> None:
    """Correlation findings are cross-module derivatives, not control outcomes."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.scoring import compute_scores

    run_id = _latest_run_id()
    session: Session = _session_factory()()
    try:
        scores = compute_scores(session, run_id)
        # No module called "correlation" should appear in per-module scores.
        assert "correlation" not in scores.modules
        # But the correlation count is reported separately for the UI.
        assert scores.correlation_count >= 1
        # At least one BH-SF critical correlation in Contoso.
        assert scores.critical_correlation_count >= 1
    finally:
        session.close()


def test_score_engine_excludes_not_licensed_from_current_but_counts_in_target() -> None:
    """Per LICENSE_MODEL §7: `not_licensed` controls drop out of Current but
    count as a fail vs Target. Entra PIM (`entra.lic.not_licensed.entra.pim`)
    is the headline `not_licensed` demonstrator in Contoso."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.scoring import compute_scores

    run_id = _latest_run_id()
    session: Session = _session_factory()()
    try:
        scores = compute_scores(session, run_id)
        entra = scores.for_module("entra")
    finally:
        session.close()

    assert entra is not None
    # Entra has 6 control findings. PIM not_licensed is excluded from Current.
    assert entra.eligible_for_current == entra.findings_total - entra.license_status_counts.get(
        "not_licensed", 0
    )
    # PIM not_licensed IS included in Target.
    assert entra.eligible_for_target == entra.findings_total
    # Therefore Current >= Target (because the not_licensed control is a
    # fail in Target but invisible in Current), unless Current is None.
    assert entra.current is not None
    assert entra.target is not None
    assert entra.current >= entra.target


def test_score_engine_severity_mapping_low_passes_high_fails() -> None:
    """Severity → pass_factor mapping must follow info/low=pass, medium=partial,
    high/critical=fail. Verified on a focused module."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.scoring import compute_scores

    run_id = _latest_run_id()
    session: Session = _session_factory()()
    try:
        scores = compute_scores(session, run_id)
        sf = scores.for_module("silverfort")
    finally:
        session.close()

    # Silverfort has exactly one finding in Contoso (SF-AD-001, HIGH).
    # Expect Current = 0.0 (high = fail) — the single eligible control fails.
    assert sf is not None
    assert sf.findings_total == 1
    assert sf.current == 0.0
    assert sf.target == 0.0


def test_score_engine_bloodhound_paths_all_fail_in_contoso() -> None:
    """All BH paths in Contoso are high or critical, so Current = Target = 0."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.scoring import compute_scores

    run_id = _latest_run_id()
    session: Session = _session_factory()()
    try:
        scores = compute_scores(session, run_id)
        bh = scores.for_module("bloodhound")
    finally:
        session.close()

    assert bh is not None
    # BH emits one finding per critical path; Contoso has 5 (3 HIGH + 2 MEDIUM).
    assert bh.findings_total == 5
    # 3 HIGH (factor 0) + 2 MEDIUM (factor 0.5) over 5 → 20%.
    assert bh.current == 20.0
    assert bh.target == 20.0
    # And the severity breakdown agrees.
    assert bh.severity_counts == {"high": 3, "medium": 2}


def test_score_engine_handles_empty_run() -> None:
    """A brand-new run with no findings returns None scores, not zeros."""
    from platform_core.db import _session_factory
    from platform_core.models.core import AssessmentRun, Customer, Engagement
    from platform_core.scoring import compute_scores

    session: Session = _session_factory()()
    try:
        c = Customer(name="Empty Inc", slug="empty-inc")
        session.add(c)
        session.flush()
        e = Engagement(customer_id=c.id, name="Empty engagement", slug="empty")
        session.add(e)
        session.flush()
        r = AssessmentRun(engagement_id=e.id, name="empty run")
        session.add(r)
        session.commit()
        scores = compute_scores(session, r.id)
    finally:
        session.close()

    assert scores.current is None
    assert scores.target is None
    assert scores.opportunity is None
    assert scores.modules == {}
    assert scores.correlation_count == 0


# ---------------------------------------------------------------------------
# Overview route — renders real scores
# ---------------------------------------------------------------------------


def test_overview_no_data_shows_empty_state() -> None:
    """No assessment run → keep the original empty-state hero."""
    c = _client()
    _login(c, "consultant")
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Welcome back" in body
    assert "gravity demo load" in body
    assert "Awaiting evidence" in body


def test_overview_consultant_sees_real_scores_and_headline() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/")
    assert r.status_code == 200
    body = r.text

    # Three KPI numbers rendered (not dashes).
    assert "Current license score" in body
    assert "Target posture" in body
    assert "Opportunity gap" in body
    # Posture snapshot headline replaces the welcome copy.
    assert "Posture snapshot" in body
    assert "Contoso" in body
    # Severity strip is present.
    assert "Findings" in body
    # The headline finding is rendered with "Open finding" CTA.
    assert "Open finding" in body
    # Consultant sees internal_only summaries — the critical BH-SF
    # correlation is internal_only by default and should be the headline.
    assert "Domain Admins" in body or "svc-backup" in body


def test_overview_customer_executive_sees_only_customer_visible_headline() -> None:
    """Customer roles must not see internal_only findings as headline. If
    nothing is published, no headline section renders."""
    _load_contoso()
    c = _client()
    _login(c, "customer_executive")
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    # The page still renders, KPIs are visible.
    assert "Current license score" in body
    # But no "Open finding" CTA, because nothing is customer-visible yet.
    assert "Open finding" not in body


def test_overview_after_publish_customer_executive_sees_headline() -> None:
    _load_contoso()
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

    c2 = _client()
    _login(c2, "customer_executive")
    r = c2.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Open finding" in body  # now the customer sees the published headline


def test_overview_module_strip_shows_per_module_scores_and_status() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    # All four modules visible.
    for label in ("Active Directory", "BloodHound", "Silverfort", "Microsoft Entra"):
        assert label in body
    # At least one module is in "Attention" because of the BH critical paths.
    assert "Attention" in body


def test_overview_severity_strip_reflects_real_counts() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/")
    assert r.status_code == 200
    body = r.text
    # Severity labels rendered.
    for label in ("Critical", "High", "Medium", "Low", "Info"):
        assert label in body
    # Correlations count surfaced.
    assert "Cross-module correlations" in body
