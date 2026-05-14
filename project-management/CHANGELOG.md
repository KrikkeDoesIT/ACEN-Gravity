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
