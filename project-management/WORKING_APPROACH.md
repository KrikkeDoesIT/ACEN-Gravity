# WORKING_APPROACH.md

> How we will deliver this project end-to-end in a structured, token-efficient way. The official operating model.

---

## Executive summary

- **9 stages**, each ending in a review cycle. Stages 1–7 are document-only. Stage 8 is build preparation. Stage 9 is the actual POC build. **No code before Stage 8.**
- **One demo story** is the north star (§3). Every feature must support it.
- **Thin vertical slice first** (§6): we prove the lifecycle end-to-end on one path before building module pages horizontally.
- **POC / MVP / Full** tier discipline on every feature (§5).
- **Synthetic data only** in the repo (§13). No real customer evidence.
- **Hard kill criteria** (§20) protect the management go/no-go decision.
- **Documentation control rules** (§15) keep the docs reviewable, not encyclopedic.

---

## 1. Purpose

This document defines **how Claude Code and Kristof will work together** on the ACEN Gravity Security Assessment Platform.

It is **not** the product specification. It is the operating manual for the project: who does what, in what order, with what level of detail, and with what review and decision discipline.

The goal is to reach a **clear, manageable POC V1** without burning context, without overbuilding, and without turning the POC into a production SaaS too early.

---

## 2. Why a structured approach is needed

This project is unusually broad:

- 4 assessment modules in POC V1 (AD, BloodHound, Silverfort, Entra).
- 10+ future modules already in mind (Defender, Purview, Intune, Imprivata, Cato, Illumio, ...).
- 3 user personas (CISO/executive, security engineer/consultant, customer).
- 3 maturity stages (POC V1, MVP, Full Product).
- Multiple sensitive data domains (AD evidence, BloodHound graphs, Silverfort policy data, Entra Graph data).
- Strong UX, branding, and licensing-awareness expectations.
- A non-developer product owner (Kristof) who needs the platform to be self-explanatory and well-documented.

Without structure, we will:
- Repeat ourselves and waste context.
- Drift into coding before scope and architecture are clear.
- Build features the demo does not need.
- Create three dashboards instead of one platform.
- Quietly turn the POC into an MVP and miss the management decision point.

---

## 3. POC V1 demo story (the north star)

Every POC V1 feature exists to support **one specific demo story**. If a feature does not support this story, it must be mocked, postponed, or removed from POC V1.

> *We upload AD evidence, BloodHound data, Silverfort evidence and mocked Entra data for one customer. The platform identifies a critical AD attack path, shows that the involved account lacks Silverfort coverage, links the account to Entra privileged context, generates a prioritized finding, creates a remediation task, and produces a customer-ready report section.*

This story is the **single decision rule** for every "should we include this?" question during POC V1.

- If a feature supports the story → in scope (subject to the complexity checklist in §14).
- If a feature is interesting but not part of the story → log in `TASKS.md` tagged `mvp` or `full`, then drop from POC V1.
- If a feature is needed by the story but expensive to build → mock it (see §12).

The story is also the **demo script anchor** at the Cycle 7 management review.

---

## 4. Recommended overall approach

We work in **9 stages**, each ending in a **review checkpoint** with Kristof (or management at Cycle 7). We do **not start the next stage until the previous review is signed off** (or explicitly deferred).

We **do not write production code in stages 1–7**. Code work begins in stage 8 (build preparation) and stage 9 (POC build), and only after the scope, architecture, UX, security/GDPR designs, and build preparation are approved.

### Stage map

| # | Stage | Output | Review |
|---|---|---|---|
| 1 | Product framing | Discovery answers, POC V1 goal, demo story, personas | Concept review |
| 2 | Architecture framing | Platform/module model, evidence/finding/score model | Architecture review |
| 3 | Module deep dives | AD, BloodHound, Silverfort, Entra designs | Module design review |
| 4 | UX & information architecture | Screens, navigation, component library, no endless scrolling | UX review |
| 5 | Security & GDPR | Evidence, publishing, tenant boundaries | Security review |
| 6 | POC backlog | What is mocked vs built vs postponed; ≤ 40 build tasks | Backlog review |
| 7 | Management review | Concept, demo story, scope, risks, kill criteria, go/no-go | Management decision |
| 8 | **Build preparation** | Final POC backlog · Architecture skeleton (no business code) · Sample data plan · Developer handoff doc · Implementation task structure with the **first vertical slice** marked | Build-prep review |
| 9 | **POC build** | Working POC · Tests where practical · Demo flow · Report preview · Management review pack | Build acceptance |

