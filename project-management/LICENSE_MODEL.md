# LICENSE_MODEL.md

> The license-awareness model. Defines vendors, SKUs, capabilities, statuses, and scoring formulas — so that customers are scored only against capabilities they actually own, while a separate Target Posture Score shows the gap to a stronger posture.
>
> Companion: `PRODUCT_DESIGN.md` §25 Scoring, `MODULE_ARCHITECTURE.md` §12 Scoring.

---

## 1. Why this model exists

Without license-awareness, a security score becomes commercially dishonest: customers are penalized for unowned features (e.g., Entra ID Identity Protection) and the consultant loses credibility. With license-awareness:

- The **Current License Security Score** reflects what the customer is doing with what they own.
- The **Target Security Posture Score** reflects how close the customer is to a stronger recommended posture, regardless of current licensing.
- The **Opportunity Score** (the gap between the two) becomes the natural commercial conversation: *"With Entra ID P2 + Identity Protection, you would close X points of risk."*

This is a **commercial differentiator** and a **trust signal**. It is also a **complexity risk** — the catalog can grow unbounded. We keep it small and explicit.

---

## 2. Core model

The license model is a small graph:

```
Vendor ──< Product ──< Sku ──< Capability ──< Control ──< Finding
                                         (license_status)
```

Where:

- **Vendor** — Microsoft, Silverfort, Imprivata, Cato, Illumio, ACEN-advisory.
- **Product** — a vendor's named offering (e.g., "Microsoft 365", "Entra ID", "Defender for Identity", "Silverfort").
- **Sku** — a licensable plan/SKU (e.g., "Microsoft 365 E5", "Entra ID P2", "Microsoft 365 E3", "Silverfort Standard").
- **Capability** — a discrete feature/control surface (e.g., "Conditional Access", "PIM", "Identity Protection — Risky Users", "Identity Protection — Risky Sign-ins", "MFA Enforcement", "Privileged Identity Risk Detection", "Silverfort Policy Engine").
- **Control** — a platform control (`ENTRA-CA-001` Baseline Conditional Access Coverage, etc.).
- **Finding** — emitted when a control fails, partial, or unknown.

A capability is **owned** by a customer if **any** of the customer's owned SKUs includes it. A capability can be in many SKUs; a control can depend on one or more capabilities.

---

## 3. License-aware status enum (8 values)

From D-0007. Plus three operational flags. These describe the **license context** for a control result.

| Value | Meaning | Affects Current Score? | Affects Target Score? |
|---|---|:---:|:---:|
| `licensed_enabled` | Customer owns the capability; it is configured and active | ✅ scored | ✅ scored |
| `licensed_disabled` | Customer owns the capability; it is not configured or disabled | ✅ scored (down) | ✅ scored (down) |
| `licensed_misconfigured` | Customer owns and uses the capability, but with weakening misconfiguration | ✅ scored (down) | ✅ scored (down) |
| `not_licensed` | Customer does not own the capability via any current SKU | ⛔ excluded | ✅ counted as fail vs target |
| `requires_add_on` | Capability exists in the same product family but requires an add-on the customer does not own (e.g., Defender for Identity add-on) | ⛔ excluded | ✅ counted as fail vs target |
| `available_in_higher_tier` | Capability is available in a higher-tier SKU than the customer owns (e.g., from E3 → E5) | ⛔ excluded | ✅ counted as fail vs target |
| `not_applicable` | Control does not apply to this customer's environment (e.g., a hybrid-specific control on cloud-only tenant) | ⛔ excluded | ⛔ excluded |
| `unknown` | Cannot be determined (evidence missing or ambiguous) | ⛔ excluded; flagged | ⛔ excluded; flagged |

Operational flags (orthogonal to `license_status`, can co-occur):

- `connector_missing` — control depends on data from a connector that is not configured (POC: many controls show this for live-only sources).
- `evidence_missing` — required evidence was not uploaded.
- `manual_review_required` — control rubric requires a consultant to confirm.

