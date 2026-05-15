"""Silverfort manual-export parser (Stage 9 slice).

POC scope — manual export bundle only. The API connector is **design-only**
per D-0006: every endpoint claim in `SILVERFORT_MODULE_DESIGN.md` is tagged
"(unverified — requires Silverfort validation)". This parser reads a
hand-built JSON bundle that mirrors what a customer would export from
their Silverfort UI.

Coverage logic (slice-minimum):
  For each enabled policy:
    covered_sids ← direct target_user_sids
    if policy targets any Tier 0 group SID, fold in every Identity row in
      this customer that is `is_tier0=True` and `canonical_kind=user/service_account`
    covered_sids -= excluded_user_sids
  Total covered = union over enabled policies.

Then we compute `uncovered_tier0_sids` = (Tier 0 user identities) − covered.
That set drives the SF-AD-001 Finding **and** seeds the BH↔SF correlation in
`platform_core.correlations`.

Real group expansion (recursive nested groups, OUs, etc.) lands at MVP once
the SF API connector is validated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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

PARSER_VERSION = "0.1.0"

# Well-known Tier 0 group RIDs (subset shared with the BH analyzer).
TIER0_GROUP_RIDS: frozenset[str] = frozenset({"512", "519", "518", "516", "517"})


@dataclass(frozen=True)
class SilverfortParseResult:
    evidence_id: str
    policy_count: int
    enabled_policy_count: int
    covered_count: int
    uncovered_tier0_count: int
    sf_finding_id: str | None


class SilverfortExportParser:
    evidence_type = "silverfort-export"
    module_id = "silverfort"

    def parse(
        self,
        *,
        path: Path,
        session: Session,
        customer_id: str,
        assessment_run_id: str,
    ) -> SilverfortParseResult:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        if data.get("schema") != "silverfort-export/v1":
            raise ValueError(
                f"Unexpected schema {data.get('schema')!r} — expected "
                "'silverfort-export/v1'."
            )

        policies = data.get("policies", [])
        enabled = [p for p in policies if p.get("enabled")]

        # Tier 0 user/service-account identities for this customer.
        tier0_user_identities = (
            session.query(Identity)
            .filter(
                Identity.customer_id == customer_id,
                Identity.is_tier0.is_(True),
                Identity.canonical_kind.in_(("user", "service_account")),
            )
            .all()
        )
        tier0_sid_to_label = {i.sid: i.canonical_label for i in tier0_user_identities if i.sid}

        # Compute coverage.
        covered_sids: set[str] = set()
        excluded_sids: set[str] = set()
        for policy in enabled:
            direct = set(policy.get("target_user_sids", []))
            covered_sids.update(direct)
            # Group targeting: if the policy targets any well-known Tier 0 group,
            # fold in every Tier 0 user identity. This is the slice's
            # group-expansion stand-in (full recursive expansion lands at MVP).
            for group_sid in policy.get("target_group_sids", []):
                rid = group_sid.rsplit("-", 1)[-1]
                if rid in TIER0_GROUP_RIDS:
                    covered_sids.update(tier0_sid_to_label.keys())
                    break
            excluded_sids.update(policy.get("excluded_user_sids", []))
        covered_sids -= excluded_sids

        uncovered_tier0_sids = sorted(set(tier0_sid_to_label) - covered_sids)

        payload = {
            "tenant": data.get("tenant", {}),
            "policies": policies,
            "covered_sids": sorted(covered_sids),
            "uncovered_tier0_sids": uncovered_tier0_sids,
            "uncovered_tier0_labels": [
                tier0_sid_to_label[s] for s in uncovered_tier0_sids if s in tier0_sid_to_label
            ],
        }

        evidence = Evidence(
            assessment_run_id=assessment_run_id,
            module_id=self.module_id,
            evidence_type=self.evidence_type,
            parser_version=PARSER_VERSION,
            source_path=str(path),
            payload=payload,
        )
        session.add(evidence)
        session.flush()

        sf_finding_id: str | None = None
        if uncovered_tier0_sids:
            sf_finding_id = _emit_sf_ad_001(
                session=session,
                assessment_run_id=assessment_run_id,
                customer_id=customer_id,
                uncovered_sids=uncovered_tier0_sids,
                uncovered_labels=payload["uncovered_tier0_labels"],
                excluded_explanations=[
                    {
                        "policy_id": p["id"],
                        "policy_name": p.get("name", p["id"]),
                        "excluded_user_sids": p.get("excluded_user_sids", []),
                    }
                    for p in enabled
                    if p.get("excluded_user_sids")
                ],
            )

        return SilverfortParseResult(
            evidence_id=evidence.id,
            policy_count=len(policies),
            enabled_policy_count=len(enabled),
            covered_count=len(covered_sids),
            uncovered_tier0_count=len(uncovered_tier0_sids),
            sf_finding_id=sf_finding_id,
        )


def _emit_sf_ad_001(
    *,
    session: Session,
    assessment_run_id: str,
    customer_id: str,
    uncovered_sids: list[str],
    uncovered_labels: list[str],
    excluded_explanations: list[dict],
) -> str:
    """SF-AD-001 — Tier 0 Coverage Gap."""
    identity_refs = [
        i.id
        for i in (
            session.query(Identity)
            .filter(Identity.customer_id == customer_id, Identity.sid.in_(uncovered_sids))
            .all()
        )
    ]

    names = ", ".join(f"`{lbl}`" for lbl in uncovered_labels) or "(none)"
    finding = Finding(
        assessment_run_id=assessment_run_id,
        module_id="silverfort",
        category="sf.ad.tier0_coverage_gap",
        title=f"Tier 0 coverage gap: {len(uncovered_sids)} privileged identity"
        f"{'' if len(uncovered_sids) == 1 else 'ies'} not covered by Silverfort",
        severity=Severity.HIGH.value,
        risk_score=72,
        license_status=LicenseStatus.LICENSED_ENABLED.value,
        state=FindingState.NEW.value,
        customer_visibility=CustomerVisibility.INTERNAL_ONLY.value,
        summary_internal=(
            f"Silverfort policies cover most Tier 0 identities, but {len(uncovered_sids)} "
            f"privileged identity {'is' if len(uncovered_sids) == 1 else 'are'} "
            f"explicitly excluded from coverage: {names}. "
            "Any attacker who reaches one of these accounts (e.g., via a BloodHound path) "
            "would face no Silverfort enforcement on authentication."
        ),
        summary_customer=(
            "Most of your privileged accounts are protected by Silverfort, but a small "
            "number are intentionally excluded. An attacker who reaches one of these "
            "accounts would face no additional authentication challenge, eliminating the "
            "Silverfort safety net for that path."
        ),
        technical_detail=(
            "Uncovered Tier 0 SIDs:\n"
            + "\n".join(f"  - {sid} ({lbl})" for sid, lbl in zip(uncovered_sids, uncovered_labels, strict=False))
            + "\n\nExcluded by policy:\n"
            + "\n".join(
                f"  - {e['policy_name']} ({e['policy_id']}): {', '.join(e['excluded_user_sids'])}"
                for e in excluded_explanations
            )
        ),
        remediation=(
            "1. Review each policy exclusion and confirm the business reason (e.g., a "
            "backup job that cannot interactively MFA).\n"
            "2. Where possible, replace the exclusion with a source-host or service-host "
            "restriction policy (Silverfort `restrict_source` action) so the account is "
            "still protected outside its expected use.\n"
            "3. Where exclusions are truly required, add compensating controls: "
            "credential vaulting, scheduled credential rotation, restricted logon hours."
        ),
        payload={
            "uncovered_tier0_sids": uncovered_sids,
            "uncovered_tier0_labels": uncovered_labels,
            "excluded_explanations": excluded_explanations,
            "template_id": "sf-ad-tier0-coverage-gap",
        },
        identity_refs=identity_refs,
    )
    session.add(finding)
    session.flush()
    return finding.id
