# REVIEW_NOTES.md

> Cross-document review findings and consistency notes. Maintained by the Documentation / Reviewer role. Resolved items get a ✅ and a one-line resolution note; unresolved items become tasks in `TASKS.md` or questions in `OPEN_QUESTIONS.md`.

---

## Review-cycle sign-offs

| Cycle | Title | Reviewer | Status | Date | Notes |
|---|---|---|---|---|---|
| 1 | Concept & POC scope | Kristof | ⬜ pending | — | — |
| 2 | Architecture & module boundaries | Kristof | ⬜ pending | — | — |
| 3a | AD module | Kristof | ⬜ pending | — | — |
| 3b | BloodHound Analyzer | Kristof | ⬜ pending | — | — |
| 3c | Silverfort module | Kristof | ⬜ pending | — | — |
| 3d | Entra module | Kristof | ⬜ pending | — | — |
| 4 | UX & information architecture | Kristof | ⬜ pending | — | — |
| 5 | Security & GDPR | Kristof | ⬜ pending | — | — |
| 6 | POC backlog | Kristof | ⬜ pending | — | — |
| 7 | Management review | Management | ⬜ pending | — | — |

---

## Cross-document consistency checks

> Each item asserts a property that must hold across multiple documents. Add a check whenever a design choice spans more than one document. ✅ = currently consistent.

- [ ] **License-aware enum is identical** across `LICENSE_MODEL.md`, `PRODUCT_DESIGN.md` (Scoring Model section), `MODULE_ARCHITECTURE.md` (Control model), per-module design docs, and `TASKS.md` data-model entries.
- [ ] **Customer visibility flag** is identical across `SECURITY_AND_GDPR.md`, `PRODUCT_DESIGN.md` (Reporting Model), `UI_DESIGN_DIRECTION.md` (Publishing modal), `TASKS.md`.
- [ ] **Module dependency rule** ("no module imports another; correlation goes through core") stated identically in `MODULE_ARCHITECTURE.md` and `PRODUCT_DESIGN.md`.
- [ ] **BloodHound determinism rule** stated in `BLOODHOUND_ANALYZER_DESIGN.md`, `PRODUCT_DESIGN.md`, `DECISIONS.md` (D-0005), `RISKS.md` (R-0004).
- [ ] **Silverfort "manual-first / API requires validation"** stated in `SILVERFORT_MODULE_DESIGN.md`, `DECISIONS.md` (D-0006), `RISKS.md` (R-0003), `OPEN_QUESTIONS.md` (Q-0090).
- [ ] **Synthetic data only** stated in `SECURITY_AND_GDPR.md`, `DECISIONS.md` (D-0011), `RISKS.md` (R-0005), repo README.
- [ ] **Two scores** (Current License Score + Target Posture Score, gap = Opportunity Score) consistent across `PRODUCT_DESIGN.md`, `LICENSE_MODEL.md`, per-module docs, `UI_DESIGN_DIRECTION.md`.
- [ ] **Three personas** (ACEN Consultant, Customer Executive, Customer IT Lead) consistent across `PRODUCT_DESIGN.md`, `POC_V1_SCOPE.md`, `UI_DESIGN_DIRECTION.md`, `DISCOVERY_WORKSHOP_ANSWERS.md`.

---

## Pending review items

### Silverfort module design — inconsistency to reconcile
Date: 2026-05-15
Source: drafting `SILVERFORT_MODULE_DESIGN.md`.

1. **AD-PRIV-005 ↔ Silverfort coverage gap correlation** — `LICENSE_MODEL.md` §5.4 marks the Silverfort capability as a *preferred* dependency on `AD-PRIV-005`. `POC_V1_SCOPE.md` §5.3 / §10 says one AD finding is *visibly linked* to a Silverfort coverage gap. Working interpretation: the preferred-capability surfaces in correlation. Confirm at Cycle 3 review.
2. **Silverfort policy action vocabulary** — terms like `require_mfa` and `block` used in control logic are unverified against actual Silverfort policy schema. The Silverfort design doc carries this caveat in §18.3 (control `evaluator_version` will bump once Q-0092 resolves).
3. **Service-account / entity-risk identity linking** — Silverfort design adds an `unlinked = true` flag on `sf_service_account` and `sf_entity_risk` rows for cases where the Silverfort identifier cannot be deterministically resolved to a core `Identity`. Aligns with A-0011 ("no silent merging"). Confirm at Cycle 2 review (architecture).
4. **SF-ENTRA-001 vs CORR-AD-ENTRA-001 overlap** — Silverfort design treats SF-ENTRA-001 as "optional in POC, covered by `CORR-AD-ENTRA-001`" to avoid duplicate logic. Confirm at Cycle 3 review.

