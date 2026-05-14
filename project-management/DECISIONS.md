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

### D-0012 — Operating model split into 9 stages (Stage 8 = Build prep; Stage 9 = POC build)
Date: 2026-05-15
Status: proposed (pending Cycle 1 sign-off of updated `WORKING_APPROACH.md`)
Owner: Kristof (requested) / Claude Code (drafted)
Context: The previous 8-stage model bundled "build preparation" and "POC build" into a single Stage 8. This blurred a meaningful boundary: preparation is documentation + skeleton + sample data + handoff (no business code); build is implementation against the prepared backlog. Bundling them invites premature coding.
Decision: Split into Stage 8 (Build preparation: final POC backlog, architecture skeleton with no business logic, sample data plan, developer handoff, implementation task structure with the first vertical slice marked) and Stage 9 (POC build: working POC, tests where practical, demo flow, report preview, management review pack). Stage 8 ends with Cycle 8 sign-off; Stage 9 ends with Cycle 9 sign-off against the Definition of Done.
Consequences: `WORKING_APPROACH.md` §4 (stage map), §9 (review cycles), §16 (sessions), §18 (DoR), §22 (next step). `PROJECT_STATE.md`, `TASKS.md`, `REVIEW_NOTES.md` extended to 9 stages / 9 cycles. No code starts before Cycle 8 sign-off.
Linked: `WORKING_APPROACH.md`, `PROJECT_STATE.md`, `TASKS.md` (Stage 8 + Stage 9), `REVIEW_NOTES.md`.

### D-0013 — POC V1 demo story is the project's north star
Date: 2026-05-15
Status: proposed
Owner: Kristof / Claude Code
Context: A broad POC scope across four modules invites scope creep unless one concrete demo story is the authoritative scope filter. Without a north-star story, every interesting idea finds a way into POC V1 and the management decision point is missed.
Decision: Adopt one demo story (`WORKING_APPROACH.md` §3) as the authoritative scope filter for POC V1. Every feature, screen, control, and document section must support this story. If it does not, it is mocked, postponed, or removed.

> *"We upload AD evidence, BloodHound data, Silverfort evidence, and mocked Entra data for one customer. The platform identifies a critical AD attack path, shows that the involved account lacks Silverfort coverage, links the account to Entra privileged context, generates a prioritized finding, creates a remediation task, and produces a customer-ready report section."*

Consequences: The demo story is the anchor for Cycle 7 management review. Sample data is shaped to make it run end-to-end (D-0015). Vertical slice scope (D-0014) is derived directly from it. New `WORKING_APPROACH.md` §3, §14 checklist items, §16 Session 1.
Linked: `WORKING_APPROACH.md`, `POC_V1_SCOPE.md` §4 demo journey.

### D-0014 — Thin vertical slice first; no horizontal expansion until the slice is proven
Date: 2026-05-15
Status: proposed
Owner: Claude Code (Software Architect role) + Kristof
Context: Building four module pages in parallel produces four half-finished surfaces and no proven lifecycle. The risk: management sees impressive screens but no end-to-end story.
Decision: Stage 9 starts with one end-to-end vertical slice (Customer → Assessment Run → AD + BH evidence load → one critical path parsed → one Finding → review → publish → customer-visible view → one Report preview). Horizontal expansion to Silverfort, Entra, full control catalog, cross-module correlation, additional UI pages, and additional reports starts **only** after the slice is reviewed and signed off.
Consequences: `TASKS.md` Stage 9 reorganized into `9.0 Vertical slice (HARD GATE)` followed by `9.1+ horizontal` work. Slice tasks are tagged `slice`; horizontal tasks are tagged `horizontal` and blocked on slice review. New `WORKING_APPROACH.md` §6.
Linked: `WORKING_APPROACH.md` §6, `TASKS.md` (Stage 9).

### D-0015 — Sample data plan is a Stage 8 deliverable; ownership split (realism vs structure/safety)
Date: 2026-05-15
Status: proposed
Owner: Kristof (realism owner) + Claude Code (structure/safety/docs owner)
Context: Sample data quality directly determines whether the POC demo lands or feels like a toy (R-0009). Without explicit ownership, sample data quality slips between roles.
Decision: Sample data is a named Stage 8 deliverable (`WORKING_APPROACH.md` §13). Kristof validates whether each dataset is realistic from a security / domain perspective (would a consultant find it credible?). Claude Code ensures the data is safe to commit (synthetic, anonymized, or sanitized — never real customer evidence), structured (loadable via the same code path real evidence would use), documented (`SAMPLE_DATA_README.md`), and isolated under `tests/fixtures/`.
Consequences: New `WORKING_APPROACH.md` §13. `TASKS.md` §8.2 owns the implementation; T-8007 records Kristof sign-off on realism. Re-affirms D-0011 (synthetic-only).
Linked: D-0011, `WORKING_APPROACH.md` §13, `TASKS.md` §8.2, `RISKS.md` (R-0009, R-0014).

### D-0016 — POC V1 kill criteria are explicit and feed the Cycle 7 management decision
Date: 2026-05-15
Status: proposed
Owner: Kristof + ACEN management
Context: The POC exists to validate the concept, including the possibility of validating it *negatively* (a go/no-go decision on MVP investment). Without explicit kill criteria, the decision drifts toward "looks good, let's continue" by default.
Decision: A list of 10 kill criteria (`WORKING_APPROACH.md` §20) is reviewed at Cycle 7 (and re-applied at Cycle 9). If any criterion is clearly true, the project does not proceed to MVP as-is; the response is documented as one of: reduce scope, adjust demo journey, postpone feature, or stop MVP investment. Triggering a kill criterion is **not failure** — it is the POC doing its job.
Consequences: Management review pack must walk through each kill criterion and record the decision. `RISKS.md` references the criteria. New `WORKING_APPROACH.md` §20.
Linked: `WORKING_APPROACH.md` §20, `RISKS.md`.

### D-0017 — Documentation control rules (size cap, executive summary, no duplication)
Date: 2026-05-15
Status: proposed
Owner: Claude Code (Documentation / Reviewer role)
Context: Several module design docs already exceed ~800 lines (AD, BloodHound, Silverfort, Entra). Without explicit control rules, documentation grows into a second product to maintain and review burden rises.
Decision: Documentation is governed by explicit rules (`WORKING_APPROACH.md` §15): focused per file, cross-reference instead of duplicate, executive summary at the top of docs ≥ ~400 lines, soft ~800-line cap triggers a per-doc decision (summary / appendix split / accept). Updating existing docs is preferred over creating new versions. The Documentation / Reviewer role actively applies these rules.
Consequences: Per-doc decisions at Cycle 3 review for the four module docs that exceed the cap. New `REVIEW_NOTES.md` items for any duplication found. `WORKING_APPROACH.md` includes an executive summary at the top (now ~600 lines).
Linked: `WORKING_APPROACH.md` §15, `REVIEW_NOTES.md`.

---

*Last updated: 2026-05-15 — D-0012 … D-0017 added for the 9-stage operating-model update.*
