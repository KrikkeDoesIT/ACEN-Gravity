# DISCOVERY_WORKSHOP_ANSWERS.md

> Answers to the 9 questions from `Security_Dashboard_V2_Discovery_Template.docx`. Each answer includes its meaning for POC V1, MVP, and Full Product, plus open assumptions that need validation. Draft answers are working positions for **Cycle 1** review.

---

## Reading guide

| Tier | Meaning |
|---|---|
| POC V1 | What this answer means for the validation POC (sample data, no live connectors) |
| MVP | What it means for the first usable consultant version |
| Full | What it means for the production customer-facing platform |

Sources of authority: Kristof (domain, customer, security), ACEN management (commercial, brand), prospective customers (validation). Open assumptions are listed at the end of each question.

---

## 01. What triggered this project and what is the core problem?

**Answer.**
Across ACEN engagements (AD security assessments, Microsoft 365 security briefs, hybrid identity reviews, Silverfort onboarding), the same pain repeats:
- Findings are produced in **siloed deliverables** (Word reports, Excel sheets, PingCastle exports, BloodHound graphs, Silverfort screenshots, Entra/Graph extracts). The customer reads four documents and asks: *"What do I actually do first?"*
- There is **no shared lifecycle**: collect → parse → control → finding → remediation → retest → publish — each engagement reinvents it.
- License-awareness is ad-hoc: customers get scored against features they do not own.
- Customers cannot see progress between engagements; consultants do not have a clean handoff between team members.
- BloodHound / SharpHound graphs are technically rich but operationally opaque to executives.
- Silverfort coverage is rarely correlated with AD privilege escalation paths or Entra hybrid-admin risks.

**Core problem.** ACEN delivers high-quality identity-security expertise but lacks a **unified, modular, repeatable assessment platform** that connects AD, BloodHound, Silverfort, and Entra evidence into one prioritized story for executives and one actionable backlog for technical teams.

**POC V1 means.** Demonstrate, on sample data, that *one* platform can hold all four module outputs and produce a single prioritized story including a meaningful cross-module correlation.
**MVP means.** Replace sample data with real customer evidence (toolkits, Graph, manual Silverfort exports). Used by ACEN consultants on live engagements.
**Full means.** Customers self-serve; multi-tenant; managed-service supported; integrated with ACEN engagement billing.

Open assumptions: A-0001, A-0002. Open questions: Q-0002, Q-0004.

---

## 02. What is at risk if we do nothing?

**Answer.**
- **Commercial:** ACEN's identity-security offer competes with bigger vendors and integrators that *do* present unified portals. Continuing with siloed deliverables loses deals where the customer asks for a platform demo during selection.
- **Operational:** Consultants spend disproportionate time on report-writing, hand-rolled Excel, and reformatting BloodHound/PingCastle output. Margins on each engagement are thinner than they should be.
- **Quality:** Without a shared lifecycle, important cross-module risks (e.g., a BloodHound path that ends at an Entra hybrid admin who is not covered by a Silverfort policy) are missed because no single deliverable owns them.
- **Customer outcomes:** Customers receive findings but no continuous progress view. Retest cycles are manual and friction-heavy. Customers don't see improvement, so they don't renew advisory.
- **Knowledge capture:** Engagement IP lives in consultant heads and OneDrive folders. Onboarding new consultants is slow; consultant churn is expensive.

**POC V1 means.** Prove there is a credible path to address these risks. The POC itself does not solve them — it justifies investment in MVP.
**MVP means.** Begin to actually address operational and quality risks on real engagements. Commercial risk reduction starts when MVP is shown to customers.
**Full means.** Address the commercial risk fully via a credible customer-facing platform.

Open questions: Q-0003, Q-0004, Q-0140.

---

## 03. Who are the primary users and what question must the dashboard answer for each?

**Answer.** Three primary personas in POC V1 (a fourth admin role exists for setup only):

