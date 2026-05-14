# MODULE_ARCHITECTURE.md

> How the platform is shaped so that every module — AD, BloodHound, Silverfort, Entra, and every future module — plugs in additively without bespoke screens, bespoke data shapes, or module-specific hacks in the core.
>
> Companion documents: `PRODUCT_DESIGN.md`, `LICENSE_MODEL.md`, `SECURITY_AND_GDPR.md`, per-module design docs.

---

## 1. Architectural goals

1. **Modular monolith first.** Microservices are not in scope until Full Product, and only if proven necessary (D-0002).
2. **Single lifecycle.** Every module follows the same path: *evidence → parse → normalize → evaluate → finding → publish → report*.
3. **Single finding shape.** Every module emits findings into one shared shape; module-specific fields live in a typed payload, not in a new entity.
4. **No module → module imports.** Cross-module correlation flows through the core's normalized **Identity** entity and the shared finding shape.
5. **Adapters at the edges.** Parsers and connectors are adapters. Controls are pure functions of normalized data.
6. **Reuse the UI patterns.** Module pages reuse the same components from `UI_DESIGN_DIRECTION.md`. Modules do not invent new screens.
7. **License-awareness is part of the model**, not bolted on (D-0007/D-0008).
8. **Determinism in security-critical logic.** No AI in the critical path of detection, ranking, scoring, or initial explanation (D-0005).

---

## 2. Module types

We define **three module types** so we can answer "is this a module?" consistently.

| Type | Description | Examples | POC/MVP/Full |
|---|---|---|---|
| **Evidence Module** | Ingests evidence (uploaded artifacts and/or connector data), normalizes it, evaluates controls, emits findings | AD, BloodHound, Silverfort, Entra, Defender XDR (future), Intune (future) | POC has 4 |
| **Advisory Module** | No technical evidence; consultant-driven; emits findings backed by consultant notes only | Cloud Security Envisioning, AD Security Workshop deliverables | Full only |
| **Capability Module** | Provides cross-cutting capability without owning a problem domain (e.g., License Catalog, Identity correlation, Reporting helpers) | License Catalog, Identity Linker | Built as part of core in POC; harvestable later |

For POC V1, all four modules are **Evidence Modules**. Advisory and Capability module types are designed for, not implemented.

---

## 3. Module lifecycle

```
       ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
       │   UPLOAD   │    │   PARSE    │    │ NORMALIZE  │    │  EVALUATE  │    │   FINDING  │    │  REPORT /  │
       │  artifact  │──▶ │  parser    │──▶ │  module    │──▶ │  control   │──▶ │  + score   │──▶ │  PUBLISH   │
       │            │    │  decides   │    │  emits     │    │  evaluator │    │  + viz     │    │            │
       └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘
            │                  │                  │                  │                  │                  │
            ▼                  ▼                  ▼                  ▼                  ▼                  ▼
        Artifact         (no DB write       Evidence rows       ControlResult       Finding rows       Report (immutable)
        row (hash,        until parse        + module-local      rows (license       (visibility +      AuditLog entries
        manifest)         succeeds)          tables              status, score)       correlation)
```

Rules:

