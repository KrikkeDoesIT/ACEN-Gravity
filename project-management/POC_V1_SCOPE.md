# POC_V1_SCOPE.md

> The exact, bounded scope of POC V1. Authoritative answer to "is this in POC?". When in doubt, the answer is **no** — and the item moves to `TASKS.md` tagged `mvp` or `full`.

---

## 1. Goal

> **Validate that a single modular assessment platform — built on AD, BloodHound, Silverfort, and Entra modules — can produce a coherent, license-aware, ACEN-branded identity-security story for ACEN management, on synthetic data, in time for a go/no-go decision on MVP investment.**

This goal is **not**:
- A pilot for any specific customer.
- A delivery vehicle for a real engagement.
- An MVP with mocked auth.

---

## 2. What POC V1 must prove

| # | Proof | Demo evidence |
|---|---|---|
| 1 | The concept is valuable | A live demo presentable in ≤ 20 minutes that elicits "I get it" from a non-technical executive |
| 2 | The modular platform model works | Same screens, same finding shape, same publishing flow, across all four modules |
| 3 | AD + BloodHound + Silverfort + Entra fit one shared model | One data model is enough; no module-specific hacks in core |
| 4 | License-aware logic is understandable | At least one Entra and one Silverfort control visibly use license-aware status; demo viewer can explain it in one sentence |
| 5 | ACEN brand direction works for an executive product | UI passes brand owner review (D-0010, Q-0110, Q-0111) |
| 6 | Findings, evidence, remediation, reporting can follow a repeatable workflow | The whole demo journey is one click chain, not a montage of disconnected screens |
| 7 | A BloodHound / SharpHound ZIP produces a critical path finding **without AI** | Demo shows the analyzer step-by-step explanation derived from deterministic logic (D-0005) |
| 8 | The team can decide whether to invest in MVP | Cycle 7 produces a signed go/no-go |

---

## 3. Personas in POC

Three personas, one role-switcher (A-0013):

| Persona | Logs in as | Sees |
|---|---|---|
| **ACEN Consultant / Security Engineer** | "Consultant" (default) | Full platform. All modules. Internal-only details. Publishing controls. |
| **Customer CISO / Executive** | "Customer Executive" | Compressed nav. Only published items at `customer_summary` or `customer_full`. Top-3 findings. Reports. |
| **Customer IT / Security Lead** | "Customer IT Lead" | Same data as Executive, technical detail allowed (`customer_full`). Per-finding remediation guidance. |

A fourth "Platform Admin" role exists for setup only (creating the demo customer + engagement). Not part of the demo journey.

---

## 4. Demo journey (end-to-end)

> This is the single sequence we rehearse for management review. Every backlog item exists to support a step in this journey.

