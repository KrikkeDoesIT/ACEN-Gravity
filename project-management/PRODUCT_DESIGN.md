# PRODUCT_DESIGN.md

> The product specification. Authoritative for what the platform is, what it does, what it does not do, and how it is shaped at POC V1, MVP, and Full Product tiers.
>
> Companion documents (deeper detail):
> `POC_V1_SCOPE.md` · `MODULE_ARCHITECTURE.md` · `LICENSE_MODEL.md` · `SECURITY_AND_GDPR.md` · `UI_DESIGN_DIRECTION.md` · `AD_MODULE_DESIGN.md` · `AD_TOOLKIT_DESIGN.md` · `BLOODHOUND_ANALYZER_DESIGN.md` · `SILVERFORT_MODULE_DESIGN.md` · `ENTRA_MODULE_DESIGN.md`

---

## 1. Management summary

ACEN Gravity is a **modular, license-aware security assessment platform** built for the identity and access security domain. Its first version unifies the four core ACEN identity-security disciplines — Active Directory, BloodHound attack-path analysis, Silverfort, and Microsoft Entra — into a single workflow: collect evidence → evaluate controls → produce findings → prioritize remediation → publish to customer.

The platform is built once, but is **modular by design**: every module shares the same evidence, control, finding, scoring, and reporting model, so adding a new module (Defender XDR, Purview, Imprivata, Cato, etc.) is an additive operation, not a rewrite.

POC V1 validates the concept on sample data with a clear management decision point. MVP introduces real connectors and is used by ACEN consultants on real engagements. Full Product is customer-facing.

The single most important design constraint is **license-awareness**: customers are scored only against capabilities they actually own, with a separate Target Posture Score showing the gap to a stronger recommended posture. This makes the platform commercially honest and operationally useful.

---

## 2. Executive summary

| Question | Answer |
|---|---|
| What is it? | A modular identity-security assessment platform. |
| Who is it for? | ACEN consultants (delivery), customer CISOs/executives, customer IT/security leads. |
| What does it do? | Ingests AD, BloodHound, Silverfort, and Entra evidence; evaluates license-aware controls; produces prioritized findings; renders ACEN-branded reports; tracks remediation. |
| What is the differentiator? | One platform, one workflow, license-aware scoring, deterministic BloodHound analysis, customer/internal visibility separation, ACEN brand. |
| What is the POC for? | A management go/no-go on MVP investment, demonstrated on synthetic data. |
| What is the architecture? | Modular monolith — Python/FastAPI + HTMX + Tailwind + PostgreSQL. |
| What is *not* in POC? | Real connectors, real auth, multi-tenancy enforcement, encryption at rest, advisory/Defender/Intune/Purview modules. |

---

## 3. Discovery summary

Sourced from `DISCOVERY_WORKSHOP_ANSWERS.md`. Headlines:

- **Trigger:** siloed deliverables, no shared lifecycle, license-blind scoring, BloodHound opacity, no cross-module correlation.
- **Risk of inaction:** commercial, operational, quality, knowledge-capture losses.
- **Primary users:** ACEN Consultant, Customer Executive, Customer IT Lead.
- **Minimum viable:** demo journey end-to-end on sample data, with cross-module correlation.
- **Success in 6 months:** POC sign-off → MVP delivered → ≥ 1 real engagement positive.
- **Hard constraints:** POC must not become production; deterministic BloodHound; synthetic data only; ACEN brand applied.
- **Most important workshop decision:** define POC V1 scope without turning it into a production build.

---

## 4. Product vision

> **"One identity-security workspace where ACEN and its customers see the same picture, prioritize the same risks, and prove progress over time."**

A consultant logs in, picks a customer, sees one prioritized list of identity-security risks across AD, BloodHound, Silverfort, and Entra — each finding linked to evidence, license context, remediation guidance, and a customer-facing summary. The same customer's CISO logs in (later), sees the executive view of the same evidence — only what has been deliberately published — and decides what to fund first.

The platform is modular by design. New modules (Defender, Purview, Intune, Cato, etc.) plug into the same lifecycle and the same UI patterns without bespoke screens or bespoke data shapes. Modules stay small; the platform stays calm.

