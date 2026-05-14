# PROJECT_STATE.md

> Single source of truth for current project status. Updated at the end of every working session.

---

## Project

**Name (working):** ACEN Gravity — Security Assessment Platform
**Tier:** POC V1 (validate concept; not MVP, not production)
**Owner:** Kristof Laerenbergh (Microsoft Security / Identity / AD expert, product owner)
**Operating partner:** Claude Code (multi-role architect: product, software architect, UX, security, module design, QA, docs)
**Start date:** 2026-05-14

---

## Current stage

**Stages 1–5 — Initial document pass complete; awaiting review.**

Stage map (full detail in `WORKING_APPROACH.md` §4 — operating model upgraded to **9 stages**):

| Stage | Title | Status |
|---|---|---|
| 0 | Working approach v2 (9-stage model + demo story + vertical slice + kill criteria + doc control) | ✅ |
| 1 | Product framing | 🟢 drafted; awaiting Cycle 1 sign-off |
| 2 | Architecture framing | 🟢 drafted; awaiting Cycle 2 sign-off |
| 3 | Module deep dives (AD/BH/SF/Entra) | 🟢 drafted; awaiting Cycle 3 sign-off |
| 4 | UX & information architecture | 🟢 drafted; awaiting Cycle 4 sign-off |
| 5 | Security & GDPR | 🟢 drafted; awaiting Cycle 5 sign-off |
| 6 | POC backlog | 🟡 skeleton in `TASKS.md`; refined after Cycles 1–5 (vertical-slice items must be marked) |
| 7 | Management review (go/no-go on MVP) | ⬜ pending |
| 8 | **Build preparation** (final backlog · skeleton · sample data plan · dev handoff · slice tasks ready) | ⬜ pending |
| 9 | **POC build** (working POC · tests · demo flow · report preview · mgmt review pack) | ⬜ pending |

---

## Goals

### POC V1 goal (working statement, to be confirmed in Cycle 1 review)

> Demonstrate that a single, modular, ACEN-branded assessment platform can ingest AD, BloodHound, Silverfort, and Entra evidence; produce license-aware controls, prioritized findings, and at least one cross-module correlation; and present this to management with a credible path to MVP — without becoming a production platform build.

### Non-goals for POC V1

- Production-grade multi-tenant SaaS.
- Live connectors (Microsoft Graph, Silverfort API, AD live collection).
- Customer-facing portal hardening.
- Authentication via Entra ID.
- Encryption at rest / KMS / secrets vault.
- Advisory / Defender / Purview / Intune / Imprivata / Cato / Illumio modules.

---

## Completed work (initial document pass)

| Document | Lines | Status |
|---|---:|---|
| `WORKING_APPROACH.md` | ~430 | ✅ |
| `PROJECT_STATE.md` (this file) | — | ✅ |
| `DECISIONS.md` (D-0001 … D-0011) | ~190 | ✅ |
| `ASSUMPTIONS.md` (A-0001 … A-0015) | ~150 | ✅ |
| `OPEN_QUESTIONS.md` (16 topic groups) | ~170 | ✅ |
| `TASKS.md` (8 stages, 60+ items) | ~190 | ✅ |
| `RISKS.md` (R-0001 … R-0012) | ~170 | ✅ |
| `REVIEW_NOTES.md` (cross-doc consistency + 16 pending items) | ~140 | ✅ |
| `CHANGELOG.md` | — | ✅ |
| `VISUAL_REFERENCES.md` (HTB / Fortify360 / Runtime) | ~190 | ✅ |
| `DISCOVERY_WORKSHOP_ANSWERS.md` (9 questions answered, POC/MVP/Full split) | ~270 | ✅ |
| `PRODUCT_DESIGN.md` (31 sections) | ~530 | ✅ |
| `POC_V1_SCOPE.md` (21 sections) | ~410 | ✅ |
| `MODULE_ARCHITECTURE.md` (18 sections) | ~520 | ✅ |
| `LICENSE_MODEL.md` (13 sections, 8-value enum, scoring formulas) | ~370 | ✅ |
| `SECURITY_AND_GDPR.md` (21 sections) | ~370 | ✅ |
| `UI_DESIGN_DIRECTION.md` (component-led, 20 sections) | ~570 | ✅ |
| `AD_TOOLKIT_DESIGN.md` | ~586 | ✅ |
| `AD_MODULE_DESIGN.md` (full control catalog) | ~1055 | ✅ |
| `BLOODHOUND_ANALYZER_DESIGN.md` (26 sections, deterministic per D-0005) | ~1157 | ✅ |
| `SILVERFORT_MODULE_DESIGN.md` (19 sections, every API mention tagged unverified) | ~887 | ✅ |
| `ENTRA_MODULE_DESIGN.md` (25 sections, full control catalog, license-aware worked example) | ~830 | ✅ |