```
Step 1.  Consultant logs in (role = Consultant).
Step 2.  Picks customer "Contoso Corp" → engagement "Q2 2026 Identity Security Review" → assessment run "2026-05-15 Baseline".
Step 3.  Lands on Overview dashboard:
         - One H1: "Contoso Corp · Identity Security Posture".
         - Two-scores card: Current License Score / Target Posture Score (with Opportunity gap).
         - Top-3 findings strip.
         - Module status row: AD · BloodHound · Silverfort · Entra (each: status pill, last-evidence timestamp, mini score).
Step 4.  Drills into "AD" module page:
         - Module overview: 4–5 status cards (Health, Privileged, Kerberos, Delegation, GPO).
         - Donut: control coverage (passing / failing / not applicable / unknown).
         - Priority list: top AD findings.
         - Drills into a finding (e.g., AD-PRIV-005 Privileged Service Accounts) → detail drawer with evidence reference, severity, license-aware status, remediation guidance, customer-visibility selector.
Step 5.  Drills into "BloodHound" page:
         - Same layout: status cards (Tier 0 reachability, Privileged paths, ACL abuse, Delegation).
         - Ranked critical paths (top 5): source → ... → Tier 0 target, with length, severity, deterministic explanation.
         - Opens a path: step-by-step explanation, evidence reference, **correlation chips** (AD finding link, Silverfort coverage gap, Entra hybrid admin overlap).
Step 6.  Drills into "Silverfort" page:
         - Same layout: status cards (Policy Coverage, Privileged Enrollment, Service Accounts, Entity Risk).
         - Priority list of coverage gaps.
         - Opens "AD Privileged Account Silverfort Coverage" → shows the gap, the affected accounts, and the linked BloodHound paths covered/uncovered.
Step 7.  Drills into "Entra" page:
         - Same layout: status cards (Licensing, Conditional Access, Privileged Roles, Apps, Guests, Hybrid).
         - **Visible license-aware UI**: one card flagged "Licensed but disabled" (e.g., legacy auth still allowed) and one flagged "Not licensed (Entra ID P2 required)" — the latter does not penalize the Current Score.
         - Opens an Entra-hybrid finding linking back to an AD principal.
Step 8.  Returns to Findings workspace:
         - Filters by severity Critical/High.
         - Sees the cross-module correlation finding:
           "BloodHound: path from [contractor account] → DA via ACL abuse →
            AD: account is a privileged service account →
            Silverfort: no policy coverage →
            Entra: synced to Global Admin role."
         - Sets `customer_visibility = customer_summary` on this finding.
Step 9.  Opens Reports:
         - Generates "Internal Detailed" report (HTML).
         - Generates "Customer Summary" report (HTML). Shows the same correlation finding rendered for executives (no SID/UPN exposure, no graph internals).
         - (Stretch) Exports PDF.
Step 10. Publishes the customer report (modal: confirm visibility scope; consultant note).
Step 11. Switches role → "Customer Executive".
Step 12. Lands on compressed dashboard:
         - Top-3 finding cards (customer language).
         - Two-scores card with Opportunity gap.
         - Report list with only the published Customer Summary.
Step 13. Opens the correlation finding → sees the executive framing, can read the report.
Step 14. Switches role → "Customer IT Lead".
Step 15. Sees same items + technical detail; opens remediation guidance for the correlation finding.
Step 16. Returns to Consultant role.
Step 17. Opens Audit log: full trace of upload → parse → evaluate → finding state → publish → report → role-switch events.
Step 18. Closes demo with the two-scores card on screen.
```

Total elapsed (rehearsed): **≤ 20 minutes**. Demo script lives in `TASKS.md` T-6102 and will be a separate `DEMO_SCRIPT.md` later.

---

## 5. POC V1 features (in scope)

### 5.1 Platform shell
- Login screen with role + customer picker (no real auth).
- Top nav with customer / engagement / assessment-run picker.
- Side nav with the 8 entries (Overview / AD / BloodHound / Silverfort / Entra / Findings / Reports / Audit).
- ACEN-branded UI shell.

### 5.2 Core lifecycle
- Customer, engagement, assessment-run entities.
- Evidence upload (drag-and-drop, file picker; ZIP/JSON/XML).
- Evidence validation (size cap, expected file types, manifest read, hash).
- Synchronous parse-on-upload (queue-ready service layer).
- Control evaluation per module against the parsed evidence.
- Finding lifecycle (`new` → `triaged` → `published` → `retest_requested` → `closed`; POC supports `new` → `triaged` → `published`).
- Identity entity (canonical join key across modules).
- License catalog + capability mapping (small but real).
- Audit log entries for the demo events.
- Two scores per module + engagement (Current License Score, Target Posture Score, Opportunity).

### 5.3 AD module
- AD toolkit ZIP parser (manifest + JSON files + PingCastle XML).
- At least 6 controls from these groups, mixed: Health (1), Privileged (2), Kerberos (1), Delegation (1), GPO (1). Detailed list in `AD_MODULE_DESIGN.md`.
- One AD finding visibly linked to a BloodHound path.
- One AD finding visibly linked to a Silverfort coverage gap.

### 5.4 BloodHound Analyzer
- SharpHound CE ZIP parser (users/groups/computers/ous/gpos/containers/domains/acls).
- In-memory graph (networkx-based).
- Deterministic Tier 0 identification.
- Deterministic shortest-path detection to Tier 0.
- At least 3 path categories: Privilege escalation via group nesting, ACL abuse, Delegation (unconstrained).
- Template-based step-by-step explanations.
- Risk scoring per path (deterministic; documented).
- Correlation hooks (AD finding ref, Silverfort coverage flag, Entra hybrid admin flag).