---

## 5. Target users

| Persona | Goals | Pains | What the platform gives them |
|---|---|---|---|
| **ACEN Consultant / Security Engineer** | Run engagements faster; not lose findings between tools; deliver a consistent deliverable | Reformatting BloodHound/PingCastle; no continuity between consultants; siloed deliverables | Single workspace; evidence in one place; correlation pre-computed; report templates; audit log |
| **Customer CISO / Executive** | Understand current risk; decide what to fund; show progress | Drowning in technical detail; no clear "top 3"; cannot see progress between engagements | Executive dashboard; current vs target posture; prioritized investment view; published reports |
| **Customer IT / Security Lead** | Know which findings are theirs; fix them; prove fixed | Inconsistent finding formats; no retest path; unclear acceptance criteria | Personal workspace; evidence link; remediation guidance; retest workflow (MVP+) |
| **Platform Admin (ACEN)** | Manage organizations, customers, users, license catalog | None visible to demo audience | Setup screens (not part of demo) |

---

## 6. Core use cases

For POC V1, the demo journey covers these use cases:

1. **Onboard customer + engagement** (admin/consultant): create customer, create engagement, create assessment run.
2. **Upload evidence** (consultant): upload AD ZIP, SharpHound ZIP, Silverfort export, Entra JSON to an assessment run.
3. **Review parsed evidence** (consultant): see normalized data in the platform, with license context.
4. **Evaluate controls** (system): run module controls; produce findings; surface license-aware statuses.
5. **Prioritize findings** (consultant): filter, sort, drill in.
6. **See cross-module correlation** (consultant): at least one finding spans modules (e.g., BH path → AD privileged → no SF coverage → synced to Entra admin).
7. **Annotate & set visibility** (consultant): set `customer_visibility`; add consultant notes.
8. **Generate report** (consultant): Internal and Customer reports (HTML; PDF stretch).
9. **Publish** (consultant): explicit publish action; audit logged.
10. **Customer Executive view** (executive persona): land on dashboard, see top 3 findings, drill into one, see only customer-visible detail.

Out of scope for POC: retest cycle (placeholder only), customer self-service, real connectors, real auth.

---

## 7. Product scope

### 7.1 In scope (across all tiers)

- Core platform entities (organization, customer, user, role, engagement, assessment run, evidence, control, control result, finding, remediation task, report, audit log).
- Module framework (each module declares evidence needs, controls, normalized data, findings, scoring, report sections, customer-visible data).
- License-aware scoring (8-value enum, two scores + opportunity gap).
- AD, BloodHound, Silverfort, Entra modules.
- Cross-module correlation.
- ACEN-branded UI.
- Internal and Customer reports.

### 7.2 Tier-specific scope

| Capability | POC V1 | MVP | Full |
|---|---|---|---|
| Sample evidence parsing | ✅ | ✅ | ✅ |
| Real AD toolkit run | ⬜ design only | ✅ | ✅ |
| Real Microsoft Graph collector | ⬜ design only | ✅ | ✅ |
| Real Silverfort API | ⬜ design only | ⏸ gated on validation | ✅ |
| Real auth (Entra ID) | ⬜ | ✅ | ✅ |
| Multi-tenant isolation enforced | ⬜ design only | 🟡 partial | ✅ |
| Encryption at rest / KMS | ⬜ | 🟡 baseline | ✅ |
| Customer self-service portal | ⬜ | ⬜ | ✅ |
| PDF reports | 🟡 stretch | ✅ | ✅ |
| Retest workflow | 🟡 placeholder | ✅ | ✅ |
| Advisory modules | ⬜ | ⬜ | ✅ |
| Defender / Purview / Intune modules | ⬜ | ⬜ | ✅ |

### 7.3 Out of scope (always or until further decision)

- Acting on customer environments (no remediation execution; advisory only).
- Storing or processing credentials/secrets from customer environments beyond what is required for connectors.
- Compliance-framework certification (ISO 27001 / SOC2) before Full Product.
- AI/LLM in the path detection critical-path (D-0005).

---

## 8. What the product is / is not

