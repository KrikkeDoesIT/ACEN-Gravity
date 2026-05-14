# AD_MODULE_DESIGN.md

> Design specification for the **Active Directory module** in ACEN Gravity. The AD module ingests evidence produced by the AD toolkit (see `AD_TOOLKIT_DESIGN.md`), evaluates a set of AD-specific controls, contributes to the canonical `Identity` entity, and emits findings into the shared finding model.
>
> Companion documents: `AD_TOOLKIT_DESIGN.md`, `MODULE_ARCHITECTURE.md` (single lifecycle, manifest, finding shape, scoring), `LICENSE_MODEL.md`, `SECURITY_AND_GDPR.md`, `UI_DESIGN_DIRECTION.md`, `BLOODHOUND_ANALYZER_DESIGN.md` (BloodHound module owns SharpHound parsing — see §3.3 below), `POC_V1_SCOPE.md` §5.3 / §10, `DECISIONS.md`, `ASSUMPTIONS.md` (A-0004 PingCastle canonical, A-0011 identity join, A-0013 no auth in POC).

---

## 1. Goals

The AD module exists to give consultants and customers a **defensible, license-aware, license-honest assessment of an Active Directory estate**, focused on the risk classes ACEN repeatedly sees in identity-security engagements:

1. **AD health** — replication, FSMO, DNS, recycle bin, time skew. (POC)
2. **Privileged exposure** — Tier 0 group membership, nesting depth, stale privileged accounts, privileged service accounts. (POC)
3. **Kerberos** — encryption types, ticket lifetimes, AS-REP roastable accounts, RC4 / DES usage. (POC)
4. **Delegation** — unconstrained, constrained, resource-based. (POC)
5. **NTLM** — auditing posture, restrict-NTLM GPO state, legacy auth indicators. (MVP)
6. **GPO / OU** — risky GPO settings, link scope, Tier 0 GPO controls. (POC subset)
7. **AD CS readiness** — ESC1–ESC8-style misconfigurations, template enumeration. (MVP)
8. **Tier 0 boundary** — Microsoft Enterprise Access Model baseline + per-engagement override (Q-0053). (POC)
9. **Backup / recovery** — DSRM password rotation cadence, recycle bin, AD-native backup state. (MVP)
10. **Cross-module correlation** — AD ↔ BloodHound, AD ↔ Silverfort, AD ↔ Entra (hybrid identity). (POC)

The module is **not**:

- An attack-path analyzer. That is the BloodHound module's domain (`BLOODHOUND_ANALYZER_DESIGN.md`).
- An AD-CS pentest. AD CS controls in MVP focus on configuration audit, not exploitation.
- An AD security workshop deliverable replacement. The platform is a complement to consultant workshops, not a substitute.

### 1.1 Scope per tier

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| AD-HEALTH controls | ≥1 | ✅ all | ✅ |
| AD-PRIV controls | ≥2 | ✅ all | ✅ |
| AD-KERB controls | ≥1 | ✅ all | ✅ |
| AD-DELEG controls | ≥1 | ✅ all | ✅ |
| AD-NTLM controls | ⬜ | ✅ | ✅ |
| AD-GPO controls | ≥1 | ✅ | ✅ |
| AD CS readiness (`AD-ADCS-*`) | ⬜ | ✅ | ✅ |
| AD-SF correlation controls | ≥1 | ✅ all | ✅ |
| AD-ENTRA correlation controls | ⬜ design | ✅ | ✅ |
| Backup / recovery controls | ⬜ design | ✅ | ✅ |
| BloodHound correlation consumption | ✅ | ✅ | ✅ |

POC target (from `POC_V1_SCOPE.md` §5.3): **≥ 6 controls** mixed across Health (1), Privileged (2), Kerberos (1), Delegation (1), GPO (1), plus the AD-SF correlation control surfaced in the demo journey.

---

## 2. Data sources

The AD module consumes:

| Source | Origin | Evidence type | Owner |
|---|---|---|---|
| `ad-toolkit-zip` | AD toolkit (`AD_TOOLKIT_DESIGN.md`) | `ad-toolkit-zip` | AD module parses |
| Embedded `pingcastle.xml` | Inside the toolkit ZIP | implicit | AD module parses |
| Standalone `pingcastle.xml` | Direct upload (when toolkit not run) | `pingcastle-xml` | AD module parses |
| `bloodhound.zip` inside the toolkit ZIP (controlled-optional) | SharpHound CE | `sharphound-zip` | **BloodHound module parses** (not AD) |
| BloodHound findings + paths | BloodHound module evaluation output | normalized `bh_path` rows | AD module *consumes via correlation* (read-only) |

Rules:

- The AD module **never parses SharpHound output**. If a toolkit ZIP carries `bloodhound/bloodhound.zip`, the platform's upload/parse dispatcher (`MODULE_ARCHITECTURE.md` §3) extracts it and dispatches to the BloodHound module's parser. The AD module's parser leaves it alone.
- The AD module **does not import the BloodHound module**. Correlation flows through the core `view` (`MODULE_ARCHITECTURE.md` §11).
- Standalone `pingcastle-xml` uploads are supported because ACEN sometimes receives a PingCastle report alone (no toolkit). The same parser is used; only the surrounding context is missing.

---

## 3. AD toolkit relationship

The AD toolkit (`AD_TOOLKIT_DESIGN.md`) is the **producer** of the `ad-toolkit-zip` evidence type for this module. The relationship:

| Aspect | Toolkit (producer) | AD module (consumer) |
|---|---|---|
| Owns | Collection design, manifest schema, signing process, run-host security | Parsing, normalization, controls, scoring, report sections, correlation |
| Output | A single ZIP per run | `Evidence` rows + module-local normalized rows + `Identity` upserts |
| Versioning | `toolkit_version` and per-collector versions in manifest | Acceptance range declared in module manifest (`MODULE_ARCHITECTURE.md` §6) |
| Failure mode | Aborts and emits clear error; no partial ZIP | Marks artifact `parse_failed` with reason; no partial findings (`MODULE_ARCHITECTURE.md` §3) |
| BloodHound | Bundles SharpHound ZIP only when operator opts in | Treats it as a delegated artifact for the BloodHound module |
| PingCastle | Embeds XML if present | Parses XML into AD module-local data + scores |

### 3.1 Parser entry points

| Evidence type | Parser path | Output |
|---|---|---|
| `ad-toolkit-zip` | `modules/ad/parsers/toolkit_zip.py` | `Evidence` rows for each inner file; module-local rows; `Identity` upserts |
| `pingcastle-xml` | `modules/ad/parsers/pingcastle.py` | `Evidence` row; module-local PingCastle rows; `Identity` references where derivable |

Both parsers are deterministic and idempotent. Re-parsing a previously-parsed artifact either produces identical normalized rows or is rejected as an attempt to overwrite immutable evidence (per `MODULE_ARCHITECTURE.md` §3 failure rules and §18 "What to avoid").

---

## 4. PingCastle handling

PingCastle is the **canonical AD configuration baseline** (A-0004). The AD module:

| Action | Detail |
|---|---|
| Parses PingCastle XML | Using a hardened XML parser (no DTD, no external entities — `SECURITY_AND_GDPR.md` §7.2, §21). |
| Maps PingCastle rules to **module-local normalized data** | E.g., privileged-group membership, kerberos config, replication health, GPO findings flow into `ad_domain`, `ad_kerberos_config`, `ad_gpo`, etc. (§5). |
| Maps PingCastle-named principals to `Identity` refs | Via SID first, then sAMAccountName + ObjectGUID where SID is absent (`MODULE_ARCHITECTURE.md` §8 linking rules). |
| Treats PingCastle score as a control | `AD-HEALTH-004 PingCastle Composite Health` — see §8. The control uses a **custom rubric** (see §4.2). The raw PingCastle score is exposed as context, not as the score itself. |
| Treats PingCastle indicators as inputs to other controls | Not as findings on their own. The platform's controls and findings are the surface a customer sees, not PingCastle's. PingCastle indicators are **evidence references** within the platform's findings. |
| Logs PingCastle engine version | From `pingcastle.engine_version` in `manifest.json`. Used to flag unsupported versions and downgrade affected control results to `unknown`. |

### 4.1 Why PingCastle is normalized, not surfaced

PingCastle is excellent at AD enumeration, but its rule list, scoring, and language are PingCastle's, not ACEN's. The platform must speak in **ACEN's controls and findings** (see `MODULE_ARCHITECTURE.md` §10) so that:

- Customers receive a consistent ACEN deliverable across modules.
- License-aware scoring (`LICENSE_MODEL.md`) applies uniformly.
- Cross-module correlation works on `Identity` and `Finding`, not on PingCastle indicators.
- The platform's findings can be retested deterministically by the same controls.

### 4.2 PingCastle composite control rubric (`AD-HEALTH-004`)

A custom rubric, not a passthrough of PingCastle's score:

| PingCastle score (X / 100) | `result_status` | `severity` |
|---|---|---|
| 0–25 (PingCastle considers 0 best) | `pass` | Info |
| 26–50 | `partial` | Low |
| 51–75 | `partial` | Medium |
| 76–100 | `fail` | High |
| Unparseable / unsupported version | `unknown` | (mapped severity for unknown) |