**Why Stage 8 and Stage 9 are separate.** Build preparation and build execution are different activities. Splitting them prevents us from jumping into implementation too quickly. Stage 8 ends with a developer able to start work without ambiguity. Stage 9 ends with a demonstrable POC.

---

## 5. POC before MVP before Full Product

We never blur these three. **Every feature, control, and screen must declare which tier it belongs to.**

### POC V1 — validate the concept
- Sample / anonymized / manually uploaded evidence.
- Mocked connectors (Graph, Silverfort API) — design only, no live calls.
- Demonstrate the *workflow* (collect → parse → control → finding → remediation → publish).
- Prove the modular platform model with AD + BloodHound + Silverfort + Entra.
- Audience: internal stakeholders, management decision-makers.
- Success = "go/no-go for MVP investment."

### MVP — first usable version for consultants
- Real AD toolkit on customer infrastructure.
- **Real or limited Microsoft Graph collector for selected Entra checks, with license-aware status handling.** (A full Graph collector is intentionally not promised; a controlled subset of endpoints is acceptable and preferred over an over-scoped MVP.)
- Silverfort API connector once the customer/version supports the documented endpoints (gated on validation; see `DECISIONS.md` D-0006).
- Authenticated portal, RBAC, audit logs.
- Used by ACEN consultants for real engagements.
- Audience: ACEN consultants + selected pilot customers.

### Full Product — production-grade customer platform
- Multi-tenant, secure-by-default, managed-service ready.
- Customer self-service publishing controls.
- Hardened evidence storage, BCDR, support model.
- Audience: customer-facing.

If a discussion drifts toward MVP/Full Product features while we are still in POC V1 framing, we **document the idea** in `OPEN_QUESTIONS.md` or `TASKS.md` (tagged `mvp`/`full`) and pull the conversation back.

---

## 6. Thin vertical slice first

Before building all module pages or all module features, we build **one complete end-to-end slice** that demonstrates the lifecycle:

```
Customer
   → Assessment Run
   → Upload (or load) sample AD + BloodHound evidence
   → Parse one critical attack path
   → Generate one Finding
   → Review the Finding
   → Publish the Finding
   → Show the customer-visible view of the Finding
   → Generate one Report preview that includes the Finding
```

This is the slice that goes first into Stage 9 (POC build). The other modules (Silverfort and Entra), the additional controls, the additional UI pages, and the cross-module correlation all come **after** this slice works.

### Why this matters

- It proves the platform lifecycle on real wiring, not just on paper.
- It prevents half-built module dashboards that look impressive but never reach "publish".
- It validates the architecture before we expand horizontally.
- It keeps the POC focused and the backlog small.
- It gives management something tangible early — even an internal mid-build demo is possible.

### Hard working principle

> **No horizontal expansion across all modules until the first vertical slice is proven.**

Concretely, Stage 9 work is **ordered**, not parallel:

1. Stand up the skeleton (no business logic).
2. Build the vertical slice (AD + BloodHound minimal path → finding → publish → report preview).
3. **Only after the slice is reviewed**: extend horizontally — Silverfort module, Entra module, full control catalog, cross-module correlation, additional UI pages, additional reports.

A backlog item that does not belong to the vertical slice cannot enter Stage 9 work before the slice is reviewed.

---

## 7. Agent / role model

Claude Code will operate as a **multi-role architect** simulating these roles, either with subagents (when useful) or as sequential work passes (when subagents would burn context). Subagents are reserved for **parallelizable, well-scoped writing tasks** (e.g., writing the four module design documents in parallel after the foundation is approved).

### Roles