| Is | Is not |
|---|---|
| A modular **identity-security** assessment platform | A general-purpose SIEM |
| **Consultant-led** by default; customer-facing later | A self-service security-tools marketplace |
| A **license-aware** workspace (M365 + non-Microsoft vendors) | A licensing calculator or sales tool |
| **Evidence + finding + remediation + retest** lifecycle | A ticketing system |
| **Deterministic** in path detection and scoring | An AI-driven security analyst |
| **One platform**, many modules | A bundle of dashboards under one brand |
| **ACEN-branded**, executive-readable | A developer tool |

---

## 9. Product simplicity and information architecture

### 9.1 Information architecture (top level)

```
Org (ACEN)
└── Customer (e.g., Contoso Corp)
    └── Engagement (e.g., Q2 2026 Identity Security Review)
        └── Assessment Run (e.g., 2026-05-15 Baseline)
            ├── Evidence (artifacts; AD ZIP, SharpHound ZIP, SF export, Entra JSON)
            ├── Controls (per module; evaluated)
            ├── Findings (across modules; correlated)
            ├── Remediation Tasks
            ├── Reports (Internal + Customer)
            └── Audit Log
```

### 9.2 Navigation

- **Top nav:** customer picker, engagement picker, assessment run picker.
- **Side nav:** Overview · AD · BloodHound · Silverfort · Entra · Findings · Reports · Audit.
- **Persona overlay:** Customer Executive sees a compressed nav (Overview · Findings (customer) · Reports).

### 9.3 Page purpose budget

Each page has **one clear purpose**. KPI count per page ≤ 5. Charts per page ≤ 3 unless the page is a dedicated drill-down (per UX rules in `UI_DESIGN_DIRECTION.md`).

---

## 10. POC V1 definition

Detailed in `POC_V1_SCOPE.md`. Headlines:

- Demonstrate the lifecycle on synthetic data for one fictional customer ("Contoso Corp") across all four modules.
- Produce ≥ 4 controls per module, ≥ 1 finding per module, ≥ 1 cross-module correlation finding.
- Render one Internal and one Customer HTML report.
- Show explicit license-aware status badges and the two-scores model.
- Audience: ACEN management review.
- Success criterion: signed go/no-go decision.

---

## 11. POC V1 UX

Detailed in `UI_DESIGN_DIRECTION.md`. Headlines:

- ACEN brand applied (palette, Montserrat typography, square frames, ≤ 2px radius on interactive controls only).
- 3 personas via role-switcher (no real auth).
- Overview dashboard answers each persona's primary question.
- Findings workspace with filters, drill-down, evidence drawer.
- Customer visibility flag enforced in UI and report.
- Module pages reuse the same layout patterns to keep the product calm.

---

## 12. MVP after POC

Headlines for the next tier (full detail deferred):

- **Authentication:** Entra ID for ACEN consultants; customer access via per-customer share (link + magic-link or limited federation TBD).
- **Connectors:** AD toolkit deployed to customer infrastructure; Microsoft Graph collector with read-only application permissions; Silverfort manual upload remains; Silverfort API gated on validation.
- **Storage:** real evidence storage with retention policy; encrypted at rest.
- **RBAC:** enforced server-side; per-customer access policy.
- **Retest:** real retest workflow (mark finding "retest requested" → consultant re-evaluates → status update).
- **Reports:** PDF support standard.
- **Operations:** logging, monitoring, basic SLA.

---

## 13. Full product vision

- **Customer self-service portal** (with finding-level access controls).
- **Multi-tenant** with enforced isolation, BCDR, regional hosting options.
- **Advisory modules** as a first-class module type (consultant-driven; no product evidence).
- **Defender XDR**, Defender for Endpoint, Defender for Office 365, Defender for Cloud Apps, Purview, Intune, Defender for Cloud, Mail Security, M365 Posture, Hybrid Identity Security, Imprivata, Cato, Illumio modules.
- **Engagement billing integration** (per engagement and/or subscription).
- **Continuous monitoring** mode for selected modules (e.g., Entra delta queries).
- **Customer benchmarking** (anonymized industry baselines).

---

## 14. Recommended architecture

### 14.1 Architectural principles

