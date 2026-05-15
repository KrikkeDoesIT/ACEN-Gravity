# TASKS.md

> Single backlog. Grouped by stage. Each task carries a tier (POC / MVP / Full), an owner role, and a status.
>
> Status: `todo` · `doing` · `blocked` · `done` · `dropped`.
> Owner role: PO (Product Owner), SA (Software Architect), UX, SEC (Security/GDPR), AD, BH (BloodHound), SF (Silverfort), ENTRA, DOC (Documentation/Reviewer), QA, DEV.

---

## Stage 0 — Working approach

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-0001 | POC | DOC | done | Create `WORKING_APPROACH.md` |
| T-0002 | POC | DOC | done | Create control files (this file + PROJECT_STATE, DECISIONS, ASSUMPTIONS, OPEN_QUESTIONS, RISKS, REVIEW_NOTES, CHANGELOG) |

## Stage 1 — Product framing

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-1001 | POC | PO | done  | Draft `DISCOVERY_WORKSHOP_ANSWERS.md` (answer all 9 questions, with POC/MVP/Full split) |
| T-1002 | POC | PO | done  | Draft `PRODUCT_DESIGN.md` |
| T-1003 | POC | PO | done  | Draft `POC_V1_SCOPE.md` |
| T-1004 | POC | PO | todo  | Cycle 1 review with Kristof — sign off scope envelope |

## Stage 2 — Architecture framing

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-2001 | POC | SA | done  | Draft `MODULE_ARCHITECTURE.md` |
| T-2002 | POC | SA + PO | done  | Draft `LICENSE_MODEL.md` |
| T-2003 | POC | SA | done  | Define module dependency rules (in `MODULE_ARCHITECTURE.md` §3, §11, §18) |
| T-2004 | POC | SA | todo  | Cycle 2 review — sign off architecture and license model |

## Stage 3 — Module deep dives

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-3001 | POC | AD  | done  | Draft `AD_MODULE_DESIGN.md` |
| T-3002 | POC | AD  | done  | Draft `AD_TOOLKIT_DESIGN.md` |
| T-3003 | POC | BH  | done  | Draft `BLOODHOUND_ANALYZER_DESIGN.md` |
| T-3004 | POC | SF  | done  | Draft `SILVERFORT_MODULE_DESIGN.md` |
| T-3005 | POC | ENTRA | done  | Draft `ENTRA_MODULE_DESIGN.md` |
| T-3006 | POC | PO + domain | todo | Cycle 3 review — sign off the four module designs (close `REVIEW_NOTES.md` items 1–16) |

## Stage 4 — UX & information architecture

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-4001 | POC | UX  | done  | Draft `UI_DESIGN_DIRECTION.md` (component-led, mapped to `VISUAL_REFERENCES.md`) |
| T-4002 | POC | UX  | todo  | Produce low-fidelity screen wireframes (ASCII or markdown sketches) for: login, overview, customer page, engagement page, AD module, BloodHound paths, Silverfort, Entra, finding detail, report preview, publishing modal |
| T-4003 | POC | UX  | todo  | Cycle 4 review — sign off UX direction and demo journey |

## Stage 5 — Security & GDPR

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-5001 | POC | SEC | done  | Draft `SECURITY_AND_GDPR.md` |
| T-5002 | POC | SEC | todo  | Define `customer_visibility` flag enforcement points (UI, report renderer, audit log) |
| T-5003 | POC | SEC | todo  | Cycle 5 review — sign off security boundaries for POC |

## Stage 6 — POC backlog management

> Backlog **management** tasks, not build tasks. Cycle 6 ends with a frozen, ≤ 40-item POC backlog with vertical-slice items clearly marked. Build items themselves live in **Stage 9** below; preparation in **Stage 8**.

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6500 | POC | PO + SA | todo | Refine POC backlog to ≤ 40 implementation items; cut/postpone everything else (tag `mvp`/`full`) |
| T-6501 | POC | PO + SA | todo | Mark each task with `slice` (vertical slice §6) or `horizontal` (post-slice expansion) per `WORKING_APPROACH.md` §6 |
| T-6502 | POC | PO + SA | todo | Confirm each remaining task supports the demo story (`WORKING_APPROACH.md` §3) |
| T-6503 | POC | PO | todo | Cycle 6 review — sign off frozen POC backlog |

