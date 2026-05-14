# WORKING_APPROACH.md

> How we will deliver this project end-to-end in a structured, token-efficient way.

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

## 3. Recommended overall approach

We work in **8 stages**, each ending in a **review checkpoint** with Kristof. We do **not start the next stage until the previous review is signed off** (or explicitly deferred).

We **do not write production code in stages 1–6**. Code work begins in stage 7 (build preparation) and stage 8 (POC build), and only after the scope, architecture, UX, and security/GDPR designs are approved.

### Stage map (one line per stage)

| # | Stage | Output | Review |
|---|---|---|---|
| 1 | Product framing | Discovery answers, POC V1 goal, demo story | Concept review |
| 2 | Architecture framing | Platform/module model, evidence/finding/score model | Architecture review |
| 3 | Module deep dives | AD, BloodHound, Silverfort, Entra designs | Module design review |
| 4 | UX & information architecture | Screens, navigation, no endless scrolling | UX review |
| 5 | Security & GDPR | Evidence, publishing, tenant boundaries | Security review |
| 6 | POC backlog | What is mocked vs built vs postponed | Backlog review |
| 7 | Management review | Concept, journey, scope, risks, go/no-go | Management decision |
| 8 | Build preparation & POC build | Implementation tasks, dev handoff, code | Build acceptance |

---

## 4. POC before MVP before Full Product

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
- Real Microsoft Graph collector with license-awareness.
- Silverfort API connector once the customer/version supports the documented endpoints.
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

## 5. Agent / role model

Claude Code will operate as a **multi-role architect** simulating these roles, either with subagents (when useful) or as sequential work passes (when subagents would burn context). Subagents are reserved for **parallelizable, well-scoped writing tasks** (e.g., writing the four module design documents in parallel after the foundation is approved).

### Roles

#### 5.1 Product Owner Agent
- **Responsibility:** product vision, POC scope, user journeys, management story, discovery answers.
- **Inputs:** Kristof's domain expertise, customer/commercial context.
- **Outputs:** `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md`, `DISCOVERY_WORKSHOP_ANSWERS.md`.
- **Key questions:** *Who is this for? What must it prove? What is the demo story?*
- **Must not:** define implementation, architecture, or UI components.
- **Review criteria:** Can a non-developer manager understand the value and scope in 10 minutes?

#### 5.2 Software Architect Agent
- **Responsibility:** application structure, modular monolith, domain boundaries, data model, maintainability.
- **Inputs:** product scope, modules, evidence types.
- **Outputs:** `MODULE_ARCHITECTURE.md`, data model sections of `PRODUCT_DESIGN.md`.
- **Key questions:** *What is core vs module? Where do extension points live? How do we prevent module-specific hacks in the core?*
- **Must not:** add features, dictate UX, optimize prematurely.
- **Review criteria:** Can a new developer onboard from the docs alone? Do AD/BH/SF/Entra reuse the same lifecycle (evidence → finding → score → report)?

#### 5.3 UX / UI Agent
- **Responsibility:** ACEN style translation, dashboard structure, clean navigation, customer vs internal separation.
- **Inputs:** ACEN 2025 brand guide, product scope, persona journeys.
- **Outputs:** `UI_DESIGN_DIRECTION.md`, screen inventories.
- **Key questions:** *What is the first thing the user sees? Where does each persona spend most of their time? What is the drill-down depth budget?*
- **Must not:** add SIEM-style clutter, design endless scrolling pages, invent new UI patterns per module.
- **Review criteria:** Does every page have one clear purpose? Is the customer view obviously separated from the internal view?

#### 5.4 Security & GDPR Agent
- **Responsibility:** evidence protection, tenant isolation, RBAC, audit logs, secure uploads, customer publishing, data minimization.
- **Inputs:** evidence types per module, customer publishing requirements.
- **Outputs:** `SECURITY_AND_GDPR.md`.
- **Key questions:** *Who can see this evidence? What is logged? What is published? What must never leave the platform?*
- **Must not:** apply production hardening to POC V1; flag what *must* be hardened before MVP.
- **Review criteria:** Could we defend this design in front of a customer DPO and a CISO?

#### 5.5 AD Module Agent
- **Responsibility:** AD assessment model, AD toolkit, PingCastle integration, Tier 0, AD controls, AD reporting.
- **Outputs:** `AD_MODULE_DESIGN.md`, `AD_TOOLKIT_DESIGN.md`.