- **Modular monolith** in Python/FastAPI (D-0002).
- **Shared kernel** (`platform_core/`) owns entities, lifecycle, and APIs.
- **Modules** (`modules/<name>/`) own evidence parsers, controls, normalized data, findings, scoring, report sections, customer-visibility hooks.
- **No module imports another module.** Cross-module correlation is mediated by core through the normalized identity entity and the shared finding shape.
- **Hexagonal-ish:** parsers and connectors are adapters; controls are pure functions of normalized data.

### 14.2 Stack

| Layer | Choice | Why |
|---|---|---|
| Web framework | FastAPI | Async-capable, typed, fits Pydantic, easy Jinja integration |
| ORM | SQLAlchemy 2.x + Alembic | Battle-tested, typed |
| Validation | Pydantic v2 | Same type ecosystem |
| Templates | Jinja2 | Server-rendered, simple |
| Frontend interactivity | HTMX + Tailwind CSS + Alpine.js (limited) | No SPA build; matches Kristof's stack preference |
| DB | PostgreSQL | JSONB columns for evidence payloads; partial indexes |
| Background jobs | Synchronous in POC; design for Redis + RQ at MVP | D-0004 |
| Reports | HTML; PDF via Playwright (stretch) | Aligns with brand templates |
| Evidence storage | Local filesystem in POC; object storage (S3/Blob) at MVP | Simple → durable |
| Auth | None in POC (role-switcher); Entra ID at MVP | A-0013 |

### 14.3 High-level component diagram (textual)

```
[Browser] ── HTMX ──> [FastAPI app]
                          │
                          ├── Web routes (HTMX partials + JSON for tables)
                          ├── platform_core/  (services, models, lifecycle)
                          │     ├── identity/      (canonical identity join)
                          │     ├── evidence/      (upload, validation, storage)
                          │     ├── controls/      (evaluation engine)
                          │     ├── findings/      (lifecycle, scoring, viz flags)
                          │     ├── licensing/     (catalog, capability mapping)
                          │     ├── reports/       (templates, render)
                          │     └── audit/         (audit log)
                          ├── modules/ad/         (parsers, controls, normalized data)
                          ├── modules/bloodhound/ (analyzer, path scoring)
                          ├── modules/silverfort/ (parsers, controls)
                          └── modules/entra/      (parsers, controls)
                          │
                          ▼
                  [PostgreSQL]   [Local FS: evidence/]
```

---

## 15. Module architecture (summary)

Full detail in `MODULE_ARCHITECTURE.md`. Headlines:

A module is a Python package under `modules/<name>/` that declares:

- **Evidence types** it accepts (with parsers).
- **Normalized entities** it produces (each is either core (`Identity`, `Computer`, ...) or module-local).
- **Controls** with deterministic logic.
- **Findings** with consistent shape (id, title, severity, category, evidence refs, correlation hooks).
- **Score contribution** (per control, weighted into Current License Score and Target Posture Score).
- **Report sections** (Internal and Customer templates).
- **Customer-visibility defaults** per finding category.

A module **does not**:

- Import another module.
- Define its own `Finding` shape.
- Bypass the upload/parse/evaluate lifecycle.
- Implement its own auth or audit log.

---

## 16. Data model (core)

Detailed schema in `MODULE_ARCHITECTURE.md`. Key entities:

| Entity | Owner | Purpose |
|---|---|---|
| `Organization` | core | The ACEN tenant; container for everything. |
| `Customer` | core | A customer org under ACEN. |
| `User` | core | A person who logs in (consultant or customer-side). |
| `Role` | core | Logical role (Consultant, Customer Executive, Customer IT Lead, Admin). |
| `Engagement` | core | A scoped piece of work for one customer (e.g., "Q2 2026 Identity Review"). |
| `AssessmentRun` | core | A point-in-time snapshot within an engagement; everything below ties to a run. |
| `Module` | core | Module metadata (id, version, supported evidence types). |
| `Artifact` | core | An uploaded file (ZIP, JSON, XML); raw, immutable. |
| `Evidence` | core | A parsed, normalized view of an artifact (or part of it). |
| `Identity` | core | Canonical identity entity (cross-module join key — SID, UPN, sAMAccountName, ObjectGUID). |
| `Control` | module | Module-declared control definition (id, version, title, severity defaults, evidence reqs). |
| `ControlResult` | core | Evaluated control outcome for an assessment run; has `license_status`, `score_contribution`. |
| `Finding` | core | A finding emitted by a control evaluation; one common shape, with module-specific data. |
| `RemediationTask` | core | Action proposed against a finding; assigned, tracked. |
| `Report` | core | A rendered report (Internal or Customer); references findings; immutable once generated. |
| `AuditLog` | core | Append-only log of consequential actions (upload, parse, publish, report, etc.). |
| `LicenseCatalog` / `Capability` / `Sku` | core | License catalog used by control evaluation and scoring. |