| Persona | Who | Primary question |
|---|---|---|
| **ACEN Consultant / Security Engineer** | Internal delivery, runs engagements | *"What is the current risk for this customer, what evidence supports it, and what should I fix first with them — and what is blocked by missing licensing, connectors, or evidence?"* |
| **Customer CISO / Executive** | Customer-side decision-maker, time-poor | *"Where do I stand on identity security, what changed since last engagement, and what 3 things should I invest in or fix first?"* |
| **Customer IT / Security Lead** | Customer-side hands-on owner | *"Which findings are mine to fix, in what order, with what evidence, and what does success look like for retest?"* |

A fourth role exists in the system but is not a "user" in the demo sense:

| Role | Who | Visibility |
|---|---|---|
| **Platform Admin** | ACEN ops | Setup screens only (organizations, customers, users, license catalog management) — not part of the demo journey |

**POC V1 means.** All three personas are demonstrable via a role-switcher (no real auth, A-0013). Each persona's "first screen" answers its primary question within ~10 seconds of landing.
**MVP means.** Real authentication via ACEN Entra tenant (consultants) and per-customer access policy (customer roles). RBAC enforced server-side.
**Full means.** Customer Entra B2B federation or magic-link invites; granular per-customer roles; access reviews.

Open assumptions: A-0003, A-0013. Open questions: Q-0030, Q-0031, Q-0043.

---

## 04. What is the minimum functionality needed on day one?

**Answer.** "Day one" here = POC V1 management review demo. The minimum is **the demo journey** end-to-end on sample data.

Required for POC V1:
1. **Customer / engagement / assessment run** entities exist; consultant can pick one.
2. **Evidence upload** for each of the four modules works on sample files (AD toolkit ZIP, SharpHound ZIP, Silverfort export, Entra Graph JSON dump).
3. **At least one parser per module** produces normalized data.
4. **At least 4 controls per module** evaluate and produce findings with severities and license-aware statuses.
5. **At least one cross-module correlation finding** is produced and visible in the UI.
6. **One overview dashboard** answers each persona's primary question.
7. **Findings workspace** with filters, detail drawer, evidence link, customer visibility flag.
8. **Publishing modal** allowing consultant to mark findings `internal_only` / `customer_summary` / `customer_full`.
9. **One report (HTML)** generated from the demo data, split into Internal and Customer versions.
10. **Audit log** records the demo workflow steps.
11. **ACEN-branded shell** — visible enough to demonstrate the brand alignment for management.

Out of scope for day one (POC V1):
- Authentication, RBAC enforcement, multi-tenancy enforcement.
- Live connectors (AD live, Graph live, Silverfort API live).
- Retest workflow (placeholder only).
- Customer self-service.
- PDF rendering (HTML acceptable).
- Background jobs, scheduling.

**MVP minimum (later).**
Add: real AD toolkit deployment, real Microsoft Graph collector, manual Silverfort upload remains, retest workflow, real auth (ACEN consultants only), audit log enforcement, encrypted evidence storage.
**Full minimum (later).**
Add: customer self-service portal, multi-tenant isolation enforcement, BCDR, support model, billing integration.

Open assumptions: A-0009, A-0010, A-0012, A-0013. Open questions: Q-0010, Q-0011, Q-0012.

---

## 05. How will we know V2 has succeeded in 6 months?

> "V2" here = the POC V1 + MVP delivery sequence over the next ~6 months.

**Success indicators.**

For POC V1 (target: weeks 1–8 from sign-off):
- [ ] Demo journey runs end-to-end on sample data without manual hacks.
- [ ] Management signs off "go" decision for MVP investment, in writing.
- [ ] Discovery questions in this document are not re-asked (i.e., the design holds up).
- [ ] At least 1 ACEN sales/account stakeholder confirms the demo is presentable to prospects.