#### 7.1 Product Owner Agent
- **Responsibility:** product vision, POC scope, user journeys, management story, discovery answers.
- **Inputs:** Kristof's domain expertise, customer/commercial context.
- **Outputs:** `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md`, `DISCOVERY_WORKSHOP_ANSWERS.md`.
- **Key questions:** *Who is this for? What must it prove? What is the demo story?*
- **Must not:** define implementation, architecture, or UI components.
- **Review criteria:** Can a non-developer manager understand the value and scope in 10 minutes?

#### 7.2 Software Architect Agent
- **Responsibility:** application structure, modular monolith, domain boundaries, data model, maintainability.
- **Inputs:** product scope, modules, evidence types.
- **Outputs:** `MODULE_ARCHITECTURE.md`, data model sections of `PRODUCT_DESIGN.md`.
- **Key questions:** *What is core vs module? Where do extension points live? How do we prevent module-specific hacks in the core?*
- **Must not:** add features, dictate UX, optimize prematurely.
- **Review criteria:** Can a new developer onboard from the docs alone? Do AD/BH/SF/Entra reuse the same lifecycle (evidence → finding → score → report)?

#### 7.3 UX / UI Agent
- **Responsibility:** ACEN style translation, dashboard structure, clean navigation, customer vs internal separation.
- **Inputs:** ACEN 2025 brand guide, product scope, persona journeys.
- **Outputs:** `UI_DESIGN_DIRECTION.md`, screen inventories.
- **Key questions:** *What is the first thing the user sees? Where does each persona spend most of their time? What is the drill-down depth budget?*
- **Must not:** add SIEM-style clutter, design endless scrolling pages, invent new UI patterns per module.
- **Review criteria:** Does every page have one clear purpose? Is the customer view obviously separated from the internal view?

#### 7.4 Security & GDPR Agent
- **Responsibility:** evidence protection, tenant isolation, RBAC, audit logs, secure uploads, customer publishing, data minimization.
- **Inputs:** evidence types per module, customer publishing requirements.
- **Outputs:** `SECURITY_AND_GDPR.md`.
- **Key questions:** *Who can see this evidence? What is logged? What is published? What must never leave the platform?*
- **Must not:** apply production hardening to POC V1; flag what *must* be hardened before MVP.
- **Review criteria:** Could we defend this design in front of a customer DPO and a CISO?

#### 7.5 AD Module Agent
- **Responsibility:** AD assessment model, AD toolkit, PingCastle integration, Tier 0, AD controls, AD reporting.
- **Outputs:** `AD_MODULE_DESIGN.md`, `AD_TOOLKIT_DESIGN.md`.

#### 7.6 BloodHound Analyzer Agent
- **Responsibility:** SharpHound ZIP parsing, graph model, deterministic critical path analysis, risk scoring, path explanations, correlation.
- **Outputs:** `BLOODHOUND_ANALYZER_DESIGN.md`.
- **Key constraint:** detection, ranking, correlation, and initial explanations must be **deterministic and consultant-reviewable**. AI is allowed only for *language polish later*.

#### 7.7 Silverfort Module Agent
- **Responsibility:** Silverfort evidence model, manual/API modes, policy coverage, service accounts, enrollment, risk, correlation.
- **Outputs:** `SILVERFORT_MODULE_DESIGN.md`.
- **Key constraint:** any API endpoint claim must be marked as **requires validation against official Silverfort documentation / support / customer version**.

#### 7.8 Entra Module Agent
- **Responsibility:** Entra assessment model, Graph collection design, license-aware controls, CA, PIM, apps, hybrid identity.
- **Outputs:** `ENTRA_MODULE_DESIGN.md`.

#### 7.9 Documentation / Reviewer Agent
- **Responsibility:** consistency across documents, readability, deduplication, non-developer clarity, final handoff quality.
- **Outputs:** `REVIEW_NOTES.md`, cross-document diff lists, final pass before management review.
- **Key questions:** *Does this doc contradict another? Is anything restated 3 times? Is anything assumed without being written down?*

