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

## Stage 6 — POC backlog (build tasks)

> These are placeholder implementation tasks. They are not "ready" until cycles 1–5 are signed off. Reordered and refined at Cycle 6.

### 6.1 Project skeleton

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6001 | POC | DEV | todo | Initialize Python project (pyproject.toml, ruff, mypy, pytest) |
| T-6002 | POC | DEV | todo | FastAPI app scaffolding + Jinja2 + Tailwind build pipeline (no Node SPA) |
| T-6003 | POC | DEV | todo | PostgreSQL + Alembic baseline migration |
| T-6004 | POC | DEV | todo | Folder layout per `MODULE_ARCHITECTURE.md` (`platform_core/`, `modules/{ad,bloodhound,silverfort,entra}/`) |
| T-6005 | POC | DEV | todo | Simple role-switching "login" (no real auth) per A-0013 |

### 6.2 Shared core data model

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6010 | POC | DEV | todo | SQLAlchemy models: Organization, Customer, User, Role, Engagement, AssessmentRun |
| T-6011 | POC | DEV | todo | SQLAlchemy models: Module, Artifact, Evidence, Control, ControlResult |
| T-6012 | POC | DEV | todo | SQLAlchemy models: Finding, RemediationTask, Report, AuditLog |
| T-6013 | POC | DEV | todo | Identity entity (canonical identifiers; cross-module join key) per A-0011 |
| T-6014 | POC | DEV | todo | License/Capability catalog models per `LICENSE_MODEL.md` |

### 6.3 Evidence lifecycle

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6020 | POC | DEV | todo | Evidence upload endpoint with file validation, hash, manifest read |
| T-6021 | POC | DEV | todo | Module-aware parser dispatch (AD ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON) |
| T-6022 | POC | DEV | todo | Synchronous parse-on-upload (queue-ready service layer per D-0004) |
| T-6023 | POC | DEV | todo | Audit log entries for upload, parse, evaluate, publish, report |

### 6.4 AD module

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6030 | POC | DEV + AD | todo | AD toolkit ZIP parser (manifest + JSON files + PingCastle XML) |
| T-6031 | POC | DEV + AD | todo | Implement controls per `AD_MODULE_DESIGN.md` (Tier 0, kerberos, delegation, GPO subset) |
| T-6032 | POC | AD | todo | Synthetic AD evidence ZIP for "Contoso Corp" demo |

### 6.5 BloodHound Analyzer

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6040 | POC | DEV + BH | todo | SharpHound ZIP parser (users/groups/computers/ous/gpos/domains/acls) |
| T-6041 | POC | DEV + BH | todo | In-memory graph model (networkx-based) + Tier 0 identification |
| T-6042 | POC | DEV + BH | todo | Deterministic shortest-path detection to Tier 0 (per D-0005) |
| T-6043 | POC | DEV + BH | todo | Path categorization (privilege escalation, ACL abuse, delegation) — minimum 3 categories |
| T-6044 | POC | DEV + BH | todo | Template-based path explanations |
| T-6045 | POC | DEV + BH | todo | Findings with cross-module hooks (AD/SF/Entra correlation) |
| T-6046 | POC | BH | todo | Synthetic SharpHound ZIP for "Contoso Corp" with ≥ 3 Tier 0 paths |

### 6.6 Silverfort module

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6050 | POC | DEV + SF | todo | Manual evidence parser (policies / service accounts / enrollment / entity risk JSON) |
| T-6051 | POC | DEV + SF | todo | Implement controls per `SILVERFORT_MODULE_DESIGN.md` |
| T-6052 | POC | DEV + SF | todo | Connector-design stub (documented, not implemented) per D-0006 |
| T-6053 | POC | SF | todo | Synthetic Silverfort evidence for "Contoso Corp" |

### 6.7 Entra module

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6060 | POC | DEV + ENTRA | todo | Entra JSON evidence parser (users/groups/roles/CA/apps/risky users) |
| T-6061 | POC | DEV + ENTRA | todo | Implement controls per `ENTRA_MODULE_DESIGN.md` |
| T-6062 | POC | DEV + ENTRA | todo | License-aware status logic per D-0007/D-0008 |
| T-6063 | POC | ENTRA | todo | Synthetic Entra JSON evidence for "Contoso Corp" |

### 6.8 Correlation

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6070 | POC | DEV + SA | todo | Identity-based join across modules (A-0011) |
| T-6071 | POC | DEV + SA | todo | Produce at least one cross-module correlation finding for demo |

### 6.9 UI shell

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

### 6.10 Reporting

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6090 | POC | DEV + UX | todo | HTML report templates: Internal Detailed + Customer Summary |
| T-6091 | POC | DEV | todo | (Stretch) PDF render via Playwright |

### 6.11 QA & demo

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-6100 | POC | QA | todo | Acceptance tests covering the demo journey end-to-end |
| T-6101 | POC | QA | todo | Sample data validation tests (parsers + controls produce expected findings) |
| T-6102 | POC | QA | todo | Demo script document (sequence of UI actions for management review) |

## Stage 7 — Management review

| ID | Tier | Owner | Status | Task |
|---|---|---|---|---|
| T-7001 | POC | PO + DOC | todo | Management deck (≤ 15 slides) |
| T-7002 | POC | PO | todo | Run demo with management, capture go/no-go decision |

## Stage 8 — Build preparation (MVP)

Not in scope yet. Placeholder.

---

*Last updated: 2026-05-15.*
