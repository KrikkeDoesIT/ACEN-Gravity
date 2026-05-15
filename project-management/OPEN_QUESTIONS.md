# OPEN_QUESTIONS.md

> Questions that need an answer before they become decisions. Grouped by topic. Each question carries a target reviewer and a tier (POC / MVP / Full).
>
> **Format:** `Q-NNNN  | tier | owner | question` with a follow-up `Why it matters:` line.
> Resolved questions are moved to `DECISIONS.md` (or `ASSUMPTIONS.md` if validated) and **removed from this file**.

---

## 1. Product strategy

- **Q-0001 | POC | Kristof** — Is "ACEN Gravity" the correct working name, or should we pick another? *Why it matters:* affects all document headings, repo branding, and demo screens.
- **Q-0002 | POC | Kristof + ACEN management** — Who is the **primary audience** for the POC demo: management/board, customers in a sales setting, or internal consultants for usability validation? *Why it matters:* drives the demo journey emphasis (commercial vs technical).
- **Q-0003 | MVP | Kristof + ACEN sales** — Will this platform be sold standalone, bundled with engagements, or used as a free pre-engagement teaser? *Why it matters:* affects publishing, licensing, branding decisions.
- **Q-0004 | Full | Kristof + ACEN management** — What is the commercial relationship to existing ACEN assessment offerings (current engagement deliverables, M365 security brief, AD security workshop)? *Why it matters:* determines whether this replaces or augments them.

## 2. POC scope

- **Q-0010 | POC | Kristof** — Confirm the four POC modules: AD, BloodHound, Silverfort, Entra. Any to drop or swap for POC? *Why it matters:* defines build effort.
- **Q-0011 | POC | Kristof** — Should POC V1 include a single fictional "demo customer" only, or two customers to demonstrate the multi-customer model? *Why it matters:* +1 customer = some UI work but stronger demo.
- **Q-0012 | POC | Kristof** — Is the PDF report a hard requirement for POC, or is HTML-only acceptable for management review? *Why it matters:* Playwright dependency.

## 3. MVP scope

- **Q-0020 | MVP | Kristof** — Which connector ships first in MVP: AD toolkit deployed to customer infra, Microsoft Graph for Entra, or Silverfort API? *Why it matters:* shapes the MVP backlog ordering.
- **Q-0021 | MVP | Kristof** — Will MVP target ACEN consultants only, or a small pilot customer cohort as well? *Why it matters:* security/operational maturity required.

## 4. Customer access

- **Q-0030 | MVP | Kristof** — Do customers self-serve in the portal (read-only finding access, retest requests, etc.), or do consultants always present results in person? *Why it matters:* publishing workflow vs presentation workflow.
- **Q-0031 | MVP | Kristof** — Should customers see the **technical detail** of findings or only **executive summaries** by default? *Why it matters:* default visibility flag (`customer_summary` vs `customer_full`).

## 5. Security & GDPR

- **Q-0040 | POC | Kristof + ACEN DPO** — For POC demo data, do we use a fictional company name and fully synthetic data, or sanitized excerpts from prior real engagements? *Why it matters:* DPO sign-off and repo-safety.
- **Q-0041 | MVP | Kristof + ACEN DPO** — Where will evidence files be stored at MVP — ACEN-managed object storage, on-prem at the customer, or both? *Why it matters:* tenancy and BCDR model.
- **Q-0042 | MVP | Kristof + ACEN DPO** — Retention policy for evidence and findings: how long, and what happens after engagement close? *Why it matters:* GDPR data-minimization compliance.
- **Q-0043 | MVP | Kristof** — Will MVP authentication use ACEN's own Entra tenant (employee identities) only, or customer Entra federation (B2B)? *Why it matters:* drives RBAC and identity model.

## 6. AD toolkit

