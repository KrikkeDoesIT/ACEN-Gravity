# ENTRA_MODULE_DESIGN.md

> Design for the **Entra** evidence module: how ACEN Gravity ingests Microsoft Entra ID (Azure AD) evidence, normalizes it, and evaluates license-aware controls covering Conditional Access, MFA / authentication methods, privileged roles & PIM, breakglass accounts, enterprise apps & service principals, guests, hybrid identity, and (where licensed) Identity Protection signals.
>
> Microsoft licensing is the **primary commercial nuance** of this module: every control declares its license dependency, and the `not_licensed` status never reduces the **Current License Score** (D-0008, `LICENSE_MODEL.md` §3 / §7).
>
> Companion: `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md` §5.6 / §13, `MODULE_ARCHITECTURE.md` §11 (correlation), `LICENSE_MODEL.md`, `SECURITY_AND_GDPR.md`, `UI_DESIGN_DIRECTION.md` §12 / §15, `AD_MODULE_DESIGN.md`, `BLOODHOUND_ANALYZER_DESIGN.md`, `SILVERFORT_MODULE_DESIGN.md`.

---

## 1. Goals

The Entra module exists to assess the **identity-security posture of a Microsoft Entra ID tenant** for one customer, in one assessment run, with **license-aware** controls and **deterministic** findings.

It assesses:

- **Conditional Access (CA):** policy coverage, MFA enforcement, legacy auth, risk-based access, exclusions, breakglass exclusions, device compliance.
- **MFA & authentication methods:** registration coverage, phishing-resistant methods for admins, weak method policy state.
- **Privileged roles & PIM:** Global Administrator count, permanent vs eligible vs active assignments, activation settings, role assignment review.
- **Breakglass accounts:** presence, monitoring, CA handling.
- **Enterprise apps, app registrations, service principals:** high-privilege application permissions, long-lived secrets, expired credentials, ownership, risky consent grants, unused apps.
- **Guests / external collaboration:** exposure, invite settings, external collaboration restrictions.
- **Hybrid identity:** synced privileged accounts, Entra Connect server identification, on-prem-to-cloud privilege overlap, BloodHound path overlap on hybrid admins.
- **Risky users / risky sign-ins:** Identity Protection signals (license-gated to Entra ID P2).
- **Device compliance context:** referenced as input to CA controls; full device posture is **not** owned by this module (Intune is a future module).
- **Tenant-wide security settings:** authentication method policy, external collaboration settings, default user role permissions.
- **Access reviews / entitlement management:** capability detection (P2-gated).
- **Silverfort coverage of Entra-privileged identities:** cross-module correlation.

The module does **not** assess:

- Defender XDR or Defender for Identity (future modules; capability is referenced for `requires_add_on` accounting only).
- Intune device compliance posture itself (future Intune module).
- Email security / Purview / data classification.
- Application-level vulnerabilities (Defender for Cloud Apps territory).
- Real-time signals beyond the dump's snapshot (continuous monitoring is `Full` tier).

### 1.1 Tiered intent

| Intent | POC | MVP | Full |
|---|:---:|:---:|:---:|
| Parse `entra-graph-json-bundle` and produce ≥ 6 controls | ✅ | ✅ | ✅ |
| License-aware UI visibly demonstrated (≥ 1 `licensed_disabled`, ≥ 1 `not_licensed`) | ✅ | ✅ | ✅ |
| Live Microsoft Graph collector (application permissions) | ⬜ design only | ✅ | ✅ |
| `subscribedSkus` auto-detected; consultant confirms | ⬜ consultant picks SKUs | ✅ Graph reads, consultant confirms | ✅ Graph reads, optional auto-trust |
| Identity Protection signals (P2-gated) | 🟡 dump-only, not in core controls | ✅ | ✅ |
| Continuous Entra delta monitoring | ⬜ | ⬜ | ✅ |
| Access reviews / entitlement management deep evaluation | ⬜ detection only | 🟡 partial | ✅ |
| Hybrid Identity correlation with AD + BloodHound + Silverfort | ✅ minimum viable | ✅ | ✅ |

---

## 2. Data sources

### 2.1 POC — `entra-graph-json-bundle`

A ZIP bundle of JSON dumps that mirror the Microsoft Graph response shapes. Authored synthetically for POC (D-0011, A-0012). Files inside the bundle are named after their Graph collection.

| File | Graph endpoint mirrored | Required (POC) |
|---|---|---|
| `manifest.json` | (toolkit-specific) tenant id, dump version, collected_at | ✅ |
| `organization.json` | `/organization` | ✅ |
| `subscribedSkus.json` | `/subscribedSkus` | ✅ (or consultant override) |
| `users.json` | `/users` (selected props) | ✅ |
| `groups.json` | `/groups` | ✅ |
| `groupMembers/*.json` | `/groups/{id}/members` | ✅ (for privileged groups) |
| `directoryRoles.json` | `/directoryRoles` | ✅ |
| `roleAssignments.json` | `/roleManagement/directory/roleAssignments` | ✅ |
| `roleEligibility.json` | `/roleManagement/directory/roleEligibilitySchedules` | 🟡 (only if PIM in scope) |
| `roleActive.json` | `/roleManagement/directory/roleAssignmentSchedules` | 🟡 |
| `conditionalAccessPolicies.json` | `/identity/conditionalAccess/policies` | ✅ |
| `authenticationMethodPolicy.json` | `/policies/authenticationMethodsPolicy` | ✅ |
| `userAuthenticationMethods/*.json` | `/users/{id}/authentication/methods` | 🟡 (sample for top admins) |
| `applications.json` | `/applications` | ✅ |
| `servicePrincipals.json` | `/servicePrincipals` | ✅ |
| `oauth2PermissionGrants.json` | `/oauth2PermissionGrants` | ✅ |
| `appRoleAssignments.json` | `/servicePrincipals/{id}/appRoleAssignments` | ✅ |
| `appOwners/*.json` | `/applications/{id}/owners` | 🟡 |
| `appCredentials/*.json` (synthetic) | passwordCredentials + keyCredentials extracted | ✅ |
| `devices.json` | `/devices` | 🟡 (used as input to CA-007 only) |
| `riskyUsers.json` | `/identityProtection/riskyUsers` | 🟡 license-gated |
| `riskDetections.json` | `/identityProtection/riskDetections` | 🟡 license-gated |
| `directorySettings.json` | `/groupSettings` + tenant settings | 🟡 |
| `policies/authorizationPolicy.json` | `/policies/authorizationPolicy` | 🟡 |
| `accessReviews.json` | `/identityGovernance/accessReviews/definitions` | 🟡 P2-gated |
| `entitlementManagement.json` | `/identityGovernance/entitlementManagement/*` | 🟡 P2-gated |
| `onPremisesPublishingProfiles.json` (sync) | `/onPremisesPublishingProfiles` | 🟡 hybrid only |
| `directorySync.json` (synthetic indicator) | derived: `onPremisesSyncEnabled` + connector accounts | 🟡 hybrid only |

The `manifest.json` is mandatory; parsing aborts if it is missing or invalid (per `MODULE_ARCHITECTURE.md` §3 failure rules).

### 2.2 MVP — Microsoft Graph application-permissions read flow

The MVP collector authenticates via an **app registration** with **read-only application permissions** (A-0007). Permissions are granted by the customer's Global Administrator at consent time and never escalated by the platform.

Operational model (Q-0081 carries the multitenant vs single-tenant decision):

- **Bring-your-own app registration** (recommended for POC→MVP transition): customer creates the app, grants consent, shares tenant id + client id. ACEN platform never sees the client secret if certificate-based auth is used.
- **ACEN-published multitenant app**: faster onboarding, more trust burden on ACEN.

The collector dumps Graph endpoints into the same `entra-graph-json-bundle` shape used by the POC parser. **No reshaping happens MVP-side**: the parser is the single source of truth and operates identically against synthetic data and live data.

### 2.3 Recommended least-privilege application permissions

Per A-0007, all permissions are **read-only application permissions**.

| Permission | Why | Used by |
|---|---|---|
| `Organization.Read.All` | Tenant metadata, `onPremisesSyncEnabled` | ENTRA-LIC-001, ENTRA-HYBRID-* |
| `Directory.Read.All` | Users, groups, group members, directory roles | ENTRA-PRIV-*, ENTRA-GUEST-* |
| `User.Read.All` | User properties | All |
| `Group.Read.All` | Group membership detail | ENTRA-PRIV-*, ENTRA-GUEST-* |
| `RoleManagement.Read.Directory` | Role assignments + PIM eligibility/active | ENTRA-PRIV-*, ENTRA-BG-* |
| `Policy.Read.All` | CA policies, authentication method policy, authorization policy | ENTRA-CA-*, ENTRA-AUTH-* |
| `Application.Read.All` | Applications + service principals + permissions | ENTRA-APP-* |
| `AppRoleAssignment.ReadWrite.All` | **Avoided** — read-only alternative used | (none) |
| `Device.Read.All` | Device list (for CA context) | ENTRA-CA-007 |
| `AuditLog.Read.All` | Inactivity detection (last sign-in, app last activity) | ENTRA-APP-006, ENTRA-USER-* (Full) |
| `IdentityRiskyUser.Read.All` | Risky user signals — **license-gated** to P2 | ENTRA-IP-* (license-gated) |
| `IdentityRiskEvent.Read.All` | Risk detections — **license-gated** to P2 | ENTRA-IP-* (license-gated) |
| `AccessReview.Read.All` | Access reviews definitions | ENTRA-LIC-005 |
| `EntitlementManagement.Read.All` | Entitlement management state | ENTRA-LIC-005 |
| `AuthenticationContext.Read.All` | Authentication contexts for CA | ENTRA-CA-* (Full) |

Notes:

- We do **not** request `Application.ReadWrite.All`, `Directory.ReadWrite.All`, or `Policy.ReadWrite.All` at any tier. The platform is read-only.
- `AuditLog.Read.All` is the permission most often questioned by customer admins (Q-0080); the module degrades gracefully when it is absent (controls that depend on last-activity move to `unknown` with a documented reason).
- Identity Protection permissions degrade to `not_licensed` (not `unknown`) when the tenant lacks Entra ID P2.

---

## 3. Graph model

The Entra module consumes the following Graph object types. Endpoints are written in the canonical Graph form; the JSON dump files mirror these shapes.

