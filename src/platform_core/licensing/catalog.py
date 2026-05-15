"""POC license catalog — small hand-curated mapping from Microsoft Graph SKU
identifiers to our internal capability ids.

POC scope (per `LICENSE_MODEL.md` §5 + A-0014):
  - Only the SKUs Contoso owns or might reasonably own are listed here.
  - Mapping is by **Graph SKU ID** (the UUID from `subscribedSkus`).
  - Capability ids match `LICENSE_MODEL.md` §5.3.

At MVP we replace this with an authoritative source (Microsoft service-plan
catalog via Graph + official docs).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- SKU ID → internal SKU metadata --------------------------------------------

# Microsoft Graph `subscribedSkus[].skuId` UUIDs (well-known).
# We only need the SKUs that appear in our POC catalog.
GRAPH_SKU_TO_INTERNAL: dict[str, str] = {
    "05e9a617-0261-4cee-bb44-138d3ef5d965": "m365-e3",
    "06ebc4ee-1bb5-47dd-8120-11324bc54e06": "m365-e5",
    "078d2b04-f1bd-4111-bbd4-b4b1b354cef4": "entra-id-p1",
    "84a661c4-e949-4bd2-a560-ed7766fcaf2b": "entra-id-p2",
    "efccb6f7-5641-4e0e-bd10-b4976e1bf68e": "ems-e3",
    "b05e124f-c7cc-45a0-a6aa-8cf78c946968": "ems-e5",
    "16ddbbfc-09ea-4de2-b1d7-312db6112d70": "defender-for-identity-standalone",
}


@dataclass(frozen=True)
class Sku:
    id: str
    title: str
    capabilities: frozenset[str] = field(default_factory=frozenset)


# Internal SKU catalog → capability set.
SKU_CATALOG: dict[str, Sku] = {
    "m365-e3": Sku(
        id="m365-e3",
        title="Microsoft 365 E3",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
            }
        ),
    ),
    "m365-e5": Sku(
        id="m365-e5",
        title="Microsoft 365 E5",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
                "entra.pim",
                "entra.identity-protection.risky-users",
                "entra.identity-protection.risky-signins",
                "entra.access-reviews",
                "entra.entitlement-management",
                "defender-identity.lateral-movement-detection",
            }
        ),
    ),
    "entra-id-p1": Sku(
        id="entra-id-p1",
        title="Entra ID P1 (standalone)",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
            }
        ),
    ),
    "entra-id-p2": Sku(
        id="entra-id-p2",
        title="Entra ID P2 (standalone)",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
                "entra.pim",
                "entra.identity-protection.risky-users",
                "entra.identity-protection.risky-signins",
                "entra.access-reviews",
                "entra.entitlement-management",
            }
        ),
    ),
    "ems-e3": Sku(
        id="ems-e3",
        title="Enterprise Mobility + Security E3",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
            }
        ),
    ),
    "ems-e5": Sku(
        id="ems-e5",
        title="Enterprise Mobility + Security E5",
        capabilities=frozenset(
            {
                "entra.conditional-access",
                "entra.mfa.enforcement",
                "entra.authentication-methods-policy",
                "entra.basic-mfa-registration",
                "entra.pim",
                "entra.identity-protection.risky-users",
                "entra.identity-protection.risky-signins",
                "entra.access-reviews",
                "entra.entitlement-management",
                "defender-identity.lateral-movement-detection",
            }
        ),
    ),
    "defender-for-identity-standalone": Sku(
        id="defender-for-identity-standalone",
        title="Defender for Identity (standalone)",
        capabilities=frozenset({"defender-identity.lateral-movement-detection"}),
    ),
    "silverfort-standard": Sku(
        id="silverfort-standard",
        title="Silverfort",
        capabilities=frozenset(
            {
                "silverfort.policy-engine",
                "silverfort.service-account-protection",
                "silverfort.privileged-mfa",
            }
        ),
    ),
}


@dataclass(frozen=True)
class Capability:
    id: str
    title: str


CAPABILITY_TITLES: dict[str, str] = {
    "entra.conditional-access":                       "Conditional Access",
    "entra.mfa.enforcement":                          "MFA enforcement",
    "entra.authentication-methods-policy":            "Authentication methods policy",
    "entra.basic-mfa-registration":                   "Basic MFA registration",
    "entra.pim":                                      "Privileged Identity Management",
    "entra.identity-protection.risky-users":          "Identity Protection — risky users",
    "entra.identity-protection.risky-signins":        "Identity Protection — risky sign-ins",
    "entra.access-reviews":                           "Access Reviews",
    "entra.entitlement-management":                   "Entitlement Management",
    "defender-identity.lateral-movement-detection":   "Defender for Identity — lateral movement",
    "silverfort.policy-engine":                       "Silverfort policy engine",
    "silverfort.service-account-protection":          "Silverfort service-account protection",
    "silverfort.privileged-mfa":                      "Silverfort privileged MFA",
}


def graph_sku_to_internal(graph_sku_id: str) -> str | None:
    return GRAPH_SKU_TO_INTERNAL.get(graph_sku_id.lower())


def capabilities_for_skus(internal_sku_ids: list[str]) -> set[str]:
    """Union of capabilities granted by the given owned SKUs."""
    caps: set[str] = set()
    for sid in internal_sku_ids:
        sku = SKU_CATALOG.get(sid)
        if sku is not None:
            caps |= set(sku.capabilities)
    return caps


def upgrade_path_for(missing_capability: str) -> str | None:
    """Cheapest SKU that grants the missing capability. Used for the
    Opportunity card on the Entra page."""
    candidates = [
        sku for sku in SKU_CATALOG.values() if missing_capability in sku.capabilities
    ]
    if not candidates:
        return None
    # Cheapest-by-name heuristic — P2 before E5; deterministic ordering by id.
    ordered = sorted(candidates, key=lambda s: (len(s.capabilities), s.id))
    return ordered[0].id if ordered else None