**Total drafted:** ~9,500 lines across 22 documents.

**Decisions logged:** 11 (D-0001 … D-0011) — all proposed pending review.
**Assumptions logged:** 15 (A-0001 … A-0015) — all open pending validation.
**Open questions logged:** ~80 across 16 topics.
**Risks logged:** 12 (R-0001 … R-0012).
**Cross-document inconsistencies surfaced and reconciled or flagged:** 16 (see `REVIEW_NOTES.md`).

---

## Next steps

1. **Kristof reviews `WORKING_APPROACH.md`** and confirms the operating model.
2. **Cycle 1 review** — `DISCOVERY_WORKSHOP_ANSWERS.md`, `PRODUCT_DESIGN.md` (§1–6), `POC_V1_SCOPE.md`. Output: scope envelope sign-off.
3. **Cycle 2 review** — `MODULE_ARCHITECTURE.md`, `LICENSE_MODEL.md`. Output: architecture sign-off.
4. **Cycle 3 review** — `AD_MODULE_DESIGN.md`, `AD_TOOLKIT_DESIGN.md`, `BLOODHOUND_ANALYZER_DESIGN.md`, `SILVERFORT_MODULE_DESIGN.md`, `ENTRA_MODULE_DESIGN.md`. Output: module sign-off + close the 16 items in `REVIEW_NOTES.md`.
5. **Cycle 4 review** — `UI_DESIGN_DIRECTION.md`, `VISUAL_REFERENCES.md`. Output: UX sign-off; brand owner confirmation on D-0010 (Trinidad usage, ≤ 2 px radius).
6. **Cycle 5 review** — `SECURITY_AND_GDPR.md`. Output: security boundaries sign-off for POC.
7. **Cycle 6** — refine `TASKS.md` POC backlog to ≤ 40 items; mark vertical-slice tasks per `WORKING_APPROACH.md` §6.
8. **Cycle 7** — Management review (go/no-go vs. kill criteria, `WORKING_APPROACH.md` §20).
9. **Stage 8 — Build preparation** (architecture skeleton, sample data plan, dev handoff) → Cycle 8 sign-off.
10. **Stage 9 — POC build** begins (vertical slice first, then horizontal expansion).

Suggested cadence: see `WORKING_APPROACH.md` §16 — five working sessions to reach build-ready.

---

## Blockers

None at this time.

---

## Key references

| Reference | Location | Purpose |
|---|---|---|
| ACEN 2025 brand guide (EN) | `OneDrive - Cronos\ACEN Intranet - Branding\ACEN\Styleguide\Acen_2025_Huisstijlgids_12nov_EN.pdf` | Source of truth for typography, colour, graphics, layout rules |
| ACEN 2025 brand guide (NL) | `OneDrive - Cronos\ACEN Intranet - Branding\ACEN\Styleguide\ACEN_Stijlgids_Dutch_2025.pdf` | Dutch reference copy |
| Visual references shared 2026-05-15 | `VISUAL_REFERENCES.md` | HTB, Fortify360, Runtime API dashboards |
| Discovery template | (provided in initial brief: `Security_Dashboard_V2_Discovery_Template.docx`) | Source of discovery questions answered in `DISCOVERY_WORKSHOP_ANSWERS.md` |
| Microsoft licensing reference | https://m365maps.com | **Inspiration only** — not source of truth; replace with official Microsoft references before MVP (Q-0071) |
| Silverfort API references | Public integration documentation | **Requires validation against official Silverfort docs/support and customer version** before MVP (D-0006, Q-0090) |

---

*Last updated: 2026-05-15 — Stages 1–5 drafted; operating model upgraded to 9 stages (D-0012 … D-0017); ready for Cycle 1 review.*