| Object | Endpoint | Why this module needs it |
|---|---|---|
| Tenant / Organization | `/organization` | `tenantId`, `displayName`, `onPremisesSyncEnabled`, `verifiedDomains`, region indicators |
| Subscribed SKUs | `/subscribedSkus` | License catalog resolution per `LICENSE_MODEL.md` §5; mapped to capabilities |
| Users | `/users` | UPN, ObjectId, onPremisesImmutableId, accountEnabled, signInActivity, userType (`Member`/`Guest`), creationType, ageGroup |
| Groups | `/groups` | Security groups (esp. role-assignable), membership relations, mailEnabled, groupTypes |
| Group members | `/groups/{id}/members` | Resolve transitive privileged group membership |
| Directory roles | `/directoryRoles` | Active built-in directory roles + role templates |
| Role assignments | `/roleManagement/directory/roleAssignments` | Permanent assignments (`principalId`, `roleDefinitionId`, `directoryScopeId`) |
| Role eligibility schedules | `/roleManagement/directory/roleEligibilitySchedules` | PIM eligible assignments |
| Role assignment schedules | `/roleManagement/directory/roleAssignmentSchedules` | PIM active (just-in-time) assignments |
| Role management policies | `/policyRoot/roleManagementPolicies` | PIM activation settings (MFA on activation, approval, max duration) |
| CA policies | `/identity/conditionalAccess/policies` | Conditions, controls, exclusions, state |
| Auth method policy | `/policies/authenticationMethodsPolicy` | Per-method state, target groups, registration campaign |
| User authentication methods | `/users/{id}/authentication/methods` | Registered methods; phishing-resistant detection |
| Authorization policy | `/policies/authorizationPolicy` | Default user role permissions, guest invite settings |
| Applications | `/applications` | App registrations: appId, displayName, signInAudience, publisherDomainVerified, requiredResourceAccess |
| Service principals | `/servicePrincipals` | Enterprise apps: appOwnerOrganizationId, tags (built-in), assignmentRequired |
| OAuth2 permission grants (delegated) | `/oauth2PermissionGrants` | Delegated consent grants; user-consented vs admin-consented |
| App role assignments (application) | `/servicePrincipals/{id}/appRoleAssignments` | Application permissions assigned to SPs |
| App owners | `/applications/{id}/owners` + `/servicePrincipals/{id}/owners` | Ownerless app detection |
| App credentials | extracted from `passwordCredentials` + `keyCredentials` | Expiry, length-of-life detection |
| Devices | `/devices` | Compliance state context for CA-007 |
| Risky users | `/identityProtection/riskyUsers` | Identity Protection signal (P2-gated) |
| Risk detections | `/identityProtection/riskDetections` | Identity Protection events (P2-gated) |
| Group settings | `/groupSettings` | Guest restrictions, unified group settings |
| Access reviews | `/identityGovernance/accessReviews/definitions` | Capability detection only at POC; P2-gated |
| Entitlement management | `/identityGovernance/entitlementManagement/accessPackages` | Capability detection only at POC; P2-gated |
| On-premises publishing | `/onPremisesPublishingProfiles` (hybrid) | Indicators only |

> Inspiration for SKU → capability shape comes from public Microsoft documentation. m365maps is **inspiration only** (A-0014). Authoritative replacement before MVP is `subscribedSkus` plus Microsoft licensing documentation (Q-0071).

---

## 4. License-aware model (most important section)

This module is the **anchor case for `LICENSE_MODEL.md`**. License-awareness must be visibly demonstrated in the POC demo (per `POC_V1_SCOPE.md` §5.6 / §13 / §14).

### 4.1 How `subscribedSkus` is consumed

#### POC

- The consultant **picks owned SKUs** in the engagement setup screen (`CustomerSku.confirmed_by = "consultant"`).
- If the `subscribedSkus.json` file is present in the bundle, the **parser proposes** owned SKUs based on its content; the consultant accepts or overrides.
- Consultant override is logged in the audit log (`license.confirm`, `license.override`).

#### MVP

- The Graph collector reads `/subscribedSkus` and writes `CustomerSku.confirmed_by = "graph"`.
- The consultant can still override individual entries (e.g., grace-period mis-reporting).
- Q-0072 carries the question: *automatic detection vs always-confirm*. The default proposal is **auto-detect, consultant confirms** before scoring is finalized.

#### Full

- Live `subscribedSkus` re-read on a configurable cadence (continuous mode). Consultant confirmation continues to be available for edge cases.

### 4.2 SKU → capability mapping

Per `LICENSE_MODEL.md` §5. The Entra module reads only capabilities relevant to its controls; the full catalog is shared across modules.

Capabilities that this module's controls reference:

| Capability id | Required-by controls | Available in SKUs (POC catalog) |
|---|---|---|
| `entra.conditional-access` | ENTRA-LIC-002, ENTRA-CA-001..007 | `entra-id-p1`, `m365-e3`, `m365-e5`, `ems-e3`, `ems-e5`, `entra-id-p2` |
| `entra.mfa.enforcement` | ENTRA-AUTH-001, ENTRA-CA-002 | same as CA |
| `entra.authentication-methods-policy` | ENTRA-AUTH-002, ENTRA-AUTH-003, ENTRA-AUTH-004 | `entra-id-p1`, `entra-id-p2`, `m365-e3`, `m365-e5`, `ems-e3`, `ems-e5` |
| `entra.pim` | ENTRA-LIC-003, ENTRA-PRIV-003, ENTRA-PRIV-005 | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.identity-protection.risky-users` | ENTRA-LIC-004, ENTRA-CA-004 | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.identity-protection.risky-signins` | ENTRA-CA-004 | same as risky-users |
| `entra.access-reviews` | ENTRA-LIC-005, ENTRA-PRIV-004 | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `entra.entitlement-management` | ENTRA-LIC-005 | `entra-id-p2`, `m365-e5`, `ems-e5` |
| `defender-identity.lateral-movement-detection` | preferred on ENTRA-HYBRID-001/004/005 | `m365-e5`, `ems-e5`, `defender-for-identity-standalone` |
| `silverfort.policy-engine` | preferred on ENTRA-SF-001/002 | `silverfort-standard` |
| `silverfort.privileged-mfa` | preferred on ENTRA-SF-001 | `silverfort-standard` |

### 4.3 Resolving each control to a `license_status`

Each Entra control runs through the resolver in `LICENSE_MODEL.md` §4.2. The Entra module's evaluator then refines `licensed_enabled` into `licensed_disabled` / `licensed_misconfigured` based on configuration evidence.

Worked decision tree (per control):

```
required capabilities for control
        │
        ▼
all required owned?  ── no ──▶ requires_add_on if missing cap has add_on
        │                       available_in_higher_tier if in higher SKU
        │ yes                   not_licensed otherwise
        ▼
evidence sufficient? ── no ──▶ unknown   (record reason; out of both scores)
        │ yes
        ▼
configured + active?  ── no ──▶ licensed_disabled  (fail or partial)
        │ yes
        ▼
weakening misconfig? ── yes ──▶ licensed_misconfigured (partial or fail)
        │ no
        ▼
                                 licensed_enabled (pass)
```

A control returns `not_applicable` **only** if its rubric explicitly declares the environment-exclusion case (e.g., a hybrid-only control on a cloud-only tenant).

### 4.4 Two-score behaviour on the Entra module

Restating `LICENSE_MODEL.md` §7 in Entra terms, with a worked example.

**Customer profile:** Contoso Corp — owns E3 (`m365-e3`) plus standalone Entra ID P1 (`entra-id-p1`). **No P2**. No Defender for Identity. Owns Silverfort.

**Example controls evaluating against Contoso:**

| Control | Required capabilities | license_status | Current Score | Target Score |
|---|---|---|---|---|
| `ENTRA-CA-001` Baseline CA Coverage | `entra.conditional-access` | `licensed_enabled` (configured) → **pass** | full contribution | full contribution |
| `ENTRA-CA-003` Legacy Auth Blocked | `entra.conditional-access` | `licensed_disabled` (capability owned, not configured) → **fail** | 0 contribution (fail) | 0 contribution (fail) |
| `ENTRA-CA-004` Risk-Based Access Policy | `entra.conditional-access` + `entra.identity-protection.risky-signins` | `not_licensed` (IP requires P2) | **excluded** | **counted as fail** |
| `ENTRA-PRIV-003` PIM Eligibility Coverage | `entra.pim` | `not_licensed` (PIM requires P2) | **excluded** | **counted as fail** |
| `ENTRA-LIC-005` Access Reviews Capability Available | `entra.access-reviews` | `not_licensed` (P2) | **excluded** | **counted as fail** |
| `ENTRA-AUTH-001` MFA Registration Coverage | `entra.mfa.enforcement` | `licensed_enabled` (some users registered) → **partial** | 0.5 × weight | 0.5 × weight |
| `ENTRA-HYBRID-001` Synced Privileged Accounts | (none required); preferred: `defender-identity.lateral-movement-detection` | `licensed_enabled` (no required caps); preferred missing → flagged | scored normally | scored normally |
| `ENTRA-SF-001` Entra Privileged User SF Coverage | preferred: `silverfort.policy-engine` (owned) | `licensed_enabled` | scored normally | scored normally |

**Outcome:**

- **Current License Score (Entra)** is calculated **only** over the controls in {`ENTRA-CA-001`, `ENTRA-CA-003`, `ENTRA-AUTH-001`, `ENTRA-HYBRID-001`, `ENTRA-SF-001`, …}. The P2-required controls (`ENTRA-CA-004`, `ENTRA-PRIV-003`, `ENTRA-LIC-005`, plus other Identity Protection / PIM / Access Reviews controls) are **excluded entirely** from the denominator. Contoso is not penalized for not owning P2.
- **Target Posture Score (Entra)** **counts** the P2-required controls as **fail** because the customer is not at the target posture without those capabilities. The gap (Opportunity Score) tells the consultant exactly what the upgrade would unlock.

This is the headline behaviour that **must be visible** in the POC demo (per `POC_V1_SCOPE.md` §13 / §14).

### 4.5 Visible UI states (POC requirement)

At least one Entra control must surface **each** of these UI states on the demo tenant. They map to `StatusBadge` variants in `UI_DESIGN_DIRECTION.md` §3.3.

| UI state | Control demonstrating it (POC default) | Reason |
|---|---|---|
| `licensed_enabled` (badge `licensed`) | `ENTRA-CA-001` baseline CA pass | Customer owns CA and has a baseline MFA policy |
| `licensed_disabled` (badge `info`/`warn`) | `ENTRA-CA-003` legacy auth not blocked | Customer owns CA but did not configure the policy |
| `licensed_misconfigured` (badge `warn`) | `ENTRA-CA-002` admin MFA with a 7-member breakglass exclusion group | Capability owned + configured, but weakened |
| `not_licensed` (badge `not-licensed`) | `ENTRA-LIC-004` Identity Protection not owned | Customer is on E3+P1, no P2 — **must not reduce Current Score** |
| `requires_add_on` | `ENTRA-HYBRID-002` (preferred DfI not owned) | Capability lives in DfI add-on; shown but not penalizing Current Score |
| `available_in_higher_tier` | (same as `not_licensed` in many cases; tooltip text differs) | Tooltip explains "available in E5 / EMS E5" |
| `not_applicable` | `ENTRA-HYBRID-*` on a cloud-only tenant variant (alt demo dataset) | Rubric excludes hybrid controls for cloud-only |
| `unknown` | An auth-method control where `userAuthenticationMethods` was not collected | Documented reason; user is told what to upload |

The POC must explicitly include the two callouts described in `POC_V1_SCOPE.md` §5.6:

- **One control showing `licensed_disabled`** — POC default: `ENTRA-CA-003 Legacy Authentication Blocked`. The control's tooltip says: *"You own Conditional Access (Entra ID P1). Legacy authentication is not blocked. Configuring this policy is a no-cost change."*
- **One control showing `not_licensed`** — POC default: `ENTRA-LIC-004 Identity Protection Capability Available` (and the downstream `ENTRA-CA-004 Risk-Based Access Policy`). Tooltip: *"Risk-based access requires Identity Protection (Entra ID P2). Your current SKUs do not include it. This does not reduce your Current License Score; it contributes to the Target Posture Opportunity."* (text per `UI_DESIGN_DIRECTION.md` §12).

---

## 5. Normalized model

Schemas follow the conventions in `MODULE_ARCHITECTURE.md` §4 (module-local tables prefixed `entra_`; cross-module entities go through core `Identity`).

### 5.1 Module-local tables (sketches)

