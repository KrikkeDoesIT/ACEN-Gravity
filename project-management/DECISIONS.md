# DECISIONS.md

> Log of product, architecture, UX, security, and scope decisions. Each entry is durable: once recorded, decisions are not silently changed — they are superseded by a new dated entry that explicitly references the old one.

Format:

```
### D-NNNN — <short title>
Date: YYYY-MM-DD
Status: proposed | accepted | superseded by D-XXXX | reverted
Owner: <who decided>
Context: <1–3 lines>
Decision: <the actual decision>
Consequences: <what this implies>
Linked: <files / OPEN_QUESTIONS items / ASSUMPTIONS items>
```

---

### D-0001 — Three-tier product roadmap (POC V1 → MVP → Full Product)
Date: 2026-05-14
Status: proposed (pending Cycle 1 sign-off)
Owner: Claude Code on behalf of Kristof
Context: Project scope is broad (4 modules now, 10+ later, multiple sensitive data domains). Without a clear tier separation, POC will drift toward MVP.
Decision: Every feature, control, screen, and document section explicitly declares its tier (POC V1 / MVP / Full Product / Not in scope). POC V1 validates concept on sample data; MVP introduces real connectors and consultant usage; Full Product is customer-facing production.
Consequences: Documents and backlog items without a tier tag are not "ready". Tier discipline is enforced via the §11 complexity checklist in `WORKING_APPROACH.md`.
Linked: `WORKING_APPROACH.md` §4, §11.

### D-0002 — Modular monolith first
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Software Architect role)
Context: A modular customer-facing platform with shared core entities and pluggable modules. Microservices would add operational complexity disproportionate to POC value.
Decision: Build the platform as a modular monolith in Python/FastAPI with clear module boundaries (`platform_core`, `modules/ad`, `modules/bloodhound`, `modules/silverfort`, `modules/entra`). Defer service decomposition until proven necessary.
Consequences: Module boundaries enforced by package layout + dependency rules. No module imports another module directly — correlation happens through the platform core's normalized model.
Linked: `MODULE_ARCHITECTURE.md`.

### D-0003 — Stack baseline: FastAPI + HTMX + Tailwind + PostgreSQL
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Software Architect role)
Context: Kristof's preferred stack. Matches the team's existing PingCastleDashboard work and keeps the frontend simple enough to render server-side without a separate SPA build pipeline.
Decision: Backend = FastAPI + SQLAlchemy + Alembic + Pydantic. Frontend = Jinja2 templates + HTMX + Tailwind CSS + Alpine.js for small interactions only. DB = PostgreSQL. Reports = HTML rendered to PDF via Playwright (PDF optional for POC).
Consequences: No React/Vue. No GraphQL. No microservice runtime. UI is server-rendered with HTMX partials for interactivity.
Linked: `PRODUCT_DESIGN.md` (Recommended Architecture), `MODULE_ARCHITECTURE.md`.

### D-0004 — Background jobs deferred for POC; design for Redis + RQ
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Software Architect role)
Context: POC uses sample evidence; synchronous parse-on-upload is acceptable. Real collectors and BloodHound parsing will need background work.
Decision: POC V1 runs parsing synchronously inside the upload request (single-process). The data model and service layer are designed to be queue-friendly so we can drop in Redis + RQ for MVP without refactor. RQ chosen over Celery/Dramatiq for POC because of lower operational footprint; revisit at MVP.
Consequences: No Redis dependency in POC. Long-running parsing (e.g., a real SharpHound ZIP) is acknowledged as a known limitation, documented in `RISKS.md`.
Linked: `PRODUCT_DESIGN.md`, `RISKS.md`.

### D-0005 — Deterministic BloodHound Analyzer; no AI in the critical path
Date: 2026-05-14
Status: proposed
Owner: Claude Code (BloodHound Analyzer role)
Context: Customers and consultants must be able to audit how a critical path was identified. AI is unreliable for that auditability.
Decision: BloodHound Analyzer detection, ranking, scoring, correlation, and initial explanation are deterministic and template-based. AI may polish language at MVP/Full Product stage **only after** a consultant has reviewed the underlying deterministic output.
Consequences: Algorithms must be documented in code and in `BLOODHOUND_ANALYZER_DESIGN.md`. No LLM dependency for POC.
Linked: `BLOODHOUND_ANALYZER_DESIGN.md`.