#### 5.6 BloodHound Analyzer Agent
- **Responsibility:** SharpHound ZIP parsing, graph model, deterministic critical path analysis, risk scoring, path explanations, correlation.
- **Outputs:** `BLOODHOUND_ANALYZER_DESIGN.md`.
- **Key constraint:** detection, ranking, correlation, and initial explanations must be **deterministic and consultant-reviewable**. AI is allowed only for *language polish later*.

#### 5.7 Silverfort Module Agent
- **Responsibility:** Silverfort evidence model, manual/API modes, policy coverage, service accounts, enrollment, risk, correlation.
- **Outputs:** `SILVERFORT_MODULE_DESIGN.md`.
- **Key constraint:** any API endpoint claim must be marked as **requires validation against official Silverfort documentation / support / customer version**.

#### 5.8 Entra Module Agent
- **Responsibility:** Entra assessment model, Graph collection design, license-aware controls, CA, PIM, apps, hybrid identity.
- **Outputs:** `ENTRA_MODULE_DESIGN.md`.

#### 5.9 Documentation / Reviewer Agent
- **Responsibility:** consistency across documents, readability, deduplication, non-developer clarity, final handoff quality.
- **Outputs:** `REVIEW_NOTES.md`, cross-document diff lists, final pass before management review.
- **Key questions:** *Does this doc contradict another? Is anything restated 3 times? Is anything assumed without being written down?*

#### 5.10 QA / Test Agent
- **Responsibility:** acceptance criteria, test strategy, sample data validation, edge cases, regression checklist.
- **Outputs:** acceptance criteria sections in `POC_V1_SCOPE.md` and `TASKS.md`, test strategy section in build phase.
- **Key questions:** *How do we prove this works? What is the minimum sample dataset? What are the demo failure modes?*

---

## 6. Work phases (operational view)

Within each stage we follow the same micro-loop:

1. **Audit** — read what already exists (control files, prior decisions, related docs).
2. **Draft** — produce a focused output (one document or one section).
3. **Document state** — update `PROJECT_STATE.md`, log decisions in `DECISIONS.md`, log assumptions in `ASSUMPTIONS.md`, log questions in `OPEN_QUESTIONS.md`, log changes in `CHANGELOG.md`.
4. **Summarize** — short summary at the end of each work session (see §13).
5. **Wait for review** — do not progress past a checkpoint without explicit go.

---

## 7. Review cycles

Each stage ends in a named review. We do not start the next stage until the review is signed off (✅), explicitly deferred (⏸), or marked accepted-with-risk (⚠ logged in `RISKS.md`).

| Cycle | Reviewer | Focus | Approval artifact |
|---|---|---|---|
| 1. Concept & POC scope | Kristof | Is the value clear? Is scope right-sized? | Sign-off comment in `PROJECT_STATE.md` |
| 2. Architecture & module boundaries | Kristof + (optional) dev advisor | Are core/module boundaries clean? | `DECISIONS.md` entry |
| 3. Module designs (AD/BH/SF/Entra) | Kristof (domain) | Do controls and evidence make sense? | Per-module sign-off in `REVIEW_NOTES.md` |
| 4. UX / information architecture | Kristof | Does the demo journey flow? Is it ACEN-branded? | UX sign-off in `REVIEW_NOTES.md` |
| 5. Security & GDPR | Kristof | Is evidence handling defensible? | Security sign-off in `REVIEW_NOTES.md` |
| 6. POC build backlog | Kristof | Is the backlog small enough to actually deliver? | Backlog sign-off in `TASKS.md` |
| 7. Management review | Management | Go/no-go for MVP investment | External decision, logged in `DECISIONS.md` |

---

## 8. How Kristof should work with Claude Code

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

## 9. How developers should use the docs

When we hand off to developers, they should be able to:

1. Read `PRODUCT_DESIGN.md` and `POC_V1_SCOPE.md` to understand the product and the POC scope.
2. Read `MODULE_ARCHITECTURE.md` to understand the application shape.
3. Read the per-module design docs to understand domain logic per module.
4. Read `UI_DESIGN_DIRECTION.md` for the visual and interaction language.
5. Read `SECURITY_AND_GDPR.md` for non-negotiable security/GDPR boundaries.
6. Read `TASKS.md` for the prioritized backlog.

Developers should not need to ask Kristof for clarification on architecture, UX, or scope — those questions belong in `OPEN_QUESTIONS.md` and are resolved before they pick up a task.

---

## 10. What to mock, what to build, what to postpone

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
- The shared data model (organization, customer, engagement, assessment run, evidence, control, control result, finding, remediation task, report, audit log).
- The lifecycle (upload → parse → control evaluation → finding → review → publish).
- One real parser per module that runs against a sample file (AD toolkit ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON dump).
- The AD + BloodHound + Silverfort + Entra **correlation logic** at a minimum viable level.
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

