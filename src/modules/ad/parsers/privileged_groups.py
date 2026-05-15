"""Parser for the AD privileged-groups evidence file (Stage 9 slice).

Reads `ad/privileged-groups.json` from the Contoso fixture (and from real
toolkit ZIPs at MVP). Produces:

  - One `Evidence` row tagged `privileged-groups` with the raw JSON payload.
  - One `Identity` row per principal in the file (idempotent on (customer, sid)).
  - `is_privileged` / `is_tier0` flags on principals that belong to a Tier 0 group
    (per the file's `tier == 0` annotation).

POC scope: minimal. Does not yet derive recursive group membership, GPO-applied
admin rights, or constrained delegation — those are MVP/full-product expansions
per `AD_MODULE_DESIGN.md`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from platform_core.evidence.models import Evidence
from platform_core.identity.models import Identity

PARSER_VERSION = "0.1.0"


@dataclass(frozen=True)
class PrivilegedGroupsParseResult:
    evidence_id: str
    identities_created: int
    identities_updated: int
    tier0_count: int
    domain_sid: str


class PrivilegedGroupsParser:
    """Stage-9-slice parser for `ad/privileged-groups.json`."""

    evidence_type = "privileged-groups"
    module_id = "ad"

    def parse(
        self,
        *,
        path: Path,
        session: Session,
        customer_id: str,
        assessment_run_id: str,
    ) -> PrivilegedGroupsParseResult:
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)

        if payload.get("schema") != "ad-privileged-groups/v1":
            raise ValueError(
                f"Unexpected schema {payload.get('schema')!r} — expected "
                "'ad-privileged-groups/v1'."
            )

        domain_sid = payload["domain_sid"]
        groups = payload.get("groups", [])

        # 1. Persist the evidence row (one per parse).
        evidence = Evidence(
            assessment_run_id=assessment_run_id,
            module_id=self.module_id,
            evidence_type=self.evidence_type,
            parser_version=PARSER_VERSION,
            source_path=str(path),
            payload=payload,
        )
        session.add(evidence)
        session.flush()  # need evidence.id

        # 2. Upsert identities — group rows + their member rows.
        created = 0
        updated = 0
        tier0 = 0

        for group in groups:
            tier = int(group.get("tier", 99))
            is_tier0 = tier == 0

            group_identity = self._upsert_identity(
                session=session,
                customer_id=customer_id,
                kind="group",
                label=group["name"],
                sid=group["sid"],
                object_guid=None,
                sam_account_name=None,
                is_privileged=True,
                is_tier0=is_tier0,
            )
            if group_identity._was_created:
                created += 1
            else:
                updated += 1
            if is_tier0:
                tier0 += 1

            for member in group.get("members", []):
                member_identity = self._upsert_identity(
                    session=session,
                    customer_id=customer_id,
                    kind=_member_kind(member),
                    label=member["sam_account_name"],
                    sid=member["sid"],
                    object_guid=member.get("object_guid"),
                    sam_account_name=member["sam_account_name"],
                    is_privileged=True,
                    is_tier0=is_tier0,
                )
                if member_identity._was_created:
                    created += 1
                else:
                    updated += 1

        return PrivilegedGroupsParseResult(
            evidence_id=evidence.id,
            identities_created=created,
            identities_updated=updated,
            tier0_count=tier0,
            domain_sid=domain_sid,
        )

    @staticmethod
    def _upsert_identity(
        *,
        session: Session,
        customer_id: str,
        kind: str,
        label: str,
        sid: str,
        object_guid: str | None,
        sam_account_name: str | None,
        is_privileged: bool,
        is_tier0: bool,
    ) -> Identity:
        existing = (
            session.query(Identity)
            .filter(Identity.customer_id == customer_id, Identity.sid == sid)
            .one_or_none()
        )
        if existing is None:
            identity = Identity(
                customer_id=customer_id,
                canonical_kind=kind,
                canonical_label=label,
                sid=sid,
                object_guid=object_guid,
                sam_account_name=sam_account_name,
                is_privileged=is_privileged,
                is_tier0=is_tier0,
            )
            session.add(identity)
            session.flush()
            identity._was_created = True  # type: ignore[attr-defined]
            return identity

        # Promote-only updates: never demote a flag once true.
        existing.is_privileged = existing.is_privileged or is_privileged
        existing.is_tier0 = existing.is_tier0 or is_tier0
        if existing.canonical_label != label:
            existing.canonical_label = label
        if object_guid and not existing.object_guid:
            existing.object_guid = object_guid
        if sam_account_name and not existing.sam_account_name:
            existing.sam_account_name = sam_account_name
        existing._was_created = False  # type: ignore[attr-defined]
        return existing


def _member_kind(member: dict) -> str:
    raw = member.get("kind", "user")
    if raw == "computer":
        return "computer"
    if raw == "group":
        return "group"
    if member.get("is_service_account"):
        return "service_account"
    return "user"
