# SILVERFORT_MODULE_DESIGN.md

> Design specification for the **Silverfort module** of ACEN Gravity. Defines goals, collection modes, evidence model, normalized data, controls, correlations, UI composition, reporting, and tiered scope (POC / MVP / Full).
>
> Companion documents: `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md` §5.5 + §12, `MODULE_ARCHITECTURE.md` (single lifecycle, Finding shape, scoring, §11 correlations), `LICENSE_MODEL.md` §5 (Silverfort SKU + capabilities), `SECURITY_AND_GDPR.md`, `UI_DESIGN_DIRECTION.md` §14, `DECISIONS.md` (D-0006 binding), `ASSUMPTIONS.md` (A-0006, A-0011), `RISKS.md` (R-0003), `OPEN_QUESTIONS.md` (Q-0090, Q-0091, Q-0092).

---

## 1. API validation disclaimer

> **This document references five publicly cited Silverfort API endpoints. All such references in this document are tagged `(unverified — requires Silverfort validation)`. Availability, request/response shape, authentication, and rate limits depend on the customer's Silverfort version, licensing tier, and customer-side configuration. None of these endpoints have been validated against authoritative Silverfort documentation or support for the purposes of POC V1.**

The five endpoints in scope as **design inspiration only**:

- `/getServiceAccountsInsights` *(unverified — requires Silverfort validation)*
- `/getBootStatus` *(unverified — requires Silverfort validation)*
- `/getEntityRisk` *(unverified — requires Silverfort validation)*
- `/v2/public/policies` *(unverified — requires Silverfort validation)*
- `/getUsersEnrollment` *(unverified — requires Silverfort validation)*

Per **D-0006 (binding)**:

- POC V1 **accepts manually exported Silverfort evidence only**.
- The API connector is **designed and documented** in this file but **not implemented in POC**.
- MVP connector implementation is **gated** on official Silverfort validation (R-0003, Q-0090).
- Every API endpoint mention below carries the **unverified** tag inline.

If the Silverfort vendor confirms a different endpoint surface, the design adapts; the evidence model and controls remain stable because both modes converge on the same normalized data shape (see §3, §4, §8).

---

## 2. Goals

The Silverfort module exists to assess, in increasing order of dependency on live integration:

1. **Connector availability and health** — when API mode is live (MVP+), is the Silverfort tenant reachable, authorized, and version-compatible? In POC, this is a *design stub* — the connector card is always `pending` with the explanation "Connector not configured (POC)" *(POC)*.
2. **Policy coverage** — does the customer have Silverfort policies that cover privileged groups, Tier 0 identities, and critical service accounts? *(POC)*
3. **Privileged-user enrollment** — are privileged identities enrolled (MFA-capable / step-up authentication ready) in Silverfort? *(POC)*
4. **Entity risk awareness** — what does Silverfort's own entity-risk signal say about high-risk identities? *(POC for manual evidence; MVP for live API)*
5. **Service-account / NHI discovery** — does Silverfort have a complete-enough view of non-human identities (NHIs), with ownership and risk prioritization? *(POC)*
6. **AD correlation** — for AD Tier 0 / AD-privileged identities, is Silverfort actually covering them with a policy? *(POC)*
7. **BloodHound correlation** — for each detected BH critical path, is the path's target identity protected by a Silverfort policy? *(POC)*
8. **Entra correlation** — for hybrid privileged identities (AD-privileged AND a cloud-privileged Entra role), is Silverfort covering them? *(POC)*
9. **Operational maturity** — how well does the customer use Silverfort beyond minimum coverage (policy exclusions reviewed, ownership of service accounts known, risk-based action followed up)? *(MVP)*

The module does **not** try to act on the Silverfort tenant (no remediation execution). It is **advisory and evidence-driven**, consistent with the platform-wide stance (`PRODUCT_DESIGN.md` §7.3).

---

## 3. Collection modes

The module supports two collection modes with **deliberate design symmetry**:

| Mode | Tier | Source | Trust boundary |
|---|---|---|---|
| **Manual Export Mode** | POC, MVP fallback, Full fallback | ZIP bundle uploaded by consultant | Untrusted file (validated like any artifact) |
| **API Connector Mode** | MVP (gated), Full | Read-only Silverfort API via app token | Untrusted external system (validated like a connector) |

### 3.1 Design symmetry

Both modes converge on the **same normalized evidence shape** in the module-local tables:

- `sf_policy`
- `sf_policy_coverage`
- `sf_service_account`
- `sf_enrollment`
- `sf_entity_risk`

This means:

- Controls are written **once** and run identically against manual-uploaded data or API-fetched data.
- Reports and UI composition do not care which mode produced the data — only the freshness timestamp and source attribution differ.
- Migrating from manual to API at MVP is **additive** (a new parser entry point), not a refactor of controls or schemas.

### 3.2 Mode selection

Per assessment run, the module reads:

1. **Manual evidence first** — if a `silverfort-export-bundle` artifact is present for the run, it is parsed. *(POC)*
2. **API mode** — if the customer has a Silverfort connector configured in the engagement and no manual evidence is uploaded, API collection runs at evaluate time. *(MVP, gated)*
3. **Hybrid** — if both are present, the **most recent** snapshot wins per evidence type, with a consultant-visible warning if timestamps diverge by more than a documented threshold (e.g., 7 days). *(MVP)*

In POC, only Mode 1 is implemented; Mode 2 is documented and stubbed in the UI as `pending`.

---

## 4. Manual / API model

### 4.1 Manual evidence bundle (POC)

Artifact type: `silverfort-export-bundle` (registered in the module manifest).

**Shape**: a single ZIP archive (`silverfort_export_<customer>_<yyyymmdd>.zip`) containing JSON files. The expected layout:

```
silverfort_export_<customer>_<yyyymmdd>.zip
├── env.json                  # tenant metadata (tenant id, region, exported_at, exported_by, sf_version, evidence_schema_version)
├── policies.json             # list of policies (id, name, type, scope, target groups, action, mfa_required, enabled)
├── service-accounts.json     # list of discovered service accounts (id, identity_keys, discovered_at, source_count, risk_score, ownership_known)
├── enrollment.json           # list of enrollment records (identity_keys, enrolled, last_enrolled_at, method)
└── entity-risk.json          # list of entity-risk records (identity_keys, risk_score, factors[])
```

Validation rules (per `SECURITY_AND_GDPR.md` §7):

- ZIP guarded against Zip Slip (no `..`, no absolute paths, no symlinks).
- Each inner file is JSON; size cap (default 50 MB per file).
- `env.json` is **required**; absence fails parse with a clear error.
- Other files are **optional** per evidence type; absence yields `evidence_missing` flags for the affected controls (see §10).
- Per-file schema validation (Pydantic models) before persistence.
- The bundle is stored as an immutable `Artifact` row; produced `Evidence` rows are typed `sf-policies`, `sf-service-accounts`, `sf-enrollment`, `sf-entity-risk`, `sf-env`.

