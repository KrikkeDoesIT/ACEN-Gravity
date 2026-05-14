# RISKS.md

> Project risks (process, scope, technical, security, commercial). Each carries probability, impact, owner, and mitigation. Risks that materialize become issues and move to `TASKS.md`.

Format:

```
### R-NNNN — <short title>
Date: YYYY-MM-DD
Status: open | mitigating | accepted | closed
Category: process | scope | technical | security | commercial | data
Probability: low | medium | high
Impact: low | medium | high
Owner: <who>
Description: <statement>
Mitigation: <action>
Trigger / signal: <what tells us it materialized>
```

---

### R-0001 — POC silently becomes MVP
Date: 2026-05-15
Status: mitigating
Category: scope
Probability: high
Impact: high
Owner: Kristof + Claude Code
Description: Without strict tier discipline, the POC grows real connectors, real auth, hardened evidence handling, and ends up as a slow, unfinished MVP — failing the management decision point.
Mitigation: Every feature carries an explicit tier tag. Complexity checklist applied to every doc and backlog item. Cycle 1 sign-off explicitly names the demo journey.
Trigger: POC tasks growing past 40 implementation items; any "we should also..." discussion ending in "yes, add it".

### R-0002 — Three dashboards instead of one platform
Date: 2026-05-15
Status: mitigating
Category: scope / technical
Probability: medium
Impact: high
Owner: Software Architect role
Description: AD, BloodHound, Silverfort, and Entra each get bespoke parsers, finding shapes, scoring, and UI patterns — defeating the modular platform value proposition.
Mitigation: Shared evidence/control/finding/score model in core. Module dependency rule: modules do not import each other; correlation goes through core. Architecture review explicitly checks for this.
Trigger: Module-specific code appearing in `platform_core/`; duplicate finding shapes; new UI patterns invented per module.

### R-0003 — Silverfort API assumptions break at MVP
Date: 2026-05-15
Status: mitigating
Category: technical / commercial
Probability: medium
Impact: medium
Owner: Silverfort Module role
Description: The publicly referenced Silverfort endpoints may not be available, may have different shapes, or may require unexpected licensing or onboarding effort.
Mitigation: POC is manual-mode only (D-0006). MVP connector implementation is gated on official Silverfort validation. Every API claim tagged "requires validation" in the docs.
Trigger: Connector implementation begun without explicit Silverfort validation.

### R-0004 — BloodHound analyzer drifts to "AI does it"
Date: 2026-05-15
Status: mitigating
Category: technical
Probability: medium
Impact: high
Owner: BloodHound Analyzer role
Description: Under time pressure, deterministic path detection/scoring is replaced with LLM calls. Consultants can no longer audit or defend the output.
Mitigation: D-0005 — no AI in the critical path. Algorithms documented in `BLOODHOUND_ANALYZER_DESIGN.md` and code. AI only polishes language *after* consultant review.
Trigger: LLM call appearing in path detection, ranking, scoring, or initial explanation.

### R-0005 — Real customer evidence committed to git
Date: 2026-05-15
Status: mitigating
Category: security / data
Probability: medium
Impact: high
Owner: Security & GDPR role
Description: A consultant or developer commits a real customer ZIP, JSON, or screenshot containing usernames, SIDs, group memberships, or attack paths.
Mitigation: D-0011 — sample/synthetic data only. `.gitignore` rules for evidence directories. Pre-commit hook (MVP) for known-sensitive extensions. Repository README explicit warning.
Trigger: PR review surfaces real-looking data; secret/PII scan trips.

### R-0006 — Endless-scrolling SIEM-style UI emerges
Date: 2026-05-15
Status: mitigating
Category: scope / UX
Probability: medium
Impact: medium
Owner: UX role
Description: KPI cards, charts, and tables accumulate on every module page until users cannot find the "what should I fix first" answer.
Mitigation: UX principles in `UI_DESIGN_DIRECTION.md` ("summary first, details later"). UX review explicitly checks page purpose and KPI count per page.
Trigger: Module pages exceeding one screen height at typical desktop resolution without explicit drill-down.

### R-0007 — License-aware logic produces unfair customer scores
Date: 2026-05-15
Status: mitigating
Category: commercial / data
Probability: medium
Impact: high
Owner: Product Owner role
Description: Scoring penalizes customers for capabilities they do not own. Customer churn and reputational damage.
Mitigation: D-0007/D-0008 — Current License Score never reduced by `not_licensed`. Capabilities mapped from explicit owned SKUs. Consultant review before publishing.
Trigger: Customer complaint or internal QA showing a score penalty for not-licensed feature.

### R-0008 — Cross-module correlation produces false positives
Date: 2026-05-15
Status: mitigating
Category: technical / data
Probability: medium
Impact: medium
Owner: Software Architect role
Description: Identity join based on SID/UPN/sAMAccountName matches the wrong principals, producing misleading correlation findings.
Mitigation: A-0011 — surface ambiguous matches for consultant review. No silent merging. Joined identities are explicitly marked in evidence drawer.
Trigger: Demo or pilot finds an obvious mismatch in a correlation finding.

### R-0009 — POC demo data is unconvincing
Date: 2026-05-15
Status: open
Category: process
Probability: medium
Impact: high
Owner: QA + module owners
Description: Synthetic data is too small, too clean, or too unrealistic — management dismisses the demo as "toy".
Mitigation: Synthetic dataset designed to include ≥ 3 BloodHound paths, mixed Tier 0 issues, realistic Entra CA gaps, Silverfort coverage gaps, and at least one strong cross-module correlation. A-0012.
Trigger: Demo dry-run feedback.