#### 7.10 QA / Test Agent
- **Responsibility:** acceptance criteria, test strategy, sample data validation, edge cases, regression checklist.
- **Outputs:** acceptance criteria sections in `POC_V1_SCOPE.md` and `TASKS.md`, test strategy section in build phase.
- **Key questions:** *How do we prove this works? What is the minimum sample dataset? What are the demo failure modes?*

---

## 8. Work phases (operational view)

Within each stage we follow the same micro-loop:

1. **Audit** — read what already exists (control files, prior decisions, related docs).
2. **Draft** — produce a focused output (one document or one section).
3. **Document state** — update `PROJECT_STATE.md`, log decisions in `DECISIONS.md`, log assumptions in `ASSUMPTIONS.md`, log questions in `OPEN_QUESTIONS.md`, log changes in `CHANGELOG.md`.
4. **Summarize** — short summary at the end of each work session (see §17).
5. **Wait for review** — do not progress past a checkpoint without explicit go.

---

## 9. Review cycles

Each stage ends in a named review. We do not start the next stage until the review is signed off (✅), explicitly deferred (⏸), or marked accepted-with-risk (⚠ logged in `RISKS.md`).

| Cycle | Reviewer | Focus | Approval artifact |
|---|---|---|---|
| 1. Concept & POC scope | Kristof | Is the value clear? Is the demo story right? Is scope right-sized? | Sign-off comment in `PROJECT_STATE.md` |
| 2. Architecture & module boundaries | Kristof + (optional) dev advisor | Are core/module boundaries clean? | `DECISIONS.md` entry |
| 3. Module designs (AD/BH/SF/Entra) | Kristof (domain) | Do controls and evidence make sense? | Per-module sign-off in `REVIEW_NOTES.md` |
| 4. UX / information architecture | Kristof | Does the demo journey flow? Is it ACEN-branded? | UX sign-off in `REVIEW_NOTES.md` |
| 5. Security & GDPR | Kristof | Is evidence handling defensible? | Security sign-off in `REVIEW_NOTES.md` |
| 6. POC build backlog | Kristof | Is the backlog small enough to actually deliver? Is the vertical slice marked? | Backlog sign-off in `TASKS.md` |
| 7. Management review | Management | Demo story + kill criteria + go/no-go for MVP investment | External decision, logged in `DECISIONS.md` |
| 8. Build preparation | Kristof + dev | Is the developer handoff complete? Architecture skeleton OK? Sample data plan approved? Vertical slice tasks ready? | Build-prep sign-off in `REVIEW_NOTES.md` |
| 9. Build acceptance | Kristof | Does the built POC meet the Definition of Done (§19)? | Build acceptance sign-off in `REVIEW_NOTES.md` |

---

## 10. How Kristof should work with Claude Code

You (Kristof) are the **Microsoft / AD / Entra / Silverfort / security domain expert** and the **product owner**.

You should:
- Validate or correct domain assumptions when asked (AD, Entra, licensing, Silverfort, security methodology).
- Decide what is customer-visible vs internal.
- Approve or reject scope additions.
- Sign off reviews per stage.
- Push back when a document is too long, too technical, or off-scope.

You should **not** be expected to:
- Design the software architecture.
- Choose Python libraries.
- Write code or tests.
- Resolve UI layout details below the principle level.

When I ask a domain question, I will give you a **bounded set of options** with my recommendation marked, so you can answer in seconds. I will not ask open-ended "what do you want?" questions.

When I make assumptions instead of waiting for you (as instructed), I will log them in `ASSUMPTIONS.md` so you can override later.

---

## 11. How developers should use the docs

When we hand off to developers, they should be able to:

1. Read `PRODUCT_DESIGN.md` and `POC_V1_SCOPE.md` to understand the product and the POC scope.
2. Read `MODULE_ARCHITECTURE.md` to understand the application shape.
3. Read the per-module design docs to understand domain logic per module.
4. Read `UI_DESIGN_DIRECTION.md` for the visual and interaction language.
5. Read `SECURITY_AND_GDPR.md` for non-negotiable security/GDPR boundaries.
6. Read `TASKS.md` for the prioritized backlog — **starting with the vertical slice items** (§6).

Developers should not need to ask Kristof for clarification on architecture, UX, or scope — those questions belong in `OPEN_QUESTIONS.md` and are resolved before they pick up a task.