- **Q-0050 | POC | Kristof** — Confirm the AD toolkit runs **manually** under a delegated read-only privileged account, with no service install and no automation. *Why it matters:* security posture and customer onboarding friction.
- **Q-0051 | MVP | Kristof** — Should the toolkit be **digitally signed** by ACEN, and if so, is a code-signing process in place? *Why it matters:* customer execution policy.
- **Q-0052 | POC | Kristof** — PingCastle: do we always require a PingCastle run as part of evidence, or only "if available"? *Why it matters:* completeness of AD controls.
- **Q-0053 | POC | Kristof** — Tier 0 boundary: do we follow Microsoft's Enterprise Access Model definition strictly, or accept a customer-specified Tier 0 list per engagement? *Why it matters:* control results and BloodHound target set.

## 7. BloodHound Analyzer

- **Q-0060 | POC | Kristof + dev** — Confirm SharpHound CE JSON format is the target format. Do we also need to support legacy BloodHound 4.x ZIPs for any current customers? *Why it matters:* parser scope.
- **Q-0061 | POC | Kristof** — How many critical path categories should POC demonstrate at minimum? Current proposal: at least 3 (privilege escalation via group nesting, ACL abuse, unconstrained delegation). *Why it matters:* demo richness vs parser scope.
- **Q-0062 | MVP | Kristof** — Should the analyzer support AD CS (ESC1–ESC8) paths in MVP, or defer? *Why it matters:* significant additional scope.
- **Q-0063 | POC | Kristof** — Should the demo include a **graph visualization** of paths, or only ranked path tables with step-by-step text explanations? *Why it matters:* UI scope.

## 8. Licensing

- **Q-0070 | POC | Kristof** — For POC, do we use a small license catalog (E3, E5, EMS E3/E5, Entra ID P1/P2, Defender for Identity, Silverfort) or a fuller list? *Why it matters:* catalog maintenance.
- **Q-0071 | MVP | Kristof + Microsoft licensing reference** — What authoritative source should replace m365maps before MVP — Microsoft service plan catalog via Graph (`subscribedSkus`), official Microsoft licensing docs, or a third-party feed? *Why it matters:* accuracy.
- **Q-0072 | MVP | Kristof** — Should the platform automatically detect customer licensing from Microsoft Graph at MVP, or always require consultant confirmation? *Why it matters:* trust model.

## 9. Microsoft Graph

- **Q-0080 | MVP | Kristof** — Confirm read-only application permissions set (see ASSUMPTIONS A-0007). Any reluctance from customers about `Application.Read.All` or `AuditLog.Read.All`? *Why it matters:* customer onboarding friction.
- **Q-0081 | MVP | Kristof** — Should the Entra collector run inside the customer tenant (e.g., ACEN-published multitenant app) or be a "bring-your-own-app-registration" model? *Why it matters:* operational and trust model.

## 10. Silverfort

- **Q-0090 | MVP | Kristof + Silverfort support** — Validate which API endpoints are available in the customer's Silverfort version and the auth model. The five endpoints in the prompt are unconfirmed. *Why it matters:* connector design.
- **Q-0091 | POC | Kristof** — What evidence format will customers export from Silverfort manually for POC — JSON exports from Silverfort UI, CSV, or screenshots? *Why it matters:* parser scope.
- **Q-0092 | POC | Kristof** — Do customers have a standard Silverfort "AD privileged groups" policy template we should assume exists, or is policy state highly customer-specific? *Why it matters:* control logic.

## 11. Reporting

- **Q-0100 | POC | Kristof** — Two reports (Internal Detailed + Customer Summary) for POC, or just one? *Why it matters:* template work.
- **Q-0101 | POC | Kristof** — Branding on customer report — full ACEN brand, co-branded with customer, or generic? *Why it matters:* report template. **Related:** Q-0151 (broader customer co-branding scope at Full Product).

## 12. UI & branding