Note: PingCastle's score scale runs low-is-good. The rubric is calibrated to that direction; we surface the score consistently in the UI with a tooltip ("PingCastle: lower is better. Composite score X means …").

`license_status`: always `licensed_enabled` for AD itself (`LICENSE_MODEL.md` §10) — AD is the customer's infrastructure, not a paid Microsoft add-on.

---

## 5. BloodHound

The AD module's relationship to BloodHound is **cross-module correlation only**.

| Concern | Approach |
|---|---|
| Parsing SharpHound CE JSON | BloodHound module (`BLOODHOUND_ANALYZER_DESIGN.md`). |
| Detecting paths to Tier 0 | BloodHound module. |
| Ranking paths | BloodHound module. |
| Producing path-level findings (`category = "bh.path"`) | BloodHound module. |
| AD finding "this account is on a BloodHound path" | AD module emits a finding referencing the BloodHound `path` and `Identity`. The platform's correlation orchestrator (`MODULE_ARCHITECTURE.md` §11) typically produces the joined narrative (`CORR-BH-AD-001`); AD controls can also reference BH paths directly when the AD-side finding is the primary story (e.g., `AD-PRIV-005`). |
| AD module Python imports of BloodHound code | None. Read-only access via the core `view` API. |
| AD module DB reads of BloodHound tables | Allowed when the read is for a correlation control. Module-local BH tables (`bh_path`, etc.) are exposed via the core `view`. |

The headline cross-module finding for the management demo is `CORR-BH-ENTRA-001` (per `MODULE_ARCHITECTURE.md` §11.3). The AD module's role is to expose privileged-identity context so that finding has the AD shape (privileged service account, Tier 0 membership, delegation flag) in its `payload`.

---

## 6. Normalized model

The AD module's local tables. Names prefixed `ad_` per `MODULE_ARCHITECTURE.md` §14. Contributions to core entities listed at the end.

### 6.1 Module-local tables (schema sketch)

```python
class ad_domain(Base):
    id: UUID
    customer_id: UUID
    run_id: UUID
    domain_dns_name_hash: str          # SHA-256 of the DNS name; raw name internal_only
    domain_sid: str
    forest_functional_level: str
    domain_functional_level: str
    tombstone_lifetime_days: int | None
    recycle_bin_enabled: bool | None
    pingcastle_score: int | None       # 0-100 (PingCastle scale; lower better)
    pingcastle_engine_version: str | None
    collected_at: datetime
```

```python
class ad_dc(Base):
    id: UUID
    ad_domain_id: UUID
    dc_label_hash: str                 # hashed hostname; raw hostname internal_only
    fsmo_roles: list[str]              # e.g., ["pdc_emulator", "rid_master"]
    os_major: str
    site: str | None
    replication_partner_count: int
    last_replication_success_at: datetime | None
    health_status: enum("ok", "warning", "fail", "unknown")
```

```python
class ad_kerberos_config(Base):
    ad_domain_id: UUID
    max_tgt_lifetime_hours: int
    max_renewal_lifetime_hours: int
    allowed_encryption_types_summary: dict   # {"rc4_allowed": true, "des_allowed": false, ...}
    accounts_supporting_rc4: int
    accounts_supporting_des_only: int
    accounts_asrep_roastable: int            # DONT_REQ_PREAUTH set
    accounts_trustedfordelegation: int
```

```python
class ad_gpo(Base):
    id: UUID
    ad_domain_id: UUID
    gpo_id: str                              # AD GPO id (GUID)
    display_name: str
    enabled: bool
    linked_ou_count: int
    risky_settings: list[str]                # e.g., ["ntlm_allowed", "anonymous_share"]
    affects_tier0_ou: bool
    pingcastle_rule_refs: list[str]
```

```python
class ad_delegation(Base):
    id: UUID
    ad_domain_id: UUID
    identity_id: UUID                        # FK to core Identity
    delegation_type: enum("unconstrained", "constrained_s4u", "rbcd")
    target_principals: list[str]             # for constrained / rbcd
    risk_class: enum("low", "medium", "high", "critical")
    pingcastle_rule_refs: list[str]
```

```python
class ad_privileged_group_membership(Base):
    id: UUID
    ad_domain_id: UUID
    group_label: str                         # "Domain Admins", "Enterprise Admins", ...
    member_identity_id: UUID                 # FK to core Identity
    is_direct: bool
    nest_path: list[str]                     # ["DA -> NestedGroup -> sub-group"]
    last_logon_days_ago: int | None
    pwd_last_set_days_ago: int | None
    is_service_account: bool
    is_disabled: bool
```

```python
class ad_service_account(Base):
    id: UUID
    ad_domain_id: UUID
    identity_id: UUID                        # FK to core Identity
    account_class: enum("spn_holder", "msa", "gmsa", "legacy_heuristic")
    has_dontexpirepassword: bool
    pwd_last_set_days_ago: int | None
    spn_count: int
    is_kerberoastable: bool                  # RC4 enctype + has SPN + user (not gMSA)
    is_privileged: bool
```

### 6.2 Contributions to core entities

| Core entity | What AD writes | Linking rule |
|---|---|---|
| `Identity` (users, service accounts) | SID, sAMAccountName, ObjectGUID, canonical label | SID primary, sAMAccountName + ObjectGUID secondary (`MODULE_ARCHITECTURE.md` §8) |
| `Identity.is_privileged` | `true` when in well-known Tier 0 group or in customer-defined Tier 0 list (Q-0053) | AD module sets; BH and Entra may further confirm |
| `Identity.is_tier0` | `true` when in Tier 0 per `Tier 0` definition (§9) | AD module sets baseline; BH may add (path target); Entra contributes hybrid context |
| `Computer` | Domain controllers + member computers from PingCastle / toolkit | By SID where present |
| `Group` | Privileged groups (membership tracked in `ad_privileged_group_membership`) | By SID |

### 6.3 What we deliberately do not normalize

- Full LDAP attribute dumps (data minimization, `SECURITY_AND_GDPR.md` §13.3).
- Mailbox contents, OneDrive data, certificates.
- Session data (A-0015 — synthetic ZIPs omit sessions; real ZIPs at MVP do not persist session data into normalized tables).
- Raw GPO XML (we keep summaries only — §6.1).

---

## 7. Tier 0 definition

Per `OPEN_QUESTIONS.md` Q-0053 and `MODULE_ARCHITECTURE.md` §15, Tier 0 is the boundary that drives much of the AD risk model. The module's approach:

| Component | Detail |
|---|---|
| Baseline | **Microsoft Enterprise Access Model** — well-known privileged groups (`Domain Admins`, `Enterprise Admins`, `Schema Admins`, `Administrators`, `Account Operators`, `Server Operators`, `Print Operators`, `Backup Operators`, `Replicator`, `Group Policy Creator Owners`, `DnsAdmins` where present, plus the local Administrators groups of DCs and FSMO-role holders). |
| Per-engagement override | The consultant can extend the Tier 0 list at engagement setup (additional groups, additional accounts, additional Tier 0 OUs / GPOs). This override is recorded in the engagement and surfaced in every Tier 0 control's explanation: "Tier 0 boundary: Microsoft baseline + customer-specified additions: …" |
| What Tier 0 drives | `Identity.is_tier0`, BloodHound path targets (BloodHound module reads `Identity.is_tier0` via core `view`), `AD-PRIV-*` and `AD-DELEG-*` controls, correlation rules (`CORR-AD-SF-001`, `CORR-BH-AD-001`, `CORR-BH-ENTRA-001`). |
| What Tier 0 does not change | The license-aware status of AD controls (AD itself is `licensed_enabled` — see `LICENSE_MODEL.md` §10). It changes severity, not capability ownership. |

---

## 8. Controls

The full POC + MVP + Full control list. Each control has an id of the form `AD-<group>-NNN`. Compact-block style per control.

> Conventions:
>
> - **License status** behaviour: AD controls default to `licensed_enabled` because AD is the customer's existing infrastructure (`LICENSE_MODEL.md` §10). A few controls reference *preferred* third-party capabilities (e.g., Silverfort for compensating control on delegation) — these surface as `available_in_higher_tier` when the customer does not own Silverfort, **only** for the Target Posture Score; Current License Score is unaffected.
> - **Severity** defaults are starting points; the evaluator may up-/down-grade based on Tier 0 involvement, scale, or correlation breadth.
> - **POC support** column reflects `POC_V1_SCOPE.md` §5.3.

### 8.1 AD-HEALTH-* (Health)

#### AD-HEALTH-001 — Domain Replication Health
- **Objective:** All inter-DC replication partners have reported success within the configured tolerance (default: last 24 h).
- **Evidence required:** `replication-health.json`, `domain-controllers.json`.
- **Status behaviour:** `pass` if 100% partners succeeded ≤ 24 h; `partial` if 1 partner failed or last success > 24 h; `fail` if ≥ 2 partners failed or last success > 72 h on any DC; `unknown` if evidence missing.
- **Finding example:** "Replication failures observed on DC-3 (3 partners failing, oldest 4 d)."
- **Remediation:** Standard AD replication troubleshooting (DNS, network, RPC, DC time skew).
- **POC / MVP / Full:** POC ✅ (Health representative) / MVP ✅ / Full ✅