For MVP (target: weeks 8–26):
- [ ] At least 1 real engagement is delivered with the platform end-to-end (AD + Entra at minimum).
- [ ] BloodHound Analyzer produces critical paths a consultant signs off as accurate.
- [ ] At least 1 customer sees a published Customer Summary report and feeds back positively.
- [ ] ACEN consultant feedback: net time-savings ≥ 20% versus the prior siloed flow (measured on one matched engagement).
- [ ] No security/GDPR incident from evidence handling.

**POC V1 means.** Track the POC indicators only. Cycle 7 management decision is the lead measure.
**MVP means.** All five MVP indicators apply.
**Full means.** Add: customer retention, recurring revenue indicators, support tickets per customer per month, multi-tenant isolation audits.

Open questions: Q-0002, Q-0020, Q-0021.

---

## 06. What would tell us V2 missed the mark?

**Answer.**
- Management defers the go/no-go decision a second time without specific, addressable reasons.
- Demo audiences cannot summarize what the platform does after the demo.
- Consultants prefer the legacy siloed approach for real engagements after MVP.
- Customer audiences ask "where's my data?" and the answer is "it's mocked / from sample data" *after MVP* — i.e., MVP shipped without real connectors when they were promised.
- BloodHound paths produced by the analyzer get rejected by consultants as inaccurate.
- Cross-module correlation produces obvious false positives in the first real customer dataset.
- A scoring result triggers a customer complaint (e.g., scored down for an unlicensed feature → A-0007, R-0007).
- Evidence-handling concerns from a customer DPO or CISO block onboarding.
- The platform becomes another silo (one more dashboard to look at), not a consolidator.

**POC V1 means.** Run a demo dry-run with at least one internal "fresh eyes" reviewer; capture early signals.
**MVP means.** First real engagement is the moment of truth — fast feedback loop with the consultant team is critical.
**Full means.** Add quantified leading indicators (churn, NPS, ticket volume) once the population is large enough.

---

## 07. What are the hard constraints?

**Answer.**

Process / scope constraints:
- POC is for **management decision**. It must finish on time, not be technically perfect.
- POC must not require live customer data, customer auth, or production-grade hosting.
- POC must not require new vendor contracts (Silverfort API access, Microsoft Premier, etc.).
- Build effort must be small enough that one developer can deliver POC in ~6–8 weeks part-time.

Technical constraints:
- Stack is FastAPI + HTMX + Tailwind + PostgreSQL (D-0003). No SPA build pipeline.
- BloodHound analyzer must be deterministic (D-0005).
- Synthetic data only in repo (D-0011).
- ACEN brand guide applies (D-0010).

Domain constraints:
- License-aware logic must not penalize customers for unowned capabilities (D-0007/D-0008).
- Customer visibility is `internal_only` by default (D-0009).
- AD toolkit is read-only and non-destructive (per prompt, expanded in `AD_TOOLKIT_DESIGN.md`).
- Silverfort API claims are tagged "requires validation" (D-0006).

Security/GDPR constraints:
- No real customer evidence committed to git.
- Sensitive data classes (privileged accounts, attack paths, GPO weaknesses) cannot leak to customers without consultant publishing action.
- Designed with future encryption-at-rest, KMS, audit retention — but not implemented in POC.

Commercial constraints (working assumptions):
- ACEN brand identity must be visibly applied.
- Microsoft and Silverfort vendor naming used only in supportable ways (no claims beyond public documentation).

**POC V1 means.** Above constraints apply now.
**MVP means.** Hard constraints expand: real customer data handling, real auth, real connectors, GDPR DPA terms.
**Full means.** Production-grade SLAs, BCDR, certified hosting.

Open questions: Q-0040, Q-0041, Q-0042.

---

## 08. What dependencies could block or delay delivery?

**Answer.**

