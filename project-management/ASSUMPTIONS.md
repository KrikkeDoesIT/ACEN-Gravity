# ASSUMPTIONS.md

> Assumptions we are making to keep moving. Each one needs validation. When validated, the assumption is closed and the result moves to `DECISIONS.md` (if it changes a decision) or is removed (if confirmed).

Format:

```
### A-NNNN — <short title>
Date: YYYY-MM-DD
Status: open | validated | invalidated | superseded
Owner to validate: <who>
Assumption: <statement>
Why we are assuming it: <reason>
Impact if wrong: <what changes>
Linked: <files / decisions>
```

---

### A-0001 — Project name "ACEN Gravity" is the working title
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: The platform is internally named "ACEN Gravity" during POC. Final commercial naming is decided later.
Why: The repository folder is already named "ACEN Gravity"; using it consistently helps Cycle 1 review.
Impact if wrong: Cosmetic. Search/replace across docs.

### A-0002 — Single tenant in POC V1
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: POC V1 runs as single-tenant — one ACEN organization with one or two demo customers — and multi-tenant isolation is *designed for* but not *enforced* at the database/permission level.
Why: Cuts complexity dramatically; sufficient for demo and management review.
Impact if wrong: We would need to enforce tenant isolation in code from day one. MVP work.
Linked: D-0001.

### A-0003 — Three personas are enough for POC
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: We design for three personas in POC: (1) ACEN Consultant / Security Engineer, (2) Customer CISO / Executive, (3) Customer IT/Security Lead. Internal admin / superuser is a fourth role visible only in setup screens.
Why: Covers the main user journeys identified in the prompt without inflating UX scope.
Impact if wrong: New personas may require new screens; not catastrophic but adds UX work.
Linked: `POC_V1_SCOPE.md`, `UI_DESIGN_DIRECTION.md`.

### A-0004 — PingCastle XML is the canonical AD configuration baseline
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: For POC V1, AD configuration data (privileged groups, kerberos config, GPO state, replication health, etc.) is sourced from PingCastle XML plus targeted PowerShell collectors in the AD toolkit. We do not implement our own full AD scanner.
Why: PingCastle is widely used, well-known, and produces structured data; reinventing it is out of scope.
Impact if wrong: We would need to design and build a full AD scanner module — significant scope.
Linked: `AD_MODULE_DESIGN.md`, `AD_TOOLKIT_DESIGN.md`.

### A-0005 — BloodHound CE JSON format (current schema) for SharpHound ZIPs
Date: 2026-05-15
Status: open
Owner to validate: Kristof + dev
Assumption: SharpHound ZIPs uploaded to the BloodHound Analyzer follow the BloodHound Community Edition JSON schema (users, groups, computers, ous, gpos, containers, domains, sessions optional). Legacy BloodHound 4.x format support is best-effort.
Why: BloodHound CE is the current direction of the project; assuming the legacy format adds parser complexity.
Impact if wrong: We may need to support both formats; adds parser work but is bounded.
Linked: `BLOODHOUND_ANALYZER_DESIGN.md`.

### A-0006 — Silverfort API endpoints listed are *named correctly* but require version/licence validation
Date: 2026-05-15
Status: open
Owner to validate: Kristof + Silverfort support
Assumption: The endpoints in the prompt (`/getServiceAccountsInsights`, `/getBootStatus`, `/getEntityRisk`, `/v2/public/policies`, `/getUsersEnrollment`) exist as named in *some* Silverfort version, but their availability, request/response shape, auth model, and rate limits are unverified for any specific customer.
Why: They appear in public integration references but are not documented in a single authoritative public schema.
Impact if wrong: Connector design must be reworked. POC is unaffected (manual mode).
Linked: D-0006, `SILVERFORT_MODULE_DESIGN.md`, `OPEN_QUESTIONS.md`.