### 5.5 Silverfort module
- Manual evidence parser: policies JSON, service-account insights JSON, enrollment JSON, entity risk JSON.
- At least 5 controls (Connector design stub, Policy coverage, Privileged enrollment, Service-account discovery coverage, AD Tier 0 coverage correlation).
- Connector design documented; no live API calls.

### 5.6 Entra module
- Entra Graph JSON dump parser (users, groups, roles, role assignments, CA policies, authentication methods, applications, risky users (where licensed)).
- At least 6 controls: License & capability detection, CA baseline coverage, Privileged user MFA enforcement, Legacy auth blocked, Hybrid privileged identity overlap, Long-lived client secrets.
- Visible license-aware UI:
  - One control surfaces `licensed_disabled` (e.g., legacy auth not blocked).
  - One control surfaces `not_licensed` (e.g., Identity Protection not owned), with no score penalty on Current Score.

### 5.7 Findings workspace
- Filterable list (severity, module, customer-visibility, license-status).
- Sort by severity, risk score, date.
- Detail drawer (lazy load).
- Customer-visibility selector + audit log capture.
- Cross-module correlation chip(s).

### 5.8 Evidence drawer
- Linked from any finding.
- Shows the file name, hash, upload timestamp, parsed-by module, normalized excerpt.
- Customer visibility flag visible.

### 5.9 Reports
- Internal Detailed (HTML): all findings, all evidence refs, scores, license context.
- Customer Summary (HTML): only customer-visible findings; executive framing; license-aware framing.
- (Stretch) PDF via Playwright.

### 5.10 Audit log
- View accessible to Consultant role.
- Records: login (role-switch), upload, parse, evaluate, finding state change, visibility change, report generated, report published.

---

## 6. POC V1 features that are **mocked**

These are *visible* in the UI but *not implemented end-to-end*. They exist to show the platform direction without burning POC budget.

- **Authentication** — replaced by role-switcher (A-0013). Audit log captures the chosen identity.
- **Multi-tenant isolation** — single tenant only; UI shows the model.
- **Live connectors** — AD live, Microsoft Graph, Silverfort API. All design-only, with status pills "Connector not configured (POC)".
- **Encryption at rest / secrets vault** — designed, not implemented.
- **Retest workflow** — finding states `retest_requested` and `closed` exist but are not part of the demo journey.
- **Customer self-service portal** — represented by the role-switcher view, not by a true separate portal.
- **Background jobs** — synchronous parsing; UI shows a progress indicator only.
- **PDF rendering** — stretch goal (HTML acceptable for management review).

---

## 7. POC V1 features that are **excluded**

Off-limits for POC. Tagged `mvp`/`full` in `TASKS.md`.

- Advisory modules.
- Defender XDR / Defender for Endpoint / Defender for Office 365 / Defender for Cloud Apps / Defender for Cloud.
- Purview / Intune / Mail Security / General M365 Posture / General Hybrid Identity Security.
- Imprivata / Cato / Illumio modules.
- Real customer onboarding flows.
- Customer self-service portal hardening.
- Billing / metering / commercial features.
- Continuous monitoring / scheduled re-collection.
- AI-based language polish.

---

## 8. Data assumptions for POC

- **One fictional customer** "Contoso Corp" (Q-0011 may extend to two).
- **Synthetic datasets** authored by the team (D-0011, A-0012):
  - **AD toolkit ZIP**: synthetic AD forest with ~50 users, ~10 groups, ~3 DCs, mixed kerberos/delegation/GPO issues.
  - **PingCastle XML**: synthetic, score ~ 70/100, with at least 5 indicators reflecting toolkit findings.
  - **SharpHound ZIP**: synthetic graph with ≥ 3 critical paths (group nesting, ACL abuse, unconstrained delegation).
  - **Silverfort export**: synthetic policies, service-account insights, enrollment, entity risk; with intentional coverage gaps overlapping AD/BH evidence.
  - **Entra JSON dump**: synthetic tenant with **E3 + standalone Entra ID P1, no P2** (so Identity Protection + PIM controls demonstrate `not_licensed` cleanly), partial CA coverage, one over-permissioned enterprise app, one synced hybrid admin.