- **Upload** is core. Only core handles file IO, hashing, storage, and audit. Modules never touch the filesystem directly.
- **Parse** is module. The module's `parse(artifact)` returns one or more `Evidence` units plus zero or more module-local normalized rows.
- **Normalize** writes module-local tables *and* updates core entities (e.g., upserts `Identity` rows).
- **Evaluate** is module. Each control reads only normalized data (its own module's + core); it does not re-parse artifacts.
- **Finding** is core-typed; the module fills the payload.
- **Report / Publish** is core. Modules contribute report sections (Jinja partials).

Failure rules:

- A failing parser does **not** produce partial findings. Core marks the artifact `parse_failed` and records the error in the audit log.
- A failing control evaluation produces a `ControlResult` with `result_status = unknown` and a documented reason. It does not silently skip.

---

## 4. Module package layout

```
modules/<name>/
├── __init__.py            # module manifest (id, version, declares evidence types, controls)
├── manifest.py            # ModuleManifest object
├── parsers/               # one parser per evidence type
│   ├── __init__.py
│   └── <evidence_type>.py
├── models/                # SQLAlchemy models for module-local normalized data
│   ├── __init__.py
│   └── *.py
├── controls/              # one file per control or grouped by category
│   ├── __init__.py
│   ├── <category>.py
│   └── _registry.py       # registers controls into core registry
├── correlations/          # module-side correlation contributors (read-only on other modules' core data)
│   └── __init__.py
├── scoring.py             # per-control score contribution and weights
├── reports/               # Jinja partials and assets for report sections
│   ├── internal.html
│   └── customer.html
├── ui/                    # module page composition (uses core components only)
│   └── page.py
└── tests/
    ├── fixtures/          # synthetic evidence files
    └── test_*.py
```

The package is discovered at app startup; the manifest is registered with `platform_core.module_registry`.

---

## 5. Core package layout

```
platform_core/
├── app.py                 # FastAPI app factory
├── settings.py
├── module_registry.py     # registers modules; exposes manifest lookups
├── lifecycle/
│   ├── upload.py
│   ├── parse_dispatcher.py
│   ├── evaluate_dispatcher.py
│   ├── publish.py
│   └── report_render.py
├── identity/              # the canonical Identity entity + linker
│   ├── models.py
│   ├── linker.py          # deterministic identity match (SID, UPN, sAMAccountName, ObjectGUID)
│   └── ambiguity.py       # surfaces ambiguous matches for consultant review
├── evidence/
│   ├── storage.py         # local FS (POC); object-storage backend at MVP
│   ├── validation.py
│   └── models.py
├── controls/
│   ├── models.py          # Control, ControlResult
│   └── engine.py
├── findings/
│   ├── models.py
│   ├── visibility.py      # customer_visibility enforcement
│   └── scoring.py
├── licensing/
│   ├── catalog.py
│   ├── capabilities.py
│   └── status.py          # 8-value license_status enum
├── reports/
│   ├── render.py          # Jinja → HTML → optional PDF (Playwright)
│   └── templates/
├── audit/
│   └── log.py
├── web/                   # FastAPI routes + Jinja templates + HTMX endpoints
│   ├── routes/
│   ├── templates/
│   └── components/        # reusable UI components (see VISUAL_REFERENCES.md + UI_DESIGN_DIRECTION.md)
├── models/                # core SQLAlchemy models (Organization, Customer, etc.)
└── tests/
```

---

## 6. Module manifest

A module declares itself via `ModuleManifest`:

```python
@dataclass
class ModuleManifest:
    id: str                     # "ad", "bloodhound", "silverfort", "entra"
    version: str                # semver
    title: str                  # "Active Directory"
    icon: str                   # icon token used in UI
    evidence_types: list[EvidenceTypeDecl]
    controls: list[ControlDecl]
    correlation_contributors: list[CorrelationContributorDecl]
    report_sections: ReportSectionsDecl
    customer_visibility_defaults: dict[str, CustomerVisibility]  # by finding category
```

Rules:

- A module ships only one manifest, registered once at app start.
- `evidence_types` map directly to parser entry points.
- `controls` carry id, version, title, category, severity defaults, evidence dependencies, capability dependencies (for license-aware logic), score weights.
- `correlation_contributors` declare which core entities the module contributes to (e.g., AD contributes `Identity` rows for SIDs, `Computer` rows for AD computers).
- `customer_visibility_defaults` allows the module to declare safer defaults per category (e.g., "raw SharpHound data is always `internal_only`").

---

## 7. Evidence model

### 7.1 Artifact vs Evidence

- **Artifact** = raw uploaded file (immutable, content-addressed by SHA-256). Stored at `evidence/<sha256[:2]>/<sha256>`.
- **Evidence** = parsed, normalized view of part of an artifact. Has `artifact_id`, `module_id`, `evidence_type`, `payload` (JSONB), `parsed_at`, `parser_version`.

A single artifact can produce many `Evidence` rows (e.g., an AD toolkit ZIP produces one Evidence per JSON file inside).

### 7.2 Evidence types (POC)

| Module | Evidence type | Artifact format | Parser |
|---|---|---|---|
| AD | `ad-toolkit-zip` | ZIP with manifest + JSON files + optional PingCastle XML | `modules/ad/parsers/toolkit_zip.py` |
| AD | `pingcastle-xml` | Standalone PingCastle XML (when uploaded separately) | `modules/ad/parsers/pingcastle.py` |
| BloodHound | `sharphound-zip` | SharpHound CE JSON files in a ZIP | `modules/bloodhound/parsers/sharphound_zip.py` |
| Silverfort | `silverfort-export-bundle` | ZIP containing policies/service-accounts/enrollment/entity-risk JSON files | `modules/silverfort/parsers/export_bundle.py` |
| Entra | `entra-graph-json-bundle` | ZIP containing graph dumps (users, groups, roles, ca, apps, ...) | `modules/entra/parsers/graph_bundle.py` |

### 7.3 Upload validation

- Max file size enforced (configurable; POC default 200 MB).
- Magic bytes check (ZIP / XML / JSON).
- Manifest read (where applicable) before any inner-file processing.
- SHA-256 computed before storage; duplicates are not re-uploaded, only re-linked.
- Quarantine path until validation passes; only on success the artifact moves to the addressed location.

---

## 8. Identity entity (cross-module join key)

The single most important shared concept.

```python
class Identity(Base):
    id: UUID
    customer_id: UUID
    canonical_kind: enum("user", "computer", "service_account", "group", "app", "unknown")
    canonical_label: str        # human label (display name or sAMAccountName)
    sid: str | None             # AD SID
    upn: str | None             # User Principal Name
    sam_account_name: str | None
    object_guid: UUID | None    # AD ObjectGUID (also Entra immutableId derivative)
    azure_object_id: UUID | None
    is_privileged: bool         # set by AD/BH/Entra evidence
    is_tier0: bool              # set by AD/BH evidence
    is_breakglass: bool         # set by Entra evidence
    notes: str | None
```

Linking rules (deterministic):

1. AD evidence creates/updates Identity by SID (primary), sAMAccountName + ObjectGUID (secondary).
2. Entra evidence creates/updates Identity by azure_object_id (primary), upn (secondary), onPremisesImmutableId where hybrid-synced.
3. BloodHound evidence creates/updates Identity by SID + ObjectGUID where present.
4. Silverfort evidence creates/updates Identity by SID/UPN/sAMAccountName.
5. **Ambiguous matches** (e.g., two AD principals with same sAMAccountName across domains; UPN-only match in Entra without onPremisesImmutableId) are surfaced via `identity/ambiguity.py` and require consultant confirmation. The system does not silently merge.

This deterministic identity layer is what makes cross-module correlation **explainable** rather than guessed.

---

## 9. Control model

```python
class Control(Base):
    id: str                     # "AD-PRIV-005"
    module_id: str
    version: str
    title: str
    category: str               # e.g., "privileged_accounts"
    default_severity: Severity
    objective: str
    requires_evidence: list[EvidenceTypeRef]
    requires_capabilities: list[CapabilityRef]   # license-aware
    weight: float               # score weight
    customer_visibility_default: CustomerVisibility
    description_long: str       # markdown
```

```python
class ControlResult(Base):
    id: UUID
    assessment_run_id: UUID
    control_id: str
    result_status: enum("pass", "partial", "fail", "not_applicable", "unknown")
    license_status: LicenseStatus   # 8-value enum
    severity: Severity              # may override default
    score_contribution_current: float  # contribution to Current License Score
    score_contribution_target: float   # contribution to Target Posture Score
    evidence_refs: list[EvidenceRef]
    evaluated_at: datetime
    evaluator_version: str
    explanation: str                # short, human-readable
    finding_id: UUID | None         # if result produced a finding
```

Control evaluation rules:

- A control evaluator is a pure function: `(NormalizedView, CapabilitySet) -> ControlResult`.
- Evaluators must be **deterministic** and **idempotent** for the same input.
- A control may produce **zero or one** finding per evaluation (multi-finding cases must be split into multiple controls or use a single finding with a list payload).
- A control returns `not_applicable` only when explicitly modelled (e.g., a control about Entra ID P2 features when P2 is not licensed and the rubric defines this as `not_applicable`).
- A control returns `unknown` when evidence is missing or ambiguous, never silently `pass`.

---

## 10. Finding model

```python
class Finding(Base):
    id: UUID
    assessment_run_id: UUID
    title: str                     # short, human title
    category: str                  # module-defined; e.g., "ad.privileged", "bh.path", "entra.hybrid"
    module_id: str                 # primary module
    severity: Severity
    risk_score: int                # 0–100
    license_status: LicenseStatus  # mirrors the contributing control result
    summary_internal: str          # markdown
    summary_customer: str          # markdown (executive framing)
    technical_detail: str          # markdown (suppressed in customer_summary view)
    remediation: str               # markdown
    validation_method: str         # how to retest
    state: enum("new", "triaged", "published", "retest_requested", "closed")
    customer_visibility: enum("internal_only", "customer_summary", "customer_full")
    evidence_refs: list[EvidenceRef]
    identity_refs: list[UUID]      # Identity rows this finding relates to
    correlation_refs: list[CorrelationRef]   # other Findings / Controls / Identities
    payload: JSONB                 # module-specific data (e.g., BH path steps)
    created_at, updated_at
```

Rules:

- **One shape for all modules.** Module-specific fields go in `payload`.
- Severity, risk_score, and license_status are denormalized from the contributing control for easy UI/report rendering.
- `customer_visibility` is the only gate; report renderer and UI both consult it.
- `correlation_refs` enable the cross-module story without requiring module-to-module imports.

---

## 11. Cross-module correlation

Correlation findings are **not** owned by a module — they are produced by a **core orchestrator** that reads normalized data and finding outputs from multiple modules.

### 11.1 Where correlation lives

`platform_core/correlations/` is a small orchestrator that runs after all module evaluations complete. It uses *correlation rules*, each declared by modules but executed centrally:

```python
@correlation_rule(id="CORR-AD-SF-001", title="AD Tier 0 lacking Silverfort coverage")
def ad_tier0_without_silverfort_coverage(view):
    tier0_identities = view.identities.filter(is_tier0=True, kind="user")
    sf_covered = view.silverfort.covered_identity_ids()
    uncovered = tier0_identities - sf_covered
    if uncovered:
        return correlated_finding(
            severity=Severity.HIGH,
            module="correlation",
            identities=uncovered,
            evidence=[...],
            summary_internal="...",
            summary_customer="...",
        )
```

The rule is *declared next to* the module that knows it best (AD or Silverfort), but **executed by core**. The function signature only sees the read-only `view` of normalized data + completed findings — there is no inter-module Python import.

### 11.2 Correlation finding semantics

- Owner module is `"correlation"` (a built-in pseudo-module owned by core).
- Severity defaults to the highest contributing severity unless explicitly set.
- License status inherits from the most-constrained contributor (e.g., if any contributor is `not_licensed`, the correlation is `not_licensed` unless rule overrides).
- Evidence and identity refs are de-duplicated unions from contributors.

### 11.3 POC V1 correlation rules

| ID | Title | Modules |
|---|---|---|
| CORR-AD-SF-001 | AD Tier 0 lacking Silverfort coverage | AD + SF |
| CORR-BH-AD-001 | BloodHound critical path lands on AD privileged service account | BH + AD |
| CORR-BH-SF-001 | BloodHound critical path on identity without Silverfort policy coverage | BH + SF |
| CORR-AD-ENTRA-001 | AD privileged identity synced to Entra cloud-privileged role | AD + Entra |
| CORR-BH-ENTRA-001 | BloodHound path target is an Entra hybrid admin (the "headline" demo finding) | BH + AD + Entra (+ optional SF) |

The headline demo finding for management review is `CORR-BH-ENTRA-001` (with SF correlation if covered).

---

## 12. Scoring model

### 12.1 Inputs

- Each control has a **weight** (≥ 0).
- Each `ControlResult` has a **result_status** and a **license_status**.

### 12.2 Score contribution rules

For **Current License Score** (per module, then aggregated):

- Eligible: control results with `license_status` ∈ {`licensed_enabled`, `licensed_disabled`, `licensed_misconfigured`}.
- Excluded (i.e., do **not** lower Current Score): `not_licensed`, `requires_add_on`, `available_in_higher_tier`, `not_applicable`, `unknown`.
- Score contribution = `weight × pass_factor(result_status)`, where:
  - `pass` → 1.0
  - `partial` → 0.5
  - `fail` → 0.0
  - `not_applicable`, `unknown` → excluded.

For **Target Posture Score** (per module, then aggregated):

- All controls eligible regardless of license_status.
- `not_licensed` and `requires_add_on` are treated as `fail` (i.e., the customer is not at target posture because they do not own the capability).
- `not_applicable` is excluded.
- `unknown` is excluded but flagged in the report ("X controls could not be evaluated").

### 12.3 Aggregation

- Module score = sum(contributions) / sum(weights of eligible controls) × 100.
- Engagement score = weighted average of module scores (equal weights for POC; per-module weights configurable at MVP).
- Opportunity Score = Target Posture Score − Current License Score (per module and engagement).

### 12.4 Severity vs risk_score

- Severity (Critical/High/Medium/Low/Info) is qualitative and drives UI sorting.
- `risk_score` (0–100) is quantitative and used by ranking algorithms (e.g., BloodHound paths). For non-BH findings, `risk_score` is a deterministic projection from severity + license_status + correlation breadth.

Detailed formulas: `LICENSE_MODEL.md`.

---

## 13. Reporting model

### 13.1 Two reports

- **Internal Detailed**: all findings, all evidence refs, scores, license context, technical details.
- **Customer Summary**: only findings where `customer_visibility ∈ {customer_summary, customer_full}`. Technical detail rendered only for `customer_full`. Executive summary block at the top.

### 13.2 Renderer

- Pipeline: `Report` row + `findings + scores + module sections + identity context` → Jinja template → HTML.
- PDF (stretch in POC): Playwright headless renders the HTML to PDF.
- Reports are **immutable** once rendered. A new render produces a new `Report` row.

### 13.3 Module report sections

A module ships `reports/internal.html` and `reports/customer.html` Jinja partials. The core renderer assembles them in a fixed order:

1. Engagement summary (core).
2. Two-scores card (core).
3. Top findings strip (core).
4. AD section (module).
5. BloodHound section (module).
6. Silverfort section (module).
7. Entra section (module).
8. Cross-module correlations (core).
9. Appendix: license context, evidence inventory (core).

---

## 14. How modular design prevents UI/code complexity

| Risk | Mitigation in the architecture |
|---|---|
| Three dashboards instead of one platform (R-0002) | One `ModulePage` layout used by all module pages; modules supply slots, not new pages |
| Module-specific hacks in core | `platform_core/` has no `if module_id == "ad": ...` branches; module behaviour is registered via the manifest |
| Duplicate logic across modules | Common helpers in `platform_core/`; module-side helpers in `modules/<m>/_helpers.py` are not importable by other modules |
| Giant god services | Lifecycle is split into upload / parse / evaluate / publish / render services; each ≤ a few hundred lines |
| Endless scrolling SIEM dashboards | UI patterns limited in `UI_DESIGN_DIRECTION.md`; KPI count cap per page |
| Endless growing schema | Module-local data lives in module-owned tables (named `<module>_<table>`); only entities that participate in correlation graduate to core |

---

## 15. How AD, BloodHound, Silverfort, Entra fit this model

| Module | Evidence | Module-local data | Contributes to core | Notes |
|---|---|---|---|---|
| **AD** | `ad-toolkit-zip`, `pingcastle-xml` | `ad_domain`, `ad_dc`, `ad_kerberos_config`, `ad_gpo`, `ad_delegation` | `Identity` (users, groups, computers, service accounts), `Computer`, `Group` | PingCastle XML is read but normalized into AD module tables and Identity refs |
| **BloodHound** | `sharphound-zip` | `bh_graph_snapshot`, `bh_path`, `bh_path_step` | `Identity` (re-uses AD-created rows when SIDs match; flags `is_tier0`); `Computer` | Graph is held in-memory during analysis; persisted as path summaries, not the full graph |
| **Silverfort** | `silverfort-export-bundle` | `sf_policy`, `sf_policy_coverage`, `sf_service_account`, `sf_enrollment`, `sf_entity_risk` | `Identity` (linked by SID/UPN/sAMAccountName) | API connector design only |
| **Entra** | `entra-graph-json-bundle` | `entra_tenant`, `entra_ca_policy`, `entra_role_assignment`, `entra_app`, `entra_risky_user` | `Identity` (linked by azure_object_id; hybrid via onPremisesImmutableId) | License catalog populated from `subscribedSkus` (when present) or consultant-provided |

---

## 16. Future modules

Each future module follows the **same template**:

1. Decide the type (Evidence / Advisory / Capability).
2. Declare evidence types (Advisory modules declare a `consultant_note` evidence type).
3. Declare normalized entities and which (if any) graduate to core.
4. Declare controls and capability dependencies.
5. Declare correlation contributors (which core entities you read and write).
6. Declare report sections (Internal + Customer).
7. Provide synthetic sample data for tests.

A module that requires changes to core entities (new entity type, new license-status enum value) goes through architecture review.

---

## 17. POC / MVP / Full architecture roadmap

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| Modular monolith | ✅ | ✅ | ✅ |
| Synchronous parse-on-upload | ✅ | 🟡 fallback only | ⬜ |
| Background jobs (Redis + RQ) | ⬜ | ✅ | ✅ |
| Local FS evidence storage | ✅ | 🟡 fallback only | ⬜ |
| Object storage (S3/Blob) | ⬜ | ✅ | ✅ |
| Single-tenant DB | ✅ | 🟡 | ⬜ |
| Multi-tenant DB (schema-per-tenant OR row-level security) | ⬜ | 🟡 partial | ✅ |
| Auth = role switcher | ✅ | ⬜ | ⬜ |
| Auth = Entra ID | ⬜ | ✅ | ✅ |
| Encryption at rest | ⬜ | ✅ | ✅ |
| KMS / managed secrets | ⬜ | 🟡 baseline | ✅ |
| Audit log retention policy | ⬜ default | ✅ | ✅ |
| Connectors (Graph, AD live, SF API) | ⬜ design only | ✅ where validated | ✅ |

---

## 18. What to avoid

- **Module-specific code in core** (`if module_id == "ad": ...` branches).
- **Module-to-module imports** (`from modules.ad import ...` inside `modules/bloodhound/`).
- **Re-parsing artifacts** during control evaluation (controls read normalized data only).
- **Mutating Evidence rows** after parse (parse is idempotent; re-parse produces new rows or no rows).
- **Module-specific UI components** (a one-off chart for BloodHound paths is acceptable inside the BH module page, but it lives in `modules/bloodhound/ui/` and is not exported).
- **Module-specific finding shapes** (no `BloodHoundFinding` subclass; use the shared `Finding` with `payload`).
- **AI in detection/ranking/correlation/initial-explanation paths** (D-0005).
- **Silent identity merging** (ambiguous matches surface in `identity/ambiguity.py`).
- **Bypassing the audit log** (every consequential action goes through `platform_core/audit/log.py`).

---

*Last updated: 2026-05-15.*