### A-0007 — Microsoft Graph permissions for Entra collection are read-only and consented at app-registration time
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: The future Entra connector uses a multi-tenant or single-tenant app registration with read-only Graph permissions (e.g., `Directory.Read.All`, `Policy.Read.All`, `RoleManagement.Read.Directory`, `Application.Read.All`, `AuditLog.Read.All`, `IdentityRiskyUser.Read.All` where licensed). Consent is granted by customer admin; no delegated user flow in POC.
Why: Application-permissions consent model is the standard ACEN engagement approach.
Impact if wrong: We may need delegated flows; significant Entra ID auth work.
Linked: `ENTRA_MODULE_DESIGN.md`.

### A-0008 — POC runs locally (single host) and is not deployed to customers
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: POC V1 runs on a developer or consultant workstation (or a single VM) for demo purposes only. No customer deployment, no public exposure, no production hosting decisions in POC scope.
Why: Eliminates hosting, networking, certificate, and operational scope.
Impact if wrong: Adds infrastructure design work; rejection is unlikely.
Linked: `SECURITY_AND_GDPR.md`.

### A-0009 — All evidence is uploaded manually in POC; no agent/collector polling
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: Evidence is uploaded via the UI (drag-and-drop, ZIP/JSON/XML files). No agent, scheduled poll, or auto-discovery in POC.
Why: Removes connector complexity, secrets management, scheduling.
Impact if wrong: MVP scope increases; POC unaffected.
Linked: `PRODUCT_DESIGN.md`.

### A-0010 — Reports are HTML-first; PDF is a stretch goal
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: POC V1 generates HTML reports rendered in-browser. PDF (via Playwright) is desirable for the demo but is a stretch goal — we cut PDF before we cut any of the demo journey.
Why: HTML is sufficient for management review; PDF adds CI/runtime complexity.
Impact if wrong: We add Playwright earlier; bounded work.
Linked: `PRODUCT_DESIGN.md` (Reporting Model).

### A-0011 — Cross-module correlation in POC = identity-based join + manual mapping
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: Correlation between AD, BloodHound, Silverfort, and Entra is based on a normalized **Identity** entity keyed by canonical user/account identifiers (SID, UPN, sAMAccountName, ObjectGUID). Where source data uses different keys, we maintain a lookup table; ambiguous matches are surfaced for consultant review rather than silently joined.
Why: This is the smallest model that demonstrates correlation without requiring a unified identity graph.
Impact if wrong: Correlation findings may be misleading; mitigated by surfacing ambiguity.
Linked: `PRODUCT_DESIGN.md` (Data Model), `MODULE_ARCHITECTURE.md`.

### A-0012 — Synthetic sample datasets cover the demo journey end-to-end
Date: 2026-05-15
Status: open
Owner to validate: Kristof + dev
Assumption: We will create synthetic datasets for AD (PingCastle XML + toolkit JSON outputs), SharpHound (a small synthetic forest with at least 3 Tier 0 paths), Silverfort (policies + service-account insights + enrollment + entity risk JSON), and Entra (users, groups, roles, CA policies, apps JSON). The same fictional company is used across all four for cross-module correlation.
Why: Real customer data must not be committed (D-0011).
Impact if wrong: Demo data work expands; bounded.
Linked: D-0011, `POC_V1_SCOPE.md`.

### A-0013 — Authentication is bypassed in POC; role is chosen at login
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: POC V1 does not implement authentication. A simple login screen offers a role chooser (Consultant / Customer Executive / Customer IT Lead) and a customer selector. Audit log records the chosen identity.
Why: Removes Entra ID auth scope; demonstrates RBAC visually.
Impact if wrong: Adds auth scope; bounded.
Linked: D-0001, `SECURITY_AND_GDPR.md`.

### A-0014 — m365maps.com is inspiration, not source of truth
Date: 2026-05-15
Status: open
Owner to validate: Kristof + Microsoft licensing references
Assumption: The license/capability catalog is initially populated by hand from public Microsoft documentation, with m365maps.com used only as a *conceptual* reference. Before MVP, we replace this with an authoritative source (Microsoft licensing service plans, Graph subscribedSkus, official Microsoft docs).
Why: m365maps is unofficial and may lag Microsoft changes.
Impact if wrong: Customers see incorrect license-aware statuses; mitigated by tier tag "POC sample data only".
Linked: D-0007, `LICENSE_MODEL.md`.