These flags **always result in `license_status = unknown` or `not_applicable`** depending on the rubric.

---

## 4. Catalog model (data)

### 4.1 Tables (POC SQLAlchemy)

```python
class Vendor(Base):
    id: str           # "microsoft", "silverfort", "imprivata", "cato", "illumio", "acen-advisory"
    title: str

class Product(Base):
    id: str           # "m365", "entra-id", "defender-for-identity", "silverfort", ...
    vendor_id: str
    title: str

class Sku(Base):
    id: str           # stable string id
    vendor_id: str
    product_id: str   # primary product
    title: str        # "Microsoft 365 E5"
    service_plan_id: str | None    # Microsoft service plan GUID where applicable
    notes: str

class Capability(Base):
    id: str           # "entra.conditional-access", "entra.pim", "entra.identity-protection.risky-users", ...
    title: str
    description: str

class SkuCapability(Base):
    sku_id: str
    capability_id: str
    requires_add_on: bool = False
    add_on_sku_id: str | None

class ControlCapability(Base):
    control_id: str
    capability_id: str
    role: enum("required", "preferred")
    # required = absence => not_licensed; preferred = absence => available_in_higher_tier or requires_add_on

class CustomerSku(Base):
    customer_id: UUID
    sku_id: str
    quantity: int | None
    confirmed_by: enum("consultant", "graph", "import")
    confirmed_at: datetime
    notes: str | None
```

### 4.2 Resolution

For a customer:

1. Collect their owned SKU ids from `CustomerSku`.
2. Resolve owned capabilities = union of `SkuCapability` for those SKUs (respecting `requires_add_on`).
3. For each control, compute `license_status` from owned capabilities and the control's `ControlCapability` rows.

The capability resolver is a pure function:

```python
def resolve_license_status(control_id, owned_capabilities) -> LicenseStatus:
    reqs = required_capabilities(control_id)
    prefs = preferred_capabilities(control_id)
    if not (reqs - owned_capabilities):
        return LicenseStatus.LICENSED_ENABLED  # owned; whether enabled is determined by evaluator
    missing_required = reqs - owned_capabilities
    if any(c.requires_add_on for c in missing_required):
        return LicenseStatus.REQUIRES_ADD_ON
    if any(c.in_higher_tier(customer) for c in missing_required):
        return LicenseStatus.AVAILABLE_IN_HIGHER_TIER
    return LicenseStatus.NOT_LICENSED
```

The control evaluator then refines `licensed_enabled` → `licensed_disabled` / `licensed_misconfigured` based on configuration evidence.

> **POC implementation note.** Catalog is hand-populated. Customer SKUs are picked by the consultant in the engagement setup screen. At MVP, Microsoft Graph `subscribedSkus` is the authoritative read for Microsoft SKUs (A-0014, Q-0071).

---

## 5. POC license catalog (initial set)

Minimal but covers all four modules. Authoritative source: replace with Microsoft `subscribedSkus` / vendor docs before MVP.

### 5.1 Vendors and products

| Vendor | Products |
|---|---|
| Microsoft | Microsoft 365, Entra ID, Defender for Identity, Defender XDR (future), Purview (future), Intune (future) |
| Silverfort | Silverfort |
| ACEN advisory | (Capability module type — future) |

### 5.2 SKUs

| Sku id | Title | Notes |
|---|---|---|
| `m365-e3` | Microsoft 365 E3 | Includes Entra ID P1 |
| `m365-e5` | Microsoft 365 E5 | Includes Entra ID P2, Defender for Identity, MDE P2, MDO P2, MDCA |
| `ems-e3` | Enterprise Mobility + Security E3 | Entra ID P1 + Intune |
| `ems-e5` | Enterprise Mobility + Security E5 | Entra ID P2 + DfI + MDCA + Intune |
| `entra-id-p1` | Entra ID P1 (standalone) | CA, MFA features |
| `entra-id-p2` | Entra ID P2 (standalone) | PIM + Identity Protection |
| `defender-for-identity-standalone` | Defender for Identity (standalone) | Identity threat detection |
| `silverfort-standard` | Silverfort | Policy engine + service account protection |