## Stage 7 — Management review

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-7001 | POC | PO + DOC | todo | Management deck (≤ 15 slides) anchored on the demo story |
| T-7002 | POC | PO | todo | Walk management through kill criteria (`WORKING_APPROACH.md` §20); each criterion must be addressed or accepted-with-risk |
| T-7003 | POC | PO | todo | Run demo with management; capture go/no-go decision in `DECISIONS.md` |

## Stage 8 — Build preparation

> Output of this stage: a developer can start Stage 9 work without ambiguity. **No business code yet.** Cycle 8 sign-off is required before Stage 9 starts.

### 8.1 Architecture skeleton (no business logic)

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6001 | POC | DEV | done    | Initialize Python project (pyproject.toml, ruff, mypy, pytest) |
| T-6002 | POC | DEV | done    | FastAPI app scaffolding + Jinja2 + Tailwind (Play CDN — switch to standalone CLI before MVP) |
| T-6003 | POC | DEV | blocked | PostgreSQL + Alembic baseline migration (empty schema — no models yet) — **blocked on WSL2 / Virtual Machine Platform** |
| T-6004 | POC | DEV | done    | Folder layout per `MODULE_ARCHITECTURE.md` (`src/platform_core/`, `src/modules/{ad,bloodhound,silverfort,entra}/`) |
| T-6005 | POC | DEV | done    | Simple role-switching "login" (no real auth) per A-0013 — Persona enum + session middleware + login/logout routes + 9 smoke tests |

### 8.2 Sample data plan

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-8001 | POC | PO + Kristof | todo | Approve sample data plan covering all items in `WORKING_APPROACH.md` §13 |
| T-8002 | POC | DEV + AD | todo | Author synthetic AD toolkit ZIP for "Contoso Corp" (was T-6032) |
| T-8003 | POC | DEV + BH | todo | Author synthetic SharpHound ZIP for "Contoso Corp" with ≥ 3 Tier 0 paths (was T-6046) |
| T-8004 | POC | DEV + SF | todo | Author synthetic Silverfort export bundle (was T-6053) |
| T-8005 | POC | DEV + ENTRA | todo | Author synthetic Entra Graph JSON bundle — E3 + standalone Entra ID P1, no P2 (was T-6063) |
| T-8006 | POC | DEV + PO | todo | `tests/fixtures/SAMPLE_DATA_README.md` documenting provenance, structure, and intentional cross-module overlaps |
| T-8007 | POC | Kristof | todo | Sign off sample-data realism (domain check per §13 ownership rule) |

### 8.3 Developer handoff

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-8010 | POC | DOC + SA | todo | `DEVELOPER_HANDOFF.md` (reading order, dev setup, conventions, where to start) — **starts with the vertical slice** |
| T-8011 | POC | SA | todo | Define module dependency rule enforcement (lint/import-check tooling decision) |
| T-8012 | POC | DEV | todo | docker-compose for Postgres (per R-0010) + dev `.env.example` |
| T-8013 | POC | PO | todo | Cycle 8 review — build preparation sign-off |

## Stage 9 — POC build

> **Vertical slice first (§6).** Tasks tagged `slice` must complete and review before any `horizontal` task starts.

### 9.0 Vertical slice (HARD GATE) — `slice`

> One end-to-end path through the lifecycle: Customer → Assessment Run → AD + BH evidence load → one critical path parsed → one Finding → review → publish → customer-visible view → one Report preview. Slice review happens before any horizontal expansion.

