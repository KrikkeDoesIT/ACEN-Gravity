"""Entra Graph bundle parser (Stage 9 Chunk E).

POC scope — reads a folder of Graph JSON dumps that mirror what the real
Microsoft Graph collector returns at MVP (A-0007, Q-0080). Identifies:

  - Owned SKUs / capabilities (via `subscribedSkus.json` + the catalog
    in `platform_core.licensing.catalog`).
  - Cloud identities, linked to AD Identity rows via `onPremisesSecurityIdentifier`
    (SID) or `onPremisesImmutableId` → `Identity.object_guid` (fallback).
  - Hybrid privileged accounts (synced AND in a Tier 0 directory role).
  - Conditional Access policy state (enabled / disabled / configured).
  - Application credentials (long-lived secrets).

Emits findings inline for 6 controls per `POC_V1_SCOPE.md` §5.6, with a mix
of `licensed_enabled`, `licensed_disabled`, and `not_licensed` so the
license-aware UI demonstration lands (D-0007/D-0008).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from platform_core.evidence.models import Evidence
from platform_core.findings.models import (
    CustomerVisibility,
    Finding,
    FindingState,
    LicenseStatus,
    Severity,
)
from platform_core.identity.models import Identity
from platform_core.licensing.catalog import (
    CAPABILITY_TITLES,
    SKU_CATALOG,
    capabilities_for_skus,
    graph_sku_to_internal,
    upgrade_path_for,
)

PARSER_VERSION = "0.1.0"

# Well-known Entra role template ids → Tier 0 status.
TIER0_ROLE_TEMPLATE_IDS: frozenset[str] = frozenset(
    {
        "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
        "e8611ab8-c189-46e8-94e1-60213ab1f814",  # Privileged Role Administrator
        "fe930be7-5e62-47db-91af-98c3a49a38b1",  # User Administrator (sensitive)
        "729827e3-9c14-49f7-bb1b-9608f156bbb8",  # Helpdesk Administrator (sensitive)
        "8ac3fc64-6eca-42ea-9e69-59f4c7b60eb2",  # Hybrid Identity Administrator
        "194ae4cb-b126-40b2-bd5b-6091b380977d",  # Security Administrator
        "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3",  # Application Administrator
    }
)

# How old a client-secret-credential is considered "long-lived".
LONG_LIVED_DAYS = 365


@dataclass(frozen=True)
class ControlOutcome:
    control_id: str
    finding_id: str | None
    license_status: str
    result_status: str  # pass / partial / fail / not_applicable / unknown


@dataclass(frozen=True)
class EntraParseResult:
    evidence_id: str
    organization_name: str
    tenant_id: str
    owned_sku_ids: list[str]
    owned_capabilities: list[str]
    hybrid_admin_count: int
    cloud_only_admin_count: int
    control_outcomes: list[ControlOutcome] = field(default_factory=list)


class EntraGraphBundleParser:
    evidence_type = "entra-graph-bundle"
    module_id = "entra"

    EXPECTED_FILES: tuple[str, ...] = (
        "organization.json",
        "subscribedSkus.json",
        "users.json",
        "directoryRoles.json",
        "roleAssignments.json",
        "conditionalAccessPolicies.json",
        "applications.json",
    )

    def parse(
        self,
        *,
        folder: Path,
        session: Session,
        customer_id: str,
        assessment_run_id: str,
    ) -> EntraParseResult:
        for fn in self.EXPECTED_FILES:
            if not (folder / fn).exists():
                raise FileNotFoundError(f"Missing expected Entra file: {folder / fn}")

        org = _load_first(folder / "organization.json")
        subs = _load(folder / "subscribedSkus.json").get("value", [])
        users = _load(folder / "users.json").get("value", [])
        roles = _load(folder / "directoryRoles.json").get("value", [])
        role_assignments = _load(folder / "roleAssignments.json").get("value", [])
        ca_policies = _load(folder / "conditionalAccessPolicies.json").get("value", [])
        applications = _load(folder / "applications.json").get("value", [])

        # 1. Owned SKUs + capabilities (licence-aware backbone).
        owned_internal_skus = [
            graph_sku_to_internal(s["skuId"])
            for s in subs
            if s.get("capabilityStatus", "").lower() == "enabled"
            and graph_sku_to_internal(s["skuId"]) is not None
        ]
        owned_internal_skus = sorted(set(s for s in owned_internal_skus if s))
        owned_capabilities = capabilities_for_skus(owned_internal_skus)

        # 2. Identity upserts — link cloud users to AD identities where possible.
        user_by_id: dict[str, dict] = {}
        for u in users:
            user_by_id[u["id"]] = u
            _upsert_entra_identity(
                session=session,
                customer_id=customer_id,
                graph_user=u,
            )
        session.flush()

        # 3. Role-aware enrichment: flag identities in Tier 0 roles privileged + tier0.
        role_template_by_id = {r["id"]: r["roleTemplateId"] for r in roles}
        tier0_principal_ids: set[str] = set()
        admin_assignments: list[dict] = []
        for ra in role_assignments:
            template = role_template_by_id.get(ra.get("roleDefinitionId"), ra.get("roleDefinitionId"))
            if template in TIER0_ROLE_TEMPLATE_IDS:
                tier0_principal_ids.add(ra["principalId"])
                admin_assignments.append(ra)
        # Promote identity flags.
        for principal_id in tier0_principal_ids:
            u = user_by_id.get(principal_id)
            if u is None:
                continue
            ident = _find_entra_identity(session=session, customer_id=customer_id, azure_object_id=u["id"])
            if ident is not None:
                ident.is_privileged = True
                ident.is_tier0 = True
        session.flush()

        # 4. Compute hybrid admin set (synced AD ↔ Tier 0 Entra role).
        hybrid_admin_records: list[dict] = []
        cloud_only_admin_count = 0
        for principal_id in tier0_principal_ids:
            u = user_by_id.get(principal_id, {})
            sid = u.get("onPremisesSecurityIdentifier")
            synced = bool(u.get("onPremisesSyncEnabled")) and (
                u.get("onPremisesImmutableId") or sid
            )
            if synced and sid:
                ad_ident = (
                    session.query(Identity)
                    .filter(
                        Identity.customer_id == customer_id,
                        Identity.sid == sid,
                    )
                    .one_or_none()
                )
                if ad_ident is not None:
                    hybrid_admin_records.append(
                        {
                            "entra_principal_id": principal_id,
                            "entra_upn": u.get("userPrincipalName"),
                            "entra_display_name": u.get("displayName"),
                            "ad_identity_id": ad_ident.id,
                            "ad_sam_account_name": ad_ident.sam_account_name,
                            "ad_sid": ad_ident.sid,
                            "is_ad_tier0": ad_ident.is_tier0,
                        }
                    )
                    continue
            if not synced:
                cloud_only_admin_count += 1

        # 5. Persist the consolidated Evidence row.
        evidence_payload = {
            "organization": org,
            "tenant_id": org.get("id"),
            "owned_sku_ids": owned_internal_skus,
            "owned_capabilities": sorted(owned_capabilities),
            "all_owned_capability_titles": sorted(
                CAPABILITY_TITLES.get(c, c) for c in owned_capabilities
            ),
            "subscribed_skus_raw": subs,
            "tier0_principal_ids": sorted(tier0_principal_ids),
            "hybrid_admin_records": hybrid_admin_records,
            "cloud_only_admin_count": cloud_only_admin_count,
            "conditional_access_policies": ca_policies,
            "applications_summary": [
                {
                    "id": a["id"],
                    "display_name": a.get("displayName"),
                    "credential_count": len(a.get("passwordCredentials") or []),
                    "oldest_secret_age_days": _oldest_secret_age_days(a),
                    "max_secret_lifetime_days": _max_secret_lifetime_days(a),
                }
                for a in applications
            ],
        }
        evidence = Evidence(
            assessment_run_id=assessment_run_id,
            module_id=self.module_id,
            evidence_type=self.evidence_type,
            parser_version=PARSER_VERSION,
            source_path=str(folder),
            payload=evidence_payload,
        )
        session.add(evidence)
        session.flush()

        # 6. Run the 6 POC controls inline.
        outcomes: list[ControlOutcome] = []
        outcomes.append(
            _entra_lic_001(
                session=session,
                assessment_run_id=assessment_run_id,
                owned_internal_skus=owned_internal_skus,
                owned_capabilities=owned_capabilities,
            )
        )
        outcomes.append(
            _entra_ca_001(
                session=session,
                assessment_run_id=assessment_run_id,
                ca_policies=ca_policies,
                owned_capabilities=owned_capabilities,
            )
        )
        outcomes.append(
            _entra_ca_003(
                session=session,
                assessment_run_id=assessment_run_id,
                ca_policies=ca_policies,
                owned_capabilities=owned_capabilities,
            )
        )
        outcomes.append(
            _entra_priv_003(
                session=session,
                assessment_run_id=assessment_run_id,
                owned_capabilities=owned_capabilities,
            )
        )
        outcomes.append(
            _entra_hybrid_001(
                session=session,
                assessment_run_id=assessment_run_id,
                hybrid_admin_records=hybrid_admin_records,
                customer_id=customer_id,
            )
        )
        outcomes.append(
            _entra_app_002(
                session=session,
                assessment_run_id=assessment_run_id,
                applications=applications,
                owned_capabilities=owned_capabilities,
            )
        )

        return EntraParseResult(
            evidence_id=evidence.id,
            organization_name=org.get("displayName", "Unknown"),
            tenant_id=org.get("id", ""),
            owned_sku_ids=owned_internal_skus,
            owned_capabilities=sorted(owned_capabilities),
            hybrid_admin_count=len(hybrid_admin_records),
            cloud_only_admin_count=cloud_only_admin_count,
            control_outcomes=outcomes,
        )


# --- Identity helpers ---------------------------------------------------------


def _upsert_entra_identity(
    *, session: Session, customer_id: str, graph_user: dict
) -> Identity:
    """Link or create an Identity row for a Graph user.

    Linking strategy (deterministic, no silent merges per A-0011):
      1. `onPremisesSecurityIdentifier` match → reuse the AD row, attach UPN
         + azure_object_id.
      2. `azure_object_id` match → reuse existing Entra row.
      3. New cloud-only row.
    """
    sid = graph_user.get("onPremisesSecurityIdentifier")
    azure_id = graph_user["id"]
    upn = graph_user.get("userPrincipalName")
    display = graph_user.get("displayName") or upn or azure_id

    if sid:
        existing = (
            session.query(Identity)
            .filter(Identity.customer_id == customer_id, Identity.sid == sid)
            .one_or_none()
        )
        if existing is not None:
            if not existing.azure_object_id:
                existing.azure_object_id = azure_id
            if upn and not existing.upn:
                existing.upn = upn
            return existing

    existing_az = (
        session.query(Identity)
        .filter(Identity.customer_id == customer_id, Identity.azure_object_id == azure_id)
        .one_or_none()
    )
    if existing_az is not None:
        if upn and not existing_az.upn:
            existing_az.upn = upn
        return existing_az

    ident = Identity(
        customer_id=customer_id,
        canonical_kind="user",
        canonical_label=display,
        upn=upn,
        azure_object_id=azure_id,
        sid=sid,
    )
    session.add(ident)
    return ident


def _find_entra_identity(
    *, session: Session, customer_id: str, azure_object_id: str
) -> Identity | None:
    return (
        session.query(Identity)
        .filter(
            Identity.customer_id == customer_id,
            Identity.azure_object_id == azure_object_id,
        )
        .one_or_none()
    )


# --- Secret-age helpers -------------------------------------------------------


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _oldest_secret_age_days(app: dict) -> int | None:
    creds = app.get("passwordCredentials") or []
    starts = [_parse_dt(c.get("startDateTime")) for c in creds]
    starts = [s for s in starts if s is not None]
    if not starts:
        return None
    now = datetime.now(UTC)
    return (now - min(starts)).days


def _max_secret_lifetime_days(app: dict) -> int | None:
    creds = app.get("passwordCredentials") or []
    spans = []
    for c in creds:
        start = _parse_dt(c.get("startDateTime"))
        end = _parse_dt(c.get("endDateTime"))
        if start and end:
            spans.append((end - start).days)
    return max(spans) if spans else None


# --- The six Entra controls ---------------------------------------------------


def _entra_lic_001(
    *,
    session: Session,
    assessment_run_id: str,
    owned_internal_skus: list[str],
    owned_capabilities: set[str],
) -> ControlOutcome:
    """ENTRA-LIC-001 — License & Capability detection (informational).
    Always evaluable; never blocks. License status is always
    `licensed_enabled` because the act of detection itself is the value."""
    titles = [SKU_CATALOG[s].title for s in owned_internal_skus if s in SKU_CATALOG]
    title_text = ", ".join(titles) if titles else "(no SKUs detected)"
    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category="entra.lic.detection",
        title=f"License profile detected: {title_text}",
        severity=Severity.INFO.value,
        risk_score=10,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            f"Detected {len(owned_internal_skus)} active Microsoft SKU(s): "
            f"{title_text}. Granted capabilities: "
            f"{', '.join(sorted(CAPABILITY_TITLES.get(c, c) for c in owned_capabilities))}."
        ),
        summary_customer=(
            f"Your tenant is licensed for: {title_text}. We score you only against "
            "the capabilities you actually own (D-0008)."
        ),
        technical_detail=(
            "Internal SKU ids: " + ", ".join(owned_internal_skus) + "\n"
            "Granted capability ids: " + ", ".join(sorted(owned_capabilities))
        ),
        remediation="No action required. License-aware scoring uses this profile.",
        payload={
            "owned_sku_ids": owned_internal_skus,
            "owned_capabilities": sorted(owned_capabilities),
            "template_id": "entra-lic-detection",
        },
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id="ENTRA-LIC-001",
        finding_id=finding.id,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        result_status="pass",
    )


def _entra_ca_001(
    *,
    session: Session,
    assessment_run_id: str,
    ca_policies: list[dict],
    owned_capabilities: set[str],
) -> ControlOutcome:
    """ENTRA-CA-001 — Baseline Conditional Access coverage.
    Requires capability `entra.conditional-access`. Evaluates whether at
    least one enabled policy enforces MFA on All Users."""
    if "entra.conditional-access" not in owned_capabilities:
        return _emit_not_licensed_finding(
            session=session,
            assessment_run_id=assessment_run_id,
            control_id="ENTRA-CA-001",
            title="Baseline Conditional Access coverage requires Conditional Access",
            missing_capability="entra.conditional-access",
        )

    enabled_all_user_mfa = any(
        p.get("state") == "enabled"
        and "All" in (p.get("conditions", {}).get("users", {}).get("includeUsers") or [])
        and "mfa" in (p.get("grantControls", {}) or {}).get("builtInControls", [])
        for p in ca_policies
    )
    severity = Severity.LOW.value if enabled_all_user_mfa else Severity.HIGH.value
    license_status = (
        LicenseStatus.LICENSED_ENABLED.value
        if enabled_all_user_mfa
        else LicenseStatus.LICENSED_DISABLED.value
    )
    risk_score = 15 if enabled_all_user_mfa else 70
    title = (
        "Baseline Conditional Access — MFA for all users (enabled)"
        if enabled_all_user_mfa
        else "Baseline Conditional Access — MFA for all users (NOT enforced)"
    )
    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category="entra.ca.baseline",
        title=title,
        severity=severity,
        risk_score=risk_score,
        license_status=license_status,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            "Conditional Access is licensed (Entra ID P1). "
            + (
                "A baseline MFA policy is enabled for All Users — good. "
                "Recommend verifying exclusions and break-glass handling."
                if enabled_all_user_mfa
                else "No enabled policy enforces MFA on All Users. This is the "
                "single most impactful Conditional Access control."
            )
        ),
        summary_customer=(
            "Multi-factor authentication is the single most impactful identity "
            "control. " + (
                "Your baseline MFA-for-all policy is enabled."
                if enabled_all_user_mfa
                else "We did not find an enabled policy that enforces MFA for all users."
            )
        ),
        technical_detail=(
            "Enabled CA policies: "
            + ", ".join(p["displayName"] for p in ca_policies if p.get("state") == "enabled")
        ),
        remediation=(
            ""
            if enabled_all_user_mfa
            else "Enable a Conditional Access policy that requires MFA for All Users "
            "with explicit exclusions only for break-glass accounts."
        ),
        payload={
            "ca_policy_count": len(ca_policies),
            "enabled_count": sum(1 for p in ca_policies if p.get("state") == "enabled"),
            "template_id": "entra-ca-baseline",
        },
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id="ENTRA-CA-001",
        finding_id=finding.id,
        license_status=license_status,
        result_status="pass" if enabled_all_user_mfa else "fail",
    )


def _entra_ca_003(
    *,
    session: Session,
    assessment_run_id: str,
    ca_policies: list[dict],
    owned_capabilities: set[str],
) -> ControlOutcome:
    """ENTRA-CA-003 — Legacy authentication blocked.
    The headline `licensed_disabled` demonstrator (per POC_V1_SCOPE §4 step 7).
    """
    if "entra.conditional-access" not in owned_capabilities:
        return _emit_not_licensed_finding(
            session=session,
            assessment_run_id=assessment_run_id,
            control_id="ENTRA-CA-003",
            title="Block legacy authentication requires Conditional Access",
            missing_capability="entra.conditional-access",
        )

    blocking_legacy_auth = any(
        p.get("state") == "enabled"
        and "block" in (p.get("grantControls", {}) or {}).get("builtInControls", [])
        and {"exchangeActiveSync", "other"}
        & set(p.get("conditions", {}).get("clientAppTypes", []))
        for p in ca_policies
    )

    title = (
        "Legacy authentication is blocked"
        if blocking_legacy_auth
        else "Legacy authentication is NOT blocked (policy exists but disabled)"
    )
    severity = Severity.LOW.value if blocking_legacy_auth else Severity.HIGH.value
    license_status = (
        LicenseStatus.LICENSED_ENABLED.value
        if blocking_legacy_auth
        else LicenseStatus.LICENSED_DISABLED.value
    )
    risk_score = 10 if blocking_legacy_auth else 68

    legacy_policy = next(
        (p for p in ca_policies if "legacy" in p.get("displayName", "").lower()), None
    )

    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category="entra.ca.legacy_auth",
        title=title,
        severity=severity,
        risk_score=risk_score,
        license_status=license_status,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            "Conditional Access is licensed (Entra ID P1). "
            + (
                "An enabled policy blocks legacy auth — good."
                if blocking_legacy_auth
                else f"A 'Block legacy authentication' policy exists "
                f"({legacy_policy['displayName'] if legacy_policy else 'unknown'}) "
                "but is currently disabled. Legacy authentication bypasses Conditional "
                "Access and MFA — this is a classic gap."
            )
        ),
        summary_customer=(
            "Legacy authentication protocols can bypass modern security controls "
            "like MFA. " + (
                "Your tenant blocks them."
                if blocking_legacy_auth
                else "A policy is drafted but currently turned off; we recommend enabling it."
            )
        ),
        technical_detail=(
            f"Legacy auth policy state: {legacy_policy.get('state') if legacy_policy else 'not found'}\n"
            f"All enabled CA policies: "
            + ", ".join(p["displayName"] for p in ca_policies if p.get("state") == "enabled")
        ),
        remediation=(
            ""
            if blocking_legacy_auth
            else "1. Audit legacy-protocol usage in Sign-in logs.\n"
            "2. Enable the existing 'Block legacy authentication' policy "
            "after the audit confirms no production traffic depends on it.\n"
            "3. Consider rolling out gradually with a pilot group."
        ),
        payload={"template_id": "entra-ca-legacy-auth"},
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id="ENTRA-CA-003",
        finding_id=finding.id,
        license_status=license_status,
        result_status="pass" if blocking_legacy_auth else "fail",
    )


def _entra_priv_003(
    *,
    session: Session,
    assessment_run_id: str,
    owned_capabilities: set[str],
) -> ControlOutcome:
    """ENTRA-PRIV-003 — PIM eligibility coverage.
    The headline `not_licensed` demonstrator: PIM requires Entra ID P2."""
    if "entra.pim" not in owned_capabilities:
        return _emit_not_licensed_finding(
            session=session,
            assessment_run_id=assessment_run_id,
            control_id="ENTRA-PRIV-003",
            title="PIM eligibility coverage requires Entra ID P2",
            missing_capability="entra.pim",
        )
    # Owned-path is uninteresting for the slice — when Contoso adds P2, this
    # control starts evaluating real PIM eligibility coverage.
    return ControlOutcome(
        control_id="ENTRA-PRIV-003",
        finding_id=None,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        result_status="unknown",
    )


def _entra_hybrid_001(
    *,
    session: Session,
    assessment_run_id: str,
    hybrid_admin_records: list[dict],
    customer_id: str,  # noqa: ARG001 — kept for symmetry with sibling control fns
) -> ControlOutcome:
    """ENTRA-HYBRID-001 — Synced privileged accounts.
    Captures the cross-module bridge: AD privileged identity is also an
    Entra Tier 0 role assignee."""
    if not hybrid_admin_records:
        return ControlOutcome(
            control_id="ENTRA-HYBRID-001",
            finding_id=None,
            license_status=LicenseStatus.LICENSED_ENABLED.value,
            result_status="pass",
        )

    identity_refs = [r["ad_identity_id"] for r in hybrid_admin_records if r.get("ad_identity_id")]
    names = ", ".join(f"`{r['ad_sam_account_name']}`" for r in hybrid_admin_records)
    tier0_hybrid = [r for r in hybrid_admin_records if r.get("is_ad_tier0")]
    severity = Severity.HIGH.value if tier0_hybrid else Severity.MEDIUM.value
    risk = 75 if tier0_hybrid else 50

    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category="entra.hybrid.synced_privileged",
        title=(
            f"{len(hybrid_admin_records)} synced privileged identity"
            f"{'ies' if len(hybrid_admin_records) != 1 else ''} bridges AD and Entra"
        ),
        severity=severity,
        risk_score=risk,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            f"Detected {len(hybrid_admin_records)} hybrid admin{'s' if len(hybrid_admin_records) != 1 else ''} "
            f"(AD Tier 0: {len(tier0_hybrid)}): {names}. "
            "Compromise of the on-prem AD account compromises the cloud admin role and vice versa."
        ),
        summary_customer=(
            "Some of your privileged Entra ID administrators are synchronised from "
            "Active Directory. If an attacker compromises the on-prem account, they also "
            "control the cloud admin role — this 'hybrid admin bridge' deserves special handling."
        ),
        technical_detail=(
            "Hybrid admin records:\n"
            + "\n".join(
                f"  - AD `{r['ad_sam_account_name']}` (SID {r['ad_sid']}) "
                f"↔ Entra `{r['entra_upn']}` (Tier 0 AD: {r['is_ad_tier0']})"
                for r in hybrid_admin_records
            )
        ),
        remediation=(
            "1. Move hybrid admins to cloud-only privileged identities where possible.\n"
            "2. For unavoidable hybrid admins, apply Tier 0 controls on the AD side "
            "(strong password / PAW / restricted logon) AND PIM / phishing-resistant "
            "MFA on the cloud side.\n"
            "3. Consider Entra Connect cloud sync exclusion for admin accounts."
        ),
        payload={
            "hybrid_admin_records": hybrid_admin_records,
            "tier0_hybrid_count": len(tier0_hybrid),
            "template_id": "entra-hybrid-001",
        },
        identity_refs=identity_refs,
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id="ENTRA-HYBRID-001",
        finding_id=finding.id,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        result_status="fail" if tier0_hybrid else "partial",
    )


def _entra_app_002(
    *,
    session: Session,
    assessment_run_id: str,
    applications: list[dict],
    owned_capabilities: set[str],  # noqa: ARG001 — kept for signature symmetry
) -> ControlOutcome:
    """ENTRA-APP-002 — Long-lived client secrets."""
    flagged: list[dict] = []
    for app in applications:
        max_lifetime = _max_secret_lifetime_days(app)
        if max_lifetime and max_lifetime >= LONG_LIVED_DAYS:
            flagged.append(
                {
                    "app_id": app["id"],
                    "display_name": app.get("displayName"),
                    "max_lifetime_days": max_lifetime,
                    "credential_count": len(app.get("passwordCredentials") or []),
                }
            )

    if not flagged:
        return ControlOutcome(
            control_id="ENTRA-APP-002",
            finding_id=None,
            license_status=LicenseStatus.LICENSED_ENABLED.value,
            result_status="pass",
        )

    severity = Severity.MEDIUM.value
    risk = 55
    names = ", ".join(f"`{f['display_name']}`" for f in flagged)
    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category="entra.app.long_lived_secrets",
        title=f"{len(flagged)} application{'s' if len(flagged) != 1 else ''} use long-lived client secrets",
        severity=severity,
        risk_score=risk,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            f"Detected {len(flagged)} app(s) with at least one client secret valid "
            f"for ≥ {LONG_LIVED_DAYS} days: {names}. Long-lived secrets are a credential-theft amplifier."
        ),
        summary_customer=(
            "Some of your applications use very long-lived passwords (client secrets). "
            "Shorter rotations dramatically reduce the impact of a leaked secret."
        ),
        technical_detail=(
            "Flagged applications:\n"
            + "\n".join(
                f"  - {f['display_name']} (max lifetime: {f['max_lifetime_days']} days, "
                f"{f['credential_count']} credentials)"
                for f in flagged
            )
        ),
        remediation=(
            "1. Replace client secrets with certificate-based credentials where possible.\n"
            "2. Set a maximum lifetime policy (e.g., 6 months) on app credentials.\n"
            "3. Audit the listed apps and rotate immediately."
        ),
        payload={"flagged": flagged, "template_id": "entra-app-long-lived-secrets"},
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id="ENTRA-APP-002",
        finding_id=finding.id,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        result_status="fail",
    )


def _emit_not_licensed_finding(
    *,
    session: Session,
    assessment_run_id: str,
    control_id: str,
    title: str,
    missing_capability: str,
) -> ControlOutcome:
    """Shared helper — emit a `not_licensed` finding that demonstrates the
    license-aware UI without penalising the Current License Score (D-0008)."""
    cap_title = CAPABILITY_TITLES.get(missing_capability, missing_capability)
    upgrade = upgrade_path_for(missing_capability)
    upgrade_title = SKU_CATALOG[upgrade].title if upgrade and upgrade in SKU_CATALOG else "a higher SKU"

    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="entra",
        category=f"entra.lic.not_licensed.{missing_capability}",
        title=title,
        severity=Severity.INFO.value,
        risk_score=15,
        license_status=LicenseStatus.NOT_LICENSED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            f"Control `{control_id}` could not be evaluated because the required "
            f"capability `{cap_title}` is not owned by the tenant. "
            f"This does NOT reduce the Current License Score (D-0008); it contributes to "
            f"the Opportunity gap toward Target Posture."
        ),
        summary_customer=(
            f"Your tenant does not own the {cap_title} capability, so this control was not "
            f"evaluated. If you add {upgrade_title}, ACEN will start scoring this area against "
            "your target posture."
        ),
        technical_detail=(
            f"Missing capability id: {missing_capability}\n"
            f"Cheapest upgrade SKU (POC catalog): {upgrade_title}\n"
            f"License-aware status: not_licensed (excluded from Current License Score, "
            "counts toward Target Posture gap)."
        ),
        remediation=(
            f"This is a commercial decision, not a configuration fix. If your posture "
            f"target includes {cap_title}, consider adding {upgrade_title}. Otherwise no "
            "action is required."
        ),
        payload={
            "control_id": control_id,
            "missing_capability": missing_capability,
            "upgrade_path": upgrade,
            "template_id": "entra-not-licensed",
        },
    )
    session.add(finding)
    session.flush()
    return ControlOutcome(
        control_id=control_id,
        finding_id=finding.id,
        license_status=LicenseStatus.NOT_LICENSED.value,
        result_status="not_applicable",
    )


# --- File helpers -------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_first(path: Path) -> dict[str, Any]:
    data = _load(path)
    values = data.get("value", [])
    if not values:
        return {}
    return values[0]