```python
class EntraTenant(Base):
    id: UUID                          # internal
    assessment_run_id: UUID
    tenant_id: UUID                   # from Graph organization.id
    display_name: str
    on_premises_sync_enabled: bool
    verified_domains: list[str]       # JSONB
    region: str | None                # derived; "EU", "NA", "APAC", "Unknown"
    collected_at: datetime
    parser_version: str
```

```python
class EntraCAPolicy(Base):
    id: UUID
    assessment_run_id: UUID
    object_id: UUID                   # CA policy id
    name: str
    state: enum("enabled", "disabled", "enabledForReportingButNotEnforced")
    conditions: JSONB                 # users, applications, platforms, locations, clientAppTypes, signInRiskLevels, userRiskLevels
    grant_controls: JSONB             # builtInControls (mfa, compliantDevice, ...), authenticationStrength, operator
    session_controls: JSONB           # signInFrequency, persistentBrowser, ...
    exclusions: JSONB                 # excluded users / groups / roles (denormalized for fast lookup)
    created_at: datetime | None
    modified_at: datetime | None
```

```python
class EntraRoleAssignment(Base):
    id: UUID
    assessment_run_id: UUID
    identity_id: UUID                 # FK -> Identity
    role_id: str                      # roleDefinitionId
    role_name: str                    # denormalized for display
    scope: str                        # directoryScopeId ("/", "/administrativeUnits/...")
    assignment_type: enum("permanent", "eligible", "active")  # permanent = classic assignment; eligible/active = PIM
    expires_at: datetime | None
    activated_via: str | None         # "PIM", "permanent", "n/a"
    requires_mfa_on_activation: bool | None
    requires_approval: bool | None
    max_duration_minutes: int | None
```

```python
class EntraApp(Base):
    id: UUID
    assessment_run_id: UUID
    app_id: UUID                      # applications.appId
    object_id: UUID                   # applications.id
    display_name: str
    sign_in_audience: enum("AzureADMyOrg", "AzureADMultipleOrgs", "AzureADandPersonalMicrosoftAccount", "PersonalMicrosoftAccount")
    publisher_domain: str | None
    publisher_domain_verified: bool
    owners: list[UUID]                # FK -> Identity (denormalized)
    is_first_party: bool              # SP tag "WindowsAzureActiveDirectoryIntegratedApp" or appOwnerOrganizationId = Microsoft
    last_signin_at: datetime | None   # from AuditLog when available
    notes: str | None
```

```python
class EntraAppCredential(Base):
    id: UUID
    assessment_run_id: UUID
    app_object_id: UUID               # FK -> EntraApp.object_id
    kind: enum("secret", "certificate")
    key_id: UUID                      # passwordCredentials.keyId / keyCredentials.keyId
    start_date: datetime
    end_date: datetime                # expiry
    is_expired: bool                  # derived at parse time
    age_days: int                     # derived
    display_name: str | None
```

```python
class EntraAppPermission(Base):
    id: UUID
    assessment_run_id: UUID
    app_object_id: UUID               # FK -> EntraApp.object_id
    permission_id: str                # appRoleId or oauth2PermissionScopeId (GUID)
    permission_value: str             # human label, e.g., "Directory.ReadWrite.All"
    permission_type: enum("delegated", "application")
    admin_consented: bool             # for delegated: tenant-wide vs per-user
    granted_to_resource_app_id: UUID  # the API the permission targets (usually Graph)
    scope: str | None                 # delegated: scope string; application: n/a
    is_high_privilege: bool           # computed from the high-privilege list (see §13)
```

```python
class EntraRiskyUser(Base):
    id: UUID
    assessment_run_id: UUID
    identity_id: UUID                 # FK -> Identity
    risk_level: enum("low", "medium", "high", "hidden", "none")
    risk_state: enum("atRisk", "confirmedCompromised", "remediated", "dismissed", "none")
    risk_detail: str | None
    last_updated_at: datetime
    source: enum("identityProtection", "consultant_override")
```

```python
class EntraAuthnMethodPolicy(Base):
    id: UUID
    assessment_run_id: UUID
    method: enum("fido2", "windowsHelloForBusiness", "microsoftAuthenticator", "sms", "voice", "email", "temporaryAccessPass", "x509Certificate", "softwareOath")
    state: enum("enabled", "disabled")
    target_groups: JSONB              # list of group ids or "All users"
    excluded_groups: JSONB
    is_phishing_resistant: bool       # derived: fido2 / WHfB / x509 = True
    is_weak: bool                     # derived: sms / voice = True
```

```python
class EntraGuest(Base):
    id: UUID
    assessment_run_id: UUID
    identity_id: UUID
    invite_redeemed_at: datetime | None
    creation_type: str                # "Invitation", "EmailVerified", ...
    external_user_state: enum("Accepted", "PendingAcceptance")
    invited_by_identity_id: UUID | None
    has_privileged_role: bool         # set after role assignments parsed
    has_app_assignment: bool          # set after appRoleAssignments parsed
```

```python
class EntraDirectorySync(Base):
    id: UUID
    assessment_run_id: UUID
    on_premises_sync_enabled: bool
    connector_service_account_upn: str | None     # synthetic indicator; usually `Sync_<server>_<hash>@<tenant>`
    connector_server_hostnames: list[str]         # from synced device/account naming convention
    last_sync_at: datetime | None
    sync_features: JSONB                          # passwordSync, passthroughAuth, seamlessSSO, federation
```

### 5.2 Contributions to core `Identity`

The module upserts into `Identity` (per `MODULE_ARCHITECTURE.md` §8).

Fields set by Entra evidence:

| Identity field | Source |
|---|---|
| `azure_object_id` | `users.id` (primary key for Entra-side identity match) |
| `upn` | `users.userPrincipalName` |
| `canonical_label` | `users.displayName` (or UPN as fallback) |
| `object_guid` (derivative) | base64-decoded `users.onPremisesImmutableId` when present (= AD `objectGUID` value); enables AD↔Entra link |
| `sam_account_name` | `users.onPremisesSamAccountName` when present |
| `is_privileged` | set `True` if any directoryRole assignment is in the privileged-roles list |
| `is_breakglass` | set `True` via convention (display_name / upn pattern) or consultant tag in setup screen |
| `canonical_kind` | `"user"` / `"service_account"` / `"guest"` / `"app"` based on userType + assignment context |

Linking rules (deterministic):

1. **AD-then-Entra**: if AD evidence ran first and produced an `Identity` with `object_guid = X`, and Entra `users.onPremisesImmutableId` decodes to the same GUID, the same `Identity` row is updated.
2. **Entra-then-AD**: the parser writes `azure_object_id` and `object_guid` derivative; the AD parser later matches by `object_guid`.
3. **Cloud-only users**: no `object_guid` derivable; identified by `azure_object_id` only.
4. **Ambiguous match** (UPN-only match with no immutableId in a hybrid tenant): the linker raises an `IdentityAmbiguity` row per `MODULE_ARCHITECTURE.md` §8 rule 5. **No silent merging**.

---

## 6. Controls

The Entra module declares ~40 controls grouped by domain. POC implements **≥ 6** (per `POC_V1_SCOPE.md` §5.6); MVP implements the full set marked below; Full Product adds the continuous-monitoring and access-reviews evaluation depth.

Each control block below documents: id, title, objective, evidence required, required / preferred capabilities, status enum behaviour, finding example, remediation direction, and tier support (POC / MVP / Full).

> Tag legend (capability column): **(R)** = required (absence → `not_licensed` / `requires_add_on` / `available_in_higher_tier`); **(P)** = preferred (absence flagged in `correlation_refs` only; does not change `license_status`).

### 6.1 Licensing & capability detection

#### ENTRA-LIC-001 — License and Capability Detection

- **Objective:** Snapshot the tenant's owned SKUs and resolve owned capabilities; surface unknown SKUs to consultant review.
- **Evidence:** `subscribedSkus.json` and/or consultant-confirmed `CustomerSku` rows.
- **Capabilities:** (none — this control evaluates the catalog itself)
- **Status behaviour:** `licensed_enabled` when SKUs resolved; `unknown` when no `subscribedSkus.json` and no consultant input.
- **Finding example:** *"Tenant owns: Microsoft 365 E3, Entra ID P1. Identity Protection / PIM / Access Reviews require Entra ID P2 — not owned."*
- **Remediation direction:** Confirm SKU list with the consultant; map unknown SKUs to the catalog.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-LIC-002 — Conditional Access Capability Available

- **Objective:** Detect whether CA capability is owned.
- **Evidence:** owned capability set.
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:** `licensed_enabled` if owned; `not_licensed` otherwise (rare — most M365 tenants own CA).
- **Finding example:** None on success; on `not_licensed`: *"Conditional Access requires Entra ID P1+. No CA controls evaluated against the Current Score."*
- **Remediation:** Acquire any of E3 / E5 / EMS / Entra ID P1.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-LIC-003 — PIM Capability Available

- **Objective:** Detect whether PIM capability is owned.
- **Capabilities:** `entra.pim` (R)
- **Status behaviour:** `licensed_enabled` if owned; `not_licensed` / `available_in_higher_tier` if customer is on P1.
- **Finding example:** *"PIM requires Entra ID P2. Privileged role assignments default to permanent and are not time-bound. (Opportunity: P2 upgrade)."*
- **Remediation:** Upgrade to P2 or E5; recommend in Opportunity card.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-LIC-004 — Identity Protection Capability Available

- **Objective:** Detect whether risky-user / risky-sign-in signals are accessible.
- **Capabilities:** `entra.identity-protection.risky-users` (R), `entra.identity-protection.risky-signins` (R)
- **Status behaviour:** `licensed_enabled` if owned; `not_licensed` otherwise. **Used by POC as the `not_licensed` UI example** (`POC_V1_SCOPE.md` §5.6).
- **Finding example:** *"Identity Protection (risky-user / risky-sign-in signals) requires Entra ID P2. Excluded from Current Score; counted toward Target Posture."*
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-LIC-005 — Access Reviews & Entitlement Management Capability Available

- **Objective:** Detect access reviews / entitlement management capability.
- **Capabilities:** `entra.access-reviews` (R), `entra.entitlement-management` (R)
- **Status behaviour:** `licensed_enabled` if owned; `not_licensed` otherwise.
- **Finding example:** *"Access Reviews require Entra ID P2. Privileged role assignment review (ENTRA-PRIV-004) cannot enforce time-bound reviews."*
- **Tier:** POC 🟡 detection only · MVP ✅ · Full ✅

### 6.2 Conditional Access

#### ENTRA-CA-001 — Baseline Conditional Access Coverage

- **Objective:** Verify that at least one enabled CA policy enforces MFA against **All Users** (with explicit, narrow, audit-logged exclusions for breakglass).
- **Evidence:** `conditionalAccessPolicies.json`.
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:**
  - `licensed_disabled` + **fail** if no enabled CA targets All Users.
  - `licensed_misconfigured` + **partial** if a baseline policy exists but excludes broad groups.
  - `licensed_enabled` + **pass** if enabled + targets All Users + only breakglass excluded.
- **Finding example:** *"No enabled CA policy enforces MFA for all interactive sign-ins. Two report-only policies exist."*
- **Remediation:** Create a baseline CA policy: All cloud apps + All users (− breakglass) + Grant: require MFA.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-CA-002 — Privileged User MFA Enforcement