---

## 12. What to mock, what to build, what to postpone

This is the single most important discipline for the POC. We restate it explicitly:

### Mock in POC V1
- Authentication (use a hard-coded role switcher or `?role=...` query param).
- Microsoft Graph collector (use sample JSON files).
- Silverfort API (use sample evidence files).
- Email / report distribution.
- Multi-tenant isolation (single-tenant single-customer at first; the model supports more).
- Background job queue (synchronous "parse on upload" is fine for POC).
- PDF rendering (HTML report is fine; PDF can be a stretch goal).

### Build for real in POC V1
- **A simplified shared data model that proves the lifecycle.** Not the final production schema. Not over-normalized. Not a complete relational design before the workflow is proven. The POC schema is allowed to be coarse and JSON-heavy where it helps; tightening it is an MVP concern.

  POC V1 data model proves these entities exist and connect:
  - Customer
  - Engagement
  - Assessment Run
  - Evidence
  - Control Result
  - Finding
  - Remediation Task
  - Report Preview
  - Publish State (on Finding and on Report)
  - Basic Audit Event

  Anything beyond this list (e.g., identity de-duplication tables, license catalog tables, role/permission tables, retention policies) is built only if the vertical slice requires it. The MVP/Full Product can expand the model later.

- The lifecycle (upload → parse → control evaluation → finding → review → publish).
- One real parser per module that runs against a sample file (AD toolkit ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON dump). The **first vertical slice** requires only the AD + BloodHound parsers.
- The AD + BloodHound + Silverfort + Entra **correlation logic** at a minimum viable level — but only after the vertical slice is reviewed.
- License-aware status logic (Licensed / Licensed but disabled / Not licensed / Manual review / Connector missing / Evidence missing / Not applicable / Unknown).
- The ACEN-branded UI shell, navigation, dashboard, findings workspace, evidence drawer, and report preview.

### Postpone past POC V1
- Real connectors (Graph live, Silverfort live, AD live).
- Real customer publishing portal.
- Real RBAC with Entra ID auth.
- Encryption at rest, KMS integration, secrets vault.
- Multi-tenant data isolation enforcement (vs design only).
- Advisory modules and all the non-Microsoft modules (Imprivata, Cato, Illumio).
- Defender XDR / Purview / Intune / Defender for Cloud modules.

---

## 13. Sample data requirements

POC V1 depends on representative sample data. Building the platform without good sample data is the fastest way to produce an unconvincing demo (R-0009).

### Required sample data

- **AD toolkit sample ZIP** (or sample JSON package matching `AD_TOOLKIT_DESIGN.md`).
- **SharpHound / BloodHound sample ZIP** (synthetic graph with ≥ 3 Tier 0 paths in ≥ 3 categories — per `BLOODHOUND_ANALYZER_DESIGN.md`).
- **Silverfort policy export sample** (synthetic policies with intentional coverage gaps).
- **Silverfort service account export sample** (synthetic discovery output).
- **Entra Graph JSON sample** (synthetic tenant: E3 + standalone Entra ID P1, no P2, owns Silverfort — per `POC_V1_SCOPE.md` §8).
- **License/capability sample profile** for the fictional customer.
- **Example report content** (Internal Detailed + Customer Summary).
- **Example customer and engagement metadata** ("Contoso Corp", "Q2 2026 Identity Security Review").

### Hard rule

> **No real customer data is committed to the repository unless it is explicitly anonymized, approved by the customer/DPO, and documented as such.**

For POC V1, we always prefer:
- Synthetic data.
- Anonymized data.
- Sanitized exports.
- Small representative samples that cover the demo story.

### Ownership

- **Kristof** validates whether the sample data is realistic from a security/domain perspective. He owns "does this look like a real engagement?".
- **Claude Code** ensures the sample data is safe to use, structured, documented (with a `SAMPLE_DATA_README.md` in the fixtures folder), and easy for developers to load through the same code path real evidence would use.

The sample data plan is one of the Stage 8 outputs (§4 stage map).

---

## 14. Complexity control rules

