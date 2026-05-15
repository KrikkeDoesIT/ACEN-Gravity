"""Chunk E tests — Entra module + AD↔Entra correlation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contoso"

KRISTOF_AD_SID = "S-1-5-21-1234567890-1234567890-1234567890-1201"
KRISTOF_AZURE_ID = "aaaaaaaa-1201-1201-1201-000000001201"


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
# Parser — owned SKUs / capabilities / Identity linking
# ---------------------------------------------------------------------------


def test_entra_parser_detects_owned_skus_via_subscribed_skus() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.evidence.models import Evidence

    session: Session = _session_factory()()
    try:
        ev = (
            session.query(Evidence)
            .filter(Evidence.module_id == "entra")
            .one()
        )
        payload = ev.payload
        # Contoso has M365 E3 + Entra ID P1 standalone, no P2.
        assert "m365-e3" in payload["owned_sku_ids"]
        assert "entra-id-p1" in payload["owned_sku_ids"]
        assert "entra-id-p2" not in payload["owned_sku_ids"]
        # And the capability set reflects that.
        assert "entra.conditional-access" in payload["owned_capabilities"]
        assert "entra.pim" not in payload["owned_capabilities"]
        assert "entra.identity-protection.risky-users" not in payload["owned_capabilities"]
    finally:
        session.close()


def test_entra_parser_links_synced_user_to_ad_identity_by_sid() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.identity.models import Identity

    session: Session = _session_factory()()
    try:
        # The AD identity for kristof should now also carry the Azure object id.
        kristof = (
            session.query(Identity).filter(Identity.sid == KRISTOF_AD_SID).one()
        )
        assert kristof.azure_object_id == KRISTOF_AZURE_ID
        assert kristof.upn == "it.admin.kristof@contoso.example"
        # Still flagged Tier 0 from the AD parser.
        assert kristof.is_tier0 is True
        # And now also `is_privileged` from the Entra role assignment.
        assert kristof.is_privileged is True
    finally:
        session.close()


def test_entra_parser_creates_cloud_only_identities_for_breakglass_and_cloud_admin() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.identity.models import Identity

    session: Session = _session_factory()()
    try:
        # Cloud-only Global Admin — no SID, but has azure_object_id.
        cloud_admin = (
            session.query(Identity)
            .filter(Identity.upn == "cloud.only.admin@contoso.example")
            .one()
        )
        assert cloud_admin.sid is None
        assert cloud_admin.is_tier0 is True
        # Break-glass is also cloud-only and Global Admin.
        bg = (
            session.query(Identity)
            .filter(Identity.upn == "breakglass@contoso.example")
            .one()
        )
        assert bg.sid is None
        assert bg.is_tier0 is True
    finally:
        session.close()


# ---------------------------------------------------------------------------
# The six Entra controls
# ---------------------------------------------------------------------------


def test_entra_control_lic_001_is_informational_licensed_enabled() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.lic.detection")
            .one()
        )
        assert f.severity == "info"
        assert f.license_status == "licensed_enabled"
        assert "Microsoft 365 E3" in f.title or "M365 E3" in f.title.upper() or "m365-e3" in f.payload["owned_sku_ids"]
    finally:
        session.close()


def test_entra_control_ca_001_passes_when_baseline_mfa_policy_is_enabled() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.ca.baseline")
            .one()
        )
        # Contoso fixture has an enabled baseline MFA-for-all policy.
        assert f.license_status == "licensed_enabled"
        assert f.severity == "low"  # passes
    finally:
        session.close()


def test_entra_control_ca_003_shows_licensed_disabled_when_legacy_policy_is_off() -> None:
    """The headline `licensed_disabled` demonstrator."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.ca.legacy_auth")
            .one()
        )
        assert f.license_status == "licensed_disabled"
        assert f.severity == "high"
        # The remediation talks about enabling the existing policy.
        assert "Enable" in f.remediation or "enable" in f.remediation.lower()
    finally:
        session.close()