---

## 17. Security model

Detailed in `SECURITY_AND_GDPR.md`. Headlines:

- **Trust boundary:** the browser is untrusted; evidence files are untrusted; all module parsers operate on untrusted input.
- **Auth:** none in POC (role-switcher with audit log capture). Entra ID at MVP.
- **Authorization:** RBAC enforced at the service layer at MVP; UI hides/locks at POC.
- **Tenant isolation:** designed for at POC; enforced at MVP.
- **Evidence handling:** uploaded files validated (size, type, hash), parsed in a sandboxed code path (no `eval`, no shell-out), stored with a stable hash-based name.
- **Audit log:** records upload, parse, evaluate, finding state changes, publishing, report generation, user logins (when auth exists).
- **Publishing:** `customer_visibility` flag gates UI visibility and report inclusion. Default `internal_only`.
- **Secrets:** none in POC. MVP introduces a secrets approach (env-based + future KMS).
- **GDPR:** designed for at POC; data minimization, retention, export-on-request, delete-on-request.

---

## 18. GDPR

Detailed in `SECURITY_AND_GDPR.md`. Headlines:

- **Lawful basis:** processing for the ACEN engagement contract (Art. 6(1)(b)) with the customer; DPA in place per engagement at MVP.
- **Data minimization:** modules ingest only what they need for their declared controls. No "store everything we can".
- **Retention:** per-engagement retention policy (default proposal: evidence retained until engagement closure + N months, then purged on schedule).
- **Subject rights:** export and delete supported at MVP. At POC, design only.
- **Processor / sub-processor disclosure:** ACEN is processor; sub-processors (e.g., hosting provider) listed in DPA at MVP.

---

## 19. AD toolkit

See `AD_TOOLKIT_DESIGN.md`. Headlines: PowerShell-based, read-only, offline, produces a versioned ZIP with manifest + checksums + collector outputs + optional PingCastle XML + optional BloodHound ZIP (controlled).

## 20. AD module

See `AD_MODULE_DESIGN.md`. Headlines: ingests AD toolkit ZIPs (+ PingCastle XML); ~30 controls grouped by Health / Privileged / Kerberos / Delegation / NTLM / GPO / Silverfort-correlation / Entra-correlation.

## 21. BloodHound analyzer

See `BLOODHOUND_ANALYZER_DESIGN.md`. Headlines: Python parser + in-memory graph + deterministic shortest-path detection to Tier 0 + path categorization + template-based explanations + correlation with AD, Silverfort, Entra.

## 22. Silverfort module

See `SILVERFORT_MODULE_DESIGN.md`. Headlines: manual evidence parser at POC; API connector designed only; ~15 controls covering connector / policy / enrollment / risk / service accounts / AD-correlation / Entra-correlation. Every API claim tagged "requires validation".

## 23. Entra module

See `ENTRA_MODULE_DESIGN.md`. Headlines: ingests Entra Graph JSON dump at POC; ~40 controls grouped by Licensing / CA / Auth methods / Privileged roles / Apps / Guests / Hybrid / Silverfort-correlation. License-aware.

---

## 24. Reporting model

- **Two report types** at POC: Internal Detailed, Customer Summary.
- **Internal Detailed**: all findings, all evidence references, scores, license context, technical detail.
- **Customer Summary**: only findings marked `customer_summary` or `customer_full`; executive summary first; license-aware framing.
- **Renderer**: Jinja templates → HTML; PDF via Playwright (stretch).
- **Immutability**: a generated report is captured (HTML + metadata) and stored; subsequent runs produce a new report, not edit prior ones.
- **Branding**: full ACEN brand on both report types; customer co-branding deferred (Q-0101).
- **Audit**: report generation and publishing events recorded.