- **Objective:** Verify CA enforces strong authentication (MFA, preferably phishing-resistant) for users holding privileged directory roles.
- **Evidence:** `conditionalAccessPolicies.json`, `roleAssignments.json`, `directoryRoles.json`.
- **Capabilities:** `entra.conditional-access` (R); preferred: `entra.authentication-methods-policy`, `silverfort.privileged-mfa` (P).
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / `licensed_disabled` fail depending on coverage.
- **Finding example:** *"3 of 8 Global Administrators are not covered by a CA policy that requires MFA. Affected: ..."*
- **Remediation:** Add admins to a dedicated CA policy targeting `Directory Roles → Global Administrator` (and other privileged roles) with `Require authentication strength: Phishing-resistant MFA`.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-CA-003 — Legacy Authentication Blocked

- **Objective:** Verify CA blocks legacy authentication client app types (`exchangeActiveSync`, `other`).
- **Evidence:** `conditionalAccessPolicies.json`.
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:** `licensed_enabled` pass when a block policy exists and is enabled; `licensed_disabled` fail otherwise. **Used by POC as the `licensed_disabled` UI example** (`POC_V1_SCOPE.md` §5.6).
- **Finding example:** *"No CA policy blocks legacy authentication. Basic-auth IMAP/POP/SMTP sign-ins can bypass MFA."*
- **Remediation:** Enable a policy targeting `clientAppTypes = exchangeActiveSync, other` with `Grant: block`.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-CA-004 — Risk-Based Access Policy

- **Objective:** Verify CA enforces additional controls (MFA, password change, block) on high user-risk or sign-in-risk.
- **Capabilities:** `entra.conditional-access` (R) + `entra.identity-protection.risky-signins` (R) + `entra.identity-protection.risky-users` (R)
- **Status behaviour:** if Identity Protection not owned → `not_licensed` (no Current Score impact, fail vs Target).
- **Finding example:** *"Risk-based CA requires Entra ID P2. Customer is on P1; opportunity gap = +X points."*
- **Remediation:** Acquire P2; configure CA policies with `signInRiskLevels` / `userRiskLevels` conditions.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-CA-005 — Conditional Access Exclusion Review

- **Objective:** Surface every CA policy's exclusion list (users, groups, roles) for consultant review.
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:** `manual_review_required` operational flag; `license_status = licensed_enabled` with `result_status = unknown` until reviewed.
- **Finding example:** *"CA policy `Require MFA — All Users` excludes group `IT-Bypass` (member count: 14). Review."*
- **Remediation:** Move exclusions to a small, named, breakglass-only group with explicit audit logging.
- **Tier:** POC 🟡 detection only · MVP ✅ · Full ✅

#### ENTRA-CA-006 — Breakglass Account Exclusion Review

- **Objective:** Verify that CA exclusions for breakglass are limited, named, and small.
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:** `licensed_enabled` pass if exactly the configured breakglass set; `licensed_misconfigured` partial otherwise.
- **Finding example:** *"Breakglass exclusion group has 7 members; should be ≤ 2."*
- **Remediation:** Prune breakglass exclusion group; document and monitor.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-CA-007 — Device Compliance Requirement Review

- **Objective:** Surface CA policies that require compliant devices and report coverage gaps.
- **Evidence:** `conditionalAccessPolicies.json`, `devices.json`.
- **Capabilities:** `entra.conditional-access` (R); preferred: Intune (future module).
- **Status behaviour:** `licensed_enabled` pass / `licensed_disabled` fail; `unknown` if `devices.json` absent.
- **Finding example:** *"Device-compliance grant is required for high-privilege apps; 18% of devices are non-compliant."*
- **Remediation:** Address Intune compliance gaps; tighten CA targets.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

### 6.3 Authentication methods

#### ENTRA-AUTH-001 — MFA Registration Coverage

- **Objective:** Compute % of enabled users (excluding service-style accounts) with at least one strong MFA method registered.
- **Evidence:** `userAuthenticationMethods/*.json`.
- **Capabilities:** `entra.mfa.enforcement` (R)
- **Status behaviour:** `licensed_enabled` pass ≥ 95%; partial 80–95%; fail < 80%.
- **Finding example:** *"82% of users have an MFA method registered; 18% remain on password-only."*
- **Remediation:** Run an authentication-methods registration campaign.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-AUTH-002 — Phishing-Resistant MFA for Admins

- **Objective:** Verify privileged-role holders register and use a phishing-resistant method (FIDO2, WHfB, certificate).
- **Capabilities:** `entra.authentication-methods-policy` (R)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / `licensed_disabled` fail.
- **Finding example:** *"6 Global Administrators rely on Authenticator push only; no phishing-resistant method registered."*
- **Remediation:** Roll out FIDO2 security keys or WHfB; enforce via CA `authenticationStrength`.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-AUTH-003 — Weak Authentication Methods

- **Objective:** Detect enabled weak methods (SMS, voice) and report scope.
- **Capabilities:** `entra.authentication-methods-policy` (R)
- **Status behaviour:** `licensed_misconfigured` if weak methods enabled tenant-wide; `licensed_enabled` if disabled or scoped.
- **Finding example:** *"SMS is enabled for All Users. SS7 / SIM-swap risk."*
- **Remediation:** Disable SMS for admins; phase out tenant-wide.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-AUTH-004 — Authentication Method Policy Review

- **Objective:** Snapshot and surface the per-method policy (target groups, exclusions, registration campaign).
- **Capabilities:** `entra.authentication-methods-policy` (R)
- **Status behaviour:** `manual_review_required`.
- **Finding example:** *"4 methods are configured; review the target groups."*
- **Remediation:** Document and consolidate.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

### 6.4 Privileged roles & PIM

#### ENTRA-PRIV-001 — Global Administrator Count

- **Objective:** Detect excessive Global Administrator assignments.
- **Evidence:** `roleAssignments.json`, `directoryRoles.json`.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass if 2–5 GA holders; partial 6–8; fail > 8 or < 2.
- **Finding example:** *"11 users hold Global Administrator. Microsoft recommends 2–5."*
- **Remediation:** Move users to least-privilege roles (Privileged Role Administrator, User Administrator, etc.).
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-PRIV-002 — Permanent Privileged Role Assignments

- **Objective:** Surface permanent (non-PIM) assignments for high-privilege roles.
- **Capabilities:** (none required); preferred: `entra.pim` (P)
- **Status behaviour:** `licensed_enabled` pass if PIM-eligible only; `licensed_disabled` fail if permanent count > 0 and PIM is owned but unused; `not_licensed` if PIM not owned (still reportable — uses preferred capability path).
- **Finding example:** *"9 permanent privileged role assignments detected: GA × 3, PRA × 2, IA × 1, App Admin × 3."*
- **Remediation:** Convert to PIM eligible-only; require activation with MFA + approval.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-PRIV-003 — PIM Eligibility Coverage

- **Objective:** % of privileged role assignments that are PIM-eligible (vs permanent).
- **Capabilities:** `entra.pim` (R)
- **Status behaviour:** if P2 not owned → `not_licensed`; else `licensed_enabled` pass ≥ 90%; partial 50–90%; fail < 50%.
- **Finding example:** *"PIM coverage = 35%. 13 permanent privileged assignments remain."*
- **Remediation:** Migrate permanent to eligible; PIM activation rubric (MFA + approval + max 8h).
- **Tier:** POC 🟡 reporting only · MVP ✅ · Full ✅

#### ENTRA-PRIV-004 — Privileged Role Assignment Review

- **Objective:** Verify that privileged roles are subject to recurring access reviews (P2).
- **Capabilities:** `entra.access-reviews` (R)
- **Status behaviour:** if not owned → `not_licensed`; else `licensed_enabled` pass / fail by configured review state.
- **Finding example:** *"No access review is configured for Global Administrator."*
- **Remediation:** Create an access review for each privileged role at quarterly cadence.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

#### ENTRA-PRIV-005 — Privileged Role Activation Settings

- **Objective:** Inspect role-management-policy activation settings (require MFA, require approval, max duration).
- **Capabilities:** `entra.pim` (R)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / `licensed_disabled` fail.
- **Finding example:** *"GA activation does not require approval; max duration is 24h."*
- **Remediation:** Require MFA + approval, set max duration to 8h, require justification.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

### 6.5 Breakglass

> Breakglass accounts are the **emergency-access accounts** that allow recovery from a CA / MFA outage. See §11 for the full design rule set.

#### ENTRA-BG-001 — Breakglass Account Presence

- **Objective:** Verify the tenant has at least one (preferably two) named breakglass accounts.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass if ≥ 1 detected (consultant-confirmed); else fail.
- **Finding example:** *"No breakglass account identified. A tenant outage cannot be recovered without a cloud-only emergency-access account."*
- **Remediation:** Create 2 cloud-only GA accounts following Microsoft guidance.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-BG-002 — Breakglass Account Monitoring

- **Objective:** Verify alerting/monitoring on breakglass account sign-in (Defender / SIEM webhook).
- **Capabilities:** (none required); preferred: `defender-identity.lateral-movement-detection` (P)
- **Status behaviour:** `manual_review_required`; `licensed_enabled` after consultant confirms.
- **Finding example:** *"Breakglass sign-in monitoring not confirmed."*
- **Remediation:** Subscribe sign-in logs to SIEM; alert on breakglass usage.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-BG-003 — Breakglass Account Conditional Access Handling

- **Objective:** Verify breakglass exclusion strategy in CA (one of two patterns: exclude from blanket policies or use a dedicated location-based "stronger" policy).
- **Capabilities:** `entra.conditional-access` (R)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / `licensed_disabled` fail.
- **Finding example:** *"Breakglass accounts are in 3 separate CA exclusion lists — consolidate to one named group."*
- **Remediation:** Single, named, monitored exclusion group.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

### 6.6 Enterprise apps, app registrations, service principals

#### ENTRA-APP-001 — High-Privilege Application Permissions

- **Objective:** Surface service principals holding high-privilege application permissions (see §13 for the list).
- **Evidence:** `appRoleAssignments.json`, `servicePrincipals.json`.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass if 0 risky grants; `licensed_misconfigured` partial / fail otherwise.
- **Finding example:** *"Service principal `Contoso BI Connector` holds `Directory.ReadWrite.All` (application). Owners: none. Last sign-in: 41 days ago."*
- **Remediation:** Remove or reduce to least-privilege; assign owners.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-APP-002 — Long-Lived Client Secrets

- **Objective:** Detect client secrets with lifetime > 1 year or remaining validity > 1 year.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / `licensed_disabled` fail.
- **Finding example:** *"7 client secrets expire > 2 years from creation date; recommendation is ≤ 6 months + certificate-based auth."*
- **Remediation:** Rotate to short-lived secrets or certificates.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-APP-003 — Expired Credentials

- **Objective:** Detect expired secrets/certificates still on apps.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail by count.
- **Finding example:** *"3 apps carry expired credentials."*
- **Remediation:** Remove expired keys.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-APP-004 — Ownerless Applications

- **Objective:** Detect app registrations with no owners.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail.
- **Finding example:** *"12 enterprise apps have no owner."*
- **Remediation:** Assign owners or retire apps.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-APP-005 — Risky Consent Grants

- **Objective:** Detect user-consented delegated grants to non-verified publishers, with high-privilege scopes.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail.
- **Finding example:** *"4 users consented to `Mail.ReadWrite` and `offline_access` for an app with unverified publisher."*
- **Remediation:** Disable user-consent for risky permissions; enable admin-consent workflow.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

#### ENTRA-APP-006 — Unused Applications