| Dependency | Risk | Mitigation |
|---|---|---|
| Kristof's domain validation time | Medium | Sessions are scoped and time-boxed; Kristof gets bounded-option questions (`WORKING_APPROACH.md` §8). |
| Synthetic dataset quality | Medium | Dedicated task per module (T-6032, T-6046, T-6053, T-6063); R-0009. |
| ACEN brand owner sign-off on digital adaptation | Low | Q-0110 raised early; UI tokens isolate the change. |
| Silverfort API documentation access (for MVP) | Medium | POC is manual-mode only (D-0006); Q-0090 carried to MVP planning. |
| BloodHound CE schema stability | Low | A-0005 — assume current CE format; legacy support best-effort. |
| Microsoft Graph permission consent (for MVP) | Low | A-0007 — application permissions, consent-once; Q-0080 carried to MVP. |
| Postgres on demo workstation | Low | docker-compose provided; R-0010. |
| Developer availability for POC build | Medium | Backlog (`TASKS.md`) is scoped to ≤ 40 implementation tasks; complexity checklist enforced. |
| Brand guide details below the prompt level | Low | OneDrive copy is the source of truth; if a brand detail is missing, default to the prompt's palette/typography. |
| Decisions blocked on a single stakeholder | Medium | Resolution falls back to a documented assumption (A-NNNN) so work continues; Kristof can override later. |

**POC V1 means.** Above. We will not start coding before Cycles 1–6 sign-off (per `WORKING_APPROACH.md` §14).
**MVP means.** Add: customer onboarding, vendor contracts, hosting decisions, real data handling agreements.
**Full means.** Add: BCDR providers, support model, billing integration, multi-tenant security audits.

---

## 09. What is the single most important workshop decision?

**Answer (working form).**

> **The workshop must decide what POC V1 needs to prove**, using AD, BloodHound, Silverfort and Entra as the core demonstration modules, **without accidentally turning the POC into a production platform build.**

**Why this is the single most important decision.**

- Every other decision (architecture, scope, UX, security boundaries) is downstream of this one. If POC scope is wrong, the platform is wrong.
- POC V1's audience is the **management go/no-go**, not customers and not consultants. The demo must be coherent, complete, and *small*. Adding "just one more" feature is the failure mode (R-0001).
- The four modules are not equally mature: AD/PingCastle is solid evidence; BloodHound is technically rich but needs careful presentation; Silverfort is API-uncertain; Entra is license-dependent. The workshop has to agree on a balanced demo that does justice to all four without overcommitting any.
- The workshop also has to agree on what the POC explicitly **will not** prove — so that, at management review, "we did not address X" is a feature of the scope, not a gap.

**POC V1 means.** This is the Cycle 1 decision. Sign-off is the launch condition for everything else.
**MVP means.** The analogous decision is *"what does MVP need to prove to onboard a paying engagement?"* — answered at the end of POC V1.
**Full means.** The analogous decision is *"what does Full Product need to prove to onboard a self-serve paying customer?"* — answered at the end of MVP.

Open question: Q-0150.

---

## Summary — answers at a glance

| # | Question | Working answer (one line) | Cycle 1 ask of Kristof |
|---|---|---|---|
| 01 | Trigger / core problem | Need one modular platform that unifies AD/BH/SF/Entra into one story | Confirm framing |
| 02 | Risk of inaction | Commercial, operational, quality, customer-outcome, knowledge-capture losses | Confirm priorities |
| 03 | Primary users | Consultant, Customer Executive, Customer IT Lead (+ admin) | Confirm personas (A-0003) |
| 04 | Day-one minimum | The demo journey end-to-end on sample data, with cross-module correlation | Confirm minimum list |
| 05 | 6-month success | POC sign-off → MVP delivered → first real engagement positive | Confirm indicators |
| 06 | Miss signals | Decision deferred, demo unclear, consultants reject paths, customer complaint | Confirm signals |
| 07 | Hard constraints | POC tight scope, deterministic BH, synthetic data, ACEN brand | Confirm |
| 08 | Dependencies | Kristof time, synthetic data quality, brand sign-off, Silverfort API at MVP | Confirm |
| 09 | Single most important decision | Define POC scope without turning it into a production build | **Hold this workshop first** |

---

*Last updated: 2026-05-15.*
