# ACEN Gravity

Modular, license-aware identity-security assessment platform. POC V1.

> **Status (2026-05-15):** Stages 1–5 documents drafted; ready for review cycles. **No code yet.**

---

## What is this?

ACEN Gravity unifies four identity-security modules — **Active Directory**, **BloodHound attack-path analysis**, **Silverfort**, **Microsoft Entra** — into one workflow: collect evidence → evaluate controls → produce findings → prioritize remediation → publish to customer. Built modular so future modules (Defender, Purview, Intune, Imprivata, Cato, Illumio, …) plug in additively.

POC V1's goal is to validate the concept on synthetic data for an ACEN management go/no-go decision on MVP investment.

> **POC build — synthetic data only — never for customer use.** No real customer evidence in this repo.

---

## Folder layout

```
ACEN Gravity/
├── README.md                    ← you are here
└── project-management/          ← all design / scope / state documents
```

Code will live alongside `project-management/` in future folders (planned: `platform_core/`, `modules/`, `tests/`, `tools/`).

---

## Where to start

| Role | Read |
|---|---|
| First-time reviewer | [`WORKING_APPROACH.md`](project-management/WORKING_APPROACH.md) → [`PROJECT_STATE.md`](project-management/PROJECT_STATE.md) → [`DISCOVERY_WORKSHOP_ANSWERS.md`](project-management/DISCOVERY_WORKSHOP_ANSWERS.md) → [`PRODUCT_DESIGN.md`](project-management/PRODUCT_DESIGN.md) |
| Kristof (product owner) | [`PROJECT_STATE.md`](project-management/PROJECT_STATE.md) for status, then the 5-session cadence in [`WORKING_APPROACH.md` §12](project-management/WORKING_APPROACH.md) |
| Architecture review | [`MODULE_ARCHITECTURE.md`](project-management/MODULE_ARCHITECTURE.md) + [`LICENSE_MODEL.md`](project-management/LICENSE_MODEL.md) |
| Module review | [`AD_MODULE_DESIGN.md`](project-management/AD_MODULE_DESIGN.md), [`AD_TOOLKIT_DESIGN.md`](project-management/AD_TOOLKIT_DESIGN.md), [`BLOODHOUND_ANALYZER_DESIGN.md`](project-management/BLOODHOUND_ANALYZER_DESIGN.md), [`SILVERFORT_MODULE_DESIGN.md`](project-management/SILVERFORT_MODULE_DESIGN.md), [`ENTRA_MODULE_DESIGN.md`](project-management/ENTRA_MODULE_DESIGN.md) |
| UX review | [`UI_DESIGN_DIRECTION.md`](project-management/UI_DESIGN_DIRECTION.md) + [`VISUAL_REFERENCES.md`](project-management/VISUAL_REFERENCES.md) |
| Security & GDPR review | [`SECURITY_AND_GDPR.md`](project-management/SECURITY_AND_GDPR.md) |
| Build (later) | [`TASKS.md`](project-management/TASKS.md) + per-module docs |

---

## Document index

**Operating manual & state**
- [`WORKING_APPROACH.md`](project-management/WORKING_APPROACH.md) — stages, roles, complexity rules, first-5-sessions cadence
- [`PROJECT_STATE.md`](project-management/PROJECT_STATE.md) — current status, completed work, next steps
- [`DECISIONS.md`](project-management/DECISIONS.md) — D-0001 … D-0011 (durable decisions)
- [`ASSUMPTIONS.md`](project-management/ASSUMPTIONS.md) — A-0001 … A-0015 (open assumptions)
- [`OPEN_QUESTIONS.md`](project-management/OPEN_QUESTIONS.md) — questions by topic
- [`TASKS.md`](project-management/TASKS.md) — backlog across all 8 stages
- [`RISKS.md`](project-management/RISKS.md) — R-0001 … R-0012
- [`REVIEW_NOTES.md`](project-management/REVIEW_NOTES.md) — sign-off tracker + 16 cross-doc reconciliation items
- [`CHANGELOG.md`](project-management/CHANGELOG.md) — what changed in each session

**Product framing**
- [`DISCOVERY_WORKSHOP_ANSWERS.md`](project-management/DISCOVERY_WORKSHOP_ANSWERS.md) — 9 discovery questions answered (POC/MVP/Full split)
- [`PRODUCT_DESIGN.md`](project-management/PRODUCT_DESIGN.md) — product spec, vision, scope, architecture summary
- [`POC_V1_SCOPE.md`](project-management/POC_V1_SCOPE.md) — exact POC scope, demo journey, mocked vs built vs excluded

**Architecture**
- [`MODULE_ARCHITECTURE.md`](project-management/MODULE_ARCHITECTURE.md) — modular monolith, lifecycle, manifest, finding shape, correlation
- [`LICENSE_MODEL.md`](project-management/LICENSE_MODEL.md) — 8-value license status enum, scoring formulas

**Security & GDPR**
- [`SECURITY_AND_GDPR.md`](project-management/SECURITY_AND_GDPR.md) — trust boundaries, RBAC, evidence handling, audit, publishing, GDPR

**UX**
- [`UI_DESIGN_DIRECTION.md`](project-management/UI_DESIGN_DIRECTION.md) — component-led design, ACEN palette, page templates
- [`VISUAL_REFERENCES.md`](project-management/VISUAL_REFERENCES.md) — HTB / Fortify360 / Runtime references → component patterns

**Module designs**
- [`AD_MODULE_DESIGN.md`](project-management/AD_MODULE_DESIGN.md) — AD assessment model, controls, correlations
- [`AD_TOOLKIT_DESIGN.md`](project-management/AD_TOOLKIT_DESIGN.md) — PowerShell toolkit, ZIP structure, manifest
- [`BLOODHOUND_ANALYZER_DESIGN.md`](project-management/BLOODHOUND_ANALYZER_DESIGN.md) — deterministic path analysis (no AI in critical path)
- [`SILVERFORT_MODULE_DESIGN.md`](project-management/SILVERFORT_MODULE_DESIGN.md) — manual-first; API design only for POC
- [`ENTRA_MODULE_DESIGN.md`](project-management/ENTRA_MODULE_DESIGN.md) — license-aware Entra assessment

---

## Stack (planned)

- Backend: Python 3.x · FastAPI · SQLAlchemy 2.x · Alembic · Pydantic v2
- Frontend: Jinja2 + HTMX + Tailwind CSS (+ Alpine.js for small interactions)
- DB: PostgreSQL
- Reports: HTML rendered to PDF via Playwright (PDF stretch in POC)
- Auth: none in POC (role-switcher); Entra ID at MVP

Full rationale in [`PRODUCT_DESIGN.md` §14](project-management/PRODUCT_DESIGN.md) and [`DECISIONS.md`](project-management/DECISIONS.md) D-0002, D-0003.

---

## License & sensitive data policy

- Synthetic / fabricated data only. **No real customer evidence in this repository.**
- Silverfort API endpoint references are tagged "(unverified — requires Silverfort validation)" and are design-only for POC ([D-0006](project-management/DECISIONS.md)).
- BloodHound Analyzer detection, scoring, correlation, and initial explanation are **deterministic** — no AI in the critical path ([D-0005](project-management/DECISIONS.md)).
- Microsoft licensing references in the POC catalog are not authoritative; replace with `subscribedSkus` / official Microsoft docs before MVP ([Q-0071](project-management/OPEN_QUESTIONS.md)).