- **Objective:** Detect service principals with no sign-ins in the last N days (default 90).
- **Evidence:** `auditLogs` last-activity (Graph `signInActivity` on SP).
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail; `unknown` if `AuditLog.Read.All` not granted.
- **Finding example:** *"23 service principals show no sign-in activity in 90 days."*
- **Remediation:** Retire unused SPs.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

### 6.7 Guests / external collaboration

#### ENTRA-GUEST-001 — Guest User Exposure

- **Objective:** Surface guest count, especially guests with privileged roles or sensitive app assignments.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / fail.
- **Finding example:** *"143 guests; 2 guests hold the `Application Administrator` role."*
- **Remediation:** Review; remove privileged guests; consider access reviews.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-GUEST-002 — Guest Invite Settings

- **Objective:** Inspect `authorizationPolicy` invite settings (who can invite, guest user role permissions).
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / fail.
- **Finding example:** *"Any member can invite guests; guest users have the same permissions as members."*
- **Remediation:** Restrict invite to specific role; reduce guest permissions.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

#### ENTRA-GUEST-003 — External Collaboration Restrictions

- **Objective:** Inspect domain allowlist/blocklist for B2B.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_enabled` pass / `licensed_misconfigured` partial / fail.
- **Finding example:** *"No B2B domain restrictions configured."*
- **Remediation:** Configure allowlist for known partner tenants.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

### 6.8 Hybrid identity

#### ENTRA-HYBRID-001 — Synced Privileged Accounts

- **Objective:** Flag identities that hold privileged Entra roles **and** are synced from on-premises AD (`onPremisesImmutableId` present).
- **Evidence:** `roleAssignments.json`, `users.json` (onPremisesImmutableId), AD evidence (cross-module).
- **Capabilities:** (none required); preferred: `defender-identity.lateral-movement-detection` (P)
- **Status behaviour:** `licensed_enabled` pass if 0 synced privileged accounts; `licensed_disabled` fail otherwise (this is a recognized anti-pattern).
- **Finding example:** *"2 identities hold Global Administrator and are synced from AD: `svc-admin@contoso.com`, `helpdesk-admin@contoso.com`."*
- **Remediation:** Move privileged identities to cloud-only accounts; isolate from on-prem sync.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-HYBRID-002 — Entra Connect Server Tier 0 Status

- **Objective:** Identify the on-prem server running Entra Connect / Cloud Sync and verify it is treated as Tier 0 (per Microsoft Enterprise Access Model).
- **Evidence:** `directorySync.json` (synthetic indicator), AD module data (host SAM accounts), consultant input.
- **Capabilities:** (none required)
- **Status behaviour:** `manual_review_required`; on confirmation: `licensed_enabled` pass / `licensed_disabled` fail.
- **Finding example:** *"Entra Connect server `AAD-SYNC01` is in OU `Servers/Workstations`, not in a Tier 0 OU. The workstation that runs sync must be treated as Tier 0."*
- **Remediation:** Move to a Tier 0 OU; restrict logon to Tier 0 admins; harden per Microsoft guidance.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-HYBRID-003 — Hybrid Admin Path Candidate

- **Objective:** Surface synced accounts that are members of on-prem privileged groups (Domain Admins, Enterprise Admins) and hold Entra privileged roles.
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail.
- **Finding example:** *"`contoso\admin01` is in Domain Admins and Entra Global Administrator. Compromise of on-prem grants tenant-wide cloud privilege."*
- **Remediation:** Separate on-prem privileged identities from cloud privileged identities.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-HYBRID-004 — On-Prem Privileged Identity With Cloud Role

- **Objective:** For each on-prem privileged identity (AD module data), report whether it has a cloud privileged role (Entra side).
- **Capabilities:** (none required)
- **Status behaviour:** `licensed_misconfigured` partial / fail; `unknown` if AD evidence missing.
- **Finding example:** *"5 of 12 Domain Admin accounts also hold Entra cloud-privileged roles."*
- **Remediation:** Move cloud privilege off synced accounts (cloud-only equivalents).
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-HYBRID-005 — BloodHound Path to Cloud-Privileged Identity

- **Objective:** For each BloodHound critical path, check whether the target on-prem account is synced to a cloud-privileged role; emit a correlation finding (driven by core orchestrator).
- **Evidence:** BloodHound module path data + Entra role assignments.
- **Capabilities:** (none required)
- **Status behaviour:** correlated `Finding` (owner `correlation` per `MODULE_ARCHITECTURE.md` §11). Module-side it reports `licensed_enabled` on Entra evaluator.
- **Finding example:** (full example in §7)
- **Remediation:** Combination of AD privilege reduction + cloud privilege relocation + Silverfort coverage (where owned).
- **Tier:** POC ✅ (headline demo finding) · MVP ✅ · Full ✅

### 6.9 Silverfort cross-module

#### ENTRA-SF-001 — Entra Privileged User Silverfort Coverage

- **Objective:** For each identity holding an Entra privileged role, verify Silverfort coverage (policy-engine).
- **Evidence:** Entra `roleAssignments.json` + Silverfort module data.
- **Capabilities:** preferred: `silverfort.policy-engine` (P), `silverfort.privileged-mfa` (P)
- **Status behaviour:** `licensed_enabled` pass (if SF owned & covered); `licensed_disabled` fail (if SF owned & not covered); `not_licensed` if SF not owned (no Current Score penalty).
- **Finding example:** *"3 of 7 Entra Application Administrators are not covered by any Silverfort policy."*
- **Remediation:** Add to a Silverfort policy enforcing MFA on Entra cloud-app access patterns.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

#### ENTRA-SF-002 — Hybrid Admin Silverfort Coverage

- **Objective:** For each hybrid admin (ENTRA-HYBRID-003 result), verify Silverfort coverage on the on-prem AD account.
- **Capabilities:** preferred: `silverfort.policy-engine` (P)
- **Status behaviour:** as above.
- **Finding example:** *"Hybrid admin `contoso\admin01` has no Silverfort policy coverage; on-prem compromise leads to cloud privilege."*
- **Remediation:** Add to AD privileged policy.
- **Tier:** POC ✅ · MVP ✅ · Full ✅

#### ENTRA-SF-003 — Breakglass Silverfort Handling Decision

- **Objective:** Document the deliberate decision: breakglass accounts are excluded from Silverfort policies on purpose (so SF outage does not compound CA outage). Surface for consultant review only.
- **Capabilities:** preferred: `silverfort.policy-engine` (P)
- **Status behaviour:** `manual_review_required`.
- **Finding example:** *"Breakglass account `bg-01` is not in any Silverfort policy — confirm this is intentional."*
- **Remediation:** Document the decision; ensure monitoring.
- **Tier:** POC 🟡 · MVP ✅ · Full ✅

### 6.10 Risky users (license-gated)

#### ENTRA-IP-001 — Risky Users Visibility *(deferred to MVP)*

- **Objective:** Surface current risky-user state.
- **Capabilities:** `entra.identity-protection.risky-users` (R)
- **Status behaviour:** `not_licensed` if P2 not owned.
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

#### ENTRA-IP-002 — Risk Detections Trend *(deferred to MVP)*

- **Capabilities:** `entra.identity-protection.risky-signins` (R)
- **Tier:** POC ⬜ · MVP ✅ · Full ✅

### 6.11 POC V1 control selection (≥ 6 per `POC_V1_SCOPE.md` §5.6)

POC implements **at least the following 8 controls**, which satisfy the explicit POC V1 demands (License & Capability Detection, CA baseline, Privileged user MFA, Legacy auth blocked, Hybrid privileged identity overlap, Long-lived client secrets) **plus** one `licensed_disabled` and one `not_licensed` demonstration:

| Control | Why in POC | Demonstrates |
|---|---|---|
| `ENTRA-LIC-001` License and Capability Detection | Mandatory for license-aware UI | License catalog presence |
| `ENTRA-LIC-004` Identity Protection Capability Available | **`not_licensed` UI example** (per POC V1 §5.6) | Customer is on E3+P1; IP requires P2 |
| `ENTRA-CA-001` Baseline CA Coverage | Mandatory by POC §5.6 | `licensed_enabled` pass demo |
| `ENTRA-CA-002` Privileged User MFA Enforcement | Mandatory by POC §5.6 | Admin MFA gap demo |
| `ENTRA-CA-003` Legacy Authentication Blocked | **`licensed_disabled` UI example** (per POC V1 §5.6) | Capability owned but not configured |
| `ENTRA-HYBRID-001` Synced Privileged Accounts | Mandatory by POC §5.6 (hybrid overlap) | Cross-module correlation seed |
| `ENTRA-HYBRID-004` On-Prem Privileged Identity With Cloud Role | Supports correlation headline finding | Cross-module correlation seed |
| `ENTRA-APP-002` Long-Lived Client Secrets | Mandatory by POC §5.6 | Non-license-gated control |

These map to UI cards as follows (per §21): Licensing & Capabilities → LIC-001/004; Conditional Access → CA-001/002/003; Privileged Roles → HYBRID-001 (shared with Hybrid card); Authentication Methods → AUTH-001 (POC stretch); Apps & Service Principals → APP-002; Hybrid Identity → HYBRID-001/004.

---

## 7. Findings — example payloads

The finding shape is `MODULE_ARCHITECTURE.md` §10 verbatim. Module-specific fields go in `payload`.

### 7.1 `ENTRA-CA-003` — Legacy Authentication Blocked (POC `licensed_disabled` example)

```json
{
  "id": "<uuid>",
  "assessment_run_id": "<uuid>",
  "title": "Legacy authentication is not blocked",
  "category": "entra.ca",
  "module_id": "entra",
  "severity": "HIGH",
  "risk_score": 73,
  "license_status": "licensed_disabled",
  "summary_internal": "No enabled Conditional Access policy blocks legacy authentication client app types (`exchangeActiveSync`, `other`). Basic-auth IMAP, POP, SMTP, and ActiveSync sign-ins can therefore bypass MFA. The capability is owned (Entra ID P1 included in Microsoft 365 E3), it is simply not configured.",
  "summary_customer": "Your tenant licensing includes the controls needed to block legacy authentication, but no such policy is currently active. This is a low-cost configuration change with a high-impact security gain.",
  "technical_detail": "Inspected 4 enabled CA policies; none target `conditions.clientAppTypes = [exchangeActiveSync, other]` with `grantControls.builtInControls = [block]`. Two report-only policies exist (no enforcement). 3 service accounts and 2 user accounts have shown basic-auth sign-ins in the last 30 days (auditLogs).",
  "remediation": "Create a Conditional Access policy:\n- Assignments → Users: All users (− `bg-emergency-access` group)\n- Conditions → Client apps: Exchange ActiveSync clients, Other clients\n- Grant: Block access\n- State: On",
  "validation_method": "Re-collect Entra evidence; confirm a new enabled CA policy matches the rubric.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "conditionalAccessPolicies.json"}
  ],
  "identity_refs": [],
  "correlation_refs": [],
  "payload": {
    "ca_policy_count": 4,
    "blocking_policy_found": false,
    "report_only_policies": ["pol-...", "pol-..."],
    "basic_auth_signins_30d": 7
  }
}
```

### 7.2 `ENTRA-PRIV-002` — Permanent Privileged Role Assignments

```json
{
  "id": "<uuid>",
  "assessment_run_id": "<uuid>",
  "title": "Privileged roles are assigned permanently",
  "category": "entra.privileged",
  "module_id": "entra",
  "severity": "HIGH",
  "risk_score": 68,
  "license_status": "licensed_disabled",
  "summary_internal": "9 privileged role assignments are permanent (non-PIM). PIM is owned (Entra ID P2 included in Microsoft 365 E5) but unused for these roles. Permanent assignments grant 24/7 standing privilege, increasing the blast radius of a compromised admin account.",
  "summary_customer": "Privileged administrators currently have continuous, time-unbound access. Activating just-in-time elevation (already included in your licensing) would reduce the window of opportunity for an attacker.",
  "technical_detail": "Roles affected: Global Administrator (3), Privileged Role Administrator (2), Intune Administrator (1), Application Administrator (3). Identities: ... (see identity_refs).",
  "remediation": "For each affected assignment, convert to PIM eligible-only with the following rubric:\n- Activation requires MFA\n- Activation requires approval (Global Administrator only)\n- Max activation duration: 8 hours\n- Justification required",
  "validation_method": "Re-collect Entra evidence; confirm no permanent assignments for the listed roles, and that role-management-policy reflects the activation rubric.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "roleAssignments.json"},
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "directoryRoles.json"}
  ],
  "identity_refs": ["<id-1>", "<id-2>", "<id-3>", "<id-4>", "<id-5>", "<id-6>", "<id-7>", "<id-8>", "<id-9>"],
  "correlation_refs": [
    {"kind": "control", "id": "ENTRA-LIC-003", "relation": "depends_on_capability"},
    {"kind": "control", "id": "ENTRA-PRIV-005", "relation": "related"}
  ],
  "payload": {
    "permanent_count": 9,
    "eligible_count": 4,
    "active_count": 1,
    "roles": [
      {"role": "Global Administrator", "permanent": 3},
      {"role": "Privileged Role Administrator", "permanent": 2},
      {"role": "Intune Administrator", "permanent": 1},
      {"role": "Application Administrator", "permanent": 3}
    ]
  }
}
```

### 7.3 `ENTRA-HYBRID-004` — On-Prem Privileged Identity With Cloud Role (correlation seed)

```json
{
  "id": "<uuid>",
  "assessment_run_id": "<uuid>",
  "title": "On-premises privileged identity also holds Entra cloud-privileged role",
  "category": "entra.hybrid",
  "module_id": "entra",
  "severity": "CRITICAL",
  "risk_score": 88,
  "license_status": "licensed_disabled",
  "summary_internal": "Identity `contoso\\admin01` (UPN: `admin01@contoso.com`) is a member of on-prem `Domain Admins` (AD evidence) **and** holds the Entra `Global Administrator` role. Compromise of the on-prem account therefore grants tenant-wide cloud privilege without further lateral movement.",
  "summary_customer": "One administrator account currently has the highest privilege on both your on-premises Active Directory and your Microsoft 365 cloud tenant. Separating these privileges into dedicated accounts is a high-impact, low-cost change recommended by Microsoft.",
  "technical_detail": "On-prem: AD module `AD-PRIV-005` flagged member in `Domain Admins`, no SmartCard required, no Silverfort policy coverage. Cloud: permanent `Global Administrator` assignment, no PIM, CA exclusion via legacy `IT-Bypass` group.",
  "remediation": "1. Create a cloud-only Entra account `admin01-cloud@contoso.onmicrosoft.com`; assign GA there (PIM-eligible).\n2. Remove the GA assignment from `admin01@contoso.com`.\n3. Document the separation in the tenant runbook.\n4. (Compensating) Add `contoso\\admin01` to a Silverfort policy enforcing MFA on privileged auth.",
  "validation_method": "Re-collect AD + Entra evidence; confirm no identity is both Domain Admin and Entra GA.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "roleAssignments.json"},
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "users.json"},
    {"artifact_id": "<uuid>", "evidence_id": "<uuid>", "path": "<ad-toolkit-zip>/privileged_groups.json"}
  ],
  "identity_refs": ["<id-of-admin01>"],
  "correlation_refs": [
    {"kind": "finding", "module": "ad", "id": "<AD-PRIV-005 finding id>", "relation": "shared_identity"},
    {"kind": "finding", "module": "bloodhound", "id": "<BH path finding id>", "relation": "path_terminates_at_identity"},
    {"kind": "finding", "module": "silverfort", "id": "<SF-POL-002 finding id>", "relation": "coverage_gap"},
    {"kind": "control", "id": "ENTRA-SF-002", "relation": "related_control"}
  ],
  "payload": {
    "on_prem_groups": ["Domain Admins", "Enterprise Admins"],
    "cloud_roles": ["Global Administrator"],
    "sync_state": "hybrid",
    "ca_excluded": true,
    "ca_excluded_via_group": "IT-Bypass",
    "silverfort_covered": false
  }
}
```

This finding is the **headline correlation candidate** for the management-review demo (cf. `MODULE_ARCHITECTURE.md` §11.3 `CORR-BH-ENTRA-001`).

---

## 8. Conditional Access — design notes

### 8.1 Parsing

CA policy JSON is parsed into `EntraCAPolicy` rows with three structured columns: `conditions`, `grant_controls`, `session_controls`, plus a denormalized `exclusions` column for fast lookup.

Parsed structures:

- **state**: `enabled`, `disabled`, `enabledForReportingButNotEnforced` (report-only).
- **conditions.users**: `includeUsers`, `excludeUsers`, `includeGroups`, `excludeGroups`, `includeRoles`, `excludeRoles`, `includeGuestsOrExternalUsers`.
- **conditions.applications**: `includeApplications`, `excludeApplications`, `includeUserActions`, `includeAuthenticationContextClassReferences`.
- **conditions.clientAppTypes**: `[all, browser, mobileAppsAndDesktopClients, exchangeActiveSync, other]`.
- **conditions.signInRiskLevels** / **userRiskLevels**: `[low, medium, high]`.
- **conditions.platforms**, **locations**, **devices**.
- **grantControls.builtInControls**: `[mfa, compliantDevice, domainJoinedDevice, approvedApplication, compliantApplication, passwordChange, block]`.
- **grantControls.authenticationStrength**: ref to authentication strength policy.
- **grantControls.operator**: `AND` / `OR`.
- **sessionControls.signInFrequency**, **persistentBrowser**.

### 8.2 Evaluator rubrics

Controls in §6.2 evaluate by intersecting **what the policy targets** with **what the rubric requires**.

Example (ENTRA-CA-001 baseline):

```
policy P satisfies baseline iff
  P.state == enabled
  AND (All Users ∈ P.conditions.users.includeUsers OR All Users ∈ P.conditions.users.includeGroups)
  AND P.grantControls.builtInControls contains "mfa"
  AND every excluded principal is justified (consultant or breakglass group rule)