**Question carried**: Q-0091 — final export format (JSON / CSV / screenshots) is unconfirmed. The design assumes JSON; CSV/screenshots are explicitly out of scope until Q-0091 resolves.

### 4.2 API connector (MVP design only)

Pseudo-flow (no POC code):

```
1. Engagement configuration: consultant registers a Silverfort tenant (base URL + auth metadata).
   Token storage: secret manager at MVP+ (SECURITY_AND_GDPR §10).
2. Connector health probe at engagement open:
   - GET /getBootStatus  (unverified — requires Silverfort validation)
3. Token acquisition (model TBD — Q-0090):
   - Most likely an application-style token / API key flow; details unverified.
4. Poll each endpoint (read-only) on assessment-run trigger:
   - GET /v2/public/policies         (unverified — requires Silverfort validation)
   - GET /getServiceAccountsInsights (unverified — requires Silverfort validation)
   - GET /getUsersEnrollment         (unverified — requires Silverfort validation)
   - GET /getEntityRisk              (unverified — requires Silverfort validation)
5. Normalize each response into the same module-local schemas as manual mode.
6. Upsert per identity (deterministic identity link via SID / UPN / sAMAccountName per A-0011).
7. Record source attribution: source = "api", source_version, fetched_at, request_id (for audit).
8. Audit log entries: connector.health, connector.fetch.start, connector.fetch.success / connector.fetch.error.
```

Per-endpoint mapping is shared with manual mode and documented in §5 and §8.

### 4.3 Identity linking

Both modes feed the module-local rows through the **core identity linker** (`MODULE_ARCHITECTURE.md` §8 / A-0011):

- Primary keys: SID, sAMAccountName + ObjectGUID, UPN.
- Ambiguous matches are **never** silently merged; they are surfaced via `identity/ambiguity.py` for consultant confirmation.
- Each Silverfort row is associated to an `Identity.id` once linked; rows that fail to link are retained with a flag `unlinked = true` and surfaced in the evidence drawer for consultant action.

---

## 5. Publicly referenced endpoints

The table below is **inspiration only** until Silverfort confirms (R-0003, Q-0090). Expected response shapes are **best-guess** and must be re-validated at MVP gating.

| # | Endpoint *(unverified — requires Silverfort validation)* | Claimed purpose | Status | Expected response shape (best-guess; unverified) | What we would normalize from it |
|---|---|---|---|---|---|
| 1 | `/getBootStatus` *(unverified — requires Silverfort validation)* | Connector / tenant health probe | Unverified | `{ status, version, last_heartbeat, modules_enabled[] }` | `connector_status` (one of: `not_configured`, `configured_unreachable`, `configured_ok`, `unauthorized`, `version_mismatch`); populates the `Connector` status card. |
| 2 | `/v2/public/policies` *(unverified — requires Silverfort validation)* | List Silverfort policies and their scope | Unverified | `[{ id, name, type, scope: { groups[], users[], exclusions[] }, action, mfa_required, enabled }]` | `sf_policy` rows + `sf_policy_coverage` rows (per identity that falls in scope). |
| 3 | `/getUsersEnrollment` *(unverified — requires Silverfort validation)* | Enrollment status of users (e.g., MFA-ready) | Unverified | `[{ user_identifier, enrolled, last_enrolled_at, method }]` | `sf_enrollment` rows linked to `Identity`. |
| 4 | `/getEntityRisk` *(unverified — requires Silverfort validation)* | Risk score per entity from Silverfort's own analytics | Unverified | `[{ entity_identifier, risk_score, factors: [{ id, description }] }]` | `sf_entity_risk` rows linked to `Identity`. |
| 5 | `/getServiceAccountsInsights` *(unverified — requires Silverfort validation)* | Discovered service-account NHIs with ownership and risk | Unverified | `[{ id, identity_keys, discovered_at, source_count, risk_score, ownership_known, last_seen }]` | `sf_service_account` rows linked to `Identity`. |

**Reading this table**:

- Anything in the "Expected response shape" column is **provisional**. The module's Pydantic models are written to be permissive (extra fields allowed; missing optional fields tolerated) so the schema can evolve once Silverfort confirms.
- Manual-export JSON files mirror these shapes (same field names where possible) to keep parser logic identical (§4.1 layout).
- If Silverfort confirms a different shape, only the parsers change; controls and UI stay stable.

---

## 6. Connector health

The Silverfort module exposes a **connector status pill** on the module page (using `StatusBadge` from `UI_DESIGN_DIRECTION.md` §3.3 — **no new component is introduced**).

### 6.1 States

| State | StatusBadge variant | Meaning | POC behaviour |
|---|---|---|---|
| `not_configured` | `pending` | No connector registered for the engagement | **POC default** — pill always reads "Connector not configured (POC)" with a tooltip pointing to the manual upload flow |
| `configured_unreachable` | `warn` | Connector registered but `/getBootStatus` *(unverified — requires Silverfort validation)* fails (timeout, DNS, 5xx) | MVP only |
| `configured_ok` | `ok` | Connector reachable, authorized, version compatible | MVP only |
| `unauthorized` | `critical` | Connector reachable but auth rejected (401 / 403) | MVP only |
| `version_mismatch` | `warn` | Connector reachable but a required API category is missing for the customer's Silverfort version | MVP only |

UI rule (per `UI_DESIGN_DIRECTION.md` §14): connector card in POC **always** shows `pending` with the explanatory tooltip. The state machine above is implemented at MVP.

### 6.2 Connector health controls

These map to `SF-CONN-001` and `SF-CONN-002` (see §10).

---

## 7. Data sources

Sources used by the Silverfort module:

| Source | Mode | Tier | Purpose |
|---|---|---|---|
| Manual export bundle (`silverfort-export-bundle`) | Manual | POC, MVP fallback | Primary POC source |
| `/getBootStatus` *(unverified — requires Silverfort validation)* | API | MVP gated | Connector health |
| `/v2/public/policies` *(unverified — requires Silverfort validation)* | API | MVP gated | Policies + scope |
| `/getUsersEnrollment` *(unverified — requires Silverfort validation)* | API | MVP gated | Enrollment |
| `/getEntityRisk` *(unverified — requires Silverfort validation)* | API | MVP gated | Entity risk |
| `/getServiceAccountsInsights` *(unverified — requires Silverfort validation)* | API | MVP gated | Service accounts / NHIs |
| Core `Identity` view (from AD / BH / Entra modules) | Cross-module | POC | Correlation join key (per A-0011) |
| Core `LicenseCatalog` (Silverfort SKU + capabilities) | Cross-module | POC | License-aware control gating (see `LICENSE_MODEL.md` §5) |