---

## 25. Scoring model

- **Per-control inputs:** `result_status` (pass / partial / fail / not_applicable / unknown) and `license_status` (8-value enum from D-0007). Severity weight from module definition.
- **Current License Security Score (per module and engagement):** weighted aggregate of controls where `license_status` ∈ {`licensed_enabled`, `licensed_disabled`, `licensed_misconfigured`}. `not_licensed` and `not_applicable` are excluded (do not penalize).
- **Target Security Posture Score (per module and engagement):** weighted aggregate of all controls, treating `not_licensed` and `requires_add_on` as "fail" against the target.
- **Opportunity Score:** `Target Posture Score − Current License Score`. Surfaces capability gaps without penalizing the customer.
- **Severity:** Critical / High / Medium / Low / Info. Each finding has a `severity` and a numeric `risk_score` (0–100).
- **Cross-module correlation findings** carry the severity of the most-severe participating evidence, unless explicitly overridden by the analyzer template.

Detailed formulas live in `LICENSE_MODEL.md`.

---

## 26. License-aware model

See `LICENSE_MODEL.md`. Headlines: vendor catalog → SKUs → capabilities → controls. A control's evaluation considers both *capability ownership* (license_status) and *configuration state* (result_status). Two scores are produced.

---

## 27. ACEN UI principles

See `UI_DESIGN_DIRECTION.md`. Headlines: ACEN palette (Jakarta/Bunting/Trinidad/Turquoise + neutrals), Montserrat typography, square frames except ≤ 2px on interactive controls (D-0010), executive-readable, calm whitespace, no SIEM clutter, summary first / details later, consistent module page layout.

---

## 28. Future module readiness

The platform is built to plug new modules in additively. To add a module:

1. Create `modules/<name>/` with the standard layout (`parsers/`, `models/`, `controls/`, `correlations/`, `reports/`).
2. Declare the module's manifest (id, version, supported evidence types, controls, score contribution, customer-visibility defaults).
3. Register the module with the core module registry.
4. Provide synthetic sample evidence for tests.

Modules that match this template without code changes to core qualify as "in-shape". Modules that need core changes (e.g., a new normalized entity type) go through the architecture review.

---

## 29. Implementation phases

Aligned with `WORKING_APPROACH.md` §3 and `TASKS.md`:

- **Phase 1 — Foundation docs** (now): scope, architecture, UX, security, module designs.
- **Phase 2 — Project skeleton & shared core**: FastAPI app, models, evidence lifecycle, audit log, license catalog.
- **Phase 3 — Modules**: AD, BloodHound, Silverfort, Entra in parallel (each: parser + controls + sample data).
- **Phase 4 — UI**: shell, dashboard, findings workspace, evidence drawer, publishing, reports.
- **Phase 5 — Demo dry-run & polish**: synthetic data realism, demo script, performance pass on parser.
- **Phase 6 — Management review**: deck + live demo + go/no-go.

---

## 30. Risks

Tracked in `RISKS.md`. The top three to manage during product design:

1. POC silently becomes MVP (R-0001).
2. Three dashboards instead of one platform (R-0002).
3. BloodHound analyzer drifts toward AI (R-0004).

---

## 31. Developer handoff

When the build phase starts, the developer reads (in order):

1. `WORKING_APPROACH.md` — how we work.
2. `PRODUCT_DESIGN.md` (this file) — what we are building.
3. `POC_V1_SCOPE.md` — exact POC scope.
4. `MODULE_ARCHITECTURE.md` — application shape.
5. Per-module design docs.
6. `UI_DESIGN_DIRECTION.md`.
7. `SECURITY_AND_GDPR.md`.
8. `LICENSE_MODEL.md`.
9. `TASKS.md` — prioritized backlog.

Developer must not extend scope without an `OPEN_QUESTIONS.md` entry and a Kristof-approved decision in `DECISIONS.md`.

---

*Last updated: 2026-05-15.*