## 11. Complexity control rules

We apply these rules to **every feature, screen, control, and document section**. If the answer is "no" to most, we cut, mock, or defer.

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

---

## 12. Suggested first 5 working sessions

This is the recommended starting cadence. Each session is **scoped to fit one focused conversation** so that context stays clean.

### Session 1 — Concept & POC framing (≈ 60–90 min)
- Walk through `DISCOVERY_WORKSHOP_ANSWERS.md`, `PRODUCT_DESIGN.md` (sections 1–6), and `POC_V1_SCOPE.md`.
- Decide: POC V1 goal, primary personas, demo story, sign-off on scope envelope.
- Outcome: Cycle 1 sign-off.

### Session 2 — Architecture & module boundaries (≈ 60 min)
- Walk through `MODULE_ARCHITECTURE.md`, `LICENSE_MODEL.md`, the data-model section of `PRODUCT_DESIGN.md`.
- Decide: are core/module boundaries clean? Is the license-aware status model right?
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
- Decide: Demo journey UX approved? Security boundaries approved? Backlog right-sized?
- Outcome: Cycles 4, 5, 6 sign-off → ready for management review (Cycle 7).

We do not start coding before Session 5 sign-off.

---

## 13. End-of-session summary template

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

## 14. Definition of Ready for POC build

We begin building only when **all** of the following are true:

- [ ] `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md`, `MODULE_ARCHITECTURE.md` signed off.
- [ ] All four module design docs signed off.
- [ ] `UI_DESIGN_DIRECTION.md` signed off.
- [ ] `SECURITY_AND_GDPR.md` signed off for POC boundary set.
- [ ] `TASKS.md` POC backlog approved and small enough (target: ≤ 40 implementation tasks).
- [ ] Sample data sources identified for each module (AD ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON).
- [ ] Demo journey documented end-to-end in `POC_V1_SCOPE.md`.

---

## 15. Definition of Done for POC V1

POC V1 is "done" when:

- [ ] Demo journey runs end-to-end on sample data without manual hacks.
- [ ] AD, BloodHound, Silverfort, Entra each produce at least one published finding.
- [ ] At least one **cross-module correlation finding** is produced (e.g., BloodHound path to a Tier 0 account that lacks Silverfort coverage, or an Entra-privileged user synced from an AD account on a BloodHound path).
- [ ] License-aware logic is visible on at least one Entra control and one Silverfort control.
- [ ] One report (HTML, PDF optional) can be generated and reviewed.
- [ ] Customer publishing controls are visible in the UI (even if not enforced end-to-end).
- [ ] Audit log records the demo workflow.
- [ ] Documentation is up to date with the actual code (no documented features that do not exist, no built features that are not documented).
- [ ] Management review pack is ready (one deck + the demo).

---

## 16. Risks in our way of working

Tracked in `RISKS.md`; surfaced here so we can mitigate during the process:

| Risk | Mitigation |
|---|---|
| POC silently mutates into MVP | Use the §11 checklist on every feature; flag and remove. |
| Endless scrolling docs | Hard cap: split docs over ~800 lines; reuse via links. |
| Module-specific hacks leak into core | Architecture review (Cycle 2) explicitly checks for this. |
| Silverfort API assumptions go untested | Every API claim is tagged "requires validation"; manual-first design. |
| BloodHound analyzer slides toward "AI does it" | Constraint repeated: detection/scoring/explanations are deterministic. |
| Customer data leaks via sample data | Use synthetic data only; never embed real customer evidence in repo. |
| Style/branding fatigue derails progress | UX approved once, then locked; no rebrand in module sessions. |
| Token budget burned on re-summarizing | All decisions live in files; chat is for action and review, not storage. |

---

## 17. Recommended next step

> Read this document and confirm:
> 1. The stage model in §3 is acceptable.
> 2. The role model in §5 is acceptable.
> 3. The first-5-sessions cadence in §12 is acceptable.
>
> Once confirmed, I will move to creating the foundation working files (`PROJECT_STATE.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `OPEN_QUESTIONS.md`, `TASKS.md`, `RISKS.md`, `REVIEW_NOTES.md`, `CHANGELOG.md`), then `DISCOVERY_WORKSHOP_ANSWERS.md` and `PRODUCT_DESIGN.md` for Session 1.

---

*Last updated: 2026-05-14 — Stage 0 (Working approach defined).*