#### AD-HEALTH-002 — FSMO Holders Reachable and Healthy
- **Objective:** All five FSMO roles are present, assigned, and the holders are healthy.
- **Evidence required:** `ad-health.json`, `domain-controllers.json`.
- **Status behaviour:** `pass` if 5/5 roles assigned, holders reachable, no replication failures. `partial` if 1 role holder degraded. `fail` if a role unassigned or holder unreachable. `unknown` if evidence missing.
- **Finding example:** "PDC Emulator role holder DC-1 has not replicated successfully in 5 days."
- **Remediation:** Recover or seize FSMO role per Microsoft guidance; fix underlying DC health.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-HEALTH-003 — DNS and Time-Skew Health
- **Objective:** Forward/reverse zones configured, scavenging enabled appropriately; domain-wide time skew ≤ 5 minutes.
- **Evidence required:** `dns-health.json`, `ad-health.json`.
- **Status behaviour:** `pass` if both healthy; `partial` if one degraded; `fail` if Kerberos-affecting time skew > 5 min; `unknown` if evidence missing.
- **Finding example:** "Reverse DNS zones missing on 2 of 4 sites; risk of NTLM fallback."
- **Remediation:** Configure missing zones; verify scavenging; review NTP hierarchy.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-HEALTH-004 — PingCastle Composite Health
- **Objective:** PingCastle composite score sits within an acceptable band (see rubric, §4.2).
- **Evidence required:** `pingcastle.xml`. If absent → `unknown` with explanation.
- **Status behaviour:** see §4.2.
- **Finding example:** "PingCastle composite score 78/100 (high risk); top 3 contributing PingCastle rules: …"
- **Remediation:** Address contributing PingCastle rules in order of risk, mapped to platform findings where they overlap.
- **POC / MVP / Full:** POC ✅ (Health representative for `POC_V1_SCOPE.md` §5.3) / MVP ✅ / Full ✅

### 8.2 AD-PRIV-* (Privileged)