---

## 8. Normalized model

All Silverfort module-local tables are prefixed `sf_` (per `MODULE_ARCHITECTURE.md` §14). Schemas are sketches — final field set is fixed at build time and reviewed at architecture gate.

### 8.1 `sf_policy`

```python
class SfPolicy(Base):
    id: str                        # Silverfort-side policy id (or hash if missing)
    assessment_run_id: UUID
    name: str
    type: str                      # e.g., "access", "step_up", "block" — vendor-defined; unverified
    scope: JSONB                   # raw scope as captured (groups, users, exclusions)
    target_groups: list[str]       # normalized list of group identifiers (SID/sAMAccountName/UPN where present)
    action: str                    # e.g., "require_mfa", "block", "monitor" — vendor-defined; unverified
    mfa_required: bool
    enabled: bool
    source: enum("manual", "api")
    source_version: str | None     # parser or API version
    fetched_at: datetime
    raw_payload_ref: str | None    # pointer into the artifact (manual mode) or null
```

### 8.2 `sf_policy_coverage`

A denormalized projection that answers "is identity X covered by policy Y, and how?".

```python
class SfPolicyCoverage(Base):
    id: UUID
    assessment_run_id: UUID
    policy_id: str                 # FK to sf_policy.id
    identity_id: UUID              # FK to core.Identity
    coverage_kind: enum("direct", "indirect", "excluded")
    # direct   = identity explicitly in policy.scope.users
    # indirect = identity is a member of a group in policy.scope.groups
    # excluded = identity matches policy.scope.exclusions
    resolved_via: str              # e.g., "group:Domain Admins" or "user:alice@contoso.com"
```

`sf_policy_coverage` is produced by a deterministic expansion at parse time: scope groups are expanded to identities via the core `Identity` view (which has AD group memberships from the AD module).

> **Cross-module read note.** This expansion is the only place the Silverfort module reads AD-contributed data. It reads via the **core `Identity` view** (`MODULE_ARCHITECTURE.md` §8); it does **not** import the AD module. Per the architecture rules, this is correct (read-only view of core data).

### 8.3 `sf_service_account`

```python
class SfServiceAccount(Base):
    id: str                        # Silverfort-side service-account id
    assessment_run_id: UUID
    identity_id: UUID | None       # FK to core.Identity; null if unlinked
    discovered_at: datetime
    source_count: int              # number of sources Silverfort used to identify the NHI
    risk_score: int                # 0–100 as reported by Silverfort (unverified scale; mapped at parse)
    ownership_known: bool          # whether Silverfort has an attested owner
    raw_metadata: JSONB
    unlinked: bool = False
```

### 8.4 `sf_enrollment`

```python
class SfEnrollment(Base):
    id: UUID
    assessment_run_id: UUID
    identity_id: UUID              # FK to core.Identity (required; unlinked rows held separately)
    enrolled: bool
    last_enrolled_at: datetime | None
    method: str | None             # e.g., "mobile_push", "totp", "fido2", "sms" — vendor-defined; unverified
```

### 8.5 `sf_entity_risk`

```python
class SfEntityRisk(Base):
    id: UUID
    assessment_run_id: UUID
    identity_id: UUID              # FK to core.Identity (required; unlinked rows held separately)
    risk_score: int                # 0–100 as reported (unverified scale; mapped at parse)
    factors: JSONB                 # list of { id, description } as reported (unverified)
    fetched_at: datetime
```

### 8.6 Schema versioning

Each table carries an implicit `evidence_schema_version` traceable through `Evidence.parser_version` (per `MODULE_ARCHITECTURE.md` §7). Schema changes require an Alembic migration and a parser version bump.

---

## 9. Assessment areas

The Silverfort module evaluates ten distinct areas. Each maps to one or more controls in §10.

| # | Area | What it answers | Primary controls |
|---|---|---|---|
| 1 | Connector / data availability | Can we trust that Silverfort data is fresh and complete? | SF-CONN-001, SF-CONN-002 |
| 2 | Policy coverage | Are there policies, and do they cover the right groups? | SF-POL-001, SF-POL-002, SF-POL-003 |
| 3 | Privileged account protection | Are privileged identities effectively guarded by Silverfort? | SF-POL-002, SF-ENR-001 |
| 4 | Service account / NHI visibility | Are service accounts known, owned, prioritized, and protected? | SF-SA-001, SF-SA-002, SF-SA-003, SF-SA-004 |
| 5 | Enrollment / MFA readiness | Are privileged users actually enrollment-ready? | SF-ENR-001 |
| 6 | Entity risk | Are there high-risk entities Silverfort itself flagged? | SF-RISK-001 |
| 7 | AD correlation (Tier 0) | Are AD Tier 0 identities covered? | SF-AD-001, SF-AD-002 |
| 8 | BloodHound correlation | Are BH-critical-path target identities covered? | SF-AD-003 |
| 9 | Entra correlation (hybrid) | Are hybrid privileged identities covered? | SF-ENTRA-001 |
| 10 | Operational maturity | Are exclusions reviewed, ownership filled, follow-up tracked? | SF-POL-003, SF-SA-002 (MVP+ enrichments) |

---

## 10. Proposed controls

15 controls, grouped by area. Each carries: id, title, objective, evidence required, capability requirement (per `LICENSE_MODEL.md` §5), status enum behaviour, finding example, remediation direction, and POC / MVP / Full support.

> **License-status reminder (8 values, verbatim from D-0007).** `licensed_enabled`, `licensed_disabled`, `licensed_misconfigured`, `not_licensed`, `requires_add_on`, `available_in_higher_tier`, `not_applicable`, `unknown`. Operational flags: `connector_missing`, `evidence_missing`, `manual_review_required`.

> **Capability shorthand**. The Silverfort capabilities used below come from `LICENSE_MODEL.md` §5.3: `silverfort.policy-engine`, `silverfort.service-account-protection`, `silverfort.privileged-mfa`.

### SF-CONN-001 — Silverfort Connector Availability

- **Objective**: confirm the platform has a working pathway to the customer's Silverfort tenant (or accepted manual evidence).
- **Evidence required**: either a manual export bundle for the current run **or** a successful `/getBootStatus` *(unverified — requires Silverfort validation)* result.
- **Capability requirement**: `silverfort.policy-engine` (required — implies Silverfort is owned).
- **Status enum behaviour**: `not_licensed` if no Silverfort SKU is recorded for the customer (excluded from Current Score). `licensed_disabled` if owned and connector both unavailable and no manual evidence. `licensed_enabled` if manual evidence is present OR connector returns `configured_ok`. `unknown` if customer ownership is undetermined.
- **Finding example**: "Silverfort tenant data unavailable for this assessment run. No manual export uploaded and no connector configured. Current run cannot evaluate Silverfort controls."
- **Remediation direction**: upload a manual export bundle (POC) or configure the connector at MVP.
- **POC V1 support**: **Yes** (manual-mode default; connector pill shows `pending`).
- **MVP / Full**: full implementation.