- **License catalog (POC)**: small set — E3, E5, EMS E3/E5, Entra ID P1, Entra ID P2, Defender for Identity, Silverfort. Q-0070 confirms.
- **No real customer data** in repo or demo.

---

## 9. POC V1 screens

Inventoried here; design in `UI_DESIGN_DIRECTION.md`.

| ID | Screen | Purpose |
|---|---|---|
| S-01 | Login (role + customer picker) | Choose persona for the demo |
| S-02 | Overview dashboard | Persona-aware top-level view |
| S-03 | Customer page | Engagement list + last assessment summary |
| S-04 | Engagement page | Assessment-run list + status |
| S-05 | Assessment-run page | Module strip + recent activity |
| S-06 | AD module page | Module status cards + priority list |
| S-07 | BloodHound module page | Ranked critical paths + (POC: optional small graph stub) |
| S-08 | Silverfort module page | Coverage status + priority gaps |
| S-09 | Entra module page | License-aware status + priority findings |
| S-10 | Findings workspace | Filterable findings list |
| S-11 | Finding detail drawer | Evidence ref + correlation chips + visibility + remediation |
| S-12 | Evidence drawer | Artifact view + visibility |
| S-13 | Reports list + Report preview | HTML report viewer |
| S-14 | Publishing modal | Visibility, consultant note, confirm |
| S-15 | Audit log | Append-only event view |
| S-16 | Settings / role-switcher (POC only) | Switch persona |

---

## 10. AD demo

- Upload synthetic AD toolkit ZIP.
- Show parsed health + privileged + kerberos data.
- Evaluate controls: e.g., AD-PRIV-005 Privileged Service Accounts → finding linked to a BH path; AD-DELEG-001 Unconstrained Delegation → finding linked to a BH path; AD-SF-001 Tier 0 Silverfort Coverage → correlation finding.

## 11. BloodHound demo

- Upload synthetic SharpHound ZIP.
- Identify Tier 0.
- Detect ≥ 3 paths covering ≥ 3 categories.
- Rank, score, explain.
- One path's explanation includes a correlation chip linking to an AD finding and a Silverfort coverage gap.

## 12. Silverfort demo

- Upload synthetic Silverfort export.
- Evaluate policy coverage and service-account insight controls.
- One control surfaces a Tier 0 coverage gap that explicitly references the BloodHound path.

## 13. Entra demo

