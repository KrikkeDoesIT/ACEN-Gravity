# CHANGELOG.md

> Log of meaningful changes to documentation, scope, decisions, architecture, and (later) code. One entry per work session, newest first.

Format:

```
## YYYY-MM-DD — <session title>
Stage: <0–8>
By: <role / who>
Added:
  - <bullet>
Changed:
  - <bullet>
Removed:
  - <bullet>
Decisions:
  - D-NNNN (see DECISIONS.md)
Tasks moved:
  - T-NNNN → status
Open questions touched:
  - Q-NNNN
```

---

## 2026-05-15 — Stage 9 horizontal expansion — Chunk D (module pages with archetypes)

Stage: 9.8 (horizontal expansion)
By: Claude Code.

Per `WORKING_APPROACH.md` §6 (no horizontal expansion until the slice is
reviewed) and D-0018 (each module gets its own page archetype on a shared
frame), this chunk turns the four dead side-nav links into real pages —
**every** module is now navigable and renders its archetype-defining
surface.

Added — route + dispatcher
- `src/platform_core/web/routes/modules.py` — `GET /modules/{module_id}`.
  Loads the most-recent run, filters findings by `customer_visibility`
  for non-consultant roles (defence-in-depth), assembles per-archetype
  `page_data` (paths for BH, coverage matrix for SF, posture categories
  for AD, license-aware placeholders for Entra), and renders the right
  template. 404 on unknown module ids.

Added — shared partials
- `templates/components/module_header.html` — breadcrumb (Overview / Module
  / Customer), accent-coloured module mark, archetype-label pill,
  severity strip (one chip per severity present).
- `templates/components/module_no_data.html` — accent-coloured empty state
  with module-specific copy.

Added — four archetype templates
- **`module_ad.html` — Posture archetype**:
  - 5 category status cards (Health / Privileged / Kerberos / Delegation /
    GPO); only Privileged is "Evaluated" in the slice — others show a
    "Pending" pill so the archetype's shape is visible.
  - Control-coverage donut (placeholder until the full control catalog
    lands — 1/5 categories evaluated; svc-backup flagged as service
    account in the mini-stats).
  - Top-findings priority list with link-through to `/findings/{id}`.
  - Privileged-group membership table (real data from the AD parser:
    Domain Admins / Enterprise Admins / Domain Controllers + their
    members).