### D-0006 — Silverfort: manual-first, API-design-only for POC
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Silverfort Module role)
Context: Public Silverfort API documentation is limited; endpoint behaviour and availability depend on customer version and licensing. Building against unverified endpoints is risky.
Decision: POC V1 accepts manually exported Silverfort evidence only (policies, service accounts, enrollment, entity risk). The API connector is *designed* and documented but not implemented. Every API endpoint claim is tagged "requires validation against official Silverfort documentation / support / customer version".
Consequences: POC demo uses sample files. MVP gating: confirm endpoints with Silverfort before connector implementation.
Linked: `SILVERFORT_MODULE_DESIGN.md`, `OPEN_QUESTIONS.md`.

### D-0007 — License-aware status enum (8 values)
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Product Owner + Software Architect roles)
Context: Customers must not be unfairly penalized for capabilities they do not own. Scoring must distinguish "not licensed" from "licensed but not used".
Decision: Every control result carries a `license_status` with one of 8 values: `licensed_enabled`, `licensed_disabled`, `licensed_misconfigured`, `not_licensed`, `requires_add_on`, `available_in_higher_tier`, `not_applicable`, `unknown`. Plus operational flags: `connector_missing`, `evidence_missing`, `manual_review_required`.
Consequences: Scoring formulas reference `license_status` directly. UI surfaces these states explicitly. Scope of `LICENSE_MODEL.md`.
Linked: `LICENSE_MODEL.md`, `PRODUCT_DESIGN.md` (Scoring Model).

### D-0008 — Two scores per assessment: Current License Score and Target Posture Score
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Product Owner role)
Context: Customers need to see both "are you using what you bought?" and "where could you be with investment?".
Decision: Two scores per module and per engagement: (1) Current License Security Score — based only on capabilities the customer actually owns; (2) Target Security Posture Score — based on the recommended posture regardless of current licensing. The gap between them is the **Opportunity Score**.
Consequences: Scoring engine computes both. Reports present both, side by side. "Not licensed" never reduces the Current License Score.
Linked: `LICENSE_MODEL.md`, `PRODUCT_DESIGN.md` (Scoring Model).

### D-0009 — Customer publishing is explicit, not default
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Security & GDPR role)
Context: Sensitive data (privileged accounts, attack paths, GPO weaknesses) must not leak to customers by default. Consultants curate what is shared.
Decision: Every finding and evidence item has a `customer_visibility` flag: `internal_only` (default), `customer_summary` (executive-grade summary, no technical detail), `customer_full` (full detail). Publishing requires explicit consultant action. POC enforces this in the UI; full enforcement at MVP.
Consequences: Reports come in two flavours: Internal and Customer. Audit log records publishing events. Default is *never publish*.
Linked: `SECURITY_AND_GDPR.md`, `PRODUCT_DESIGN.md` (Reporting Model).

### D-0010 — ACEN brand guide is the visual source of truth (with one digital adaptation)
Date: 2026-05-14
Status: proposed
Owner: Claude Code (UX role)
Context: The ACEN 2025 brand guide specifies straight (square) corners on frames, plus a defined palette and typography. Strict square corners may hurt web usability for some controls.
Decision: Follow the ACEN 2025 guide for typography, palette, graphics, and layout. **Allow one digital adaptation**: a very small border-radius (≤ 2px) on interactive controls (buttons, inputs, cards) where strict square corners would noticeably hurt clarity or affordance. Non-interactive frames (sections, page borders, image frames) remain square. Documented in `UI_DESIGN_DIRECTION.md`.
Consequences: Visual design retains brand identity while remaining usable. Any deviation must be documented in `UI_DESIGN_DIRECTION.md`.
Linked: `UI_DESIGN_DIRECTION.md`.

### D-0011 — Sample/synthetic data only in repository; no real customer evidence
Date: 2026-05-14
Status: proposed
Owner: Claude Code (Security & GDPR role)
Context: Real AD, BloodHound, Silverfort, or Entra data would create GDPR and customer-confidentiality risk if committed to a repository.
Decision: Repository contains only synthetic / fabricated sample data. Real customer evidence is never committed to git. Sample data lives under `tests/fixtures/` with a clear `SAMPLE_DATA_README.md` explaining provenance.
Consequences: Test datasets must be designed (synthetic AD forest, synthetic SharpHound graph, etc.). `.gitignore` rules enforce this for evidence upload directories.
Linked: `SECURITY_AND_GDPR.md`, `TASKS.md`.

---

*Last updated: 2026-05-14.*