- **Q-0110 | POC | Kristof** — Confirm the single digital adaptation in D-0010 (≤ 2px border-radius on interactive controls) is acceptable to ACEN brand owners. *Why it matters:* brand consistency.
- **Q-0111 | POC | Kristof** — Is Trinidad orange (`#fd5400`) the primary action accent (buttons, CTAs), or do we reserve it for alerts/critical findings and use a calmer accent for default actions? *Why it matters:* UI tone.
- **Q-0112 | POC | Kristof** — Should the application UI use the ACEN gradient backgrounds (subtle, executive) or remain flat for data clarity? *Why it matters:* readability vs brand feel.

## 13. Future modules

- **Q-0120 | Full | Kristof** — Of the 10+ future modules, which 2–3 are the **highest priority** after the POC four? *Why it matters:* architecture extension priorities.
- **Q-0121 | Full | Kristof** — Are Advisory modules (no product evidence, consultant-driven) a *first-class* module type, or implemented differently? *Why it matters:* core data model.

## 14. Operations & support

- **Q-0130 | MVP | Kristof + ACEN ops** — Who runs and supports MVP — internal ACEN ops, an external partner, or the consultants themselves? *Why it matters:* support model and SLA design.

## 15. Commercial model

- **Q-0140 | Full | Kristof + ACEN sales** — Subscription, per-engagement, or hybrid pricing? *Why it matters:* metering, audit log retention, customer publishing controls.

## 16. Discovery decisions

- **Q-0150 | POC | Kristof** — The most important workshop decision (per discovery template): confirm framing as *"What POC V1 needs to prove using AD/BH/SF/Entra, without becoming a production build."* — agreed? *Why it matters:* anchors the entire program.

## 17. Outbound integrations

- **Q-0160 | MVP | Kristof + ACEN delivery** — **Xurrent (4me) integration** — at MVP, push a Finding's `RemediationTask` into ACEN's Xurrent tenant as a service request; store `xurrent_request_id` + URL on the task; optional periodic pull of request state to sync the Finding's `state` / `retest_requested`. Open sub-questions: (a) one-way push (simpler) vs two-way sync; (b) automatic per-publish push vs explicit "Send to Xurrent" button; (c) CMDB enrichment scope (asset ownership / business unit / criticality on the `Identity` row); (d) field mapping — Finding.title → SR subject, severity → priority, remediation → SR description, identity_refs → affected CIs. *Why it matters:* ACEN consultants already live in Xurrent during delivery, so this is the highest-leverage outbound integration. It also seeds the pattern for the **Full Product** customer-tenant version (customer's own Xurrent / ServiceNow / Jira).
- **Q-0161 | Full | Kristof + ACEN sales** — **Customer-tenant ITSM push** — at Full Product, replicate the Xurrent pattern but into the customer's own ITSM (Xurrent / ServiceNow / Jira). Open sub-questions: (a) per-customer connector config UI; (b) OAuth vs API token; (c) closed-loop status sync; (d) custom field mapping per customer. *Why it matters:* big SaaS-platform expectation; sells the platform; needs careful permissioning since data flows outbound to a customer system.

## 18. Customer co-branding (Full Product)

- **Q-0151 | Full | Kristof + ACEN sales** — Per-customer **co-branding scope**: should customers see their **logo + 3 accent colours** (primary + 2 secondary) in their portal and on the Customer Summary report? Strict rules under consideration: themes touch *accents only* (chart series, customer-summary CTA tint, report header); never override status colours (ok / warn / critical / neutral / info) or module category colours (AD / BH / SF / Entra). Customer report theming is the lowest-friction first version. Consultant view never themed. *Why it matters:* commercial positioning (white-label as an add-on or standard), Customer Summary report template (couples directly to Q-0101), customer self-service portal scope (Full Product). Tag: **Full Product**, **not POC**, **probably not MVP** — captured here to prevent scope-creep into POC V1 (R-0001).
- Sibling: Q-0101 (Customer Summary report co-branding — *first* place this lands once the report exists).

---

*Last updated: 2026-05-15 — Q-0151 added (customer co-branding scope).*