```

### 8.3 Breakglass handling (ENTRA-BG-003)

A CA exclusion list containing the breakglass group is **expected**. The breakglass group is identified by:

- A `Identity.is_breakglass = True` membership (set via convention or consultant tag).
- A `Group` whose name matches a configurable pattern (default: `^bg-` or `^break-?glass`).

When the CA evaluator sees an exclusion targeting the breakglass group, it does **not** penalize the policy. When it sees an exclusion targeting a non-breakglass group, it surfaces it for review (ENTRA-CA-005 / ENTRA-CA-006).

### 8.4 Report-only policies

Report-only policies (`enabledForReportingButNotEnforced`) **do not count** toward `licensed_enabled` for any rubric. They are surfaced for review and counted toward "operational hygiene".

---

## 9. MFA / Authentication methods — design notes

### 9.1 Method policy parse

`authenticationMethodPolicy.json` is parsed into `EntraAuthnMethodPolicy` rows, one per method. For each method:

- `state` (`enabled` / `disabled`).
- Target groups (`includeTargets`, `excludeTargets`).
- Per-method config flags (e.g., `microsoftAuthenticator.featureSettings.numberMatching`).
- Derived flags: `is_phishing_resistant` (true for `fido2`, `windowsHelloForBusiness`, `x509Certificate`), `is_weak` (true for `sms`, `voice`).

### 9.2 Per-user authentication methods

`userAuthenticationMethods/*.json` is collected per user (in MVP: only for users in privileged roles + a sampled subset; in POC: per the synthetic fixture).

A user is **MFA-registered** if at least one method other than `password` is present. They are **phishing-resistant** if at least one method is in the phishing-resistant set.

### 9.3 Weak-method detection

A method is **weak** if it is enabled for any privileged user. ENTRA-AUTH-003 fails if SMS is enabled for `All Users` or for any group containing a privileged identity.

### 9.4 Phishing-resistant detection

ENTRA-AUTH-002 fails if any privileged identity has **no** phishing-resistant method registered. The detection is per-identity; the result lists affected admins.

---

## 10. Roles / PIM — design notes

### 10.1 Permanent vs eligible vs active

- **Permanent**: classic role assignment via `roleAssignments` with no expiry; treated as `assignment_type = permanent`.
- **Eligible**: PIM eligibility schedule (`roleEligibilitySchedules`) — a principal can activate.
- **Active**: PIM active schedule (`roleAssignmentSchedules`) — currently activated, time-bound.

A single identity can have multiple of these for the same role (uncommon but possible). The evaluator treats them as a tuple.

### 10.2 Activation settings (ENTRA-PRIV-005)

`roleManagementPolicies` carry the activation rubric per role:

- `requireMfaOnActivation` (bool).
- `requireApprovalOnActivation` (bool) and approvers.
- `maximumDuration` (hours).
- `requireJustification` (bool).
- `requireTicket` (bool, ITSM integration).

ENTRA-PRIV-005 fails if any high-privilege role's activation rubric is weaker than the recommended baseline (MFA on, approval on for GA, max 8h, justification required).

### 10.3 Privileged role list

The POC treats the following as **high-privilege**:

- Global Administrator
- Privileged Role Administrator
- Privileged Authentication Administrator
- Conditional Access Administrator
- Application Administrator
- Cloud Application Administrator
- Authentication Administrator
- Security Administrator
- Exchange Administrator
- SharePoint Administrator
- User Administrator (with caveat — can reset MFA)
- Intune Administrator
- Hybrid Identity Administrator (especially: can manage AD Connect)

The list is data-driven (in `entra` module config) so it can be extended without code changes.

---

## 11. Breakglass — definition and detection

### 11.1 Definition

Breakglass accounts are **cloud-only, named, monitored, Global Administrator emergency-access accounts** used **only** to recover from a CA / MFA outage. Microsoft guidance: at least two such accounts, with FIDO2 keys stored in a tamper-evident container.

### 11.2 Detection

Breakglass status is set on `Identity.is_breakglass` via:

1. **Convention**: UPN or display name matches a configurable pattern (default: `^bg-`, `^break-?glass`, `emergency`).
2. **Consultant tag**: the consultant marks an identity as breakglass in the engagement setup screen.

The convention rule is **suggestive, not authoritative** — the consultant must confirm. The platform logs the basis (`convention` vs `consultant_confirmed`) in the audit log.

### 11.3 Special handling rules

- ENTRA-BG-001 expects ≥ 1 breakglass detected (preferably 2).
- ENTRA-CA-006 expects breakglass exclusions to be **small, named, and consolidated** in a single dedicated group.
- ENTRA-BG-003 expects CA exclusion to follow one of two patterns:
  - **Pattern A** (recommended): a single named breakglass group is excluded from *blanket* CA policies and is *not* included in any other CA policy.
  - **Pattern B** (alternative): the breakglass group is in a CA policy with location-bound + FIDO2-only authentication strength (no MFA outage exposure).
- ENTRA-SF-003: breakglass accounts are **deliberately excluded** from Silverfort policies to avoid compounding outages — the platform flags this for consultant review rather than as a failure.

---

## 12. Enterprise apps / Service principals — what we parse

### 12.1 App vs Service Principal distinction

- **Application** (`/applications`) — the registration object owned by a tenant; declares permissions, redirect URIs, secrets/certs.
- **ServicePrincipal** (`/servicePrincipals`) — the instance of an application **in a tenant**. Every consented or assigned app in the tenant has an SP, including Microsoft built-in apps (first-party).

A single `Application` in tenant A produces one `ServicePrincipal` per tenant that consents to it (multi-tenant case). For POC, we treat:

- The tenant's **own** `Application` registrations as `EntraApp` with `is_first_party = False`.
- Service principals **without** a tenant-local Application (consented third-party apps) as `EntraApp` with `is_first_party = False`, app_id pointing to the external app.
- **First-party Microsoft apps** are filtered out of finding lists by default (they would dominate the noise floor).

### 12.2 What we parse

For each SP / Application:

- App id, object id, display name, publisher information.
- `signInAudience` — single-tenant, multi-tenant, personal accounts.
- Owners (`/applications/{id}/owners` + `/servicePrincipals/{id}/owners`) — joined into `EntraApp.owners`.
- Credentials (secrets + certificates).
- Required resource access (declared permissions).
- App role assignments (granted application permissions).
- OAuth2 permission grants (granted delegated permissions).
- Last sign-in (from `signInActivity` on SP).
- Tags (e.g., `WindowsAzureActiveDirectoryIntegratedApp`).

---

## 13. App permissions — high-privilege list

### 13.1 Delegated vs application

- **Delegated permissions (`Scope`)**: the app acts as a user; effective permission is the intersection of user's permission and the consented scope.
- **Application permissions (`Role`)**: the app acts as itself (no user). Effective permission is the consented permission alone — far more dangerous.

A single Graph permission name (e.g., `Directory.ReadWrite.All`) exists as both delegated and application — the application form is the one to scrutinize.

### 13.2 High-privilege application permissions (POC list)

The following application permissions are flagged as **high-privilege** by `EntraAppPermission.is_high_privilege` and drive `ENTRA-APP-001`:

| Permission | Why it is high-privilege |
|---|---|
| `Directory.ReadWrite.All` | Modify users, groups, roles |
| `Application.ReadWrite.All` | Create / modify app registrations & secrets (privilege escalation pivot) |
| `Application.ReadWrite.OwnedBy` | Limited but still allows lifecycle on owned apps |
| `RoleManagement.ReadWrite.Directory` | Grant any directory role to any principal |
| `AppRoleAssignment.ReadWrite.All` | Grant application permissions to other principals |
| `Group.ReadWrite.All` | Modify any group, including role-assignable ones |
| `User.ReadWrite.All` | Reset passwords, modify any user |
| `User.ManageIdentities.All` | Manage federated identity issuers per user |
| `Policy.ReadWrite.ConditionalAccess` | Modify CA policies |
| `Policy.ReadWrite.AuthenticationMethod` | Modify authentication method policy |
| `Mail.ReadWrite` (application) | Read/write any mailbox |
| `Mail.Send` (application) | Send as any user |
| `Files.ReadWrite.All` | Modify any file |
| `Sites.FullControl.All` | Full SharePoint control |
| `Domain.ReadWrite.All` | Add/remove tenant domains |
| `PrivilegedAccess.ReadWrite.AzureAD` | Modify PIM assignments |
| `IdentityProvider.ReadWrite.All` | Modify federation |
| `TeamSettings.ReadWrite.All`, `TeamMember.ReadWrite.All` | Teams data exfil |

The list is data-driven (`modules/entra/data/high_privilege_permissions.json`) so it can be extended without code changes.

### 13.3 Risky consent grants (ENTRA-APP-005)

A delegated grant is **risky** when:

- The publisher is **not verified** (`publisherDomainVerified = False`).
- The scopes include high-privilege ones (subset of the above for delegated case: `Mail.ReadWrite`, `Files.ReadWrite.All`, `offline_access` + sensitive scopes).
- The grant is **user-consented** (not admin-consented) — visible via `OAuth2PermissionGrant.consentType = Principal`.

---

## 14. Guests — design notes

### 14.1 Guest classification

A user is a guest when `userType = Guest` or `creationType = Invitation`. The `EntraGuest` table denormalizes guest properties for fast filtering.

### 14.2 Exposure (ENTRA-GUEST-001)

A guest is **high-exposure** if:

- They hold an Entra privileged role.
- They are assigned to an app with high-privilege application permissions.
- They are a member of a group that is `isAssignableToRole = True`.

### 14.3 Invite settings (ENTRA-GUEST-002)

Parsed from `authorizationPolicy.allowInvitesFrom` and `defaultUserRolePermissions.allowedToInviteGuests`:

- `everyone` → fail (any member can invite).
- `adminsAndGuestInviters` → partial.
- `admins` → pass.

### 14.4 External collaboration restrictions (ENTRA-GUEST-003)

Parsed from `policies/crossTenantAccessPolicy` and `B2BManagementPolicy`. POC reports presence only; MVP evaluates.

---

## 15. Devices / compliance — context only

POC **does not** build an Intune module. Device data is collected solely as **input to ENTRA-CA-007**:

- `/devices` provides compliance state per device (`isCompliant`).
- The control evaluator uses this to report aggregate non-compliance among devices targeted by CA grant `compliantDevice`.

Full device posture analysis (e.g., Defender for Endpoint, configuration profiles, baseline drift) is **deferred to a future Intune module** (`PRODUCT_DESIGN.md` §13).

---

## 16. Risky users / sign-ins — license-gated

`riskyUsers.json` and `riskDetections.json` are parsed into `EntraRiskyUser` only when:

- `entra.identity-protection.risky-users` is owned (P2 in any included form), and
- The corresponding Graph permissions were granted (MVP).

When not owned: the file is absent (consultant unable to export it) → license resolver returns `not_licensed`; relevant controls (ENTRA-IP-*, ENTRA-CA-004) exit with `not_licensed` (no Current Score impact, fail vs Target).

At POC: even if a synthetic `riskyUsers.json` is uploaded, the controls reference `entra.identity-protection.*` and respect the consultant-confirmed SKU set. If P2 is not in the owned set, the controls are `not_licensed` regardless of file presence — the resolver is **authoritative over evidence**.

---

## 17. Hybrid identity — design notes

### 17.1 Entra Connect server

A tenant is hybrid when `Organization.onPremisesSyncEnabled = True`. We identify the Entra Connect / Cloud Sync server by:

- Looking for synthetic `Sync_<server>_<hash>@<tenant>` service-account UPNs (Entra Connect convention).
- Cross-referencing AD module data for a host matching the connector account's `lastLogonHostName` (where AD evidence is present).
- Consultant-provided override (engagement setup field "Entra Connect server hostname").

The workstation that runs sync **must be treated as Tier 0** because compromise of the connector account allows password-hash synchronization manipulation and arbitrary cloud account modification. ENTRA-HYBRID-002 surfaces this regardless of whether the AD module flags it.

### 17.2 On-prem-to-cloud privilege overlap

For every `Identity` with both:

- `is_privileged = True` (set by AD evidence — Domain Admin, Enterprise Admin, etc.), and
- a cloud-privileged role assignment (set by Entra evidence — GA, PRA, etc.),

ENTRA-HYBRID-003 / ENTRA-HYBRID-004 emit findings. The on-prem privilege list comes from the AD module's normalized data (read-only via `view.ad` in the correlation orchestrator); no module-to-module import (per `MODULE_ARCHITECTURE.md` §11).

### 17.3 ENTRA-HYBRID-005 — BloodHound path overlap

For each BloodHound path whose target `Identity` is privileged in Entra (cloud-privileged role) and whose source `Identity` is *not* Tier 0, the correlation orchestrator emits `CORR-BH-ENTRA-001`. The Entra-side evaluator returns `licensed_enabled` (the control is data-driven, not capability-gated); preferred capability `defender-identity.lateral-movement-detection` adds a remediation note when missing.

---

## 18. Entra ↔ AD

### 18.1 Identity overlap

The deterministic match keys are (per `MODULE_ARCHITECTURE.md` §8):

- AD `objectGUID` ↔ Entra `users.onPremisesImmutableId` (base64 of the same GUID).
- AD `sAMAccountName` ↔ Entra `users.onPremisesSamAccountName` (secondary).
- AD `userPrincipalName` (when set) ↔ Entra `users.userPrincipalName`.

Where ambiguity exists (e.g., UPN-only matches across multiple AD forests), the linker raises an `IdentityAmbiguity` row — **no silent merge**.

### 18.2 Cross-controls AD-ENTRA-*

These cross-module controls belong to the **AD module** by convention (the AD module is the on-prem authority); the Entra module *links* to them via `correlation_refs`. They are documented in `AD_MODULE_DESIGN.md`:

- `AD-ENTRA-001` — Domain Admin synced to cloud (links to ENTRA-HYBRID-001/004).
- `AD-ENTRA-002` — AD account `kerberoastable` AND holds Entra role (privilege chain).

The Entra module evaluator does not duplicate these; it produces its own `ENTRA-HYBRID-*` findings that share `correlation_refs.identity` with the AD-side findings.

---

## 19. Entra ↔ BloodHound

### 19.1 ENTRA-HYBRID-005

The cross-module finding is owned by the **core orchestrator** (per `MODULE_ARCHITECTURE.md` §11) but seeded by Entra-side data. The Entra module declares a `correlation_contributor` that exposes:

- The set of identities holding cloud-privileged roles (with role names).
- The Identity Connect server (where detected).

The BloodHound module declares the path data. The orchestrator matches: *for each BH critical path, is the target identity in the Entra-privileged set?* If yes → emit `CORR-BH-ENTRA-001`.

`CORR-BH-ENTRA-001` is the **headline demo finding** (`MODULE_ARCHITECTURE.md` §11.3, `POC_V1_SCOPE.md` §4 step 8).

### 19.2 Cross-referencing in the Entra finding

When `CORR-BH-ENTRA-001` is emitted, the Entra-side finding `ENTRA-HYBRID-004` for the same identity carries a `correlation_refs` entry pointing to the BH path finding (and vice versa). The UI surfaces this as a chip on both finding drawers (per `UI_DESIGN_DIRECTION.md` §13).

---

## 20. Entra ↔ Silverfort

### 20.1 ENTRA-SF-001 / ENTRA-SF-002

The Silverfort module declares which identities are covered by which Silverfort policies (its `view.silverfort.covered_identity_ids()`). The Entra module's correlation contributor exposes the Entra-privileged identity set.

`ENTRA-SF-001` (cloud-privileged) and `ENTRA-SF-002` (hybrid-admin synced) each test the intersection. If Silverfort is **not** owned at all, both controls resolve to `not_licensed` and contribute to Target Score only — never penalizing Current.

### 20.2 ENTRA-SF-003 (breakglass)

Special-case control — deliberate exclusion. Always `manual_review_required` until the consultant confirms intent. See §11.3 Pattern A/B.

---

## 21. Dashboard — module page composition

The Entra module page uses the **shared `M` template** from `UI_DESIGN_DIRECTION.md` §4.3. No new components are introduced.

### 21.1 Composition

- **`PageHeader`**: "Microsoft Entra ID" · supporting sentence ("Identity, access, and licensing posture for `<tenant.displayName>`") · secondary actions: Upload evidence, Re-evaluate.
- **Row 1 — 6 `StatusCard`** (per `UI_DESIGN_DIRECTION.md` §15):
  1. **Licensing & Capabilities** — driven by `ENTRA-LIC-001..005`. Shows owned SKUs + capability summary. Always visible. License-aware badge: variant based on coverage.
  2. **Conditional Access** — driven by `ENTRA-CA-001..007`. Headline metric: % of identities covered by an MFA-enforcing CA. License-aware badge: `licensed_enabled` or `licensed_disabled`.
  3. **Privileged Roles** — driven by `ENTRA-PRIV-001..005` + PIM detection. Headline: GA count + permanent-vs-eligible ratio. **License-aware badge** (this is one of the two cards required to show a license-aware badge per `UI_DESIGN_DIRECTION.md` §15): `licensed_enabled` (P2 owned) or `not_licensed` (PIM not owned) with tooltip.
  4. **Authentication Methods** — driven by `ENTRA-AUTH-001..004`. Headline: % MFA registered + weak methods enabled.
  5. **Apps & Service Principals** — driven by `ENTRA-APP-001..006`. Headline: high-privilege SP count + ownerless count.
  6. **Hybrid Identity** — driven by `ENTRA-HYBRID-001..005`. Headline: hybrid admin count + Entra Connect Tier 0 status. **License-aware badge** for the optional `defender-identity` preferred capability.
- **Row 2** — `RingChart` (control coverage: passing / failing / not-applicable / not-licensed / unknown) + `PriorityList` (top Entra findings).
- **Row 3** — `PriorityList` of CA exclusion review items (ENTRA-CA-005) when count > 0.
- **Right rail** (optional `ActionPanel`): "Confirm owned SKUs" form (links to engagement setup).

### 21.2 License-aware UI placement

Per `UI_DESIGN_DIRECTION.md` §15, the Entra page shows **at least two** `StatusCard` with a license-aware badge:

- **Licensing & Capabilities** card — always shows a license-aware badge (it *is* the license summary).
- **Privileged Roles** card — `licensed_enabled` or `not_licensed` depending on PIM ownership.

The **`POC_V1_SCOPE.md` §5.6** demand for **one `licensed_disabled` + one `not_licensed`** is satisfied within these cards:

- `licensed_disabled` appears on the **Conditional Access** card via `ENTRA-CA-003 Legacy authentication not blocked`.
- `not_licensed` appears on the **Privileged Roles** card (when PIM not owned, e.g., the Contoso E3+P1 scenario) and/or on the **Licensing & Capabilities** card via `ENTRA-LIC-004 Identity Protection`.

A `License` info-icon next to each `not_licensed` badge opens the tooltip described in `UI_DESIGN_DIRECTION.md` §12 — explicit, non-sales language.

### 21.3 Finding drawer

Standard `Finding` drawer (per `UI_DESIGN_DIRECTION.md` §13 pattern, reused). Entra-specific touches inside the drawer body:

- For ENTRA-CA-* findings: a small policy summary block (state, conditions, controls, exclusions) — no new component, uses `Card` with table-of-key-values.
- For ENTRA-APP-* findings: a credentials block (kind, expiry, age) and a permissions block (delegated/application + value).
- For ENTRA-HYBRID-* findings: an identity-overlap block with chips (AD, BH, Silverfort, Entra).

---

## 22. Reporting

### 22.1 Internal Detailed report

- Module section "Microsoft Entra ID" rendered from `modules/entra/reports/internal.html`.
- Lists all evaluated controls, results, license context, evidence references.
- Includes per-control license-aware status with explanation ("Not licensed: requires Entra ID P2").
- Includes the cross-module correlation findings owned by Entra-side seeds (`ENTRA-HYBRID-001..005`, `ENTRA-SF-001..003`).

### 22.2 Customer Summary report

- Module section rendered from `modules/entra/reports/customer.html`.
- Only findings with `customer_visibility ∈ {customer_summary, customer_full}` (default `internal_only`).
- License-aware framing in **plain language**: every `not_licensed` finding is rendered as an **Opportunity card** (per `UI_DESIGN_DIRECTION.md` §12). Example text:
  > *"Risk-based access policies and just-in-time elevation require Microsoft 365 E5 (or Entra ID P2 as an add-on). These capabilities are not currently in your subscription. Acquiring them would address X of your Y highest identity risks and close N points of the Target Posture gap."*
- The Opportunity card **does not include pricing or sales messaging**. It states capability, gap, and impact.
- Technical detail (UPNs, role names, policy ids) is rendered only when `customer_visibility = customer_full` (per `MODULE_ARCHITECTURE.md` §13.1).

### 22.3 Internal vs Customer comparison

| Section | Internal | Customer Summary | Customer Full |
|---|:---:|:---:|:---:|
| Owned SKU list | ✅ | ✅ | ✅ |
| Capability ownership table | ✅ | ✅ aggregated | ✅ |
| Controls (per-control results) | ✅ | ⬜ | ✅ |
| CA policy summary | ✅ | ⬜ | ✅ |
| Identity-level finding lists | ✅ | ⬜ | ✅ (UPN-masked optional) |
| Opportunity cards | ✅ | ✅ | ✅ |
| Two-scores card | ✅ | ✅ | ✅ |

The renderer applies visibility before composing the template (per `SECURITY_AND_GDPR.md` §17). Audit log records `report.generate` and `report.publish` events (per `SECURITY_AND_GDPR.md` §6).

---

## 23. POC / MVP / Full — module capability table

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| `entra-graph-json-bundle` parser | ✅ | ✅ | ✅ |
| Live Microsoft Graph collector | ⬜ design | ✅ | ✅ |
| Consultant-confirmed SKU set | ✅ | ✅ | ✅ |
| `subscribedSkus` auto-detect | ⬜ (parser proposes from file) | ✅ | ✅ |
| License-aware controls (8 enum) | ✅ | ✅ | ✅ |
| Identity Protection signals | ⬜ controls; ✅ capability detection | ✅ | ✅ |
| Access reviews controls | ⬜ detection only | ✅ | ✅ |
| PIM controls (PRIV-003/005) | 🟡 reporting only | ✅ | ✅ |
| CA controls (CA-001..007) | ✅ 3 of 7 (CA-001, CA-002, CA-003) | ✅ all 7 | ✅ all 7 |
| Authentication-method controls | ✅ AUTH-001 (POC stretch); AUTH-002/3/4 ⬜ | ✅ | ✅ |
| Apps controls | ✅ APP-002; APP-001/3/4/5/6 ⬜ | ✅ | ✅ |
| Guests controls | ⬜ | ✅ | ✅ |
| Hybrid controls | ✅ HYBRID-001/004; HYBRID-002/3/5 🟡 detection | ✅ | ✅ |
| Silverfort correlation | ✅ ENTRA-SF-002; SF-001/3 🟡 | ✅ | ✅ |
| BloodHound correlation (CORR-BH-ENTRA-001) | ✅ headline demo | ✅ | ✅ |
| Continuous monitoring (Graph delta) | ⬜ | ⬜ | ✅ |
| Tenant-wide security baseline scoring | 🟡 partial | ✅ | ✅ |
| Per-app last-activity (AuditLog) | ⬜ | ✅ | ✅ |
| Risky-user dashboard integration | ⬜ | ✅ | ✅ |

POC controls (8) satisfy `POC_V1_SCOPE.md` §5.6 "≥ 6 controls". Excess of 2 is intentional to ensure both a `licensed_disabled` and a `not_licensed` UI example are present without removing a mandated control.

---

## 24. Risks and questions

### 24.1 Risks

| Risk | Mitigation |
|---|---|
| **R-0007** — Licensing catalog drift causes wrong scoring (m365maps inspiration only) | Catalog is hand-populated for POC; replace via Microsoft `subscribedSkus` + official docs before MVP (Q-0071). Catalog rows carry a `last_verified_at` (MVP). m365maps cited only as inspiration (A-0014). |
| Identity-link ambiguity (UPN-only matches across forests) | `identity/ambiguity.py` surfaces ambiguous matches; no silent merge (per `MODULE_ARCHITECTURE.md` §8). |
| Customer admin reluctance to grant `Application.Read.All` / `AuditLog.Read.All` (Q-0080) | Module degrades gracefully: APP-006 and similar move to `unknown` with a documented reason; rest of the module still evaluates. |
| Graph throttling on real collection (MVP) | Collector uses paging + retry-with-backoff; documented in `MVP` design only. |
| `riskyUsers` exposed but tenant lacks P2 — false confidence | Resolver is authoritative over evidence: P2 ownership is the gate, not file presence (§16). |
| Breakglass mis-detection by convention | Consultant must confirm; convention is suggestive only (§11). |
| Synced privileged account false positive on managed identities | Filter `is_privileged` to exclude managed-identity types (parser config). |
| App permission list drift (Microsoft adds new high-privilege permissions) | List is data-driven (`high_privilege_permissions.json`); reviewed before MVP. |
| Customer reads "Not licensed" as a sales gimmick | Tooltip language is explicit and non-sales (per `UI_DESIGN_DIRECTION.md` §12). Reports never include pricing. |

### 24.2 Carried open questions

| Question | Scope | Why it matters here |
|---|---|---|
| **Q-0070** Small license catalog (E3 / E5 / EMS / Entra ID P1/P2 / DfI / Silverfort) — confirmed? | POC | Drives §4.2 capability mapping. |
| **Q-0071** Authoritative source post-POC (Graph `subscribedSkus`, official docs) | MVP | Replaces hand-populated catalog. |
| **Q-0072** Auto-detect customer licensing from Graph at MVP or always require consultant confirmation? | MVP | Drives trust model and audit log volume. |
| **Q-0080** Customer reluctance to grant `Application.Read.All` / `AuditLog.Read.All`? | MVP | Drives module degradation behaviour (§2.3). |
| **Q-0081** Multitenant ACEN-published app vs BYO app registration? | MVP | Drives §2.2 operational model. |

---

## 25. Cross-document references

- `WORKING_APPROACH.md` — operating model.
- `PRODUCT_DESIGN.md` §23 — module summary; §25 — scoring; §27 — UI principles.
- `POC_V1_SCOPE.md` §4 step 7 + step 8 — demo journey for Entra and correlation; §5.6 — POC Entra scope.
- `MODULE_ARCHITECTURE.md` §3 — lifecycle; §8 — Identity; §10 — Finding shape (verbatim); §11 — correlation; §12 — scoring; §15 — module fit.
- `LICENSE_MODEL.md` §3 — 8-value enum (verbatim); §5 — catalog; §7 — scoring formulas; §8 — Microsoft examples.
- `SECURITY_AND_GDPR.md` §6 — audit log; §7 — evidence protection; §17 — publishing controls.
- `UI_DESIGN_DIRECTION.md` §3 — components; §4.3 — `M` template; §12 — license-aware UI (Opportunity card); §15 — Entra module page composition.
- `DECISIONS.md` — D-0007 (8-value enum), D-0008 (two scores), D-0011 (synthetic data), D-0009 (publishing default).
- `ASSUMPTIONS.md` — A-0007 (Graph permissions), A-0014 (m365maps inspiration only).
- `OPEN_QUESTIONS.md` — Q-0070, Q-0071, Q-0072, Q-0080, Q-0081.
- `AD_MODULE_DESIGN.md` — cross-controls AD-ENTRA-* and identity link.
- `BLOODHOUND_ANALYZER_DESIGN.md` — `CORR-BH-ENTRA-001` path target overlap.
- `SILVERFORT_MODULE_DESIGN.md` — coverage-set contributors for ENTRA-SF-001..003.

---

*Last updated: 2026-05-15.*