### 5.3 Capabilities (subset — full list at MVP)

| Capability id | Surfaced by | In SKUs |
|---|---|---|
| `entra.conditional-access` | Entra | `entra-id-p1`, `m365-e3`, `m365-e5`, `ems-e3`, `ems-e5`, `entra-id-p2` |
| `entra.mfa.enforcement` | Entra | same as CA |
| `entra.pim` | Entra | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.identity-protection.risky-users` | Entra | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.identity-protection.risky-signins` | Entra | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.access-reviews` | Entra | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.entitlement-management` | Entra | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.authentication-methods-policy` | Entra | `entra-id-p1`, `entra-id-p2`, `m365-e3`, `m365-e5`, `ems-e3`, `ems-e5` |
| `defender-identity.lateral-movement-detection` | (future) | `m365-e5`, `ems-e5`, `defender-for-identity-standalone` |
| `silverfort.policy-engine` | Silverfort | `silverfort-standard` |
| `silverfort.service-account-protection` | Silverfort | `silverfort-standard` |
| `silverfort.privileged-mfa` | Silverfort | `silverfort-standard` |

(For POC, AD module controls do **not** require any license — AD itself is the customer's existing infrastructure.)

### 5.4 Control → capability mapping (examples)

| Control | Required capabilities | Preferred |
|---|---|---|
| `ENTRA-CA-001` Baseline Conditional Access Coverage | `entra.conditional-access` | — |
| `ENTRA-CA-004` Risk-Based Access Policy | `entra.conditional-access` + `entra.identity-protection.risky-signins` | — |
| `ENTRA-PRIV-003` PIM Eligibility Coverage | `entra.pim` | — |
| `ENTRA-AUTH-003` Weak Authentication Methods | `entra.authentication-methods-policy` | — |
| `ENTRA-HYBRID-001` Synced Privileged Accounts | (none — works on evidence) | `defender-identity.lateral-movement-detection` |
| `SF-POL-002` Privileged Groups Covered by Policy | `silverfort.policy-engine` | — |
| `SF-SA-004` Service Account Protection Policy | `silverfort.service-account-protection` | — |
| `AD-PRIV-005` Privileged Service Accounts | (none) | `silverfort.service-account-protection` |

> **Reading these mappings:** a control with no required capabilities is always evaluated; license status reflects only preferred capabilities (the gap toward a stronger posture). A control with required capabilities returns `not_licensed`/`requires_add_on`/`available_in_higher_tier` when missing.

---

## 6. License-aware statuses in detail

### 6.1 `licensed_enabled`
- Capability owned AND evidence shows it is configured and active.
- Example: CA owned; baseline CA policy exists and targets All Users with MFA.

### 6.2 `licensed_disabled`
- Capability owned AND evidence shows it is not configured or actively disabled.
- Example: CA owned; no CA policy enforces MFA for privileged users.

### 6.3 `licensed_misconfigured`
- Capability owned AND evidence shows it is configured **but weakened**.
- Example: CA enforces MFA for privileged users but excludes "break-glass" group that has 7 members instead of 2.

### 6.4 `not_licensed`
- None of the customer's SKUs include the capability.
- Example: Identity Protection required for `ENTRA-CA-004`; customer has only E3 (no P2).
- **Never reduces Current License Score.** Always counts as fail against Target Posture Score.

### 6.5 `requires_add_on`
- Capability is part of the same product family but requires an add-on.
- Example: Defender for Identity stand-alone add-on, not bundled with the customer's M365 plan.
- Treated as `not_licensed` for Current Score; reported separately to clarify the commercial path.

### 6.6 `available_in_higher_tier`
- The capability is in a higher-tier SKU than what the customer owns.
- Example: PIM in P2 vs P1.
- Treated as `not_licensed` for Current Score; reported separately to highlight upgrade path.

### 6.7 `not_applicable`
- The control's rubric explicitly excludes the customer's environment.
- Example: an AD-CS-specific control when the customer does not run AD CS.
- Excluded from both scores.

### 6.8 `unknown`
- Evidence is missing or ambiguous; the resolver cannot decide.
- Example: Entra evidence does not include `subscribedSkus` AND consultant did not confirm SKUs.
- Excluded from both scores; reported as "X controls unevaluated" in the report.

---

## 7. Scoring formulas

### 7.1 Per-control contribution

Define `pass_factor(result_status)`:

| result_status | pass_factor |
|---|---|
| `pass` | 1.0 |
| `partial` | 0.5 |
| `fail` | 0.0 |
| `not_applicable` | excluded |
| `unknown` | excluded |

### 7.2 Current License Score (per module)

Let `E_curr(c)` = `c.license_status ∈ {licensed_enabled, licensed_disabled, licensed_misconfigured}`.

```
CurrentLicenseScore_module = (
  Σ_c { c.weight × pass_factor(c.result_status) : E_curr(c) }
) / (
  Σ_c { c.weight : E_curr(c) }
) × 100
```

If denominator = 0 (no eligible controls), `CurrentLicenseScore_module = None` and UI shows "Insufficient evidence to score".

### 7.3 Target Posture Score (per module)

Let `E_target(c)` = `c.license_status ≠ not_applicable AND c.license_status ≠ unknown`.

Map for target scoring:

- `licensed_enabled` → use `pass_factor(c.result_status)` as-is.
- `licensed_disabled` → use `pass_factor(c.result_status)` as-is.
- `licensed_misconfigured` → use `pass_factor(c.result_status)` as-is.
- `not_licensed` → fail (factor 0.0).
- `requires_add_on` → fail (factor 0.0).
- `available_in_higher_tier` → fail (factor 0.0).

```
TargetPostureScore_module = (
  Σ_c { c.weight × target_factor(c) : E_target(c) }
) / (
  Σ_c { c.weight : E_target(c) }
) × 100
```

### 7.4 Engagement-level scores

```
CurrentLicenseScore_engagement = avg_over_modules(CurrentLicenseScore_module)
TargetPostureScore_engagement = avg_over_modules(TargetPostureScore_module)
OpportunityScore_engagement = TargetPostureScore_engagement − CurrentLicenseScore_engagement
```

(Equal module weights in POC; per-module weights at MVP.)

### 7.5 Severity vs risk_score

- Severity is qualitative.
- `risk_score` (0–100) is computed per finding and used to rank findings within a list. For BloodHound paths it is the analyzer's deterministic path-risk score (see `BLOODHOUND_ANALYZER_DESIGN.md`). For other findings, a default projection:

```
risk_score = base_by_severity(severity) +
             license_adjustment(license_status) +
             correlation_breadth_bonus(correlation_refs)