We apply these rules to **every feature, screen, control, and document section**. If the answer is "no" to most, we cut, mock, or defer.

### Why-this-feature questions

1. Does this feature support the POC demo journey?
2. Can it be mocked instead of built?
3. Does it belong in POC, MVP, full product, or not needed at all?
4. Does it introduce a *new* UI pattern, or does it reuse existing components?
5. Does it break module boundaries (e.g., AD-specific code in core)?
6. Does it require production-grade security to ship safely?
7. Does it increase customer data risk?
8. Does it make the product harder to explain to management?
9. Does it create endless scrolling, KPI clutter, or SIEM-style noise?
10. Does it require a live connector before the concept is even validated?

### Complexity control checklist (use at the end of every doc and every backlog item)

- [ ] Tier explicitly tagged (POC / MVP / Full / Not in scope).
- [ ] Belongs to a single module or to core — no overlap.
- [ ] Reuses an existing UI pattern, evidence type, finding shape, or scoring model.
- [ ] Has a clear demo or test path.
- [ ] Has a clear "what we will NOT do here" line.
- [ ] Does not require a real connector at this tier.
- [ ] Does not duplicate logic from another document.
- [ ] **Does this feature support the POC V1 demo story (§3)?**
- [ ] **Can it be proven through the first thin vertical slice (§6)?**
- [ ] **Can it be represented with sample data instead of a real connector?**
- [ ] **Does it avoid production-grade complexity in POC V1?**
- [ ] **Does it keep the UI focused and avoid endless scrolling?**
- [ ] **Does it reduce consultant/customer effort?**
- [ ] **Does it create real cross-module value?**
- [ ] **Is the documentation for this feature in the right file, without duplication (§15)?**

---

## 15. Documentation control rules

Documentation must stay reviewable, not become a second product to maintain.

### Rules

- Keep each document focused on one topic.
- Avoid repeating the same architecture explanation in every file.
- **Cross-reference, do not duplicate.** Link to the canonical statement; never restate it.
- Add an **executive summary** at the top of any document over ~400 lines.
- Move deep details into appendices if a document grows large.
- Target: every major design document remains readable in one sitting.
- Avoid endless-scrolling docs the same way we avoid endless-scrolling UI.
- Do not create competing versions of the same document. **Update the existing document; do not fork it.**
- When a topic belongs in another document, link to it or reference it — do not re-explain.

### Size rule

> **If a document grows beyond roughly 800 lines, add a concise executive summary at the top and consider splitting detailed appendices into a separate file.**

This is a soft cap that triggers a review, not an automatic split. Long docs are allowed when the content is genuinely cohesive (e.g., the `ENTRA_MODULE_DESIGN.md` control catalog). The executive summary is mandatory regardless.

### Roles

- **Claude Code (Documentation / Reviewer role, §7.9)** is responsible for actively applying these rules during and after every documentation pass.
- **Cross-document inconsistencies and duplication** are surfaced in `REVIEW_NOTES.md` and resolved at the relevant cycle review.

---

## 16. Suggested first 5 working sessions

This is the recommended starting cadence. Each session is **scoped to fit one focused conversation** so that context stays clean.

### Session 1 — Concept & POC framing (≈ 60–90 min)
- Walk through `DISCOVERY_WORKSHOP_ANSWERS.md`, `PRODUCT_DESIGN.md` (sections 1–6), and `POC_V1_SCOPE.md`.
- Decide: POC V1 goal, primary personas, **demo story (§3) approved**, sign-off on scope envelope.
- Outcome: Cycle 1 sign-off.

### Session 2 — Architecture & module boundaries (≈ 60 min)
- Walk through `MODULE_ARCHITECTURE.md`, `LICENSE_MODEL.md`, the data-model section of `PRODUCT_DESIGN.md`.
- Decide: are core/module boundaries clean? Is the simplified POC data model (§12) right? Is the license-aware status model right?
- Outcome: Cycle 2 sign-off.