### BloodHound Analyzer — defaults to confirm
Date: 2026-05-15
Source: drafting `BLOODHOUND_ANALYZER_DESIGN.md`.

5. **Edge severity weights (1–10 scale)** — analyzer assigns numeric weights per edge type (e.g., `DCSync`=10, `GenericAll`=9, `WriteDacl`=8, `ForceChangePassword`=7, ..., `MemberOf`=1). Needed to make the risk formula concrete. Confirm at Cycle 3 review (Kristof — AD domain).
6. **Risk-score → severity bands** — bands chosen: 85+ Critical / 65+ High / 45+ Medium / 25+ Low / <25 Info. Configurable at MVP. Confirm at Cycle 3 review.
7. **Analyzer caps (POC defaults)** — max path length 8, top K=3 paths per source, top N=50 considered, top 5 reported. Configurable at MVP. Confirm at Cycle 3 review.
8. **Path category match precedence** — when a path matches more than one category (very common, e.g., ACL abuse *and* group nesting), analyzer uses a first-match priority order documented in `BLOODHOUND_ANALYZER_DESIGN.md` §12.2. Confirm the priority order at Cycle 3 review.

### AD module & toolkit — reconciliation items
Date: 2026-05-15
Source: drafting `AD_MODULE_DESIGN.md` and `AD_TOOLKIT_DESIGN.md`.

9. **AD-HEALTH-004 (PingCastle Composite Health) chosen as the POC Health control** — instead of AD-HEALTH-001 (Replication), because PingCastle XML is the canonical AD baseline (A-0004) and is already in the demo data set. Both controls remain in the catalog; only the Health pick for the POC ≥ 6 set is reordered. Confirm at Cycle 3 review.
10. **PingCastle XML delivery path** — `MODULE_ARCHITECTURE.md` §7.2 lists `pingcastle-xml` as a *separate* parser entry; `POC_V1_SCOPE.md` §5.3 implies PingCastle XML always arrives *inside* the toolkit ZIP. Both paths are kept in the AD design (toolkit-embedded is canonical; standalone XML upload supported). Worth a one-line clarification in `POC_V1_SCOPE.md` §5.3 to lock the POC default.
11. **AD-SF-001 vs the AD POC ≥ 6 count** — `POC_V1_SCOPE.md` §5.3 names AD-SF-001 in the demo journey (§10) but the ≥ 6 target counts controls from Health / Privileged / Kerberos / Delegation / GPO. The AD design treats AD-SF-001 as **additional** to those 6 (correlation control). One-line clarification recommended in `POC_V1_SCOPE.md` §5.3.
12. **Toolkit thresholds (Domain Admins ≤ 5, stale > 90 d, ...)** — default starting values chosen for POC; configurable per engagement at MVP. Confirm baselines at Cycle 3 review.

### Entra module — items addressed and remaining
Date: 2026-05-15
Source: drafting `ENTRA_MODULE_DESIGN.md`.

13. **POC_V1_SCOPE.md SKU profile corrected** — earlier draft said "E5 + EMS E5 + Entra ID P1 (no P2)" which is internally inconsistent (E5 bundles P2). **Already fixed**: §13 and §8 now read "E3 + standalone Entra ID P1, no P2, owns Silverfort". Worked example in `ENTRA_MODULE_DESIGN.md` §4.4 anchors on this profile. ✅ resolved.
14. **ENTRA-CA-004 capability requirements** — `LICENSE_MODEL.md` §5.4 lists `entra.conditional-access + entra.identity-protection.risky-signins`. Entra design adds `entra.identity-protection.risky-users` for consistency with ENTRA-LIC-004. Minor — resolver returns `not_licensed` either way for a P1-only customer. Confirm wording at Cycle 3 review.
15. **Hybrid Identity Administrator categorized as high-privilege** — not explicitly in the brief but consistent with Entra Connect Tier 0 logic in §17 (ENTRA-HYBRID-002). Confirm at Cycle 3 review.
16. **POC `licensed_disabled` demonstrator = ENTRA-CA-003 (Legacy Auth Blocked)** — chosen per the explicit cue in `POC_V1_SCOPE.md` §4 step 7. POC `not_licensed` demonstrator = ENTRA-LIC-004 (Identity Protection), with downstream effects on ENTRA-CA-004 and ENTRA-PRIV-003. Confirm at Cycle 3 review.

---

## Resolved review items

(Populated as items above are resolved.)

---

*Last updated: 2026-05-15.*