#### AD-PRIV-001 — Privileged Group Membership Count
- **Objective:** Membership of well-known Tier 0 groups stays within recommended bounds (`Domain Admins` ≤ 5 active members; `Enterprise Admins` ≤ 2; etc., baseline configurable).
- **Evidence required:** `privileged-groups.json`.
- **Status behaviour:** `pass` if all groups within bounds; `partial` if 1 group exceeds; `fail` if multiple groups exceed; `unknown` if evidence missing.
- **Finding example:** "`Domain Admins` has 14 active members (recommended ≤ 5)."
- **Remediation:** Audit and remove unnecessary members; use PIM (Entra hybrid) or JIT/JEA where applicable.
- **POC / MVP / Full:** POC ✅ (Privileged representative #1) / MVP ✅ / Full ✅

#### AD-PRIV-002 — Stale Privileged Accounts
- **Objective:** No privileged account has been inactive (`LastLogonTimestamp`) beyond the threshold (default 90 days) or has `pwdLastSet` older than the threshold (default 365 days).
- **Evidence required:** `privileged-groups.json`.
- **Status behaviour:** `pass` if 0 stale; `partial` if 1–2; `fail` if ≥ 3 or any with `pwdLastSet` > 730 days; `unknown` if evidence missing.
- **Finding example:** "3 privileged accounts inactive > 180 days; 1 with `pwdLastSet` 1,124 days ago."
- **Remediation:** Disable or rotate; review whether they are required.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-PRIV-003 — Nested Privileged Group Depth
- **Objective:** No Tier 0 group has indirect members beyond depth 1 (i.e., no nested groups granting effective Tier 0).
- **Evidence required:** `privileged-groups.json` (with `is_direct` + `nest_path`).
- **Status behaviour:** `pass` if max depth ≤ 1; `partial` if depth 2 on non-DA groups; `fail` if depth ≥ 2 on `Domain Admins` / `Enterprise Admins`; `unknown` if evidence missing.
- **Finding example:** "`Enterprise Admins` includes group `Helpdesk-Tier2` via `IT-Operations`, indirectly granting EA to 47 users."
- **Remediation:** Flatten privileged groups; revoke indirect grants; use direct membership.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-PRIV-004 — Privileged Accounts With UPN / Email
- **Objective:** Privileged accounts should not be mail-enabled or used as primary user accounts (preventing phishing → privilege escalation overlap).
- **Evidence required:** `privileged-groups.json`, optional cross-check with Entra evidence.
- **Status behaviour:** `pass` if 0 privileged accounts are mail-enabled; `partial` if ≤ 2; `fail` if ≥ 3; `unknown` if evidence missing.
- **Finding example:** "2 `Domain Admins` members are mail-enabled (matching their primary user UPN); recommend dedicated admin accounts."
- **Remediation:** Dedicated admin accounts; remove mailbox; rename per Tier 0 admin naming convention.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-PRIV-005 — Privileged Service Accounts
- **Objective:** Identify service accounts that hold privileged group memberships and assess their hygiene (Kerberoastable, weak/legacy, password age).
- **Evidence required:** `privileged-groups.json`, `service-accounts.json`, `kerberos-config.json`.
- **Status behaviour:** `pass` if 0 privileged service accounts; `partial` if ≤ 1 and not Kerberoastable; `fail` if ≥ 1 Kerberoastable privileged SA, or ≥ 2 privileged SAs; `unknown` if evidence missing.
- **Finding example:** see §11.1.
- **Remediation:** Migrate to gMSA where supported; remove from privileged groups; rotate password; enforce AES enctypes.
- **POC / MVP / Full:** POC ✅ (Privileged representative #2; demo journey `POC_V1_SCOPE.md` §10) / MVP ✅ / Full ✅
- **Preferred capability:** `silverfort.service-account-protection` — surfaces as `available_in_higher_tier` on Target Score when Silverfort not owned (`LICENSE_MODEL.md` §5.4).

#### AD-PRIV-006 — Tier 0 Computer Group Hygiene
- **Objective:** DCs and Tier 0 servers are members of Tier 0 OUs and not exposed via local admin groups that include non-Tier 0 accounts.
- **Evidence required:** `domain-controllers.json`, GPO summaries from `gpo-summary.json`.
- **Status behaviour:** `pass` if all DCs in Tier 0 OUs and Tier 0 GPO scope is clean; `partial` if 1 deviation; `fail` if ≥ 2 deviations; `unknown` if evidence missing.
- **Finding example:** "DC-2 is not in Tier 0 OU; the Tier 0 admin GPO does not apply to it."
- **Remediation:** Move DC to Tier 0 OU; verify GPO scope; review local admin membership on Tier 0 servers.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.3 AD-KERB-* (Kerberos)

#### AD-KERB-001 — RC4 / DES Encryption Usage
- **Objective:** Domain Kerberos policy disallows RC4 / DES; per-account `msDS-SupportedEncryptionTypes` reflect AES-256.
- **Evidence required:** `kerberos-config.json`.
- **Status behaviour:** `pass` if RC4 disabled at policy AND ≤ 5% accounts list RC4; `partial` if RC4 enabled but ≤ 5% of accounts use it; `fail` if RC4 default OR > 5% of accounts; `unknown` if evidence missing.
- **Finding example:** "Kerberos policy allows RC4 (`HMAC-SHA1`); 312 accounts (12%) advertise RC4-only support."
- **Remediation:** Enforce AES-only at domain policy; remediate per-account encryption support; review services dependent on RC4.
- **POC / MVP / Full:** POC ✅ (Kerberos representative) / MVP ✅ / Full ✅

#### AD-KERB-002 — AS-REP Roastable Accounts
- **Objective:** No account has `DONT_REQ_PREAUTH` set.
- **Evidence required:** `kerberos-config.json`, `service-accounts.json`.
- **Status behaviour:** `pass` if 0 roastable; `partial` if 1 non-privileged; `fail` if ≥ 1 privileged OR ≥ 3 non-privileged; `unknown` if evidence missing.
- **Finding example:** "2 service accounts have AS-REP pre-authentication disabled; both have SPNs."
- **Remediation:** Re-enable Kerberos pre-authentication; rotate password.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-KERB-003 — Max Ticket Lifetime
- **Objective:** Max TGT lifetime ≤ 10 h; max renewal ≤ 7 d (Microsoft default).
- **Evidence required:** `kerberos-config.json`.
- **Status behaviour:** `pass` if within recommended bounds; `partial` if up to 2× recommended; `fail` if > 2× recommended; `unknown` if evidence missing.
- **Finding example:** "Max TGT lifetime is 24 h; recommended 10 h."
- **Remediation:** Reduce ticket lifetimes via domain policy.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-KERB-004 — KRBTGT Password Age
- **Objective:** `krbtgt` password rotated within the last 180 days; rotated twice within the last year (recommended).
- **Evidence required:** `ad-health.json`, PingCastle indicator references.
- **Status behaviour:** `pass` if rotated ≤ 180 d; `partial` if 180–365 d; `fail` if > 365 d; `unknown` if evidence missing.
- **Finding example:** "`krbtgt` password last set 624 days ago; golden-ticket window is wide."
- **Remediation:** Run Microsoft's `New-KrbtgtKeys` rotation script twice with a sufficient interval.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.4 AD-DELEG-* (Delegation)

#### AD-DELEG-001 — Unconstrained Delegation
- **Objective:** No principal (user, computer, service account) has `TrustedForDelegation = true` outside of DCs.
- **Evidence required:** `delegation.json`, `domain-controllers.json`.
- **Status behaviour:** `pass` if 0 non-DC principals; `partial` if ≤ 1 non-DC, non-Tier 0; `fail` if ≥ 1 non-DC Tier 0 or ≥ 2 non-DC overall; `unknown` if evidence missing.
- **Finding example:** see §11.2.
- **Remediation:** Convert to constrained or resource-based constrained delegation; otherwise remove.
- **POC / MVP / Full:** POC ✅ (Delegation representative; demo journey `POC_V1_SCOPE.md` §10) / MVP ✅ / Full ✅
- **Preferred capability:** `silverfort.policy-engine` (compensating control when delegation cannot be removed) — `available_in_higher_tier` on Target Score when Silverfort not owned.

#### AD-DELEG-002 — Constrained Delegation Target Hygiene
- **Objective:** Constrained delegation (`msDS-AllowedToDelegateTo`) targets only the services they need; no Tier 0 services in target lists from non-Tier 0 principals.
- **Evidence required:** `delegation.json`.
- **Status behaviour:** `pass` if all targets within Tier; `partial` if 1 cross-tier target; `fail` if ≥ 2 cross-tier or any DC service targeted from non-Tier 0; `unknown` if evidence missing.
- **Finding example:** "`svc_appA` is allowed to delegate to `cifs/DC-1` (Tier 0 target from non-Tier 0 principal)."
- **Remediation:** Restrict the target list; review business need; convert to RBCD.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-DELEG-003 — Resource-Based Constrained Delegation Audit
- **Objective:** `msDS-AllowedToActOnBehalfOfOtherIdentity` entries reviewed; no surprise Tier 0 delegations.
- **Evidence required:** `delegation.json`.
- **Status behaviour:** `pass` if all RBCD entries documented; `partial` if 1 undocumented; `fail` if ≥ 1 Tier 0 RBCD; `unknown` if evidence missing.
- **Finding example:** "RBCD entry on DC-1 allows `svc_helpdesk_app` to act on behalf of any user."
- **Remediation:** Remove the entry; document the use case; restrict.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-DELEG-004 — Delegation on Privileged Accounts Disabled (`NOT_DELEGATED`)
- **Objective:** Privileged accounts have `NOT_DELEGATED` flag set, so they cannot be impersonated via delegation.
- **Evidence required:** `privileged-groups.json` + `delegation.json` cross-reference.
- **Status behaviour:** `pass` if 100% of privileged users have flag set; `partial` if ≥ 80%; `fail` if < 80%; `unknown` if evidence missing.
- **Finding example:** "Only 4 of 14 `Domain Admins` members have `NOT_DELEGATED` set."
- **Remediation:** Set `NOT_DELEGATED` for all privileged accounts (Microsoft "Protected Users" group is preferred).
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.5 AD-NTLM-* (NTLM)

#### AD-NTLM-001 — NTLM Auditing Enabled
- **Objective:** Domain-controller NTLM auditing GPO is enabled so the customer can measure NTLM usage.
- **Evidence required:** `gpo-summary.json`, event-log evidence (where toolkit collects sample event-log indicators — MVP only).
- **Status behaviour:** `pass` if auditing enabled; `partial` if enabled on some DCs; `fail` if disabled domain-wide; `unknown` if evidence missing.
- **Finding example:** "NTLM auditing GPO is unlinked; the customer has no visibility into NTLM usage."
- **Remediation:** Configure `Network security: Restrict NTLM` policies in audit mode first.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-NTLM-002 — NTLMv1 Allowed
- **Objective:** NTLMv1 is denied by domain policy.
- **Evidence required:** `gpo-summary.json`.
- **Status behaviour:** `pass` if denied; `partial` if mixed; `fail` if allowed; `unknown` if evidence missing.
- **Finding example:** "`LmCompatibilityLevel` allows NTLMv1 fallback."
- **Remediation:** Set `LmCompatibilityLevel = 5` after audit.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-NTLM-003 — Restrict NTLM in Domain
- **Objective:** `Network security: Restrict NTLM: NTLM authentication in this domain` is at least in audit mode, ideally Deny.
- **Evidence required:** `gpo-summary.json`, event-log evidence where available.
- **Status behaviour:** `pass` if Deny; `partial` if Audit; `fail` if Allow; `unknown` if evidence missing.
- **Finding example:** "Restrict-NTLM is Allow; NTLM accounts for 41% of authentications observed in audit logs (MVP)."
- **Remediation:** Move to Audit first; remediate hot callers; then Deny.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.6 AD-GPO-* (GPO / OU)

#### AD-GPO-001 — Anonymous Access GPO Settings
- **Objective:** `EveryoneIncludesAnonymous`, anonymous SAM access, and similar legacy settings disabled.
- **Evidence required:** `gpo-summary.json`.
- **Status behaviour:** `pass` if 0 GPOs with risky settings; `partial` if 1 GPO; `fail` if ≥ 1 affects Tier 0 OU; `unknown` if evidence missing.
- **Finding example:** "GPO `Legacy Domain Settings` enables `EveryoneIncludesAnonymous` and is linked to root."
- **Remediation:** Remove legacy settings; verify no application dependency.
- **POC / MVP / Full:** POC ✅ (GPO representative) / MVP ✅ / Full ✅

#### AD-GPO-002 — Risky Restricted-Groups Settings
- **Objective:** No GPO grants Tier 0 group membership to non-Tier 0 principals via `Restricted Groups`.
- **Evidence required:** `gpo-summary.json` with `risky_settings` indicators.
- **Status behaviour:** `pass` if 0; `partial` if 1 non-DA grant; `fail` if ≥ 1 DA / EA grant; `unknown` if evidence missing.
- **Finding example:** "GPO `Helpdesk Tools` places `Helpdesk-Admins` into local Administrators on Tier 0 servers."
- **Remediation:** Remove the assignment; use tier-appropriate admin groups.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-GPO-003 — Weak Password Policy GPO
- **Objective:** No GPO weakens password policy below the domain baseline.
- **Evidence required:** `gpo-summary.json`.
- **Status behaviour:** `pass` if no weaker GPO present; `partial` if weaker GPO present but scope limited; `fail` if weaker GPO affects privileged OU; `unknown` if evidence missing.
- **Finding example:** "GPO `Service Accounts OU` allows 8-character passwords (domain baseline 14)."
- **Remediation:** Align scoped GPOs with domain baseline; use fine-grained password policies (PSO) instead.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-GPO-004 — Tier 0 GPO Editor Hygiene
- **Objective:** Only Tier 0 admins can edit GPOs linked to Tier 0 OUs.
- **Evidence required:** `gpo-summary.json` (ACL summary; MVP enriches this).
- **Status behaviour:** `pass` if all Tier 0 GPOs have Tier 0-only editors; `partial` if 1 non-Tier 0 editor on a non-DA GPO; `fail` if any Tier 0 GPO has non-Tier 0 editor; `unknown` if evidence missing.
- **Finding example:** "GPO `DC Hardening` is writable by `Helpdesk-Admins`."
- **Remediation:** Restrict GPO ACLs to Tier 0; remove inherited delegations.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.7 AD-SF-* (AD ↔ Silverfort correlation)

These controls live in the AD module but **depend on the Silverfort module's normalized data** via the core `view` (`MODULE_ARCHITECTURE.md` §11). They produce AD-side findings whose narrative is "AD identifies X; Silverfort would compensate / does not compensate".

> The `LICENSE_MODEL.md` §5.4 mapping treats Silverfort as a **preferred** capability for these controls — i.e., the control is always evaluated; if Silverfort is not owned, the result surfaces as `not_licensed` for the SF-side capability but the AD-side risk is still scored. See §6.5 in `LICENSE_MODEL.md` for the operational semantics.

#### AD-SF-001 — Tier 0 Identities Covered by Silverfort Policy
- **Objective:** Every Tier 0 identity (AD-derived) is covered by at least one Silverfort policy that enforces MFA / risk-based denial.
- **Evidence required:** AD `privileged-groups.json` + Silverfort `policies` evidence (via core `view`).
- **Status behaviour:** `pass` if 100% covered; `partial` if 80–99%; `fail` if < 80% or any DA member uncovered; `not_applicable` if Silverfort owned but no Tier 0 identities (unlikely); `unknown` if Silverfort evidence missing.
- **License status:** if customer owns Silverfort → mirrors result. If not → `available_in_higher_tier` (preferred capability missing): Current Score unaffected, Target Score counts as fail.
- **Finding example:** see §11.3.
- **Remediation:** Extend Silverfort policy coverage; align with Tier 0 list (§7).
- **POC / MVP / Full:** POC ✅ (correlation finding for demo journey `POC_V1_SCOPE.md` §10) / MVP ✅ / Full ✅

#### AD-SF-002 — Privileged Service Accounts Covered by Silverfort
- **Objective:** Privileged service accounts identified by AD-PRIV-005 are inside a Silverfort service-account protection policy.
- **Evidence required:** AD `service-accounts.json` + Silverfort `sf_service_account` (core view).
- **Status behaviour:** `pass` if all covered; `partial` if ≥ 80%; `fail` if < 80%; `unknown` if evidence missing.
- **License status:** mirrors `silverfort.service-account-protection`.
- **Finding example:** "3 privileged service accounts (`svc_backup`, `svc_sql_db1`, `svc_appA`) are not in Silverfort's service-account protection policy."
- **Remediation:** Add to the Silverfort service-account protection policy.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-SF-003 — Unconstrained Delegation Compensated by Silverfort
- **Objective:** Where AD-DELEG-001 finds unconstrained delegation, Silverfort policy enforces MFA on access from those principals.
- **Evidence required:** `delegation.json` + Silverfort `sf_policy_coverage`.
- **Status behaviour:** `pass` if all compensated; `partial` if some; `fail` if none and unconstrained delegation present; `not_applicable` if no unconstrained delegation; `unknown` if evidence missing.
- **License status:** mirrors `silverfort.policy-engine`.
- **Finding example:** "`svc_appA` has unconstrained delegation; no Silverfort policy enforces MFA on its authentications."
- **Remediation:** Add Silverfort policy; or remove delegation per AD-DELEG-001.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-SF-004 — Stale Privileged Accounts Not in Silverfort Decommission Path
- **Objective:** Stale privileged accounts (AD-PRIV-002) are in Silverfort's `disabled` or `risky` cohort, or have been decommissioned.
- **Evidence required:** AD `privileged-groups.json` + Silverfort `sf_entity_risk`.
- **Status behaviour:** `pass` if 100% accounted for; `partial` if some; `fail` if multiple stale + not in SF risk cohort; `unknown` if evidence missing.
- **License status:** mirrors `silverfort.policy-engine`.
- **Finding example:** "2 stale `Domain Admins` accounts not flagged in Silverfort entity risk."
- **Remediation:** Decommission AD-side; update Silverfort entity records.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.8 AD-ENTRA-* (AD ↔ Entra correlation)

Hybrid-identity correlation. Driven by the canonical `Identity` entity (`MODULE_ARCHITECTURE.md` §8) — Entra evidence sets `azure_object_id` and `onPremisesImmutableId`; AD evidence sets `sid`, `sam_account_name`, `object_guid`. The linker matches; the module reads the joined view.

#### AD-ENTRA-001 — AD Privileged Identity Synced to Entra Cloud-Privileged Role
- **Objective:** No AD-privileged identity is also a member of an Entra cloud-privileged role (`Global Administrator`, `Privileged Role Administrator`, etc.) — i.e., no cross-tier admin.
- **Evidence required:** AD `privileged-groups.json` + Entra `entra_role_assignment` (core view).
- **Status behaviour:** `pass` if 0 overlap; `partial` if 1 with PIM eligibility (Just-in-time); `fail` if ≥ 1 standing overlap or ≥ 2 PIM-eligible overlaps; `unknown` if Entra evidence missing.
- **License status:** `licensed_enabled` (depends on AD + Entra evidence; no specific capability paywall). PIM detection upgrades semantics where available.
- **Finding example:** "`alice.admin` is in `Domain Admins` (AD) **and** `Global Administrator` (Entra, standing assignment)."
- **Remediation:** Separate AD-tier and Entra-tier admin identities; enable PIM for Global Admin.
- **POC / MVP / Full:** POC ⬜ design (correlation `CORR-AD-ENTRA-001` in core orchestrator covers demo; AD-side detail surfaces at MVP) / MVP ✅ / Full ✅

#### AD-ENTRA-002 — Hybrid Synced Disabled / Non-Existent Cloud Counterpart
- **Objective:** Every Entra-synced AD account exists in both directions; no orphaned cloud accounts for deleted AD users (and vice versa).
- **Evidence required:** AD + Entra evidence via core view.
- **Status behaviour:** `pass` if 0 orphans; `partial` if ≤ 1%; `fail` if > 1% or any Tier 0 mismatch; `unknown` if Entra evidence missing.
- **Finding example:** "47 cloud user objects without an active on-prem counterpart; 2 are Entra-privileged."
- **Remediation:** Lifecycle hygiene; Entra Connect sync scope review.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-ENTRA-003 — Privileged AD Account Without Strong Cloud MFA
- **Objective:** Hybrid privileged AD accounts that authenticate to cloud services have phishing-resistant MFA (FIDO2 / WHfB / cert) at Entra.
- **Evidence required:** AD `privileged-groups.json` + Entra `entra_role_assignment` + Entra authentication methods evidence.
- **Status behaviour:** `pass` if all hybrid privileged accounts have phishing-resistant MFA; `partial` if standard MFA only; `fail` if password-only; `unknown` if Entra evidence missing.
- **License status:** `licensed_enabled` for Entra MFA. Phishing-resistant strength may prefer `entra.authentication-methods-policy`.
- **Finding example:** "5 hybrid privileged identities still rely on phone-call MFA."
- **Remediation:** Roll out FIDO2 keys / Windows Hello for Business; update authentication-methods policy.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

#### AD-ENTRA-004 — Pass-Through / Federated Auth Posture
- **Objective:** Hybrid authentication mechanism (Password Hash Sync, Pass-Through, Federation) is documented and Tier 0 accounts are protected accordingly.
- **Evidence required:** Entra tenant evidence (sync method) + AD evidence (Tier 0).
- **Status behaviour:** `pass` if PHS + cloud Kerberos enabled and Tier 0 accounts protected; `partial` if PTA-only with no fallback; `fail` if Federation with weak protection; `unknown` if Entra evidence missing.
- **Finding example:** "Tenant uses federation via ADFS 4.0; no cloud-only break-glass path; Tier 0 admins authenticate via federated identity."
- **Remediation:** Move to PHS / cloud Kerberos where applicable; establish break-glass.
- **POC / MVP / Full:** POC ⬜ / MVP ✅ / Full ✅

### 8.9 Control summary table

| ID | Group | Title | POC | MVP | Full |
|---|---|---|:---:|:---:|:---:|
| AD-HEALTH-001 | Health | Domain Replication Health | ⬜ | ✅ | ✅ |
| AD-HEALTH-002 | Health | FSMO Holders Reachable and Healthy | ⬜ | ✅ | ✅ |
| AD-HEALTH-003 | Health | DNS and Time-Skew Health | ⬜ | ✅ | ✅ |
| AD-HEALTH-004 | Health | PingCastle Composite Health | ✅ | ✅ | ✅ |
| AD-PRIV-001 | Privileged | Privileged Group Membership Count | ✅ | ✅ | ✅ |
| AD-PRIV-002 | Privileged | Stale Privileged Accounts | ⬜ | ✅ | ✅ |
| AD-PRIV-003 | Privileged | Nested Privileged Group Depth | ⬜ | ✅ | ✅ |
| AD-PRIV-004 | Privileged | Privileged Accounts With UPN / Email | ⬜ | ✅ | ✅ |
| AD-PRIV-005 | Privileged | Privileged Service Accounts | ✅ | ✅ | ✅ |
| AD-PRIV-006 | Privileged | Tier 0 Computer Group Hygiene | ⬜ | ✅ | ✅ |
| AD-KERB-001 | Kerberos | RC4 / DES Encryption Usage | ✅ | ✅ | ✅ |
| AD-KERB-002 | Kerberos | AS-REP Roastable Accounts | ⬜ | ✅ | ✅ |
| AD-KERB-003 | Kerberos | Max Ticket Lifetime | ⬜ | ✅ | ✅ |
| AD-KERB-004 | Kerberos | KRBTGT Password Age | ⬜ | ✅ | ✅ |
| AD-DELEG-001 | Delegation | Unconstrained Delegation | ✅ | ✅ | ✅ |
| AD-DELEG-002 | Delegation | Constrained Delegation Target Hygiene | ⬜ | ✅ | ✅ |
| AD-DELEG-003 | Delegation | Resource-Based Constrained Delegation Audit | ⬜ | ✅ | ✅ |
| AD-DELEG-004 | Delegation | Delegation on Privileged Accounts Disabled | ⬜ | ✅ | ✅ |
| AD-NTLM-001 | NTLM | NTLM Auditing Enabled | ⬜ | ✅ | ✅ |
| AD-NTLM-002 | NTLM | NTLMv1 Allowed | ⬜ | ✅ | ✅ |
| AD-NTLM-003 | NTLM | Restrict NTLM in Domain | ⬜ | ✅ | ✅ |
| AD-GPO-001 | GPO | Anonymous Access GPO Settings | ✅ | ✅ | ✅ |
| AD-GPO-002 | GPO | Risky Restricted-Groups Settings | ⬜ | ✅ | ✅ |
| AD-GPO-003 | GPO | Weak Password Policy GPO | ⬜ | ✅ | ✅ |
| AD-GPO-004 | GPO | Tier 0 GPO Editor Hygiene | ⬜ | ✅ | ✅ |
| AD-SF-001 | SF-corr | Tier 0 Identities Covered by Silverfort Policy | ✅ | ✅ | ✅ |
| AD-SF-002 | SF-corr | Privileged Service Accounts Covered by Silverfort | ⬜ | ✅ | ✅ |
| AD-SF-003 | SF-corr | Unconstrained Delegation Compensated by Silverfort | ⬜ | ✅ | ✅ |
| AD-SF-004 | SF-corr | Stale Privileged Accounts Not in Silverfort Decommission Path | ⬜ | ✅ | ✅ |
| AD-ENTRA-001 | Entra-corr | AD Privileged Identity Synced to Entra Cloud-Privileged Role | ⬜ | ✅ | ✅ |
| AD-ENTRA-002 | Entra-corr | Hybrid Synced Disabled / Non-Existent Cloud Counterpart | ⬜ | ✅ | ✅ |
| AD-ENTRA-003 | Entra-corr | Privileged AD Account Without Strong Cloud MFA | ⬜ | ✅ | ✅ |
| AD-ENTRA-004 | Entra-corr | Pass-Through / Federated Auth Posture | ⬜ | ✅ | ✅ |

POC total: **6 controls** in scope (AD-HEALTH-004, AD-PRIV-001, AD-PRIV-005, AD-KERB-001, AD-DELEG-001, AD-GPO-001) **plus** AD-SF-001 as the cross-module correlation showcase, satisfying `POC_V1_SCOPE.md` §5.3.

---

## 9. Privileged groups

Baseline list (POC + MVP):

| Group | Source | Notes |
|---|---|---|
| `Domain Admins` | well-known SID `*-512` | Per domain. |
| `Enterprise Admins` | well-known SID `*-519` | Forest root. |
| `Schema Admins` | well-known SID `*-518` | Forest root. |
| `Administrators` (builtin) | well-known SID `S-1-5-32-544` | Domain-local. |
| `Account Operators` | well-known SID `S-1-5-32-548` | Domain-local. |
| `Server Operators` | well-known SID `S-1-5-32-549` | Domain-local. |
| `Print Operators` | well-known SID `S-1-5-32-550` | Domain-local. |
| `Backup Operators` | well-known SID `S-1-5-32-551` | Domain-local. |
| `Replicator` | well-known SID `S-1-5-32-552` | Domain-local. |
| `Group Policy Creator Owners` | well-known SID `*-520` | Often risky. |
| `DnsAdmins` (if present) | named lookup | Frequent privilege-escalation vector. |
| Custom Tier 0 groups | per-engagement (Q-0053) | Consultant-defined. |

Rules:

- All members of these groups are upserted into `ad_privileged_group_membership` with direct/indirect tagging.
- Members are upserted into `Identity` with `is_privileged = true`; Tier 0 baseline groups also set `is_tier0 = true`.
- Nested groups are walked once on parse; the walk records the full nest path for traceability.

---

## 10. Service accounts

Definition (operational):

| Class | Detection rule |
|---|---|
| **SPN holder** | `servicePrincipalName` attribute non-empty on a user object (not computer). |
| **MSA** (Managed Service Account) | `objectClass = msDS-ManagedServiceAccount`. |
| **gMSA** (Group MSA) | `objectClass = msDS-GroupManagedServiceAccount`. |
| **Legacy service account (heuristic)** | All of: account name matches `svc[-_]*` / `service[-_]*` / `app[-_]*` patterns (configurable); `pwdLastSet` > 365 days; `dontExpirePassword = true`; never interactive logon. Heuristics are documented and adjustable per engagement. |

Risks evaluated:

| Risk | Detection |
|---|---|
| Kerberoastable | SPN holder + user (not gMSA) + RC4 enctype allowed. |
| Stale password | `pwdLastSet` > threshold (default 365 d). |
| `DontExpirePassword` set | flag in attribute. |
| Privileged service account | service-account class + member of any privileged group → `AD-PRIV-005`. |
| Service account in Tier 0 OU | direct presence in Tier 0 OU. |
| Service account with delegation | cross-reference `ad_delegation`. |
| Inactive service account | `LastLogonTimestamp` > threshold (default 180 d). |

POC focus: detection (`AD-PRIV-005`), Silverfort cross-reference (`AD-SF-002` — MVP).

---

## 11. Example finding payloads

The platform uses one shared `Finding` shape (`MODULE_ARCHITECTURE.md` §10). Module-specific data goes in `payload`. Three examples follow.

### 11.1 `AD-PRIV-005` Privileged Service Accounts

```json
{
  "id": "f1b8a3e4-…",
  "assessment_run_id": "…",
  "title": "Privileged service accounts detected with Kerberoastable hygiene gaps",
  "category": "ad.privileged",
  "module_id": "ad",
  "severity": "high",
  "risk_score": 78,
  "license_status": "licensed_enabled",
  "summary_internal": "3 service accounts (`svc_backup`, `svc_sql_db1`, `svc_appA`) are members of privileged groups. All three are SPN-holders with RC4 enctype allowed and `pwdLastSet` older than 12 months.",
  "summary_customer": "Three service accounts have administrative rights and rely on legacy authentication settings. They are an attractive target for credential theft via Kerberoasting.",
  "technical_detail": "## Affected accounts\n\n| Account | Groups | SPN count | Enctype | pwdLastSet | DontExpirePassword |\n|---|---|---|---|---|---|\n| svc_backup | Backup Operators, Domain Admins | 2 | RC4_HMAC_MD5 | 524 d | true |\n| svc_sql_db1 | Account Operators | 4 | RC4_HMAC_MD5 | 387 d | true |\n| svc_appA | Server Operators | 1 | RC4_HMAC_MD5 | 412 d | true |\n\nAll three accounts hold SPNs and are not gMSA; they are vulnerable to Kerberoasting.",
  "remediation": "1. Migrate to gMSA where the dependent service supports it.\n2. Remove from privileged groups (use service-account-specific groups with least privilege).\n3. Rotate password (≥ 25-character random) and set `msDS-SupportedEncryptionTypes` to AES-only.\n4. Compensating control: include in Silverfort service-account protection policy (see `AD-SF-002`).",
  "validation_method": "Re-run AD toolkit; the control should report 0 Kerberoastable privileged service accounts.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/service-accounts.json" },
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/privileged-groups.json" },
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/kerberos-config.json" }
  ],
  "identity_refs": [ "ident-svc_backup", "ident-svc_sql_db1", "ident-svc_appA" ],
  "correlation_refs": [
    { "kind": "control", "id": "AD-SF-002" },
    { "kind": "finding", "id": "bh-path-002", "note": "BloodHound path uses svc_appA" }
  ],
  "payload": {
    "accounts": [
      { "identity_id": "ident-svc_backup", "spn_count": 2, "enctype": "RC4_HMAC_MD5", "pwd_last_set_days": 524, "dontexpirepassword": true, "groups": ["Backup Operators", "Domain Admins"] },
      { "identity_id": "ident-svc_sql_db1", "spn_count": 4, "enctype": "RC4_HMAC_MD5", "pwd_last_set_days": 387, "dontexpirepassword": true, "groups": ["Account Operators"] },
      { "identity_id": "ident-svc_appA", "spn_count": 1, "enctype": "RC4_HMAC_MD5", "pwd_last_set_days": 412, "dontexpirepassword": true, "groups": ["Server Operators"] }
    ]
  }
}
```

### 11.2 `AD-DELEG-001` Unconstrained Delegation

```json
{
  "id": "a93d…",
  "title": "Unconstrained delegation enabled on a non-DC principal",
  "category": "ad.delegation",
  "module_id": "ad",
  "severity": "high",
  "risk_score": 81,
  "license_status": "licensed_enabled",
  "summary_internal": "`svc_appA` has `TrustedForDelegation = true` and is not a domain controller. Any service ticket sent to it can be relayed to any service in the domain.",
  "summary_customer": "A service account is configured so that any user authenticating through it can be impersonated to any other service in the domain. This is a high-impact misconfiguration.",
  "technical_detail": "## Principal\n\n- `svc_appA` (SID …): user object\n- `TrustedForDelegation`: true\n- Member of: `Server Operators`\n- Last logon: 3 d ago\n\n## Why this matters\n\nUnconstrained delegation lets the principal extract the TGT of any user who authenticates to it. Combined with privileged-group membership, this is a direct path to Domain Admin.",
  "remediation": "1. Switch to Constrained Delegation (`msDS-AllowedToDelegateTo`) listing only the required SPNs.\n2. If business need cannot be met, switch to Resource-Based Constrained Delegation on the resource side.\n3. Otherwise remove delegation entirely.\n4. Compensating control: Silverfort policy enforcing MFA on access by `svc_appA` (see `AD-SF-003`).",
  "validation_method": "Re-run AD toolkit; `delegation.json` should not list `svc_appA` as unconstrained.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/delegation.json" },
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/domain-controllers.json" }
  ],
  "identity_refs": [ "ident-svc_appA" ],
  "correlation_refs": [
    { "kind": "control", "id": "AD-SF-003" },
    { "kind": "finding", "id": "bh-path-001", "note": "BloodHound path leverages this delegation" }
  ],
  "payload": {
    "principal_identity_id": "ident-svc_appA",
    "delegation_type": "unconstrained",
    "is_dc": false,
    "groups": ["Server Operators"]
  }
}
```

### 11.3 `AD-SF-001` Tier 0 Identities Covered by Silverfort Policy

```json
{
  "id": "c2e1…",
  "title": "Tier 0 identities not fully covered by Silverfort MFA policy",
  "category": "ad.silverfort-correlation",
  "module_id": "ad",
  "severity": "high",
  "risk_score": 76,
  "license_status": "licensed_enabled",
  "summary_internal": "Of 16 Tier 0 identities (Microsoft baseline + customer additions), 11 are referenced by at least one Silverfort policy enforcing MFA. 5 are not covered. 2 of the uncovered are `Domain Admins` members.",
  "summary_customer": "Five of your top-tier privileged identities are not currently protected by your Silverfort MFA policy. This is the most impactful gap in your privileged-access posture.",
  "technical_detail": "## Coverage matrix\n\n| Identity | AD group(s) | Silverfort policy | Coverage |\n|---|---|---|---|\n| alice.admin | Domain Admins, Enterprise Admins | sf-policy-priv-mfa | ✅ |\n| bob.admin | Domain Admins | — | ❌ |\n| svc_appA | Server Operators | — | ❌ |\n| … | … | … | … |\n\n5 Tier 0 identities uncovered; 2 in `Domain Admins`.",
  "remediation": "1. Extend Silverfort's privileged-MFA policy to all Tier 0 identities listed in this finding.\n2. Align the Silverfort policy scope with the Tier 0 list defined in this engagement (Q-0053).\n3. Verify alerting on uncovered authentications.",
  "validation_method": "Re-export Silverfort policies + re-run AD toolkit; AD-SF-001 should report 100% coverage.",
  "state": "new",
  "customer_visibility": "internal_only",
  "evidence_refs": [
    { "evidence_type": "ad-toolkit-zip", "file": "collectors/privileged-groups.json" },
    { "evidence_type": "silverfort-export-bundle", "file": "policies.json" }
  ],
  "identity_refs": [ "ident-bob.admin", "ident-svc_appA", "…" ],
  "correlation_refs": [
    { "kind": "correlation_rule", "id": "CORR-AD-SF-001" }
  ],
  "payload": {
    "tier0_total": 16,
    "covered": 11,
    "uncovered": 5,
    "uncovered_da_members": 2,
    "uncovered_identity_ids": [ "ident-bob.admin", "ident-svc_appA", "ident-…", "ident-…", "ident-…" ]
  }
}
```

---

## 12. Kerberos / delegation control logic summary

Quick reference for evaluators:

| Trigger | Control | Logic |
|---|---|---|
| `accounts_supporting_rc4` > 5% of users | AD-KERB-001 | `fail` |
| `DONT_REQ_PREAUTH` on any account | AD-KERB-002 | `partial` or `fail` (privileged) |
| `max_tgt_lifetime_hours` > 10 | AD-KERB-003 | `partial` (≤ 20) / `fail` (> 20) |
| `krbtgt_password_last_set_days` > 180 | AD-KERB-004 | `partial` (180–365) / `fail` (> 365) |
| `TrustedForDelegation = true` on non-DC | AD-DELEG-001 | `fail` (Tier 0) / `partial` (non-Tier 0) |
| `msDS-AllowedToDelegateTo` crosses tier | AD-DELEG-002 | `partial` / `fail` |
| `msDS-AllowedToActOnBehalfOfOtherIdentity` undocumented | AD-DELEG-003 | `partial` / `fail` |
| Privileged accounts without `NOT_DELEGATED` | AD-DELEG-004 | proportional |

All thresholds are configurable at engagement setup (MVP). POC uses defaults.

---

## 13. NTLM — detection mechanics

POC: design only. MVP detection sources:

- **PowerShell collector**: domain GPO state of `LmCompatibilityLevel`, `Restrict NTLM` settings, NTLM auditing on/off — extracted from `gpo-summary.json`.
- **Event log evidence (MVP)**: a future collector extracts a *summary* of NTLM event-log entries from DCs (event IDs 8001–8004 for NTLM audit, etc.). Only **counts and source-host counts** — never raw event payloads (data minimization, `SECURITY_AND_GDPR.md` §13.3).

No NTLM hashing material, no challenge/response bytes, no decoded session keys — ever.

---

## 14. GPO / OU — evaluated dimensions

From `gpo-summary.json`:

| Dimension | What it captures | Used by |
|---|---|---|
| Anonymous-access settings | `EveryoneIncludesAnonymous`, anonymous SAM access, anonymous shares | AD-GPO-001 |
| Restricted-groups assignments | local group memberships injected by GPO | AD-GPO-002 |
| Password-policy GPOs | scoped weakening of password baseline | AD-GPO-003 |
| GPO ACLs | who can edit Tier 0 GPOs | AD-GPO-004 |
| NTLM-allow / restrict | LmCompatibilityLevel, Restrict-NTLM | AD-NTLM-001/002/003 |
| Tier 0 OU scope | which OUs receive Tier 0 GPOs | AD-PRIV-006, AD-GPO-004 |

The module does **not** ingest full GPO XML (data minimization). Deep GPO inspection remains a consultant workshop deliverable.

---

## 15. AD CS readiness (MVP scope)

AD CS is **MVP**, not POC. Documented here so the design is ready.

| Aspect | Approach |
|---|---|
| Evidence | A future AD toolkit collector (`adcs-templates.json`) enumerates certificate templates, EKUs, enrollment permissions, manager-approval flags, and per-template SAN policies. |
| Controls | `AD-ADCS-001` Template Enumeration; `AD-ADCS-002` Templates with Client Authentication + Subject-Supplied-In-Request (ESC1); `AD-ADCS-003` Enrollment Agent Templates (ESC2); `AD-ADCS-004` Vulnerable CA ACLs (ESC4–5); `AD-ADCS-006` NTLM-Only HTTP Web Enrollment (ESC6/8); `AD-ADCS-007` PKINIT pre-auth weakness (ESC9). |
| BloodHound overlap | BloodHound's AD CS edge support (later versions) may also represent these paths; the AD module focuses on **configuration audit** rather than path detection. |
| Tier | All AD CS controls are MVP minimum; AD CS not enumerated in POC. |

---

## 16. DC health metrics

Collected by the toolkit; surfaced by the module:

| Metric | Source | Control |
|---|---|---|
| Per-DC FSMO role list | `domain-controllers.json` | AD-HEALTH-002 |
| Replication partner success rate | `replication-health.json` | AD-HEALTH-001 |
| Oldest replication failure age | `replication-health.json` | AD-HEALTH-001 |
| DC OS major version | `domain-controllers.json` | AD-HEALTH-002 (failure if EoL) |
| AD recycle bin enabled | `ad-health.json` | AD-HEALTH-002 (warning if off, MVP) |
| Tombstone lifetime | `ad-health.json` | informational |
| Time skew | `ad-health.json` | AD-HEALTH-003 |
| DNS zone state | `dns-health.json` | AD-HEALTH-003 |

---

## 17. Backup / recovery

POC: out of scope.
MVP: a `backup-recovery.json` collector ingests:

- AD recycle bin state (already in `ad-health.json`).
- Last system-state backup of any DC (where reachable via remoting — best-effort).
- DSRM password age (heuristic; documented as low-confidence).
- AD object tombstone aging vs. backup retention.

Controls: `AD-BACKUP-001` Recycle Bin Enabled, `AD-BACKUP-002` DSRM Password Hygiene, `AD-BACKUP-003` System-State Backup Recency.

Tier: MVP for all. Full Product adds integration with backup vendors via consultant evidence (Veeam, Cohesity, etc.).

---

## 18. AD + Silverfort correlation flow

Recap of `AD-SF-*` (§8.7) as data flow:

```
AD evidence  ──▶ AD module parses ──▶ ad_privileged_group_membership / ad_service_account / ad_delegation
                                       │
                                       └──▶ upserts Identity rows (is_privileged, is_tier0)

Silverfort evidence ──▶ SF module parses ──▶ sf_policy / sf_policy_coverage / sf_service_account / sf_entity_risk
                                              │
                                              └──▶ upserts Identity rows (matched by SID/UPN/sAMAccountName)

AD-SF-* controls (in AD module) read both via core view:
  - Tier 0 identity set         ← AD module
  - Silverfort coverage set     ← SF module
  - Match on Identity.id (canonical)
  - Emit AD-side finding with correlation_refs to SF evidence
```

| Control | Identity flow | Silverfort flow |
|---|---|---|
| AD-SF-001 | Tier 0 identities (AD-derived) | Identities referenced by enforcing policies (SF-derived) |
| AD-SF-002 | Privileged service accounts (AD-PRIV-005) | Identities in `sf_service_account` protection policy |
| AD-SF-003 | Unconstrained delegation principals (AD-DELEG-001) | Policy coverage of those principals |
| AD-SF-004 | Stale privileged accounts (AD-PRIV-002) | `sf_entity_risk` cohort |

No Python imports between modules — read-only via core `view` (`MODULE_ARCHITECTURE.md` §11).

---

## 19. AD + Entra correlation flow

Hybrid-identity correlation is driven by the canonical `Identity` (`MODULE_ARCHITECTURE.md` §8). The Entra module sets `azure_object_id` and `onPremisesImmutableId`. The AD module sets `sid`, `sam_account_name`, `object_guid`. The deterministic linker matches; ambiguous matches surface for consultant review (no silent merging — `MODULE_ARCHITECTURE.md` §8 rule 5).

| Control | What it joins | Identity key |
|---|---|---|
| AD-ENTRA-001 | AD privileged group ⟷ Entra cloud role assignment | matched Identity rows |
| AD-ENTRA-002 | AD account presence ⟷ Entra cloud account presence | onPremisesImmutableId ↔ ObjectGUID derivation |
| AD-ENTRA-003 | AD-privileged hybrid identity ⟷ Entra authentication methods | matched Identity rows |
| AD-ENTRA-004 | AD Tier 0 identities ⟷ Entra hybrid auth mechanism (tenant-level) | tenant + Tier 0 |

The headline cross-module demo finding `CORR-BH-ENTRA-001` (`MODULE_ARCHITECTURE.md` §11.3) consumes:

- AD: privileged-group membership, delegation, Tier 0 flag.
- BloodHound: path from a low-tier identity to the same Identity, with deterministic explanation.
- Entra: cloud-privileged role assignment on the same Identity (synced).
- Silverfort (optional): coverage state for the Identity.

The AD module's role is to expose the AD facets via normalized data and Identity flags; the joined finding is produced by the core correlation orchestrator.

---

## 20. Dashboard

AD module page composition uses **only existing components** from `UI_DESIGN_DIRECTION.md` §3 (no new patterns), per `WORKING_APPROACH.md` §11 rule 4.

| Layout slot | Component | Content (AD) |
|---|---|---|
| Page header | `PageHeader` | "Active Directory — <customer>" + supporting sentence + secondary actions (Upload evidence · Re-evaluate) |
| Row 1 (status cards) | 5 × `StatusCard` | Health · Privileged · Kerberos · Delegation · GPO (`UI_DESIGN_DIRECTION.md` §3.3 — same pattern as `POC_V1_SCOPE.md` §4 step 4) |
| Row 2 (coverage) | `RingChart` | Control coverage: passing / failing / not_applicable / unknown |
| Row 2 (priority list) | `PriorityList` | Top AD findings (severity icon + title + subtitle: `<control-id> · <n accounts/principals affected> · <license-status>`) |
| Row 3 (optional) | `Table` (privileged groups) + `RiskBarList` (Tier 0 reachability indicators) | Per `UI_DESIGN_DIRECTION.md` §4.3 |
| Right rail | `ActionPanel` | "Upload evidence" / "Re-evaluate" actions |
| Drill-down | `Drawer` with `FindingDetail` | Evidence refs · correlation chips · visibility selector · remediation (`UI_DESIGN_DIRECTION.md` §13 / §15 style) |

License-aware badging on each `StatusCard` uses the `licensed`, `licensed-disabled`, `not-licensed`, etc. variants from `UI_DESIGN_DIRECTION.md` §3.3.

No graph visualization on the AD page (BloodHound owns path UI; AD-side cross-references appear as **correlation chips** on findings, per `UI_DESIGN_DIRECTION.md` §13).

---

## 21. Reporting

The AD module ships two Jinja partials under `modules/ad/reports/` (`MODULE_ARCHITECTURE.md` §4):

### 21.1 Internal Detailed

Section order:

1. AD-at-a-glance: domain/forest functional levels, DC count, Tier 0 boundary definition for this engagement, PingCastle composite score.
2. Control results table (all evaluated AD controls; status + license_status + severity + score contribution).
3. Findings: one block per finding with full `summary_internal` + `technical_detail` + `remediation` + `validation_method` + evidence refs.
4. Privileged groups appendix (membership tables, redacted per visibility rules — internal report keeps full).
5. Service accounts appendix.
6. Delegation appendix.
7. Kerberos posture appendix.
8. GPO findings appendix.

All `internal_only` findings included.

### 21.2 Customer Summary

Section order:

1. AD overview in customer language ("Your Active Directory baseline").
2. Two-scores card (Current License Score / Target Posture Score / Opportunity) for the AD module.
3. Top customer-visible AD findings (only `customer_summary` or `customer_full`). For `customer_summary`, `summary_customer` shown only. For `customer_full`, `summary_customer` + `technical_detail` shown.
4. License-aware framing of any preferred capabilities (e.g., Silverfort as compensating control).
5. Suggested next steps (executive level).

No raw SID, UPN, sAMAccountName lists in `customer_summary`. `customer_full` may include identifier lists where the consultant decides they are appropriate (`SECURITY_AND_GDPR.md` §7.4).

---

## 22. POC / MVP / Full scope table

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| `ad-toolkit-zip` parser | ✅ | ✅ | ✅ |
| `pingcastle-xml` parser (standalone + embedded) | ✅ | ✅ | ✅ |
| Normalized AD model (§6) | ✅ | ✅ | ✅ |
| Identity contributions (SID/UPN/sAMAccountName/ObjectGUID) | ✅ | ✅ | ✅ |
| Tier 0 baseline + per-engagement override (Q-0053) | ✅ | ✅ | ✅ |
| AD-HEALTH-* | 1 control (AD-HEALTH-004) | all | all |
| AD-PRIV-* | 2 controls (AD-PRIV-001, AD-PRIV-005) | all | all |
| AD-KERB-* | 1 control (AD-KERB-001) | all | all |
| AD-DELEG-* | 1 control (AD-DELEG-001) | all | all |
| AD-GPO-* | 1 control (AD-GPO-001) | all | all |
| AD-NTLM-* | ⬜ | all | all |
| AD-SF-* | 1 control (AD-SF-001) | all | all |
| AD-ENTRA-* | ⬜ design | all | all |
| AD-ADCS-* (AD CS readiness) | ⬜ | ✅ | ✅ |
| Backup / recovery controls | ⬜ design | ✅ | ✅ |
| BloodHound correlation consumption | ✅ via core view | ✅ | ✅ |
| Internal Detailed report section | ✅ | ✅ | ✅ |
| Customer Summary report section | ✅ | ✅ | ✅ |
| Module dashboard (composed from existing components) | ✅ | ✅ | ✅ |
| Live AD collector (vs offline toolkit) | ⬜ | ⬜ | 🟡 only if specifically required; toolkit-first remains standard |
| Per-engagement Tier 0 override UI | ⬜ design | ✅ | ✅ |
| Thresholds configurable in engagement setup | ⬜ defaults only | ✅ | ✅ |

---

## 23. Risks and questions

### 23.1 AD-specific risks

| Risk | Mitigation |
|---|---|
| Tier 0 boundary disagreement (Q-0053) | Surface the boundary definition explicitly on every Tier 0 control's finding ("Tier 0: Microsoft baseline + customer-additions: …"); record the per-engagement Tier 0 list in the assessment run. |
| PingCastle version drift | `pingcastle.engine_version` recorded in `manifest.json`; AD module logs unsupported versions and downgrades affected controls to `unknown` rather than misreporting. |
| Toolkit version drift | Module manifest declares accepted `toolkit_version` range; upload validation rejects out-of-range bundles. |
| Customer disputes a privileged group definition | Privileged group baseline is documented; consultant can extend (additions) but cannot remove well-known SIDs from the Tier 0 baseline without an explicit decision logged in the engagement notes. |
| Service-account heuristics misclassify | Heuristic rules are documented in `collection-log.txt` and adjustable per engagement. False positives surface as `partial`, not `fail`. |
| Identity ambiguity (two domains, same sAMAccountName) | Linker surfaces ambiguous matches for consultant confirmation (`MODULE_ARCHITECTURE.md` §8 rule 5); the AD module does not silently merge. |
| Customer's PingCastle XML contains real names embedded in rule explanations (PingCastle may include hostnames) | Internal-only by default; `customer_full` framing strips host detail where the rule allows; otherwise consultant chooses. |
| Cross-module correlation produces stale findings between runs | Findings are tied to an assessment run; the next run re-evaluates with fresh evidence (`MODULE_ARCHITECTURE.md` §3). |
| Synthetic AD ZIP is unconvincing (R-0009) | Synthetic data designed to mirror real-world risks across all six POC controls; demo journey rehearsed (`POC_V1_SCOPE.md` §10). |
| AD CS scope inflation | AD CS controls explicitly MVP; consultant questions during demo are answered "MVP scope". |

### 23.2 Open questions (carried verbatim)

From `OPEN_QUESTIONS.md` — AD-relevant subset:

- **Q-0052 | POC | Kristof** — PingCastle: do we always require a PingCastle run as part of evidence, or only "if available"? *Why it matters:* completeness of AD controls.
- **Q-0053 | POC | Kristof** — Tier 0 boundary: do we follow Microsoft's Enterprise Access Model definition strictly, or accept a customer-specified Tier 0 list per engagement? *Why it matters:* control results and BloodHound target set.

Related toolkit questions (`AD_TOOLKIT_DESIGN.md` §18): Q-0050, Q-0051.

---

*Last updated: 2026-05-15. Phase: Module deep dive #1 (Stage 3, Cycle 3).*