### Session 3 — Module deep dive #1: AD + BloodHound (≈ 90 min)
- Walk through `AD_MODULE_DESIGN.md`, `AD_TOOLKIT_DESIGN.md`, `BLOODHOUND_ANALYZER_DESIGN.md`.
- Decide: AD control list approved? Toolkit ZIP shape approved? BloodHound deterministic path approach approved?
- Outcome: Cycle 3 partial sign-off (AD + BH).

### Session 4 — Module deep dive #2: Silverfort + Entra (≈ 75 min)
- Walk through `SILVERFORT_MODULE_DESIGN.md`, `ENTRA_MODULE_DESIGN.md`.
- Decide: Silverfort manual-first approach approved? Entra control list approved? Hybrid identity correlation approved?
- Outcome: Cycle 3 full sign-off.

### Session 5 — UX, Security/GDPR, Backlog (≈ 90 min)
- Walk through `UI_DESIGN_DIRECTION.md`, `SECURITY_AND_GDPR.md`, `TASKS.md`.
- Decide: Demo journey UX approved? Security boundaries approved? Backlog right-sized and **vertical slice tasks (§6) clearly marked**?
- Outcome: Cycles 4, 5, 6 sign-off → ready for management review (Cycle 7).

We do not start coding before Session 5 sign-off **and** Stage 8 build preparation sign-off (Cycle 8).

---

## 17. End-of-session summary template

Every major work session ends with this short summary (avoid long chat essays):

```
Done:
  - <bullet>
Files changed:
  - <path>
Decisions made (logged in DECISIONS.md):
  - <bullet>
Assumptions added (logged in ASSUMPTIONS.md):
  - <bullet>
Questions for Kristof (logged in OPEN_QUESTIONS.md):
  - <bullet>
Recommended next step:
  - <one line>
```

---

## 18. Definition of Ready for POC build

We begin Stage 9 (POC build) only when **all** of the following are true:

- [ ] `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md`, `MODULE_ARCHITECTURE.md` signed off.
- [ ] All four module design docs signed off.
- [ ] `UI_DESIGN_DIRECTION.md` signed off.
- [ ] `SECURITY_AND_GDPR.md` signed off for POC boundary set.
- [ ] `TASKS.md` POC backlog approved and small enough (target: ≤ 40 implementation tasks).
- [ ] **POC V1 demo story (§3) approved.**
- [ ] **Thin vertical slice (§6) approved** and tasks for the slice clearly marked in `TASKS.md`.
- [ ] **Sample data plan (§13) approved.**
- [ ] **Sample data ownership defined** (Kristof = domain realism; Claude Code = structure/safety/docs).
- [ ] **POC kill criteria (§20) accepted.**
- [ ] **Documentation control rules (§15) accepted** by all working roles.
- [ ] **Stage 8 build preparation completed and signed off** (Cycle 8) — separate from Stage 9.
- [ ] Demo journey documented end-to-end in `POC_V1_SCOPE.md`.

---

## 19. Definition of Done for POC V1

POC V1 is "done" when:

- [ ] **The thin vertical slice works end-to-end.**
- [ ] **The POC demo story (§3) can be demonstrated without major manual hacks.**
- [ ] **At least one BloodHound critical path finding is generated** by the analyzer.
- [ ] **At least one cross-module correlation finding is shown** (e.g., BH path to a Tier 0 account that lacks Silverfort coverage, or an Entra-privileged user synced from an AD account on a BH path).
- [ ] **At least one finding moves through review → publish → customer-visible view.**
- [ ] **At least one report preview is generated** (HTML, PDF optional).
- [ ] **The UI demonstrates clean drill-down instead of endless scrolling.**
- [ ] AD, BloodHound, Silverfort, Entra each produce at least one published finding (after the vertical slice expands horizontally).
- [ ] License-aware logic is visible on at least one Entra control and one Silverfort control.
- [ ] Customer publishing controls are visible in the UI (even if not enforced end-to-end).
- [ ] Audit log records the demo workflow.
- [ ] **Documentation matches the implemented POC** (no documented features that do not exist, no built features that are not documented).
- [ ] **Management can make a go/no-go MVP decision** with confidence; review pack ready (one deck + the demo).

---

## 20. POC V1 kill criteria