| ID | Tier | Owner | Status | Slice | Task |
|---|---|---|---|---|---|
| T-9001 | POC | DEV | done    | `slice` | Minimal SQLAlchemy 2.x models: Customer, Engagement, AssessmentRun, Evidence, Identity, Finding, AuditEvent. Alembic baseline migration applied. SQLite for now (D-0024) |
| T-9002 | POC | DEV | todo    | `slice` | Evidence upload endpoint + hardened ZIP/JSON validation (subset of T-6020). **Deferred to Chunk B** — fixtures load via CLI for now |
| T-9003 | POC | DEV + AD | done    | `slice` | AD privileged-groups parser → Identity rows (Tier 0 flagging) |
| T-9004 | POC | DEV + BH | done    | `slice` | SharpHound CE JSON parser → networkx DiGraph + transitive Tier 0 identification (well-known RIDs) |
| T-9005 | POC | DEV + BH | done    | `slice` | Deterministic shortest-path detection (severity-weighted Dijkstra, top K per source, top N reported) |
| T-9006 | POC | DEV + BH | done    | `slice` | Template-based Finding generator (per path category); deterministic explanations (D-0005) |
| T-9007 | POC | DEV + UX | done    | `slice` | Finding triage UI — explicit state machine (new ↔ triaged ↔ published ↔ retest_requested ↔ closed); state-transition buttons render only allowed targets |
| T-9008 | POC | DEV + UX | done    | `slice` | Publish action — composite endpoint that auto-triages, sets visibility (customer_summary or customer_full), marks state=published; one-click from the finding detail |
| T-9009 | POC | DEV + UX | done    | `slice` | Customer-visible view — list + detail enforce visibility server-side; customer executive sees published findings only and gets 404 (not 403) on `internal_only` ones |
| T-9010 | POC | DEV + UX | done    | `slice` | Report preview HTML — Internal Detailed (consultant) + Customer Summary (customer roles) variants from the same template; visibility-filtered server-side; headline finding card; per-module sections; severity strip; path with gap markers |
| T-9011 | POC | DEV | done    | `slice` | Audit log per state change, visibility change, and publish — events with severities `info` / `notable` / `security`; `/audit` view consultant-only |
| T-9012 | POC | PO + QA | todo    | `slice` | Slice review — demonstrate end-to-end on synthetic data. **Ready for walkthrough**: 36/36 tests pass; full demo journey verified end-to-end via HTTP probe. Awaiting Kristof's sign-off before any horizontal expansion. |
| T-9013 | POC | DEV | done    | `slice` | `gravity demo load` CLI (idempotent on customer/engagement; new run + findings per load) |
| T-9014 | POC | DEV + UX | done    | `slice` | `/findings` list + `/findings/{id}` detail with `PathStepList`; visibility gate enforced server-side |
| T-9015 | POC | QA | done    | `slice` | 9 smoke + 9 pipeline + 9 Chunk B tests = **27/27 pass**, lint clean |

### 9.1 Horizontal expansion — shared core (after slice) — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6010 | POC | DEV | todo | Expand core models: Organization, User, Role, Module, Artifact, Control |
| T-6011 | POC | DEV | todo | Identity entity (canonical identifiers; cross-module join key) per A-0011 |
| T-6012 | POC | DEV | todo | License/Capability catalog models per `LICENSE_MODEL.md` |
| T-6013 | POC | DEV | todo | Full Report model (Internal Detailed + Customer Summary) — replaces ReportPreview from slice |

### 9.2 Evidence lifecycle — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6020 | POC | DEV | todo | Evidence upload endpoint with file validation, hash, manifest read |
| T-6021 | POC | DEV | todo | Module-aware parser dispatch (AD ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON) |
| T-6022 | POC | DEV | todo | Synchronous parse-on-upload (queue-ready service layer per D-0004) |
| T-6023 | POC | DEV | todo | Audit log entries for upload, parse, evaluate, publish, report |

### 9.3 AD module — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6030 | POC | DEV + AD | todo | AD toolkit ZIP parser (manifest + JSON files + PingCastle XML) |
| T-6031 | POC | DEV + AD | todo | Implement controls per `AD_MODULE_DESIGN.md` (Tier 0, kerberos, delegation, GPO subset) |
| ~~T-6032~~ | — | — | moved | Now T-8002 (Stage 8 sample data plan) |

### 9.4 BloodHound Analyzer — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6040 | POC | DEV + BH | todo | SharpHound ZIP parser (users/groups/computers/ous/gpos/domains/acls) |
| T-6041 | POC | DEV + BH | todo | In-memory graph model (networkx-based) + Tier 0 identification |
| T-6042 | POC | DEV + BH | todo | Deterministic shortest-path detection to Tier 0 (per D-0005) |
| T-6043 | POC | DEV + BH | todo | Path categorization (privilege escalation, ACL abuse, delegation) — minimum 3 categories |
| T-6044 | POC | DEV + BH | todo | Template-based path explanations |
| T-6045 | POC | DEV + BH | todo | Findings with cross-module hooks (AD/SF/Entra correlation) |
| ~~T-6046~~ | — | — | moved | Now T-8003 (Stage 8 sample data plan) |

### 9.5 Silverfort module — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6050 | POC | DEV + SF | todo | Manual evidence parser (policies / service accounts / enrollment / entity risk JSON) |
| T-6051 | POC | DEV + SF | todo | Implement controls per `SILVERFORT_MODULE_DESIGN.md` |
| T-6052 | POC | DEV + SF | todo | Connector-design stub (documented, not implemented) per D-0006 |
| ~~T-6053~~ | — | — | moved | Now T-8004 (Stage 8 sample data plan) |