base_by_severity:
  CRITICAL → 90
  HIGH     → 70
  MEDIUM   → 50
  LOW      → 30
  INFO     → 10

license_adjustment:
  licensed_misconfigured  → +5
  licensed_disabled       → +3
  licensed_enabled        →  0
  not_licensed            → −5  (the customer doesn't own it; the action is commercial, not technical)
  others                  →  0

correlation_breadth_bonus:
  unique modules in correlation_refs > 1 → + 5 × (modules − 1)  (max +10)
```

Clamped to [0, 100].

---

## 8. Microsoft examples

| Scenario | Current Score behaviour | Target Score behaviour |
|---|---|---|
| Customer has E3, no CA baseline configured | `ENTRA-CA-001` → `licensed_disabled`, fail → contributes 0 of weight to Current Score | Same; contributes 0 of weight to Target Score |
| Customer has E3 (no P2); Identity Protection unavailable | `ENTRA-CA-004` → `not_licensed` → excluded from Current Score | Counted as fail in Target Score |
| Customer has E5; CA enforces MFA on privileged users with no exclusions | `ENTRA-CA-002` → `licensed_enabled`, pass → full contribution | Same |
| Customer has E5; PIM eligibility coverage at 30% | `ENTRA-PRIV-003` → `licensed_enabled`, partial (0.5) | Same |
| AD CS not in environment; AD-CS-related control | `not_applicable` → excluded from both scores | Excluded from both scores |

---

## 9. Silverfort examples

| Scenario | Current Score behaviour | Target Score behaviour |
|---|---|---|
| Customer has Silverfort; Tier 0 group is in a coverage policy | `SF-POL-002` → `licensed_enabled`, pass | Same |
| Customer has Silverfort; Tier 0 group is NOT in any policy | `SF-POL-002` → `licensed_disabled`, fail | Same |
| Customer does not have Silverfort | All SF controls → `not_licensed` → excluded from Current Score | Counted as fail in Target Score |
| Customer has Silverfort but service-account-protection feature disabled at tenant | `SF-SA-004` → `licensed_disabled`, fail | Same |

> **Note.** AD controls do not depend on Silverfort capabilities; only **AD-SF-correlation controls** (e.g., `AD-SF-001`) reference `silverfort.policy-engine` as a *preferred* capability — they tell the customer how Silverfort would compensate the AD risk.

---

## 10. AD + BloodHound context

AD and BloodHound are evidence-driven and rarely license-dependent. Their `license_status` defaults to `licensed_enabled` (the customer owns AD); some controls flag *preferred* third-party capabilities (e.g., Silverfort for compensating control on delegation risk → `available_in_higher_tier` if Silverfort not owned).

---

## 11. Non-Microsoft vendor readiness

The model already supports non-Microsoft vendors via the `Vendor`/`Product`/`Sku`/`Capability` graph. For future modules:

- Imprivata → Vendor with its own Product/SKUs/capabilities for clinical IAM.
- Cato → Vendor; SASE capabilities.
- Illumio → Vendor; segmentation capabilities.
- ACEN advisory → Vendor with a single virtual "advisory" SKU that owns every "advisory" capability.

This keeps the model uniform across product-driven and consultant-driven modules.

---

## 12. POC / MVP / Full product scope

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| 8-value license status enum | ✅ | ✅ | ✅ |
| Two scores per module + engagement | ✅ | ✅ | ✅ |
| Opportunity score | ✅ | ✅ | ✅ |
| Hand-populated catalog | ✅ | ⬜ replaced | ⬜ replaced |
| Microsoft Graph `subscribedSkus` | ⬜ | ✅ | ✅ |
| Silverfort policy/feature detection via API | ⬜ | 🟡 gated | ✅ |
| Consultant override of resolved license status | ✅ (advisory note) | ✅ | ✅ |
| Industry benchmarks (anonymized peer score) | ⬜ | ⬜ | ✅ |
| Customer-visible "Opportunity card" with cost/value framing | ⬜ design | ✅ basic | ✅ advanced |

---

## 13. Risks and disclaimers

- m365maps.com is **inspiration only**. The POC catalog is authored by hand and is **not authoritative**. Replace before MVP (Q-0071). Risk if shipped to customers without replacement: incorrect scoring.
- SKU contents drift over time (Microsoft, Silverfort). The catalog has a `notes` field and a `last_verified_at` timestamp at MVP.
- License-aware UI must explain **why** something is `not_licensed` (which SKU includes it). Otherwise the customer suspects a sales gimmick.
- The Opportunity Score is **not** a price quote. Avoid framing it as one in customer reports.

---

*Last updated: 2026-05-15.*