- **`module_bloodhound.html` — Attack-path archetype**:
  - 3 context KPIs (Tier 0 reachable, Top category, Graph size). **No
    control-coverage ring** — paths are the unit per D-0018.
  - Ranked critical paths list (the page's defining surface): rank,
    severity pill, category, hops, inline path-step preview, risk
    score, click-through to the BH finding's detail.
  - Per-row mini path renders the full chain inline so consultants can
    scan paths at a glance without opening each finding.
- **`module_silverfort.html` — Coverage archetype**:
  - 3 context KPIs (Connector status — always Pending in POC per D-0006,
    Tier 0 coverage %, Coverage gaps count).
  - **`CoverageMatrix`** — sticky-left identity column × policy columns
    × cells (Covered / Excluded / n.a.) + sticky-right Overall column
    (OK / Gap / n.a.). Excluded cells are the actionable rows.
  - Coverage-gap finding list at the bottom (links to SF-AD-001).
- **`module_entra.html` — License-aware tenant config archetype**:
  - 6 placeholder cards (Licensing & Capability / Conditional Access /
    Privileged Roles / Authentication Methods / Apps & Service
    Principals / Hybrid Identity) — each carries a `LicenseBadge`
    showing `Unknown` until the Entra parser lands.
  - Opportunity card placeholder explaining the License-aware story
    (D-0008: `not_licensed` never reduces the Current License Score).
  - No-data state at the bottom.

Side-nav
- `components/side_nav.html` — module links now point to
  `/modules/{module_id}` with the matching module's accent on the
  active pill (Turquoise / Rose / Violet / Sky). `active_module_id` and
  `active_nav` both supported so pages can set either marker.

Tests
- `tests/test_slice_chunk_d.py` — 10 tests:
  - Route plumbing: redirect when no persona; 404 on unknown module;
    pages render the no-data state on an empty DB.
  - AD: posture category names + privileged-membership table render
    real identities (svc-backup, it.admin.kristof, Domain Admins),
    service-account flag visible, archetype label rendered.
  - BloodHound: "Attack-path archetype" label, Tier 0 reachable KPI,
    ACL abuse category, GenericAll / MemberOf edge labels in the inline
    preview, Domain Admins target, graph-size KPI (nodes/edges).
  - Silverfort: Coverage archetype label, Pending connector pill,
    CoverageMatrix renders Tier 0, Excluded/Gap markers, coverage %
    computed, svc-backup gap visible.
  - Entra: License-aware label, six placeholder cards (Jinja-escaped
    `&amp;`), Opportunity card placeholder, no-data state.
  - Side-nav: every module link is `/modules/{id}`; active pill applies
    to the right module (Silverfort gets `bg-support-violet/15` when
    active).
  - Role visibility: customer roles can hit the pages too (chrome is
    shared; finding visibility is filtered at the route level).

Verified
- `pytest -q` → **46 passed** (9 smoke + 9 A + 9 B + 9 C + 10 D).
- `ruff check src tests` → clean. Per-file ignore added for the four
  archetype builder functions in `modules.py` (they keep a uniform
  signature even when not all params are used yet).
- Live HTTP probe: every module page returns 200; full demo journey
  still passes end-to-end.

Tasks moved
- T-9020 (route + dispatcher), T-9021 (AD page), T-9022 (BH page),
  T-9023 (SF page), T-9024 (Entra page), T-9025 (side-nav wiring) → done.

Decisions: none new — D-0018 (archetypes) realised in code.

Recommended next step
- **Chunk E — Entra module (parser + manifest + license-aware controls +
  real data on the Entra page)**: this completes the 4-module promise
  from `POC_V1_SCOPE.md` and unlocks the second cross-module correlation
  story (BH path → hybrid admin overlap). Also realistic for the
  management Cycle 7 demo to have all four modules actually populated.

---

## 2026-05-15 — Stage 9 vertical slice — Chunk C (Silverfort + correlation + HTML report)

Stage: 9.0 (vertical slice — Chunk C of 3) — **slice complete**, awaiting T-9012 review
By: Claude Code.

Closes the full demo story per `WORKING_APPROACH.md` §3:

> *"We upload AD evidence, BloodHound data, Silverfort evidence and mocked
> Entra data for one customer. The platform identifies a critical AD attack
> path, shows that the involved account lacks Silverfort coverage, links
> the account to Entra privileged context, generates a prioritized finding,
> creates a remediation task, and produces a customer-ready report section."*

(Entra is mocked for the slice as planned; the headline correlation lands
without it.)

Added — Silverfort fixture
- `tests/fixtures/contoso/silverfort/export.json` — 2 policies (1 enabled
  Tier 0 MFA policy; 1 disabled service-account policy). The enabled
  policy targets Domain Admins + Enterprise Admins as groups, and
  it.admin.kristof as a direct user, **but explicitly excludes
  svc-backup** — the realistic gap consultants see in real Silverfort
  deployments (service accounts can't interactively MFA, so they get
  exempted).

Added — Silverfort module
- `src/modules/silverfort/parsers/export.py` — reads the export bundle,
  computes coverage (direct target users + Tier-0-group expansion via
  Identity rows from the AD parser, minus excluded users), emits the
  `SF-AD-001 Tier 0 Coverage Gap` Finding (HIGH, risk=72) when any Tier 0
  user is uncovered. Payload contains the uncovered SIDs, friendly
  labels, and which policy excluded them.

Added — cross-module correlation
- `src/platform_core/correlations/__init__.py` — `run_correlations()`
  orchestrator + `CORR-BH-SF-001` rule. For every BloodHound finding, the
  rule checks whether any identity on the path (target OR intermediate
  pivot) is in the Silverfort coverage gap. Two outcomes:
  - **Pivot through the gap** (path target ∉ gap, but a step is) →
    severity bumped one rung (HIGH → CRITICAL); risk_score × 1.15.
    Title: *"Critical correlation: BloodHound path to Tier 0 (`Domain
    Admins`) pivots through `svc-backup`, which is excluded from
    Silverfort coverage"*.
  - **Path lands on the gap** (target ∈ gap) → bumped (MEDIUM → HIGH).
    Title: *"BloodHound path reaches `svc-backup` AND that account is
    excluded from Silverfort coverage"*.
  - Idempotent on (run, BH source SID, BH target SID).
  - Identity refs aggregated from BH + the gap account.
  - All consistent with D-0005 (deterministic; no AI).

Added — CLI integration
- `gravity demo load` extended: runs the SF parser after BH, then runs
  correlations. Audit event `demo.load` payload now includes
  `sf_uncovered_tier0_count` + `correlation_finding_ids`.

Added — Reports UI
- `src/platform_core/web/routes/reports.py`:
  - `GET /reports` — list of assessment runs with customer/engagement
    breadcrumbs, severity counts, and a variant chip showing whether the
    role will see Internal Detailed or Customer Summary.
  - `GET /reports/{run_id}` — HTML report preview rendered from
    `report_preview.html`. Same template, two variants: consultant sees
    every finding + internal summaries + technical details + remediation;
    customer roles see only `customer_summary` / `customer_full`
    findings, customer-framed summaries, technical detail collapsed
    behind `<details>` for `customer_full` only.
  - Headline finding selected automatically: highest-severity
    `correlation` finding if any, else highest-severity overall.
  - Visibility filter server-side (defense in depth).
- `src/platform_core/web/templates/reports_list.html` + `report_preview.html`:
  - Cover page with ACEN wordmark + customer + engagement + run + UTC
    timestamp + executive sentence + severity strip.
  - Headline finding card with risk/source/reaches mini-cards + the
    attack path rendered as a step list with **`⚠ SF gap`** markers on
    the uncovered hops.
  - Per-module sections (correlation / BH / SF / AD / Entra) in priority
    order, each with severity pill, category, state (internal only),
    risk score, finding summary, collapsible technical-detail block,
    collapsible remediation block.
- `side_nav.html`: `/reports` link real + active-pill aware.

Tests
- `tests/test_slice_chunk_c.py` — 9 new tests:
  - SF parser identifies svc-backup as the uncovered Tier 0.
  - `SF-AD-001` finding emitted at HIGH severity.
  - Correlation findings: every one references the SF gap; headline is
    CRITICAL "pivots through" with friendly labels.
  - Idempotency: 2× `demo load` → 2 runs with identical per-run
    correlation counts.
  - `/reports` list: consultant sees "Internal detailed", customer
    executive sees "Customer summary".
  - `/reports/{run_id}` preview:
    - Consultant: "Internal Detailed Report" + Technical detail block +
      "Domain Admins" + "svc-backup" + "GenericAll".
    - Customer executive (after publish at `customer_summary`):
      "Customer Summary" + headline phrase ("An attack path…") + no
      `Summary — internal` block.
    - `customer_full` published: technical detail visible.

Verified
- `pytest -q` → **36 passed** (9 smoke + 9 A + 9 B + 9 C).
- `ruff check src tests` → clean.
- Live HTTP probe: consultant `/reports/{id}` 200; publishes headline
  correlation 303; customer-exec `/reports` 200 + `/reports/{id}` 200
  with "Critical correlation", "Domain Admins", "svc-backup", and "SF gap"
  all rendering.

Tasks moved
- T-9010 (report preview HTML) → done.
- T-9012 (slice review) → still todo but **ready for the walkthrough**:
  the slice runs end-to-end, no manual hacks, all assertions hold.

Also logged in this session
- Q-0160 (Xurrent / 4me outbound integration at MVP) + Q-0161
  (customer-tenant ITSM push at Full Product) in `OPEN_QUESTIONS.md` §17.
- T-F002 (Xurrent integration), T-F003 (customer-tenant ITSM), T-F004
  (Xurrent CMDB enrichment) in `TASKS.md` Future / Full Product backlog.
- `PRODUCT_DESIGN.md` §12 (MVP) mentions outbound integrations starting
  with Xurrent.

Decisions: (no new D-NNNN — Chunk C uses the existing decision set).

Recommended next step
- **T-9012 slice review** with Kristof: live walk of the demo journey
  end-to-end at <http://127.0.0.1:8001>. If approved, the POC is feature-
  complete for the management Cycle 7 decision. The remaining Stage 9
  work is then horizontal expansion (other module pages, additional
  controls), which per `WORKING_APPROACH.md` §6 only starts after slice
  review.

---

## 2026-05-15 — Stage 9 vertical slice — Chunk B (triage → publish → audit per state change)

Stage: 9.0 (vertical slice — Chunk B of 3)
By: Claude Code.

The slice now has the full **finding lifecycle**: a consultant triages a
finding, sets customer visibility, publishes (one-click composite action),
and the customer executive immediately sees the published version. Every
state change, visibility change, and publish event is recorded in the audit
log at `/audit`.

Added — workflow module
- `src/platform_core/findings/workflow.py`:
  - `ALLOWED_TRANSITIONS` — explicit state machine: `new ↔ triaged ↔ published ↔ retest_requested ↔ closed` with rollback edges. Invalid transitions raise a typed `TransitionError`.
  - `transition_state` — moves a Finding to a target state; writes a `finding.state_change` AuditEvent (severity = notable).
  - `set_visibility` — changes `customer_visibility`; writes a `finding.visibility_change` AuditEvent (severity = security).
  - `publish_finding` — composite action: sets visibility (must be `customer_summary` or `customer_full`), transitions state to `published`, and writes a composite `finding.publish` audit event. Auto-triages findings that are still `new`.
  - All functions are session-pure (do not commit) and authority-agnostic — route layer enforces "consultant only".

Added — routes (`src/platform_core/web/routes/findings.py`)
- `POST /findings/{id}/state` — consultant transitions a finding state via form; flash message on success/error.
- `POST /findings/{id}/visibility` — consultant sets `customer_visibility`.
- `POST /findings/{id}/publish` — composite publish (visibility + state) in one step.
- `GET /audit` — consultant-only view; lists the 200 most recent audit events with actor, event type, severity, target, payload summary.
- `_ensure_consultant` helper raises 403 for non-consultant roles on every mutation route.
- Flash messages via signed session cookie (`_FLASH_KEY`).

Added — templates
- `components/flash.html` — colour-coded banner partial (ok / error / warn / info).
- `audit_log.html` — table view with severity-coloured pills + payload pretty-print per known event type (`state_change` / `visibility_change` / `publish` / generic).
- `finding_detail.html` — actions sidebar now wired:
  - **State** card: shows current state + form buttons for every allowed transition (auto-filtered by the state machine).
  - **Customer visibility** card: three buttons (internal_only / customer_summary / customer_full); the current one is disabled.
  - **Publish to customer** card: two one-click buttons (executive summary / full technical detail) that compose visibility + state in one action. After publish, the card flips to a "Published" confirmation with an "Unpublish" rollback.
- `findings_list.html` + `audit_log.html`: flash banner rendered at the top.
- `components/side_nav.html`: `/audit` link real and active-pill aware.

Verified
- `pytest -q` → **27 passed** (9 smoke + 9 Chunk A pipeline/UI + 9 Chunk B):
  - State machine walks new → triaged → published → closed; invalid `new → published` is rejected with flash, state unchanged.
  - Customer executive forbidden (403) from any mutation endpoint.
  - Visibility change creates a `finding.visibility_change` audit event with `from`/`to` payload at severity=`security`.
  - Invalid visibility value rejected with flash.
  - One-click publish from `state=new` auto-triages → publishes → sets visibility → writes 2 state-change events + 1 visibility-change event + 1 composite `finding.publish` event.
  - Publishing with `internal_only` is blocked (returns flash "Publishing requires customer_summary or customer_full").
  - After publish, the customer executive sees the finding in the list and on the detail page; "Summary — internal" block does NOT render for customer roles; "Summary — customer framing" does.
  - Audit log view returns 200 for consultant, 403 for customer executive.
- `ruff check src tests` → clean.
- Live HTTP probe: consultant `POST /findings/{id}/publish` 303 → `GET /audit` 200 → customer-executive `GET /findings` 200 (now shows ACL abuse) → customer-executive `GET /findings/{id}` 200.

Tasks moved
- T-9007 (triage), T-9008 (publish), T-9009 (customer-visible view), T-9011 (audit log per change) → done.

Decisions
- (no new D-NNNN)

Recommended next step
- Try it: log in as consultant, open a finding, click "Publish — executive summary". Switch to Customer Executive via the header dropdown. The finding is now visible. Check `/audit` to see the full trail.
- Chunk C next: Silverfort coverage stub + cross-module correlation finding ("Tier 0 service account lacks Silverfort coverage") + HTML report preview. That closes Stage 9 vertical-slice scope and trips T-9012 (slice review).

---

## 2026-05-15 — Stage 9 vertical slice — Chunk A (data → finding → UI, end-to-end)

Stage: 9.0 (vertical slice — Chunk A of 3)
By: Claude Code at Kristof's "let's start phase 2 now".

This is the first real-business-logic milestone. The Contoso Corp synthetic
fixture loads end-to-end through the platform: AD evidence → BloodHound graph
→ deterministic path detection → template-based Finding generation → UI list
+ detail with role-aware customer-visibility enforcement.

Added — persistence
- `D-0024` logged: SQLite is the temporary persistence backend until WSL/podman/Postgres unblocks. Same SQLAlchemy 2.x + Alembic toolchain targets either engine; only `DATABASE_URL` changes. JSON columns use the portable `sqlalchemy.JSON` type.
- `pyproject.toml` adds `networkx>=3.4`, `typer>=0.15`, and a `gravity` console-script entry point.
- `alembic.ini` + `migrations/env.py` + `migrations/script.py.mako` — Alembic configuration that reads `DATABASE_URL` from the runtime settings and ensures the SQLite parent directory exists.
- `migrations/versions/20260515_*_baseline_slice_schema.py` — baseline migration creating all 7 slice tables.
- `.env.example` `DATABASE_URL` default flipped to `sqlite:///./var/gravity.db`; Postgres URL kept as a commented alternative.
- `.gitignore` extended with `var/`, `*.db`, `*.db-journal`, etc.

Added — slice models (`src/platform_core/`)
- `db.py` — `Base`, lazy engine factory (creates SQLite parent dir), session factory, `get_db` FastAPI dep, `reset_for_tests` for isolated test DBs.
- `models/mixins.py` — `UuidPk` (Python-generated 36-char string UUID PKs) + `Timestamps` mixin.
- `models/core.py` — `Customer`, `Engagement`, `AssessmentRun` with FK + cascade relationships.
- `identity/models.py` — `Identity` (canonical cross-module join key per `MODULE_ARCHITECTURE.md` §8) with SID / UPN / sAMAccountName / ObjectGUID / Azure ObjectId fields + `is_privileged`/`is_tier0`/`is_breakglass` flags.
- `evidence/models.py` — `Evidence` (one parsed view per module per run, with JSON payload).
- `findings/models.py` — `Finding` with the 8-value `LicenseStatus`, 5-value `Severity`, 5-value `FindingState`, 3-value `CustomerVisibility` StrEnums, identity_refs[], module payload[].
- `audit/models.py` — `AuditEvent` (append-only).
- `models/registry.py` — single import-once module to register every model on `Base.metadata` without circular imports. Imported by Alembic env + CLI + (later) app.

Added — Contoso Corp synthetic fixture (`tests/fixtures/contoso/`)
- `README.md` documenting the headline attack path: `contractor.john → MemberOf → Helpdesk → GenericAll → svc-backup → MemberOf → Domain Admins (Tier 0)`. Three edges, classic ACL abuse + service-account exposure + Tier 0 group membership.
- `customer.json` (Contoso Corp metadata).
- `ad/manifest.json` + `ad/privileged-groups.json` — AD toolkit-shaped evidence.
- `sharphound/{domains,users,groups,computers}.json` — SharpHound CE format JSON (meta.version=6). 12 nodes, 6 edges, 3 well-known Tier 0 group RIDs.

Added — modules (`src/modules/`)
- `ad/parsers/privileged_groups.py` — reads the AD privileged-groups JSON; upserts `Identity` rows (idempotent on customer+SID); promotes `is_privileged`/`is_tier0` flags; never demotes.
- `bloodhound/parsers/sharphound.py` — reads SharpHound CE JSON; builds a directed networkx graph (nodes per principal, edges per `MemberOf` + per `Aces`); identifies Tier 0 via well-known RIDs (512/518/519/516/...) + transitive group membership. Edge severity weights map per `BLOODHOUND_ANALYZER_DESIGN.md` §8.
- `bloodhound/analyzer.py` — deterministic shortest-path detection (severity-weighted Dijkstra: high-severity edges → low distance → preferred). Caps: max length 8, top K=3 per source, top N=50 considered, top 5 reported. `_categorise` uses the first-match priority order from REVIEW_NOTES item 8. `_risk_score` per the formula in §13.
- `bloodhound/findings.py` — template-based Finding generator with 5 category templates (`acl_abuse`, `group_nesting_priv_esc`, `delegation`, `dcsync`, `privilege_escalation`). Each template substitutes path data; the `template_id` is stored on the Finding so explanations are reproducible (D-0005). Severity bands per REVIEW_NOTES item 6.

Added — CLI (`src/platform_core/cli.py`)
- `gravity demo load` — idempotent fixture loader (Customer + Engagement upsert; new AssessmentRun per load). Runs the full pipeline: load metadata → AD parser → SharpHound parser → graph build → path detection → Finding generation → AuditEvent. Rich console output with the headline findings.

Added — UI routes (`src/platform_core/web/routes/findings.py`)
- `GET /findings` — list view with severity / module / risk / state / visibility columns. Consultant sees all; customer roles see only `customer_summary` / `customer_full` findings (server-side filter).
- `GET /findings/{id}` — detail view with:
  - Title + severity + module + state + risk_score header.
  - Internal summary (consultant only).
  - Customer-framed summary (all roles when visibility permits).
  - Technical detail (consultant + `customer_full` only).
  - **Path-step list** (BloodHound findings only) — each step shows source identity, edge type with severity-tinted badge, target identity. Reusable `PathStepList` pattern from `UI_DESIGN_DIRECTION.md` §13.
  - Remediation block.
  - Properties sidebar (category, license_status, state, customer_visibility, identity_refs count).
  - Actions sidebar (Mark triaged / Set visibility / Publish — all stubbed for Chunk B).
- Customer roles get a 404 (not 403, to avoid leaking the existence of internal-only findings) when hitting an `internal_only` finding's detail URL.

Templates
- `findings_list.html`, `finding_detail.html` — built from the existing component vocabulary (`Card`, `StatusBadge`, severity pills, module accent dots).
- `components/side_nav.html` — Findings link now real (`href="/findings"`) with active-pill styling on `active_nav == 'findings'`.

Verified
- `pytest -q` → **18 passed** (9 existing smoke + 9 new slice tests):
  - Pipeline: customer/engagement/run created; AD parser flags Tier 0 identities; svc-backup categorised as `service_account`.
  - BloodHound: ACL-abuse path detected; severity ≥ High; risk_score ≥ 60; path payload contains a `GenericAll` step; target SID is a Tier 0 RID.
  - Idempotency: re-running `demo load` creates only a new AssessmentRun, not duplicate customers/engagements.
  - UI: `/findings` 200 for consultant (renders ACL abuse, severity badges); customer executive sees "No findings yet" because all defaults are `internal_only`; finding detail renders `GenericAll` edge in PathStepList; customer executive gets 404 on internal_only finding.
- `ruff check src tests` → **All checks passed**. Per-file ignores added for typer's `Option()` default pattern; project-wide ignores for `RUF002/RUF003` (deliberate Unicode in human-readable docstrings).
- `gravity demo load` (live run): 6 identities, 12-node graph, 6 Tier 0 principals, 5 critical paths, 5 findings — the headline `contractor.john → DOMAIN ADMINS` finding is HIGH severity.
- HTTP probes: `POST /login` 303 → consultant `GET /findings` 200 → finding detail 200; customer executive `GET /findings` 200 (empty) + finding detail 404.

Tasks moved
- T-9001 (models), T-9003 (AD parser), T-9004 (BH parser), T-9005 (path detection), T-9006 (Finding gen) → done.
- T-9013 (CLI), T-9014 (findings UI), T-9015 (tests) → done.
- T-9009 (customer-visible view) → partial (filter is in; publish flow lands in Chunk B).
- T-9011 (audit log) → partial (`demo.load` event captured; per-state-change events arrive in Chunk B).
- T-9002 (upload endpoint), T-9007 (triage UI), T-9008 (publish), T-9010 (report preview), T-9012 (slice review) → still todo (Chunks B + C).

Decisions
- D-0024 SQLite as temporary persistence backend until Postgres unblocks.

Recommended next step
- Try it: <http://127.0.0.1:8001/findings> after `gravity demo load`. Headline finding "ACL abuse path from contractor.john reaches Tier 0 (DOMAIN ADMINS@CONTOSO.LOCAL)".
- If happy: commit + push, then Chunk B (triage → publish → audit-log per state change).

---

## 2026-05-15 — Real ACEN logo + user profile (header dropdown + /profile route)

Stage: 8.1 (design iteration v5)
By: Claude Code at Kristof's feedback ("the gui misses a user profile" + "I also added the correct logos").

Added:
- `src/platform_core/web/static/img/acen-mark.svg` — A-with-Trinidad-orbit brand mark (SVG approximation; navy A + orange→red gradient orbit; orbit weaves behind/in-front of the A).
- `src/platform_core/web/static/img/acen-wordmark.svg` — Same mark + chunky geometric "CEN" letterforms in Bunting navy.
- `src/platform_core/web/static/img/README.md` — Documents the path; the official files can be dropped in by Kristof to replace the SVG approximations (same filenames → automatic pickup). Also clarifies that Trinidad-in-the-orbit is **brand identity**, not a critical-state signal — D-0010's "reserve Trinidad" rule applies to CTAs/status surfaces, not to the brand mark itself.
- `src/platform_core/web/routes/profile.py` — `GET /profile` route stub; renders the synthetic user's details.
- `src/platform_core/web/templates/profile.html` — Profile page: identity card (avatar + name + email + role pill + persona-key/session/auth state) + a "What this role can do" card with persona-specific Allowed / Hidden / Restricted sections + a POC note about synthetic users.

Changed:
- `src/platform_core/web/session.py`:
  - New `User` dataclass (`display_name`, `email`, `role_label`, `accent`, `initials` property derived from the name).
  - `USERS: dict[Persona, User]` table — synthetic profiles per persona. Consultant = "Kristof Laerenbergh / kristof.laerenbergh@acen.example / ACEN Consultant". Customer personas use fictional names + `.example` email domains (RFC 2606) per D-0011 (synthetic data only).
  - `get_user(request)` helper alongside `get_persona`.
- `src/platform_core/web/templating.py` — exposes `users` to Jinja globals.
- `src/platform_core/web/routes/home.py` — passes `user` to the home template via `get_user`.
- `src/platform_core/web/templates/base.html` — added Alpine.js v3.x via CDN (defer); per `WORKING_APPROACH.md` §14 stack.
- `src/platform_core/web/static/styles.css` — `[x-cloak] { display: none !important }` so Alpine elements don't flash before init.
- `src/platform_core/web/templates/components/app_header.html`:
  - **Real ACEN brand mark** (`<img src="static/img/acen-mark.svg">`) replaces the placeholder "G" square. "Gravity" wordmark sits beside it.
  - **User profile dropdown** (Alpine-powered) replaces the persona chip. Trigger = avatar (initials) + name + role + chevron. Open panel contains: a coloured-gradient profile header (avatar / name / email / role pill), menu items (My profile → /profile, Preferences, Project & docs ↗), a "Switch persona (POC)" section listing all three personas with a checkmark on the active one, and a Sign out action in critical-coloured text. Escape closes the panel; outside-click closes.
- `src/platform_core/web/templates/components/side_nav.html` — profile chip at the bottom now uses the real `user.display_name` / `user.email` / `user.initials` and links to `/profile`. The logout form moved into the header dropdown.
- `src/platform_core/web/templates/login.html` — left brand pane uses the **real ACEN wordmark** SVG; mobile/responsive header uses the brand mark SVG.
- `src/platform_core/app.py` — registers the profile router.
- `tests/test_smoke.py` — assertion updated for the new persona role labels (`Customer · IT Lead`), and a new positive assertion that the synthetic display name (`Marcus Webb`) renders for the IT-Lead persona.

Verified:
- `pytest -q` → **9 passed** in 0.60s.
- `ruff check src tests` → **All checks passed**.
- Live HTTP probes: `/login` 200, POST `/login` 303 → `GET /` 200 → `GET /profile` 200. Response body contains "Kristof Laerenbergh", references `acen-mark.svg`, and includes the `x-cloak` style rule.

Tasks moved: none (still Stage 8.1 visual iteration).
Decisions: none new; D-0010 (brand) clarified in `static/img/README.md` (Trinidad-in-mark = brand identity, not a critical signal).
Assumptions: none new.
Risks: none new.
Open questions touched: none.

Notes for Kristof:
- The brand-mark SVGs are **approximations**. Drop the official files at `src/platform_core/web/static/img/acen-mark.svg` and `acen-wordmark.svg` (same filenames) and they're picked up automatically. If the official files are PNG, save as `.png` and update the two `<img>` tags in `app_header.html` + `login.html`.
- Synthetic email domains use `.example` (RFC 2606) so they read as fake.
- Real authentication / real users land at MVP (Q-0043).

Recommended next step:
- Look at <http://127.0.0.1:8001> — header dropdown, side-nav profile chip linking to /profile, login splash with the new wordmark. If close enough, commit. Then move to Stage 8.2 (sample data plan).

---

## 2026-05-15 — Stage 8.1 neutral chrome (pull UI off brand-blue)

Stage: 8.1 (design iteration v4)
By: Claude Code (UX role) after Kristof: "I don't like the overkill on blue".

Changed:
- **D-0023 logged** — UI chrome decoupled from brand-blue. Brand palette intact; surface tokens now map to a neutral shade scale.
- `src/platform_core/web/templates/base.html` Tailwind config:
  - New `shade-*` family (950 → 500), cool dark greys with a 2 % blue tint.
  - `bg` `#0a0a12`, `bgSoft` `#13131c` (was `#0c0b24` / `#11102d`, both saturated navy).
  - `surface1` `#1a1a23` (was Bunting `#1b1b4c`), `surface2` `#22222e` (was Jakarta `#201e5c`), `surface3` `#2a2a36` (was Minsk `#2d2d72`).
  - `app-backdrop` retoned: Turquoise top-right halo + Rose bottom-left halo over a neutral shade gradient (was a navy-heavy gradient with a violet halo).
- `src/platform_core/web/templates/home.html` — hero KPI gradient retoned from `from-brand-bunting via-brand-jakarta to-support-indigo/70` (heavy brand-blue) to `from-support-violet/80 via-support-indigo/85 to-support-indigo` (vibrant, no navy in the gradient). Decorative blocks recoloured: Turquoise top-right, Rose bottom-left.
- `project-management/UI_DESIGN_DIRECTION.md` §2.1 — added the **Neutral shade scale** subsection and the **Brand moments** rule.

**Brand-blue still leads in deliberate moments only:**
- Brand mark / logo lockup (`brand-gulf` base with Turquoise + Violet overlay).
- Login left splash pane (`brand-bunting → brand-jakarta → brand-gulf` gradient).
- "ACEN Gravity" wordmark colour treatment.

**No brand-blue in chrome anywhere:** confirmed via grep — header bg, side nav bg, card bg, drawers, modals, page bg all use `shade-*` or `surface-*` tokens (which now point to shades).

Verified:
- `pytest -q` → **9 passed** in 0.36s.
- `ruff check src tests` → **All checks passed**.
- Live end-to-end: `/login` 200, POST `/login` 303 → `GET /` consultant 200.

Tasks moved: none (still Stage 8.1 visual iteration).
Decisions:
- D-0023 UI chrome decoupled from brand-blue; neutral shade scale introduced.
Assumptions: none new.
Risks: none new.
Open questions touched: Q-0111 (Trinidad usage) re-affirmed.

Recommended next step:
- Visual review at <http://127.0.0.1:8001>. If the chrome reads neutral with brand colour as moments, I commit. If still off, point at what.

---

## 2026-05-15 — Stage 8.1 visual richness pass (rounded cards, gauge, sample chart, profile chip)

Stage: 8.1 (design iteration v3)
By: Claude Code (UX role) after Kristof shared three additional reference dashboards (exon, an insurance dashboard, a SaaS metrics dashboard) and confirmed "match references at 10–12px" + "full richer redesign of the home overview".

Changed:
- `UI_DESIGN_DIRECTION.md` §2.3 — radius rule rewritten: `rounded-xs = 2px` (small elements), `rounded-control = 6px` (interactive controls), `rounded-card = 10px` (cards/drawers/modals/hero containers). Pending brand-owner confirmation at Cycle 4 review (Q-0110 extended).
- `src/platform_core/web/templates/base.html` Tailwind config — added `rounded-card`, `rounded-control`; added card shadow tokens (`shadow-card`, `shadow-cardLg`).
- `src/platform_core/web/templates/components/`:
  - **NEW `arc_gauge.html`** — vertical-bar semicircle gauge (System Health style, per reference D). N bars arranged 180°→360° around a centre point; taller toward the middle (bell curve), each bar is a rotated `<rect>`. Filled bars in module accent up to value %, remainder dimmed. Centred percent + caption.
  - **NEW `sample_chart.html`** — SVG line chart with: gradient-area solid Turquoise→Indigo "actual" series + dashed Violet "predicted" series; grid lines; vertical guide line; data dots at the pinned guide; a hover-style tooltip card (Actual / Predicted / Deviation / Confidence) positioned over the chart; an inset Insight callout in Indigo below the chart.
  - `side_nav.html` — active nav row is now a **filled tinted pill** with accent border and matching icon colour (per reference D); profile chip added at the bottom of the side nav (avatar circle with persona initial, online dot, persona name, "POC session · synthetic", switch-role icon button).
  - `app_header.html` — real search input (with disabled state + `⌘K` kbd hint); "Run analysis" key-action button at the right (placeholder); customer/engagement/run breadcrumb-pickers rendered as soft hoverable pill-buttons.
- `src/platform_core/web/templates/login.html` — radio cards now use `rounded-card` + `shadow-card` / `shadow-cardLg` on checked.
- `src/platform_core/web/templates/home.html` — fully rebuilt:
  - Page header with persona crumb + "No data" amber pill.
  - **Hero gradient KPI card** for Current License Score (Bunting → Jakarta → Indigo gradient) + neutral Target Posture and Opportunity cards (each with accent-coloured top gradient line).
  - **Mid row (3 + 6 columns):** System Health card with arc gauge (placeholder value 0) + CPU/Mem/Disk mini-KPIs + tenant-state list at the bottom · Risk Forecast card with the sample line chart, 1D/1W/1M/3M segmented control, legend, and Insight callout.
  - 4-up module strip with hover lift + module-accent top edge.
  - Bottom hero: empty-state message + 5-step demo journey list with numbered chips coloured by module accent.

Verified:
- `pytest -q` → **9 passed** in 0.27s (after fixing a divide-by-zero in `arc_gauge.html`).
- `ruff check src tests` → **All checks passed**.
- Live HTTP probe end-to-end: `/login` 200, POST `/login` 303 → `GET /` 200.

Tasks moved: still inside Stage 8.1 (T-6002 / T-6005 visual iteration).
Decisions:
- D-0022 Card rounding raised to 10px (amends D-0010).
Assumptions: none new.
Risks: none new.
Open questions touched: Q-0110 — extended to include the 10px card rounding for brand-owner confirmation at Cycle 4.

Recommended next step:
- Visual review at <http://127.0.0.1:8001>. If close enough, I commit (suggested message: *"Visual richness pass: 10px cards, arc gauge, sample chart, profile chip"*). If still off, point out specific elements and I iterate before committing.

---

## 2026-05-15 — Supporting palette + Stage 8.1 reskin

Stage: 8.1 (design iteration)
By: Claude Code (UX role) at Kristof's feedback: "I don't like the design. we should use the colors in the brand guide, but others can be introduced as well."

Changed:
- `UI_DESIGN_DIRECTION.md` §2.1 — added a **Supporting palette** subsection: 6 tokens (indigo / violet / sky / rose / amber / slate) with defined roles, plus a **module category colour map** (AD = brand Turquoise, BloodHound = Rose, Silverfort = Violet, Entra = Sky). Strict usage rules so the design stays restrained.
- `src/platform_core/module_registry.py` — `ModuleStub` gains an `accent` field (Tailwind colour class fragment). AD = `brand-turquoise`; BH = `support-rose`; SF = `support-violet`; Entra = `support-sky`.
- `src/platform_core/web/templates/base.html` — Tailwind config extended: `support.*` colour family, `bgSoft`, subtle `app-backdrop` radial gradient, `card-sheen`. POC banner restyled to a thinner less-loud row.
- `src/platform_core/web/templates/components/app_header.html` — persona-tinted chip (each persona gets its own accent: consultant = Turquoise, customer executive = Violet, customer IT lead = Sky), brand mark with gradient overlay, notification dot in Rose.
- `src/platform_core/web/templates/components/side_nav.html` — module-accent dots that scale on hover, real icons (overview / findings / reports / audit), POC footer block at the bottom of the nav.
- `src/platform_core/web/templates/login.html` — 2-column layout: left brand pane with decorative shapes in supporting colours + module legend; right persona picker with radio cards that highlight in the persona's accent.
- `src/platform_core/web/templates/home.html` — three KPI placeholder cards with module-accent top stripes (Turquoise / Violet / Amber), 4-up module strip showing each module's category colour, layered hero with gradient top edge.

Verified:
- `pytest -q` → **9 passed** in 0.28s.
- `ruff check src tests` → **All checks passed**.
- Live server: `/login` 200, `/healthz` 200.

Tasks moved: none (still inside T-6002 / T-6005 scope, just visual iteration).
Decisions:
- D-0021 Supporting palette introduced alongside the ACEN brand palette.
Assumptions: none new. Risks: none new. Open questions touched: Q-0111 (Trinidad usage) now answered in §2.1 strict-rules block.

Recommended next step:
- Review the new look at <http://127.0.0.1:8001>. If the direction is right, I commit. If specific elements are still off, point them out and I iterate before commit.

---

## 2026-05-15 — Stage 8.1 build started — architecture skeleton runs

Stage: 8.1
By: Claude Code (DEV role) at Kristof's "let's build" request.

> **Cycle status:** Cycles 1–7 not formally signed off; build started on informal sign-off per D-0019 (accepted-with-risk). Skeleton is intentionally reversible.

Added (code):
- `pyproject.toml` — Python 3.12+, FastAPI 0.136, Starlette 1.0, SQLAlchemy 2.0, Alembic 1.18, psycopg 3.3, Pydantic 2.13, pydantic-settings 2.14, itsdangerous; dev: ruff 0.15, mypy 2.1, pytest 9.0, httpx 0.28. Editable install ok.
- `compose.yaml` — podman compose: Postgres 16-alpine on port 5432 (gravity/gravity/gravity). External Postgres pattern per Kristof's choice.
- `.env.example` — `APP_*` + `DATABASE_URL` + `LOG_LEVEL`.
- `.gitignore` — Python + venv + tooling caches + `.env*` (with `!.env.example`) + `evidence/` (D-0011).
- `DEVELOPING.md` — Quickstart for fresh devs.
- `src/platform_core/`:
  - `app.py` — FastAPI factory, session middleware, static mount, healthz, route registration.
  - `settings.py` — pydantic-settings; reads `.env`; exposes paths.
  - `module_registry.py` — Stage 8.1 stub (`ModuleStub` with id/title/nav_label/icon for AD/BH/SF/Entra). Full `ModuleManifest` lands in Stage 9.
  - `web/session.py` — `Persona` `StrEnum` (consultant / customer_executive / customer_it_lead) + per-persona nav visibility set + signed session helpers. Per A-0013 (no real auth in POC).
  - `web/templating.py` — Jinja2 environment with brand globals (modules, persona labels, `is_nav_visible`).
  - `web/routes/login.py` — GET /login, POST /login, POST /logout.
  - `web/routes/home.py` — GET / (303 to /login if no persona, otherwise renders home).
  - `web/templates/base.html` — ACEN-branded shell (Montserrat, Tailwind palette tokens — Jakarta/Bunting/Minsk/Trinidad/Turquoise — square corners, 2px on interactive controls per D-0010, POC banner per `SECURITY_AND_GDPR.md` §18).
  - `web/templates/components/app_header.html` — header with brand mark, picker placeholders, action icons (disabled), persona chip + Switch role button.
  - `web/templates/components/side_nav.html` — sectioned nav with persona-aware visibility (consultant sees all; customer roles see compressed Overview/Findings/Reports).
  - `web/templates/login.html` — persona picker hero card.
  - `web/templates/home.html` — empty-state hero with persona name + status pills.
  - `web/static/styles.css` — placeholder.
- `src/modules/{ad,bloodhound,silverfort,entra}/manifest.py` — module-id stubs (full manifest in Stage 9).
- `src/modules/{ad,bloodhound,silverfort,entra}/{parsers,models,controls,correlations,reports,ui,tests}/__init__.py` — empty package markers.
- `tests/test_smoke.py` — 9 smoke tests:
  - `/healthz` returns 200.
  - `/` 303 → /login when no persona.
  - `/login` lists all 3 personas.
  - Consultant POST /login → home shows full nav (AD, BH, SF, Entra, Findings, Reports, Audit).
  - Customer Executive → compressed nav (no AD/BH/SF/Entra in nav, no Audit anywhere).
  - Customer IT Lead → compressed nav.
  - Unknown persona → 303 back to /login with `error=`.
  - Logout clears session and redirects.
  - POC banner visible in dev.

Verified:
- `pip install -e .[dev]` clean on Python 3.14.3 (uses py312-targeted wheels).
- `pytest -q` → **9 passed** in 0.27s.
- `ruff check src tests` → **All checks passed** (after switching `Persona(str, Enum)` → `Persona(StrEnum)`).
- `uvicorn` boot + `curl /healthz` 200 / `curl /login` 200 / `curl /` 303.

Tasks moved:
- T-6001 → done (project init).
- T-6002 → done (FastAPI + Jinja + Tailwind via Play CDN).
- T-6003 → blocked (Postgres + Alembic — WSL2 Virtual Machine Platform off; Kristof unblocking in parallel).
- T-6004 → done (folder layout per `MODULE_ARCHITECTURE.md`).
- T-6005 → done (role-switcher login + per-persona nav visibility).

Decisions:
- D-0019 Build started without formal Cycle 1–7 sign-off (accepted-with-risk).
- D-0020 Tailwind via Play CDN for Stage 8.1; switch to standalone CLI before component-library work.

Open questions touched: none new.

Risks touched: R-0010 (Postgres availability) materialised as the WSL/VMP blocker; mitigation in progress (Kristof enabling VMP, then `podman machine start`).

Recommended next step:
- Once `podman machine start` works, T-6003 lands in ~10 min: bring up `compose.yaml`, `alembic init migrations`, generate the empty baseline.
- Then continue to **Stage 8.2 (sample data plan)** and **Stage 8.3 (developer handoff doc)** before opening Stage 9.

---

## 2026-05-15 — Module page archetypes (per-module body, shared frame + atoms)

Stage: 4 (UX)
By: Claude Code (UX role) at Kristof's pushback

Changed:
- `UI_DESIGN_DIRECTION.md`:
  - §1 design goal rewritten: same atoms and frame across modules, **module-specific compositions are allowed and expected**.
  - New "two-layer UI" table (Frame + Atoms identical · Module-specific compositions and components deliberately different).
  - §3.5 expanded: module-specific named components are first-class library members. Promotion rule defined.
  - §4.3 split into four module page archetypes:
    - **4.3.1 AD — Posture** (status cards + control-coverage ring + priority findings).
    - **4.3.2 BloodHound — Attack-path** (ranked paths dominant + `PathStepList` drawer; no control ring).
    - **4.3.3 Silverfort — Coverage** (`CoverageMatrix` dominant + coverage-gap priority list).
    - **4.3.4 Entra — License-aware tenant config** (license-aware status cards + Opportunity card + findings with `LicenseBadge`).
  - §5 component inventory map: added rows 21 (`PathStepList`), 22 (`CoverageMatrix`), 23 (`LicenseBadge` + `CapabilityTooltip`).
  - §17 anti-patterns: "forcing identical body layouts across all module pages" is now itself called out as an anti-pattern.
- `DECISIONS.md` — D-0018 logged.
- `REVIEW_NOTES.md` — two new cross-doc consistency checks: archetypes per module and named components living in the shared library.

Decisions:
- D-0018 Module pages use module-specific archetypes built on a shared frame + shared atoms.

Assumptions: none new.
Risks: none new (R-0002 mitigation preserved via the shared frame rule).
Open questions touched: none.

---

## 2026-05-15 — Operating model v2: 9 stages, demo story, vertical slice, sample data, kill criteria, doc control

Stage: 0 (operating model)
By: Claude Code (at Kristof's request)

Changed:
- `WORKING_APPROACH.md` — operating model upgraded from 8 to 9 stages. Highlights:
  - Stage 8 split → Stage 8 (Build preparation) + Stage 9 (POC build). Build prep and build execution are now separate gates.
  - New §3 — **POC V1 demo story** (north star). Every feature must support it.
  - New §6 — **Thin vertical slice first**. Hard rule: no horizontal expansion until the slice is reviewed.
  - New §13 — **Sample data requirements** with ownership split (Kristof = realism; Claude Code = safety/structure/docs).
  - New §15 — **Documentation control rules** (≥ 400-line → executive summary; ~800-line soft cap → summary or appendix decision).
  - New §20 — **POC V1 kill criteria** with explicit response options (reduce / adjust / postpone / stop).
  - §5 MVP softened: "Real or limited Microsoft Graph collector for selected Entra checks, with license-aware status handling."
  - §12 simplified data model wording: POC builds a coarse model proving the lifecycle (Customer / Engagement / AssessmentRun / Evidence / ControlResult / Finding / RemediationTask / ReportPreview / PublishState / AuditEvent). MVP/Full expand later.
  - §14 complexity checklist extended (demo story, slice, sample data, prod-grade complexity, scrolling, consultant/customer effort, cross-module value, doc location).
  - §18 Definition of Ready and §19 Definition of Done updated for the slice + sample data + kill criteria + Stage 8 gate.
  - §22 Recommended next step rewritten.
  - Executive summary added at the top per the new §15 rule.
- `PROJECT_STATE.md` — stage map updated to 9 stages; next steps reordered to reflect Stage 8 / Stage 9 split.
- `TASKS.md`:
  - Stage 6 reframed as **backlog management** (T-6500..T-6503).
  - Stage 7 expanded with kill-criteria walkthrough (T-7002).
  - Stage 8 split into §8.1 Architecture skeleton, §8.2 Sample data plan (T-8001..T-8007), §8.3 Developer handoff (T-8010..T-8013).
  - Stage 9 reorganized: §9.0 **Vertical slice (HARD GATE)** (T-9001..T-9012), §9.1 horizontal shared core, §9.2..§9.10 horizontal modules / UI / reporting / QA (renumbered from 6.x).
  - Leftover "Stage 8 — Build preparation (MVP)" placeholder renamed "Post-Stage 9 — MVP preparation".
- `REVIEW_NOTES.md` — sign-off tracker extended to Cycles 8 and 9 (Build preparation, Build acceptance).

Decisions (in `DECISIONS.md`):
- D-0012 Operating model split into 9 stages.
- D-0013 POC V1 demo story is the north star.
- D-0014 Thin vertical slice first; no horizontal expansion until proven.
- D-0015 Sample data plan is a Stage 8 deliverable; ownership split.
- D-0016 POC V1 kill criteria are explicit and feed the Cycle 7 management decision.
- D-0017 Documentation control rules (size cap, executive summary, no duplication).

Assumptions (in `ASSUMPTIONS.md`):
- A-0016 POC V1 can run on synthetic or anonymized data only.
- A-0017 Live Graph and Silverfort API connectors are not required for POC V1.
- A-0018 The first build is a thin vertical slice; module pages come after.

Risks (in `RISKS.md`):
- R-0013 POC expands horizontally before the first slice is proven.
- R-0014 Sample data is not realistic enough to land the demo.
- R-0015 BloodHound findings are noisy without consultant tuning.
- R-0016 Documentation grows too large to be reviewed actively.

Open questions touched:
- None new (existing questions remain valid; Q-0040 / Q-0090 / Q-0092 still apply).

---

## 2026-05-15 — Folder layout: all docs into `project-management/`

Stage: housekeeping
By: Claude Code (at Kristof's request)

Changed:
- All 22 markdown documents (everything except top-level `README.md`) moved from repo root into a new `project-management/` subfolder. Root stays clean for code (future `platform_core/`, `modules/`, `tests/`, etc.).
- `README.md` updated to reference the new paths.
- Internal cross-references between docs (e.g., `PRODUCT_DESIGN.md` → `MODULE_ARCHITECTURE.md`) unaffected — they still resolve because all moved docs are in the same folder relative to each other.

Note for future work:
- When referencing these docs from chat/output, use the form `project-management/<FILE>.md`.
- When linking from a code file outside `project-management/`, use a relative or absolute path including the folder.

---

## 2026-05-15 — Stages 1–5 module designs (parallel pass) + reconciliation

Stage: 3, 4, 5 (drafting)
By: Claude Code via parallel subagents (AD pair, BloodHound, Silverfort, Entra)

Added:
- `AD_TOOLKIT_DESIGN.md` (~586 lines) — toolkit purpose, ZIP structure, manifest, checksums, logs, signing, validation.
- `AD_MODULE_DESIGN.md` (~1055 lines) — full control catalog (AD-HEALTH, AD-PRIV, AD-KERB, AD-DELEG, AD-NTLM, AD-GPO, AD-SF, AD-ENTRA), normalized model, Tier 0, correlations.
- `BLOODHOUND_ANALYZER_DESIGN.md` (~1157 lines) — 26 sections; deterministic path detection / ranking / scoring / explanation (D-0005 enforced); parser, graph model, Tier 0, risk formula, templates, correlation with AD/SF/Entra, dashboard via PathStepList.
- `SILVERFORT_MODULE_DESIGN.md` (~887 lines) — manual-first per D-0006; 30 occurrences of "(unverified — requires Silverfort validation)" tag on API references; full control catalog (SF-CONN, SF-POL, SF-ENR, SF-RISK, SF-SA, SF-AD, SF-ENTRA).
- `ENTRA_MODULE_DESIGN.md` (~830 lines) — license-aware logic with worked Contoso example (E3 + P1, no P2); full control catalog (ENTRA-LIC, CA, AUTH, PRIV, BG, APP, GUEST, HYBRID, SF).

Changed:
- `POC_V1_SCOPE.md` §8 and §13 — corrected Contoso demo SKU profile from "E5 + EMS E5 + Entra ID P1, no P2" (internally inconsistent: E5 bundles P2) to "E3 + standalone Entra ID P1, no P2, owns Silverfort". Anchors the `not_licensed` demo for Identity Protection cleanly.
- `REVIEW_NOTES.md` — 16 cross-document reconciliation items added (Silverfort 4, BloodHound 4, AD 4, Entra 4) to track at the per-cycle reviews.
- `PROJECT_STATE.md` — stages 1–5 marked drafted; awaiting cycle sign-offs.

Decisions:
- (No new D-NNNN added during the parallel pass.)

Tasks moved:
- T-3001..T-3005 → done (drafted).

Open questions touched:
- Q-0050..Q-0053 (AD), Q-0060..Q-0063 (BH), Q-0090..Q-0092 (SF), Q-0070..Q-0072, Q-0080..Q-0081 (Entra).

---

## 2026-05-15 — Stage 0 → Stage 1 initial foundation pass

Stage: 0 → 1 (drafting)
By: Claude Code (multi-role, Documentation lead)

Added:
- `WORKING_APPROACH.md` — operating manual: stages, roles, complexity rules, first-5-sessions cadence, definition of ready/done.
- `PROJECT_STATE.md` — current stage, goals, completed work, next steps, blockers, references.
- `DECISIONS.md` — 11 initial decisions (D-0001 … D-0011), all proposed pending review cycles.
- `ASSUMPTIONS.md` — 15 working assumptions (A-0001 … A-0015), all open pending Kristof validation.
- `OPEN_QUESTIONS.md` — questions grouped by topic, each with tier and target reviewer.
- `TASKS.md` — backlog skeleton across all 8 stages.
- `RISKS.md` — 12 initial risks with mitigations.
- `REVIEW_NOTES.md` — sign-off tracker and cross-document consistency checks.
- `CHANGELOG.md` — this file.

Changed:
- (none — initial creation pass)

Removed:
- (none)

Decisions:
- D-0001 Three-tier roadmap (POC → MVP → Full Product)
- D-0002 Modular monolith first
- D-0003 Stack baseline: FastAPI + HTMX + Tailwind + PostgreSQL
- D-0004 Background jobs deferred; design queue-ready
- D-0005 Deterministic BloodHound analyzer (no AI in critical path)
- D-0006 Silverfort manual-first, API design-only for POC
- D-0007 License-aware status enum (8 values)
- D-0008 Two scores: Current License + Target Posture; gap = Opportunity
- D-0009 Customer publishing is explicit, not default
- D-0010 ACEN brand guide is source of truth (one digital adaptation: ≤ 2px radius on interactive controls)
- D-0011 Synthetic data only; no real customer evidence in repo

Tasks moved:
- T-0001 Create `WORKING_APPROACH.md` → done
- T-0002 Create control files → done
- T-1001/2/3, T-2001/2, T-3001/2/3/4/5, T-4001, T-5001 → doing (drafted in this session)

Open questions touched:
- Q-0001 .. Q-0150 (initial backlog created)

---

*Last updated: 2026-05-15.*