### 9.6 Entra module — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6060 | POC | DEV + ENTRA | todo | Entra JSON evidence parser (users/groups/roles/CA/apps/risky users) |
| T-6061 | POC | DEV + ENTRA | todo | Implement controls per `ENTRA_MODULE_DESIGN.md` |
| T-6062 | POC | DEV + ENTRA | todo | License-aware status logic per D-0007/D-0008 |
| ~~T-6063~~ | — | — | moved | Now T-8005 (Stage 8 sample data plan) |

### 9.7 Correlation — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6070 | POC | DEV + SA | todo | Identity-based join across modules (A-0011) |
| T-6071 | POC | DEV + SA | todo | Produce at least one cross-module correlation finding for demo |

### 9.8 UI shell — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6080 | POC | DEV + UX | todo | App shell (top nav, side nav, footer, ACEN branding) |
| T-6081 | POC | DEV + UX | todo | Overview dashboard (per `UI_DESIGN_DIRECTION.md`) |
| T-6082 | POC | DEV + UX | todo | Customer / engagement / assessment run pages |
| T-6083 | POC | DEV + UX | todo | Module pages (AD, BloodHound, Silverfort, Entra) |
| T-6084 | POC | DEV + UX | todo | Findings workspace (filterable, with detail drawer) |
| T-6085 | POC | DEV + UX | todo | Evidence drawer (lazy, with `customer_visibility` indicator) |
| T-6086 | POC | DEV + UX | todo | License-aware UI states (badges, tooltips) |
| T-6087 | POC | DEV + UX | todo | Publishing modal (default = internal_only) |

### 9.9 Reporting (full) — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6090 | POC | DEV + UX | todo | HTML report templates: Internal Detailed + Customer Summary |
| T-6091 | POC | DEV | todo | (Stretch) PDF render via Playwright |

### 9.10 QA & demo — `horizontal`

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6100 | POC | QA | todo | Acceptance tests covering the demo journey end-to-end |
| T-6101 | POC | QA | todo | Sample data validation tests (parsers + controls produce expected findings) |
| T-6102 | POC | QA | todo | Demo script document (sequence of UI actions for management review) |
| T-9990 | POC | PO | todo | Cycle 9 review — build acceptance against Definition of Done (`WORKING_APPROACH.md` §19) |

## Post-Stage 9 — MVP preparation

Not in scope yet. Placeholder for when POC sign-off (Cycle 9) approves moving toward MVP.

## Future / Full Product backlog stubs

> Captured here so they are not forgotten. **None of these enter the POC backlog.** They land on the Full Product roadmap.

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-F001 | Full | PO + UX + SA | future | **Per-customer co-branding** — `Customer.brand` JSONB (`{logo_url, primary, secondary1, secondary2}`); theme injection only in customer-facing chrome + Customer Summary report; never overrides status colours or module category colours; consultant view never themed. Q-0151 first; Q-0101 sequenced before. Contrast check + status-collision detection + logo asset constraints designed at that stage. |
| T-F002 | MVP  | DEV + PO | future | **Xurrent (4me) outbound integration** — push `RemediationTask` rows from a published Finding into ACEN's Xurrent tenant as a service request; persist `xurrent_request_id` + URL on the task; one-way push first (Q-0160), two-way state sync later. Field mapping: Finding.title → SR subject, severity → priority, remediation (markdown) → SR description, identity_refs → affected CI list. UI: a "Send to Xurrent" action on the Finding detail (consultant only). Connector secrets live in the secret manager at MVP (per `SECURITY_AND_GDPR.md` §10). |
| T-F003 | Full | DEV + PO | future | **Customer-tenant ITSM push (Xurrent / ServiceNow / Jira)** — same shape as T-F002 but pushes into the *customer's* ITSM. Per-customer connector config UI; OAuth/API-token per customer; closed-loop status sync; configurable field mapping. Q-0161. |
| T-F004 | MVP  | DEV + AD | future | **Xurrent CMDB enrichment** (optional, paired with T-F002) — pull asset ownership / business unit / criticality from Xurrent CMDB onto the `Identity` row so prioritization sentences can read *"this Tier 0 service account is owned by Finance"*. Read-only; cached. |

---

*Last updated: 2026-05-15 — operating model upgraded to 9 stages; Stage 8 split from Stage 9; vertical-slice tasks (T-9001..T-9012) marked as the hard gate.*