### SF-CONN-002 — Required API Categories Available

- **Objective**: when API mode is configured, confirm the categories needed by SF-* controls are actually exposed by the customer's Silverfort version.
- **Evidence required**: `/getBootStatus` *(unverified — requires Silverfort validation)* reports `modules_enabled[]` including: policies, service-accounts, enrollment, entity-risk.
- **Capability requirement**: `silverfort.policy-engine`.
- **Status enum behaviour**: `licensed_enabled` if all required categories enabled; `licensed_misconfigured` if some are missing; `unknown` if probe fails.
- **Finding example**: "Silverfort connector reachable but the `entity-risk` category is not enabled on this tenant. SF-RISK-001 cannot be evaluated."
- **Remediation direction**: enable the missing module or accept the gap; consultant may convert affected controls to `manual_review_required`.
- **POC V1 support**: **No** (design-only; not evaluated in POC).
- **MVP / Full**: full implementation.

### SF-POL-001 — Policy Inventory Available

- **Objective**: confirm Silverfort has at least one enabled policy.
- **Evidence required**: `sf_policy` rows where `enabled = true`.
- **Capability requirement**: `silverfort.policy-engine`.
- **Status enum behaviour**: `licensed_enabled` + `pass` if any enabled policy exists. `licensed_disabled` + `fail` if Silverfort is owned but no enabled policy. `not_licensed` if Silverfort not owned (excluded from Current Score; counted as fail vs Target).
- **Finding example**: "Silverfort tenant has 12 policies, but 0 are enabled. Silverfort is effectively in monitor-only mode."
- **Remediation direction**: enable at least the baseline privileged-coverage policy.
- **POC V1 support**: **Yes** (one of the ≥ 5 POC controls).
- **MVP / Full**: full.

### SF-POL-002 — Privileged Groups Covered by Policy

- **Objective**: confirm AD privileged groups (Domain Admins, Enterprise Admins, etc.) are in the scope of at least one enabled enforcing policy.
- **Evidence required**: `sf_policy_coverage` for identities in core-`Identity` marked `is_privileged = true` or `is_tier0 = true`; cross-referenced to `sf_policy` where `enabled = true` and `action ∈ {"require_mfa", "block"}` (unverified action vocabulary — Q-0092).
- **Capability requirement**: `silverfort.policy-engine` (required).
- **Status enum behaviour**: `licensed_enabled` + `pass` if all privileged groups covered; `licensed_enabled` + `partial` if some are covered; `licensed_disabled` + `fail` if none. `not_licensed` if Silverfort not owned.
- **Finding example**: see §11.1.
- **Remediation direction**: add the uncovered privileged groups to the relevant policy's scope.
- **POC V1 support**: **Yes** (one of the ≥ 5 POC controls).
- **MVP / Full**: full.

### SF-POL-003 — Policy Exclusions Reviewed

- **Objective**: surface policies whose `scope.exclusions` list is non-empty for consultant review (exclusions are a common attack-surface gap).
- **Evidence required**: `sf_policy` rows where the policy is enabled AND has non-empty exclusions affecting privileged identities.
- **Capability requirement**: `silverfort.policy-engine`.
- **Status enum behaviour**: `manual_review_required` always; the rubric flags but does not auto-fail. `licensed_misconfigured` + `partial` if reviewed and exclusions deemed risky.
- **Finding example**: "Policy `priv-mfa` excludes 7 identities, including 2 marked `is_privileged`. Review and justify or remove."
- **Remediation direction**: justify each exclusion; remove unjustified ones; document break-glass exclusions.
- **POC V1 support**: **Optional** (manual_review only — not strictly needed for POC demo).
- **MVP / Full**: full.

### SF-ENR-001 — Privileged User Enrollment Coverage

- **Objective**: confirm privileged identities are enrolled and ready for step-up authentication.
- **Evidence required**: `sf_enrollment` for identities where `is_privileged = true` or `is_tier0 = true`.
- **Capability requirement**: `silverfort.privileged-mfa`.
- **Status enum behaviour**: `licensed_enabled` + `pass` if 100% privileged enrolled; `partial` if ≥ 80%; `fail` otherwise. `not_licensed` if Silverfort not owned.
- **Finding example**: "8 of 12 privileged users enrolled in Silverfort step-up (66%). 4 users remain unenrolled including 1 Tier 0 account."
- **Remediation direction**: enroll the remaining privileged users; track via the ownership channel.
- **POC V1 support**: **Yes** (one of the ≥ 5 POC controls).
- **MVP / Full**: full.

### SF-RISK-001 — High-Risk Entity Review

- **Objective**: surface high-risk identities reported by Silverfort for consultant attention.
- **Evidence required**: `sf_entity_risk` rows where `risk_score ≥ threshold` (POC threshold 70; configurable at MVP).
- **Capability requirement**: `silverfort.policy-engine`.
- **Status enum behaviour**: `licensed_enabled` + `partial` if high-risk entities exist; `pass` if none. `manual_review_required` always.
- **Finding example**: "Silverfort flagged 5 entities at risk_score ≥ 70 over the evaluation window: …".
- **Remediation direction**: review each entity in Silverfort; act per its risk factors.
- **POC V1 support**: **Optional** (depends on synthetic data realism).
- **MVP / Full**: full.

### SF-SA-001 — Service Account Discovery Coverage