### R-0010 — PostgreSQL not available on demo workstation
Date: 2026-05-15
Status: open
Category: technical
Probability: low
Impact: medium
Owner: DEV
Description: Demo environment requires Postgres; some workstations have only SQLite or no DB tooling installed.
Mitigation: Provide a docker-compose for Postgres; document a SQLite fallback for dev *only* (with explicit warning of feature gaps).
Trigger: Demo setup checklist fails.

### R-0011 — Brand non-compliance after strict-corners adaptation
Date: 2026-05-15
Status: open
Category: commercial / UX
Probability: low
Impact: low
Owner: UX + Kristof
Description: ACEN brand owners reject the ≤ 2px border-radius digital adaptation (D-0010), forcing a UI re-do.
Mitigation: Confirm Q-0110 early. Build component library with a single radius token so reverting is a one-line change.
Trigger: Brand owner pushback at UX review.

### R-0012 — Token-budget exhaustion stalls progress
Date: 2026-05-15
Status: mitigating
Category: process
Probability: medium
Impact: medium
Owner: Claude Code
Description: Long sessions reload the entire doc set and burn context, slowing progress and degrading quality.
Mitigation: All durable state lives in files, not chat. Sessions are scoped per `WORKING_APPROACH.md` §12. Subagents for parallel writing of independent docs. End-of-session summaries instead of essays.
Trigger: Conversation context filling beyond comfort within a single session.

### R-0013 — POC expands horizontally before the first slice is proven
Date: 2026-05-15
Status: mitigating
Category: scope / process
Probability: high
Impact: high
Owner: Claude Code (Software Architect role) + Kristof
Description: Under pressure to "show all four modules", Stage 9 starts building Silverfort and Entra surfaces in parallel with the AD + BloodHound slice. Result: four half-finished modules, no end-to-end flow, fragile demo, weak Cycle 7 management decision.
Mitigation: D-0014 + `WORKING_APPROACH.md` §6 (hard rule: no horizontal expansion until slice is reviewed). `TASKS.md` Stage 9 tagged `slice` vs `horizontal`; horizontal tasks blocked on T-9012 (slice review). T-6501 explicitly marks each backlog item.
Trigger: Any non-slice task starts before T-9012 completes; "let's just start the Entra page in parallel" pressure surfaces.
Linked: D-0014, `WORKING_APPROACH.md` §6, `TASKS.md` Stage 9.

### R-0014 — Sample data is not realistic enough to land the demo
Date: 2026-05-15
Status: open
Category: data / process
Probability: medium
Impact: high
Owner: Kristof (realism) + Claude Code (structure)
Description: Synthetic sample datasets are too small, too clean, or too obviously fabricated. Management sees an unconvincing demo and the kill criterion *"the POC cannot be demonstrated without too many manual hacks"* triggers regardless of platform quality.
Mitigation: D-0015 ownership split — Kristof validates realism, Claude Code ensures safety/structure/docs. T-8007 explicit sign-off task. Synthetic data is designed to include intentional cross-module overlap (CORR-BH-ENTRA-001 headline path). Demo dry-run with a fresh-eyes internal reviewer before Cycle 7.
Trigger: Cycle 7 review feedback, or dry-run feedback, says the data looks fabricated.
Linked: D-0015, A-0012, A-0016, `WORKING_APPROACH.md` §13.

### R-0015 — BloodHound findings are noisy without consultant tuning
Date: 2026-05-15
Status: open
Category: data / domain
Probability: medium
Impact: high
Owner: BloodHound Analyzer role + Kristof
Description: The deterministic analyzer enumerates many paths against a realistic synthetic graph. Without ranking discipline, the demo surfaces 50+ paths and the consultant cannot defend or prioritize them. This trips the kill criterion *"BloodHound findings are too noisy to be useful"* (`WORKING_APPROACH.md` §20).
Mitigation: `BLOODHOUND_ANALYZER_DESIGN.md` caps (top K=3 per source, top N=50 considered, top 5 reported) + deterministic risk scoring + path categorization with first-match priority. Synthetic SharpHound ZIP shaped to ≥ 3 paths in ≥ 3 categories (avoiding "thousands of noise paths"). Consultant tuning of cap values is a Cycle 3 review item (REVIEW_NOTES.md item 7).
Trigger: Demo dry-run shows > 10 paths reported, or consultant cannot pick a single headline path in < 30 seconds.
Linked: `BLOODHOUND_ANALYZER_DESIGN.md`, `REVIEW_NOTES.md` items 5–8, `WORKING_APPROACH.md` §20 kill criterion.

### R-0016 — Documentation grows too large to be reviewed actively
Date: 2026-05-15
Status: mitigating
Category: process
Probability: medium
Impact: medium
Owner: Claude Code (Documentation / Reviewer role)
Description: The module design docs already approach or exceed ~800 lines (AD ~1055, BH ~1157, SF ~887, Entra ~830). Without active control, the docs become a second product to maintain; reviewers skip large sections; inconsistencies accumulate.
Mitigation: D-0017 + `WORKING_APPROACH.md` §15. Soft ~800-line cap with executive summary trigger. Per-doc decision at Cycle 3 (summary / appendix split / accept). `WORKING_APPROACH.md` now opens with an executive summary as the example.
Trigger: A new doc passes 800 lines without an executive summary; a reviewer says "I didn't read past section X".
Linked: D-0017, `WORKING_APPROACH.md` §15, `REVIEW_NOTES.md`.

---

*Last updated: 2026-05-15 — R-0013 … R-0016 added for the 9-stage operating-model update.*