- Upload synthetic Entra JSON.
- License catalog detects: **E3 + standalone Entra ID P1, no Entra ID P2, owns Silverfort**. (Earlier draft said "E5 + EMS E5 + Entra ID P1, no P2", which is internally inconsistent because E5 already bundles P2 — corrected here so the demo's `not_licensed` story for Identity Protection / PIM stays clean. Aligns with the worked example in `ENTRA_MODULE_DESIGN.md` §4.4.)
- One control surfaces `licensed_disabled` (legacy auth) → score penalty on Current Score.
- One control surfaces `not_licensed` (Identity Protection) → contributes to Opportunity gap, no penalty on Current Score.
- One Hybrid Identity finding overlaps with the AD/BH path (consultant sees the chain explicitly).

## 14. License-aware demo

- The Entra module page shows the visible license-aware UI states.
- Two-scores card on every module and on the overview.
- Opportunity card explains "what you could unlock with [Entra ID P2]" in one sentence.

## 15. Reporting demo

- Generate Internal Detailed.
- Generate Customer Summary.
- Compare side-by-side or sequentially in the demo.
- (Stretch) PDF download.

## 16. Security boundaries in POC

- No auth → role-switcher (A-0013).
- No real data (D-0011).
- `customer_visibility` default = `internal_only` everywhere.
- Audit log captures all consequential actions.
- Evidence drawer enforces visibility flag in the UI.
- Reports enforce visibility filtering before rendering.

## 17. Success criteria (POC V1)

- [ ] Demo journey (§4) runs end-to-end on synthetic data without manual hacks.
- [ ] All ≥ 4 module success criteria met (≥ 6 AD controls, ≥ 3 BH paths in ≥ 3 categories, ≥ 5 SF controls, ≥ 6 Entra controls).
- [ ] ≥ 1 cross-module correlation finding visible.
- [ ] ≥ 1 license-aware control visible per Silverfort and Entra.
- [ ] Reports (Internal + Customer) generated and visibly differ in content.
- [ ] Audit log contains entries for every demo-journey event.
- [ ] UI passes brand owner review (Q-0110, Q-0111 resolved).
- [ ] Management review held; go/no-go decision recorded.

## 18. Risks (POC-specific)

Tracked in `RISKS.md`. POC-specific:

- **R-0001** POC silently becomes MVP — primary risk; mitigated by tier discipline.
- **R-0009** Demo data unconvincing — mitigated by realistic synthetic data with explicit cross-module overlap.
- **R-0010** Postgres not on demo workstation — docker-compose provided.

## 19. What must be decided before MVP

When POC is approved, the following must be decided before MVP build starts:

- Q-0020 First MVP connector to ship.
- Q-0030 Customer self-service or consultant-presented.
- Q-0040 / Q-0041 Real evidence storage and DPO sign-off.
- Q-0043 Authentication model.
- Q-0071 Authoritative licensing source.
- Q-0090 Silverfort API validation outcome.
- Q-0100 / Q-0101 Reporting variants.
- Q-0120 Next 2–3 future modules.

## 20. Acceptance criteria

Per major area:

- **Lifecycle**: uploading a recognized file produces a stored artifact, normalized evidence, evaluated controls, and findings without manual intervention.
- **Modules**: parsers must produce normalized objects matching the module's schema; controls must produce results with severity, status, license-aware status, and at least one human-readable explanation.
- **Correlation**: cross-module correlation finding must reference at least 2 modules and produce a single finding entity (not multiple).
- **License-aware**: `not_licensed` controls must never reduce Current License Score; `licensed_disabled` controls must always reduce Current License Score by their weight.
- **Publishing**: setting `customer_visibility` updates the UI immediately; report rendering uses the latest visibility state at render time; audit log records the change.
- **Reports**: Internal and Customer reports differ by at least the number of customer-only findings + technical-detail blocks suppressed in Customer report.
- **Audit log**: every demo-journey event listed in §4 produces an audit entry with actor, customer, engagement, run, event type, target id, and timestamp.

## 21. Feature table: POC / MVP / Later

| Feature | POC | MVP | Later | Reason |
|---|:---:|:---:|:---:|---|
| Modular monolith + 4 modules | ✅ | ✅ | ✅ | Core thesis |
| Sample evidence parsers | ✅ | ⚪ | ⚪ | POC validation |
| Real AD toolkit run on customer infra | ⬜ | ✅ | ✅ | MVP onwards |
| Real Microsoft Graph collector | ⬜ | ✅ | ✅ | MVP onwards |
| Real Silverfort API connector | ⬜ | 🟡 gated | ✅ | API validation needed (D-0006) |
| Two-scores model | ✅ | ✅ | ✅ | Core thesis |
| License-aware status (8-value) | ✅ | ✅ | ✅ | Core thesis |
| Cross-module correlation | ✅ | ✅ | ✅ | Core thesis |
| Auth via Entra ID | ⬜ | ✅ | ✅ | A-0013 |
| Multi-tenant isolation enforced | ⬜ | 🟡 | ✅ | Phased |
| Encryption at rest | ⬜ | ✅ | ✅ | MVP baseline |
| HTML reports | ✅ | ✅ | ✅ | — |
| PDF reports | 🟡 stretch | ✅ | ✅ | Phased |
| Retest workflow | ⬜ | ✅ | ✅ | Phased |
| Customer self-service portal | ⬜ | ⬜ | ✅ | Phased |
| Advisory / Defender / Purview / Intune modules | ⬜ | ⬜ | ✅ | Phased |
| Imprivata / Cato / Illumio modules | ⬜ | ⬜ | ✅ | Phased |
| AI language polish | ⬜ | ⬜ | 🟡 optional | Never in critical path (D-0005) |

---

*Last updated: 2026-05-15.*