### A-0015 — Sample BloodHound ZIPs do not include real session data
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: Synthetic SharpHound ZIPs contain users/groups/computers/ACLs but **no session data** (no claim that user X was logged on to computer Y). Sessions add realism but are sensitive; we omit them.
Why: Reduces sensitivity of sample data; sessions can be mocked at the path-detection layer if needed.
Impact if wrong: Some session-based path categories cannot be demonstrated from data alone; mitigated by template-based path fabrication for demo.
Linked: D-0011, `BLOODHOUND_ANALYZER_DESIGN.md`.

### A-0016 — POC V1 can run on synthetic or anonymized data only
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: For POC V1, the demo journey can be demonstrated using fully synthetic data (no real customer evidence) or anonymized sanitized exports. We do not require real customer data to land the management decision.
Why: Removes GDPR / customer-confidentiality scope from POC; aligns with D-0011 (synthetic-only) and D-0015 (sample data plan).
Impact if wrong: If management or ACEN sales insists the demo must run on a real customer dataset to be credible, we'd need DPO-approved anonymization and an explicit customer agreement — bounded extra work, but disruptive to the schedule. Q-0040 covers this.
Linked: D-0011, D-0015, `WORKING_APPROACH.md` §13.

### A-0017 — Live Graph and Silverfort API connectors are not required for POC V1
Date: 2026-05-15
Status: open
Owner to validate: Kristof
Assumption: POC V1 demonstrates the workflow on uploaded / mocked evidence only. No live Microsoft Graph collector, no live Silverfort API. These are designed for (interface, manifest, normalized shape) but not implemented in POC. MVP introduces a real-or-limited Graph collector (D-0012 / `WORKING_APPROACH.md` §5) and a Silverfort connector gated on validation (D-0006).
Why: Eliminates connector implementation scope, secrets management, app-registration flow, customer onboarding flow, and rate-limit handling from POC V1. Aligns with the §10/§12 "mock in POC V1" list.
Impact if wrong: If management expects a live data demo at Cycle 7, we either ship a tightly-scoped live read (bounded extra work) or re-frame the demo around uploaded evidence. Either is achievable; we choose at Session 1.
Linked: D-0006, D-0012, `WORKING_APPROACH.md` §5, §12.

### A-0018 — The first build is a thin vertical slice; module pages come after
Date: 2026-05-15
Status: open
Owner to validate: Kristof + developer
Assumption: Stage 9 begins with a vertical slice (AD + BloodHound minimal path → finding → publish → report preview). The other modules (Silverfort, Entra), additional controls, the full UI surface, and cross-module correlation are built only after the slice is reviewed and signed off.
Why: Proves the lifecycle on real wiring before horizontal expansion; protects against half-built module dashboards (R-0002). Re-affirmed by D-0014 and codified in `TASKS.md` Stage 9 ordering.
Impact if wrong: If a stakeholder pushes for parallel module dashboards before the slice is done, we'd reduce architectural confidence and risk demo-state fragility. Re-direct via §6 hard rule.
Linked: D-0014, `WORKING_APPROACH.md` §6, `TASKS.md` Stage 9.

### A-0019 — Kristof has a test Entra tenant available for MVP validation
Date: 2026-05-15
Status: open (informational)
Owner to validate: Kristof
Assumption: When the **real** Microsoft Graph collector lands at MVP (per A-0007 / Q-0080), Kristof can provide a test Entra tenant for validation — exercising real application-permissions consent flow, real `subscribedSkus`, real Conditional Access policies, real role assignments, etc. The POC V1 itself uses synthetic Entra fixtures only (D-0011); the test tenant is purely an MVP-stage validation aid.
Why: Removes the "where do we test the connector?" question from MVP planning. Kristof's offer signals this is solved.
Impact if wrong: We'd need to find a different validation tenant for MVP (likely an ACEN-owned demo tenant). Low impact.
Linked: A-0007 (Graph permissions), Q-0080 (consent friction), `ENTRA_MODULE_DESIGN.md`.

---

*Last updated: 2026-05-15 — A-0016, A-0017, A-0018 added for the 9-stage operating-model update; A-0019 added (Entra test tenant available for MVP validation).*