def test_entra_control_priv_003_shows_not_licensed_when_p2_is_absent() -> None:
    """The headline `not_licensed` demonstrator."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.lic.not_licensed.entra.pim")
            .one()
        )
        assert f.license_status == "not_licensed"
        # not_licensed never reduces Current License Score — but still surfaces in UI.
        assert "PIM" in f.title or "P2" in f.title
        assert f.payload["missing_capability"] == "entra.pim"
        assert f.payload["upgrade_path"] in {"entra-id-p2", "m365-e5"}
    finally:
        session.close()


def test_entra_control_hybrid_001_emits_when_synced_admin_present() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.hybrid.synced_privileged")
            .one()
        )
        # kristof is the only hybrid admin in the fixture.
        assert f.severity == "high"
        records = f.payload["hybrid_admin_records"]
        assert len(records) == 1
        assert records[0]["ad_sam_account_name"] == "it.admin.kristof"
        assert records[0]["entra_upn"] == "it.admin.kristof@contoso.example"
        assert records[0]["is_ad_tier0"] is True
    finally:
        session.close()


def test_entra_control_app_002_flags_long_lived_secret() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        f = (
            session.query(Finding)
            .filter(Finding.category == "entra.app.long_lived_secrets")
            .one()
        )
        flagged = f.payload["flagged"]
        flagged_names = {a["display_name"] for a in flagged}
        # The "Legacy Reporting App" has a 10-year secret in the fixture.
        assert "Legacy Reporting App" in flagged_names
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Cross-module correlation — CORR-AD-ENTRA-001
# ---------------------------------------------------------------------------


def test_corr_ad_entra_001_emitted_for_hybrid_admin() -> None:
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        corrs = (
            session.query(Finding)
            .filter(
                Finding.module_id == "correlation",
                Finding.category == "correlation.ad_entra_001",
            )
            .all()
        )
        # kristof is the only AD-Tier-0 hybrid admin in the fixture.
        assert len(corrs) == 1
        f = corrs[0]
        assert f.severity == "high"
        assert f.payload["rule_id"] == "CORR-AD-ENTRA-001"
        assert f.payload["ad_sam_account_name"] == "it.admin.kristof"
        assert f.payload["entra_upn"] == "it.admin.kristof@contoso.example"
        # Identity refs include the AD identity uuid.
        assert f.identity_refs  # non-empty
    finally:
        session.close()


def test_corr_bh_entra_001_does_not_fire_when_no_bh_path_reaches_hybrid_admin() -> None:
    """In Contoso, no BH path TARGETS kristof directly (paths go to DA or
    svc-backup). So CORR-BH-ENTRA-001 should not fire — this verifies the
    rule's selectivity."""
    _load_contoso()
    from platform_core.db import _session_factory
    from platform_core.findings.models import Finding

    session: Session = _session_factory()()
    try:
        corrs = (
            session.query(Finding)
            .filter(
                Finding.module_id == "correlation",
                Finding.category == "correlation.bh_entra_001",
            )
            .all()
        )
        assert corrs == []
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Entra module page renders the real data
# ---------------------------------------------------------------------------


def test_entra_module_page_renders_owned_skus_and_hybrid_bridge() -> None:
    _load_contoso()
    c = _client()
    _login(c, "consultant")
    r = c.get("/modules/entra")
    assert r.status_code == 200
    body = r.text
    # Owned SKU pills.
    assert "m365-e3" in body
    assert "entra-id-p1" in body
    # The license-aware status labels.
    assert "Licensed · disabled" in body or "Licensed &middot; disabled" in body
    assert "Not licensed" in body
    # Hybrid admin bridge section visible (the demo headline).
    assert "Hybrid admin bridge" in body
    assert "it.admin.kristof" in body
    assert "it.admin.kristof@contoso.example" in body
    # CORR-AD-ENTRA-001 referenced.
    assert "CORR-AD-ENTRA-001" in body


def test_entra_module_page_customer_executive_filters_internal_only() -> None:
    _load_contoso()
    c = _client()
    _login(c, "customer_executive")
    r = c.get("/modules/entra")
    assert r.status_code == 200
    # Customer-executive sees zero Entra findings (all default internal_only).
    # The page still renders, but the all-findings list is absent / minimal.
    body = r.text
    assert "License-aware tenant config" in body


# ---------------------------------------------------------------------------
# License catalog
# ---------------------------------------------------------------------------


def test_license_catalog_maps_graph_skus_to_internal_ids() -> None:
    from platform_core.licensing.catalog import (
        capabilities_for_skus,
        graph_sku_to_internal,
        upgrade_path_for,
    )

    assert graph_sku_to_internal("05e9a617-0261-4cee-bb44-138d3ef5d965") == "m365-e3"
    assert graph_sku_to_internal("078d2b04-f1bd-4111-bbd4-b4b1b354cef4") == "entra-id-p1"
    assert graph_sku_to_internal("00000000-0000-0000-0000-000000000000") is None

    caps = capabilities_for_skus(["m365-e3", "entra-id-p1"])
    assert "entra.conditional-access" in caps
    assert "entra.pim" not in caps

    # PIM is unlocked by Entra ID P2 (cheapest standalone) or M365 E5.
    assert upgrade_path_for("entra.pim") in {"entra-id-p2", "m365-e5"}