These are the failure modes that should stop the project from progressing to MVP. They feed the **Cycle 7 management review**.

POC V1 should **not** proceed to MVP if:

- The **demo journey cannot be explained clearly** in plain language to a non-technical executive.
- The platform feels like **multiple dashboards instead of one workflow**.
- **BloodHound findings are too noisy** to be useful (path detection produces 50+ paths the consultant cannot defend or prioritize).
- The **UX cannot show priority** without overwhelming users (top-3 finding view is unconvincing or buried).
- The **license-aware model confuses rather than clarifies** — customers feel scored unfairly or scored arbitrarily.
- The implementation **requires production-grade complexity before proving value** (auth/RBAC/encryption blocking the demo).
- The platform **cannot produce a convincing finding-to-remediation-to-report flow**.
- The **cross-module correlation does not create clear value** — correlation feels like a label on a coincidence, not a real story.
- The POC **cannot be demonstrated without too many manual hacks** (scripts run on the side, magic refreshes, fragile demo state).
- The product **does not simplify life** for consultants or customers — reviewers ask "what is this saving us?".

### If a kill criterion is triggered

We do **not** silently push past it. We:

1. Document it in `RISKS.md` (and reference the specific kill criterion).
2. Decide explicitly between four responses:
   - **Reduce scope** (cut the feature that triggers the failure mode).
   - **Adjust the demo journey** (change the story so the failure mode no longer applies).
   - **Postpone the feature** to MVP (acknowledge POC doesn't prove it).
   - **Stop the MVP investment** (the POC has answered "no").
3. Record the chosen response as a `DECISIONS.md` entry; this entry is the audit trail for the go/no-go.

---

## 21. Risks in our way of working

Tracked in `RISKS.md`; surfaced here so we can mitigate during the process:

| Risk | Mitigation |
|---|---|
| POC silently mutates into MVP | Use the §14 checklist on every feature; tier discipline. |
| Endless scrolling docs | §15 soft 800-line cap + executive summary trigger. |
| Module-specific hacks leak into core | Architecture review (Cycle 2) explicitly checks for this. |
| Silverfort API assumptions go untested | Every API claim is tagged "requires validation"; manual-first design. |
| BloodHound analyzer slides toward "AI does it" | Constraint repeated: detection/scoring/explanations are deterministic. |
| Customer data leaks via sample data | Use synthetic data only (§13); never embed real customer evidence in repo. |
| Style/branding fatigue derails progress | UX approved once, then locked; no rebrand in module sessions. |
| Token budget burned on re-summarizing | All decisions live in files; chat is for action and review, not storage. |
| Horizontal expansion before slice works | §6 hard principle: no horizontal expansion until vertical slice is reviewed. |
| Sample data unconvincing | Owned: Kristof (realism) + Claude Code (structure). Tracked in §13. |

---

## 22. Recommended next step

1. **Kristof reviews and approves this updated `WORKING_APPROACH.md`.**
2. **Claude Code reviews and updates the foundation working files** in `project-management/`:
   - `PROJECT_STATE.md` (stage map → 9 stages)
   - `DECISIONS.md` (log the decisions introduced by this update)
   - `ASSUMPTIONS.md` (log the assumptions introduced by this update)
   - `OPEN_QUESTIONS.md` (any new questions surfaced)
   - `TASKS.md` (split Stage 8 → Stage 8 build prep + Stage 9 POC build; mark vertical slice tasks)
   - `RISKS.md` (log the risks introduced by this update)
   - `REVIEW_NOTES.md` (extend sign-off tracker to 9 cycles)
   - `CHANGELOG.md` (entry for this update)
3. **Session 1 begins:**
   - `DISCOVERY_WORKSHOP_ANSWERS.md` review.
   - `PRODUCT_DESIGN.md` §1–6 review.
   - `POC_V1_SCOPE.md` review.
   - Cycle 1 sign-off.
4. **No coding starts** until Session 5 sign-off **and** Stage 8 build-preparation sign-off (Cycle 8).

---

*Last updated: 2026-05-15 — Operating model upgraded to 9 stages; demo story, vertical slice, sample data, kill criteria, documentation control added.*