- **Objective**: gauge whether Silverfort's service-account discovery is broad enough to support the engagement (vs only obvious accounts).
- **Evidence required**: `sf_service_account` count + cross-reference to AD-identified service accounts (via the AD module's contribution to core `Identity` rows where `canonical_kind = "service_account"`).
- **Capability requirement**: `silverfort.service-account-protection`.
- **Status enum behaviour**: `licensed_enabled` + `pass` if SF discovers ≥ X% of AD-detected service accounts (POC threshold 80%); `partial` otherwise; `fail` if < 50%.
- **Finding example**: see §11.2.
- **Remediation direction**: extend discovery sources; reconcile ownership records.
- **POC V1 support**: **Yes** (one of the ≥ 5 POC controls).
- **MVP / Full**: full.

### SF-SA-002 — Service Account Ownership

- **Objective**: confirm Silverfort-discovered service accounts have attested owners.
- **Evidence required**: `sf_service_account.ownership_known`.
- **Capability requirement**: `silverfort.service-account-protection`.
- **Status enum behaviour**: `licensed_enabled` + `pass` if ≥ 90% owned; `partial` if ≥ 60%; `fail` otherwise. `manual_review_required` always.
- **Finding example**: "23 of 41 service accounts have unknown ownership (56%). Unowned NHIs cannot be retired or rotated safely."
- **Remediation direction**: launch an ownership-attestation pass; integrate ownership records.
- **POC V1 support**: **Optional**.
- **MVP / Full**: full.

### SF-SA-003 — Service Account Risk Prioritization

- **Objective**: surface the riskiest service accounts for consultant action.
- **Evidence required**: `sf_service_account` rows sorted by `risk_score` desc; threshold-driven.
- **Capability requirement**: `silverfort.service-account-protection`.
- **Status enum behaviour**: `manual_review_required` always; `partial` if any high-risk NHIs unowned.
- **Finding example**: "Top 5 high-risk service accounts: …; 3 of 5 have `ownership_known = false`."
- **Remediation direction**: assign owners, evaluate protection policy, scope retirement.
- **POC V1 support**: **Optional**.
- **MVP / Full**: full.

### SF-SA-004 — Service Account Protection Policy

- **Objective**: confirm a Silverfort policy enforces protection (e.g., block / step-up) for service accounts deemed high-risk.
- **Evidence required**: `sf_policy_coverage` for `sf_service_account` rows where `risk_score ≥ threshold`.
- **Capability requirement**: `silverfort.service-account-protection` (required).
- **Status enum behaviour**: `licensed_enabled` + `pass` if all high-risk NHIs covered; `partial` if some; `licensed_disabled` + `fail` if none and feature owned. `not_licensed` / `requires_add_on` if the customer's Silverfort SKU does not include `silverfort.service-account-protection`.
- **Finding example**: "5 high-risk service accounts have no Silverfort protection policy covering them."
- **Remediation direction**: add high-risk NHIs to a protection policy; consider a dedicated NHI policy.
- **POC V1 support**: **Optional** (covered conceptually by SF-POL-002 and SF-SA-001 in POC).
- **MVP / Full**: full.

### SF-AD-001 — Tier 0 Coverage Gap (AD correlation)

- **Objective**: identify AD Tier 0 identities that are **not** covered by any enforcing Silverfort policy.
- **Evidence required**: AD-contributed core `Identity` rows where `is_tier0 = true` MINUS the `sf_policy_coverage` set (enabled policies, non-excluded).
- **Capability requirement**: `silverfort.policy-engine` (required for the control; AD-side data has no license dependency).
- **Status enum behaviour**: `licensed_enabled` + `pass` if the set is empty; `fail` otherwise. `not_licensed` if Silverfort not owned (the gap then surfaces as `available_in_higher_tier` / Opportunity-only context per `LICENSE_MODEL.md` §10).
- **Finding example**: see §11.3.
- **Remediation direction**: add Tier 0 groups to the privileged-coverage policy.
- **POC V1 support**: **Yes** (one of the ≥ 5 POC controls; also the AD correlation requirement in POC_V1_SCOPE §5.5).
- **MVP / Full**: full.

### SF-AD-002 — Delegation Risk Compensating Control (AD correlation)

- **Objective**: where the AD module flags an unconstrained / sensitive delegation risk on a privileged identity, is Silverfort acting as a compensating control (e.g., step-up policy)?
- **Evidence required**: AD findings of category `ad.delegation` AND `sf_policy_coverage` for the affected identity.
- **Capability requirement**: `silverfort.policy-engine` (preferred; absent → `available_in_higher_tier`).
- **Status enum behaviour**: `licensed_enabled` + `pass` if affected identity is covered by an enforcing policy; `licensed_disabled` + `partial` if covered but not enforcing; `fail` if not covered. `not_licensed` if Silverfort not owned (no Current-Score penalty; counts toward Target / Opportunity).
- **Finding example**: "Identity `svc-backup` has unconstrained delegation enabled AND no Silverfort policy coverage. AD risk is uncompensated."
- **Remediation direction**: remove delegation OR add Silverfort policy coverage.
- **POC V1 support**: **Optional**.
- **MVP / Full**: full.

### SF-AD-003 — BloodHound Path Silverfort Coverage (BH correlation)

- **Objective**: for each detected BH critical path, flag whether the path's **target** identity is Silverfort-covered.
- **Evidence required**: BH-module findings (paths) → target Identity; cross-reference to `sf_policy_coverage` (enabled, enforcing).
- **Capability requirement**: `silverfort.policy-engine` (preferred).
- **Status enum behaviour**: per-path: `pass` if target covered; `fail` if not. Control-level result aggregates: `pass` only if **all** detected paths are covered; otherwise `partial` / `fail`.
- **Finding example**: "3 of 5 BH critical paths land on identities not protected by Silverfort policy."
- **Remediation direction**: extend Silverfort policy scope OR mitigate the AD-side risk to remove the path.
- **POC V1 support**: **Yes** (this is the headline cross-module correlation — see §13 and `MODULE_ARCHITECTURE.md` §11.3 `CORR-BH-SF-001`).
- **MVP / Full**: full.

### SF-ENTRA-001 — Hybrid Privileged Identity Coverage (Entra correlation)

- **Objective**: for hybrid privileged identities (AD-privileged AND a cloud-privileged Entra role assignment), confirm Silverfort policy coverage on the AD side.
- **Evidence required**: core `Identity` rows where `is_privileged = true` (AD) AND linked to an Entra-side cloud privileged role assignment (contributed by the Entra module); cross-reference to `sf_policy_coverage`.
- **Capability requirement**: `silverfort.policy-engine` (preferred).
- **Status enum behaviour**: `pass` if all hybrid privileged identities covered; `partial` / `fail` otherwise; `not_licensed` if Silverfort not owned.
- **Finding example**: "2 of 4 hybrid privileged identities (AD-Domain-Admins ∩ Entra Global Admins) are not in Silverfort policy scope."
- **Remediation direction**: add hybrid-privileged identities to the privileged-coverage policy; review whether the same identity should remain dual-privileged (Tier 0 separation).
- **POC V1 support**: **Optional** but covered by `CORR-AD-ENTRA-001` correlation in POC (`MODULE_ARCHITECTURE.md` §11.3).
- **MVP / Full**: full.

### 10.1 Control roll-up (POC)

POC V1 ships **at least 5** Silverfort controls per `POC_V1_SCOPE.md` §5.5. The required-for-POC set:

| Control | Area | POC reason |
|---|---|---|
| `SF-CONN-001` | Connector design | Required by POC scope (Connector design stub) |
| `SF-POL-001` | Policy inventory | Required by POC scope (Policy coverage) |
| `SF-POL-002` | Privileged groups covered | Required by POC scope (Policy coverage) |
| `SF-ENR-001` | Privileged enrollment | Required by POC scope (Privileged enrollment) |
| `SF-SA-001` | Service-account discovery | Required by POC scope (Service-account coverage) |
| `SF-AD-001` | Tier 0 coverage gap | Required by POC scope (AD Tier 0 correlation) |

That is 6 controls — meeting the ≥ 5 requirement with one extra for correlation visibility. `SF-AD-003` is reused by the BloodHound demo (see §13).

---

## 11. Finding types — payload examples

The Silverfort module emits findings using the **shared core `Finding` shape** (verbatim from `MODULE_ARCHITECTURE.md` §10 — no module-specific subclass). Module-specific data lives in `payload`.

> **Finding shape (verbatim from `MODULE_ARCHITECTURE.md` §10).**
>
> `id, assessment_run_id, title, category, module_id, severity, risk_score, license_status, summary_internal, summary_customer, technical_detail, remediation, validation_method, state, customer_visibility, evidence_refs, identity_refs, correlation_refs, payload, created_at, updated_at`.

### 11.1 SF-POL-002 — Privileged Groups Covered by Policy

```yaml
title: "AD privileged groups missing Silverfort policy coverage"
category: "silverfort.policy"
module_id: "silverfort"
severity: "high"
risk_score: 72
license_status: "licensed_disabled"
summary_internal: |
  3 AD privileged groups (Domain Admins, Enterprise Admins, Schema Admins) have
  no enforcing Silverfort policy covering them. 12 privileged identities are exposed.
summary_customer: |
  Several privileged Active Directory groups are not protected by Silverfort policies,
  meaning step-up authentication is not enforced for these accounts.
technical_detail: |
  Groups uncovered:
    - Domain Admins (8 members)
    - Enterprise Admins (1 member)
    - Schema Admins (3 members)
  Reference policies considered enforcing:
    - action ∈ {require_mfa, block} AND enabled = true
remediation: |
  Add Domain Admins, Enterprise Admins, and Schema Admins to the existing
  "priv-mfa" policy scope.groups, or create a dedicated privileged-coverage policy.
validation_method: |
  Re-export Silverfort policies; SF-POL-002 should re-evaluate to pass.
state: "new"
customer_visibility: "internal_only"   # default per D-0009
evidence_refs:
  - evidence_id: "<sf-policies evidence>"
identity_refs: [<UUIDs of the 12 privileged identities>]
correlation_refs: []
payload:
  uncovered_groups: ["Domain Admins", "Enterprise Admins", "Schema Admins"]
  covered_groups: ["Backup Operators"]
  policy_inventory_count: 12
  enforcing_policy_count: 4
```

### 11.2 SF-SA-001 — Service Account Discovery Coverage

```yaml
title: "Silverfort service-account discovery covers only 62% of AD service accounts"
category: "silverfort.service_account"
module_id: "silverfort"
severity: "medium"
risk_score: 58
license_status: "licensed_misconfigured"
summary_internal: |
  AD module identified 34 service accounts (canonical_kind = service_account).
  Silverfort discovered 21 of these (62%). 13 service accounts are not visible
  to Silverfort and are therefore not protected by any service-account policy.
summary_customer: |
  About a third of service accounts visible in Active Directory are not yet visible
  to Silverfort. These accounts are not currently protected by Silverfort policies.
technical_detail: |
  Discovery gap analysis:
    - AD-identified service accounts: 34
    - Silverfort-discovered: 21
    - Missing: 13 (listed in evidence drawer)
  Threshold: ≥ 80% required for pass.
remediation: |
  Extend Silverfort discovery sources or reconcile the 13 missing service accounts
  manually with the customer team.
validation_method: |
  Re-run discovery; re-export service-accounts.json; SF-SA-001 should re-evaluate to pass.
state: "new"
customer_visibility: "internal_only"
evidence_refs:
  - evidence_id: "<sf-service-accounts evidence>"
  - evidence_id: "<ad-toolkit-zip evidence>"
identity_refs: [<13 unlinked-or-AD-only service account IDs>]
correlation_refs:
  - kind: "ad_service_account_inventory"
    target_module: "ad"
payload:
  ad_service_account_count: 34
  sf_service_account_count: 21
  gap_count: 13
  coverage_ratio: 0.617
```

### 11.3 SF-AD-001 — Tier 0 Silverfort Coverage Gap

```yaml
title: "AD Tier 0 identities lacking Silverfort policy coverage"
category: "silverfort.correlation.ad"
module_id: "silverfort"
severity: "critical"
risk_score: 88
license_status: "licensed_disabled"
summary_internal: |
  4 AD Tier 0 identities are not in scope of any enforcing Silverfort policy.
  These identities can authenticate without Silverfort step-up, undermining
  the compensating-control assumption.
summary_customer: |
  Several top-tier privileged Active Directory accounts are not protected by
  Silverfort. These accounts can authenticate without step-up verification.
technical_detail: |
  Tier 0 identities uncovered (4):
    - alice.admin (sAMAccountName)
    - svc-backup-tier0
    - krbtgt
    - svc-dc-replication
  Enforcing-policy criteria: enabled = true AND action ∈ {require_mfa, block}.
remediation: |
  Add the four uncovered Tier 0 identities (or their containing groups) to the
  "priv-mfa" policy scope. Where the identity is a service account, ensure the
  account is enrolled (see SF-ENR-001).
validation_method: |
  Re-export Silverfort policies; SF-AD-001 should evaluate to pass.
state: "new"
customer_visibility: "internal_only"
evidence_refs:
  - evidence_id: "<sf-policies evidence>"
  - evidence_id: "<ad-toolkit-zip evidence>"
identity_refs: [<UUIDs of 4 Tier 0 identities>]
correlation_refs:
  - kind: "ad_tier0_inventory"
    target_module: "ad"
  - kind: "bh_path_target"   # if any BH path lands here, see SF-AD-003
    target_module: "bloodhound"
payload:
  tier0_uncovered_count: 4
  tier0_total_count: 7
  enforcing_policies_considered: ["priv-mfa", "block-legacy"]
```

---

## 12. AD correlation

The Silverfort module is heavily AD-aware. Per `MODULE_ARCHITECTURE.md` §11.1, **correlation rules are executed by core** but **declared next to the module that knows best**. The Silverfort module declares one such rule for AD:

- `CORR-AD-SF-001` "AD Tier 0 lacking Silverfort coverage" (already listed in `MODULE_ARCHITECTURE.md` §11.3).

**How it reads AD module data**:

- Through the core `Identity` view: `is_tier0`, `is_privileged`, `canonical_kind` (per `MODULE_ARCHITECTURE.md` §8).
- The Silverfort module does **not** import from `modules/ad/...` (architecture rule §18 "no module → module imports").

**How SF-AD-001 fires**:

```
Tier 0 identities (AD-contributed)  −  identities covered by enforcing SF policies
                                    =  the SF-AD-001 finding (when non-empty)
```

The result is also surfaced as a `correlation_refs` entry on related AD findings (e.g., on `AD-PRIV-005` Privileged Service Accounts) via the core orchestrator, so the consultant sees the gap from either side.

---

## 13. BloodHound correlation

The Silverfort module participates in the **headline POC correlation**: `CORR-BH-SF-001` "BloodHound critical path on identity without Silverfort policy coverage" (per `MODULE_ARCHITECTURE.md` §11.3).

**Mechanics**:

- For each BloodHound finding of category `bh.path`, the path's **target Identity** is extracted from the BH finding's `identity_refs`.
- The Silverfort module's contribution to the orchestrator answers: is this Identity covered by an enforcing `sf_policy` (via `sf_policy_coverage`)?
- Output:
  - A per-path flag (`sf_covered: true | false`) added to the BH finding's `correlation_refs`.
  - A roll-up Silverfort finding (`SF-AD-003`) for paths whose target is uncovered.

**Surfacing on the BH finding**:

Per the BloodHound module design (and `UI_DESIGN_DIRECTION.md` §13), each BH path detail drawer shows "correlation chips" — one of them is the Silverfort coverage flag. The chip reads `SF: covered` (Turquoise dot) or `SF: not covered` (Trinidad dot) depending on this rule's output.

This **does not** require BH-module → SF-module imports. The orchestrator passes a `view` containing both modules' normalized data (`MODULE_ARCHITECTURE.md` §11.1).

---

## 14. Entra correlation

The Silverfort module contributes to `CORR-AD-ENTRA-001` "AD privileged identity synced to Entra cloud-privileged role" by providing the coverage flag on the AD side.

**SF-ENTRA-001 specifically**:

- Source set: identities where `is_privileged = true` (AD) **AND** the Entra module contributed an `entra_role_assignment` row marking the same Identity as cloud-privileged (via `azure_object_id` link to AD `onPremisesImmutableId`, per A-0011 / `MODULE_ARCHITECTURE.md` §8 linking rules).
- Output set: subset of the above that is **not** covered by an enforcing Silverfort policy.
- Finding category: `silverfort.correlation.entra`.
- Severity: defaults to `high`; risk_score elevated by correlation_breadth_bonus per `LICENSE_MODEL.md` §7.5.

---

## 15. Dashboard — Silverfort module page

Composition per `UI_DESIGN_DIRECTION.md` §14 — **no new components introduced**.

Layout (template `M` from `UI_DESIGN_DIRECTION.md` §4.3):

```
PageHeader: "Silverfort"
  supporting sentence: "<X> policies · <Y> covered identities · <Z> service accounts"
  actions: [ Upload evidence ] [ Re-evaluate ]

Row 1 — 4 × StatusCard:
  1. Connector            (POC: StatusBadge variant = pending; tooltip = "Connector not configured (POC)")
  2. Policy Coverage      (StatusBadge variant per SF-POL-002 aggregate result)
  3. Enrollment           (StatusBadge variant per SF-ENR-001 aggregate result)
  4. Service Accounts     (StatusBadge variant per SF-SA-001 aggregate result)

Row 2 — RingChart (control coverage: passing / partial / failing / not-applicable / unknown)
       + PriorityList (top Silverfort findings; default sort by risk_score desc)

Row 3 (optional) — PriorityList "Coverage gaps" (filtered to SF-POL-002, SF-AD-001, SF-AD-003, SF-ENTRA-001)

Right rail (optional) — ActionPanel for "Upload Silverfort export" (POC)
                                       "Configure Silverfort connector" (MVP, hidden in POC)
```

**Components reused** (all from `UI_DESIGN_DIRECTION.md` §3 — none are new):

- `PageHeader`
- `StatusCard` (×4) — each composed of `IconCircle` + `StatusBadge` + title + meta + progress + percent
- `StatusBadge` — `pending` for connector in POC; other variants by control result
- `RingChart`
- `PriorityList` + `PriorityListItem`
- `ActionPanel`
- `Drawer` for finding detail (opened from PriorityList rows)
- `Tag` / `Chip` for license-status badges within each row

**POC explicit behaviour**:

- Connector StatusCard always shows `pending` with the tooltip "Connector not configured (POC). Manual evidence accepted via the upload action."
- Findings drawer is the shared core finding drawer; module-side data is rendered from `payload`.

---

## 16. Reporting

The Silverfort module ships `reports/internal.html` and `reports/customer.html` Jinja partials per `MODULE_ARCHITECTURE.md` §13.3. The renderer composes them after the AD and BloodHound sections and before Entra.

### 16.1 Internal Detailed report — Silverfort section

Sections (rendered in order):

1. **Tenant context** — tenant id (where present), region, sf_version, exported_at, mode (manual / api), source attribution.
2. **Connector / data availability** — SF-CONN-001 / SF-CONN-002 status.
3. **Policy summary** — count, enabled count, enforcing count; SF-POL-001, SF-POL-002, SF-POL-003 results.
4. **Enrollment** — SF-ENR-001 result; per-identity table (privileged identities only).
5. **Service accounts** — SF-SA-001 through SF-SA-004 results; top-risk NHIs table.
6. **Entity risk** — SF-RISK-001 result; top-N entities.
7. **Correlations** — SF-AD-001, SF-AD-002, SF-AD-003, SF-ENTRA-001 findings.
8. **License context** — applicable Silverfort SKU + capability ownership table (per `LICENSE_MODEL.md` §5).

### 16.2 Customer Summary report — Silverfort section

Filtered to findings where `customer_visibility ∈ {customer_summary, customer_full}` per D-0009 / `SECURITY_AND_GDPR.md` §17.

Sections (rendered in order):

1. **Headline** — number of Silverfort-related findings, dominant theme (e.g., "privileged coverage gaps").
2. **Top 3 customer-relevant findings** — executive framing only; no raw SID/UPN exposure.
3. **Opportunity framing** — if Silverfort capabilities are `not_licensed`, an Opportunity card (no pricing, no sales framing per `LICENSE_MODEL.md` §13).

**Reminder**: even at `customer_full`, the renderer may still **suppress raw policy JSON** (default-on) under `SECURITY_AND_GDPR.md` §7.4 ("Highly sensitive: Silverfort policy state"). The consultant can override per finding but cannot override the bundle-level `internal_only` default for the raw artifact view.

### 16.3 Customer-visibility defaults (module manifest)

Per `MODULE_ARCHITECTURE.md` §6 (`customer_visibility_defaults`):

| Finding category | Default |
|---|---|
| `silverfort.policy` | `internal_only` |
| `silverfort.service_account` | `internal_only` |
| `silverfort.enrollment` | `internal_only` |
| `silverfort.entity_risk` | `internal_only` |
| `silverfort.correlation.ad` | `internal_only` |
| `silverfort.correlation.entra` | `internal_only` |
| `silverfort.aggregate_status` | `customer_summary` (allowed) |

Consultants can elevate per-finding via the drawer footer's visibility selector (`UI_DESIGN_DIRECTION.md` §10).

---

## 17. POC / MVP / Full scope

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| Manual export bundle (`silverfort-export-bundle`) parser | ✅ | ✅ | ✅ |
| Connector design documented | ✅ | ✅ | ✅ |
| Connector implementation against `/getBootStatus` *(unverified — requires Silverfort validation)* | ⬜ | 🟡 gated | ✅ |
| Connector implementation against `/v2/public/policies` *(unverified — requires Silverfort validation)* | ⬜ | 🟡 gated | ✅ |
| Connector implementation against `/getServiceAccountsInsights` *(unverified — requires Silverfort validation)* | ⬜ | 🟡 gated | ✅ |
| Connector implementation against `/getUsersEnrollment` *(unverified — requires Silverfort validation)* | ⬜ | 🟡 gated | ✅ |
| Connector implementation against `/getEntityRisk` *(unverified — requires Silverfort validation)* | ⬜ | 🟡 gated | ✅ |
| Normalized schemas (`sf_policy`, `sf_policy_coverage`, `sf_service_account`, `sf_enrollment`, `sf_entity_risk`) | ✅ | ✅ | ✅ |
| SF-CONN-001 / SF-CONN-002 | ✅ design / ⬜ eval (POC) | ✅ | ✅ |
| SF-POL-001 | ✅ | ✅ | ✅ |
| SF-POL-002 | ✅ | ✅ | ✅ |
| SF-POL-003 | 🟡 optional | ✅ | ✅ |
| SF-ENR-001 | ✅ | ✅ | ✅ |
| SF-RISK-001 | 🟡 optional | ✅ | ✅ |
| SF-SA-001 | ✅ | ✅ | ✅ |
| SF-SA-002 | 🟡 optional | ✅ | ✅ |
| SF-SA-003 | 🟡 optional | ✅ | ✅ |
| SF-SA-004 | 🟡 optional | ✅ | ✅ |
| SF-AD-001 (Tier 0 correlation) | ✅ | ✅ | ✅ |
| SF-AD-002 (Delegation correlation) | 🟡 optional | ✅ | ✅ |
| SF-AD-003 (BH path correlation) | ✅ | ✅ | ✅ |
| SF-ENTRA-001 (Hybrid correlation) | 🟡 covered by `CORR-AD-ENTRA-001` | ✅ | ✅ |
| License-aware status (8-value) on every control | ✅ | ✅ | ✅ |
| `customer_visibility` defaults per category | ✅ | ✅ | ✅ |
| Internal + Customer report sections | ✅ | ✅ | ✅ |
| Audit-log integration (upload, parse, evaluate, finding state, visibility, publish) | ✅ | ✅ | ✅ |
| Connector secret storage in secret manager | ⬜ | ✅ | ✅ |
| API rate limiting + retry / backoff | ⬜ | ✅ | ✅ |
| API health probe scheduling | ⬜ | ✅ | ✅ |
| Multi-tenant per-customer connector configuration | ⬜ | 🟡 partial | ✅ |

**Definition of "✅ POC" for the Silverfort module**: at least 5 controls (SF-CONN-001 design, SF-POL-001, SF-POL-002, SF-ENR-001, SF-SA-001, SF-AD-001) evaluable against the synthetic Silverfort export bundle, including the Tier 0 / BH-path correlation outputs visible in the demo per `POC_V1_SCOPE.md` §4 step 6 and step 8.

---

## 18. Risks and questions

### 18.1 Risks (verbatim from `RISKS.md`)

#### R-0003 — Silverfort API assumptions break at MVP

> Date: 2026-05-15
> Status: mitigating
> Category: technical / commercial
> Probability: medium
> Impact: medium
> Owner: Silverfort Module role
> Description: The publicly referenced Silverfort endpoints may not be available, may have different shapes, or may require unexpected licensing or onboarding effort.
> Mitigation: POC is manual-mode only (D-0006). MVP connector implementation is gated on official Silverfort validation. Every API claim tagged "requires validation" in the docs.
> Trigger: Connector implementation begun without explicit Silverfort validation.

### 18.2 Open questions (verbatim from `OPEN_QUESTIONS.md`)

#### Q-0090 — Silverfort API validation

> Q-0090 | MVP | Kristof + Silverfort support — Validate which API endpoints are available in the customer's Silverfort version and the auth model. The five endpoints in the prompt are unconfirmed. *Why it matters:* connector design.

#### Q-0091 — Manual export format

> Q-0091 | POC | Kristof — What evidence format will customers export from Silverfort manually for POC — JSON exports from Silverfort UI, CSV, or screenshots? *Why it matters:* parser scope.

#### Q-0092 — Standard policy template

> Q-0092 | POC | Kristof — Do customers have a standard Silverfort "AD privileged groups" policy template we should assume exists, or is policy state highly customer-specific? *Why it matters:* control logic.

### 18.3 Module-side mitigation notes

- The module's parser shape is **permissive** for all five endpoints — extra fields ignored; missing optional fields tolerated; explicit `evidence_schema_version` carried in `env.json` so future format changes are detectable.
- All references to `action ∈ {require_mfa, block}` in SF-POL-002 and SF-AD-001 are an **assumed action vocabulary** subject to Q-0092 confirmation. The control's `evaluator_version` will bump when this is confirmed.
- Manual mode is the **sole supported mode** for POC. Any drift toward API implementation in POC is a direct violation of D-0006 and must be rejected at code review.

---

## 19. Complexity-control checklist

Per `WORKING_APPROACH.md` §11:

- [x] Tier explicitly tagged on every control (POC / MVP / Full).
- [x] Belongs to the Silverfort module only (no AD / BH / Entra module logic embedded).
- [x] Reuses existing UI patterns (`UI_DESIGN_DIRECTION.md` §14) — no new components.
- [x] Reuses shared `Finding` shape verbatim (`MODULE_ARCHITECTURE.md` §10).
- [x] Reuses 8-value license_status enum verbatim (`D-0007`, `LICENSE_MODEL.md` §3).
- [x] Demo path documented (`POC_V1_SCOPE.md` §4 steps 6, 8 + §12).
- [x] Explicit "what we will NOT do here" line:
  - POC will **not** call any Silverfort API.
  - POC will **not** support CSV / screenshot evidence (Q-0091 unresolved).
  - POC will **not** alter Silverfort tenant state.
- [x] Does not require a real connector at POC tier.
- [x] Does not duplicate logic from other documents (cross-references used throughout).

---

*Last updated: 2026-05-15.*
