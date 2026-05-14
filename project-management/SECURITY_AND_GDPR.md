# SECURITY_AND_GDPR.md

> Security model and GDPR baseline for ACEN Gravity. Defines trust boundaries, authentication, authorization, tenant isolation, evidence handling, audit logging, publishing controls, secrets management, and the data-protection posture per tier (POC / MVP / Full).
>
> Companion: `PRODUCT_DESIGN.md` §17–18, `MODULE_ARCHITECTURE.md`, `POC_V1_SCOPE.md` §16.

---

## 1. Security principles

1. **Treat all external input as untrusted.** Evidence files, JSON payloads, XML, ZIP archives, query parameters, file names, browser headers — all untrusted.
2. **Fail closed.** When a security decision is ambiguous (auth, authz, visibility), default to deny / hide / not-publish.
3. **Least privilege.** Connectors and Graph permissions are read-only and as narrow as the assessment allows. No role-elevation to "make it easier."
4. **Customer visibility is explicit, not default** (D-0009). Nothing is published until a consultant marks it.
5. **Audit everything consequential.** Uploads, parses, evaluations, finding state changes, visibility changes, report generations, publishes, role-switches (POC) and logins (MVP+).
6. **Synthetic data only in repo** (D-0011, R-0005).
7. **No AI in security-critical paths** (D-0005). Determinism is part of the security model — consultants and customers must be able to defend a finding.
8. **Designed for production at MVP, not POC.** POC stays small and demoable; the *design* is production-shaped so we are not surprised at MVP.

---

## 2. Trust boundaries

```
                    Untrusted  │  Trusted
                               │
        Browser ──── HTTPS ────▶  FastAPI app
                               │     │
        Evidence file ─ upload ▶  Validators ──▶ Storage (immutable)
                               │     │
        External connector ────▶  Connector adapter ──▶ Module
        (Graph, AD, SF API)    │
                               │
                               ▼
                          PostgreSQL  ◀── platform_core only
                          (single source of truth)
```

Boundaries:

- **Browser ↔ App** — HTTPS at MVP+. POC may run over localhost HTTP. Output escaping enforced in templates.
- **Uploads ↔ Storage** — files validated in quarantine before being moved to addressed storage.
- **Connectors ↔ Modules** — read-only; outputs are normalized like uploaded evidence.
- **App ↔ Database** — only the app process talks to the DB; no shared DB access between processes.
- **Modules ↔ Modules** — no direct calls; correlation goes through core.

---

## 3. Authentication

### 3.1 POC
- **No real authentication.** A role-switcher screen lets the demo user pick (Consultant / Customer Executive / Customer IT Lead) and a customer.
- The chosen identity is captured in session and recorded in the audit log.
- The login page warns "POC — no authentication" so no one mistakes the demo state for a real product.

### 3.2 MVP
- **ACEN consultants:** OIDC against the ACEN Entra tenant. Application registration with code+PKCE flow. MFA enforced via CA.
- **Customer-side users:** TBD between (a) ACEN-issued accounts (low friction, high admin overhead), (b) magic-link per email (no shared password), (c) Entra B2B federation (cleanest long-term, more setup). Q-0043 carries this decision.
- **Sessions:** server-side; rotated on privilege change; absolute timeout configurable.

### 3.3 Full Product
- Entra B2B as default. Optional support for additional IdPs as the customer base demands.
- Session policies aligned with customer security expectations (timeouts, device binding optional).

---

## 4. Authorization (RBAC)

### 4.1 Roles

| Role | Scope | What they can do |
|---|---|---|
| `acen_admin` | ACEN org | Manage organizations, customers, users, license catalog, sub-roles |
| `acen_consultant` | ACEN org → assigned customers | Read/write findings; manage evidence; publish customer reports |
| `acen_viewer` | ACEN org → assigned customers | Read-only |
| `customer_executive` | one customer | Read customer-visible findings + reports; no internal-only data |
| `customer_it_lead` | one customer | Read customer-visible findings (including `customer_full` technical detail); request retest |

### 4.2 Enforcement points

| Action | POC | MVP | Full |
|---|---|---|---|
| UI hide/show based on role | ✅ | ✅ | ✅ |
| Server-side authorization checks at route/service layer | 🟡 stub | ✅ | ✅ |
| DB-level row visibility (RLS) | ⬜ | 🟡 baseline | ✅ |
| Customer cannot access other customers' data | ⬜ enforced by UI in POC | ✅ server-side | ✅ server-side + RLS |
| Audit log immutable from the app's perspective | ✅ (append-only) | ✅ | ✅ (append-only with retention policy) |

The authorization check sits in a single decorator at the route/service entry — modules do not implement their own authz.

---

## 5. Tenant isolation

| Concept | POC | MVP | Full |
|---|---|---|---|
| Multi-tenant data model (Organization → Customer) | ✅ | ✅ | ✅ |
| Single-tenant deployment | ✅ | ✅ default | ⬜ optional |
| Hard isolation per customer at DB level (RLS or schema-per-tenant) | ⬜ designed | 🟡 partial | ✅ |
| Per-customer encryption keys | ⬜ | ⬜ | ✅ |
| Customer self-service controls (data export, delete) | ⬜ | 🟡 | ✅ |

POC runs single-tenant single-customer for the demo; the *data model* supports multi-customer (Contoso Corp + Fabrikam Inc, optional Q-0011) but isolation is UI-only.

---

## 6. Audit log

### 6.1 What is logged

Always:

- Login / role-switch (POC: role-switch only).
- Upload (artifact id, hash, customer, engagement, run, actor, module).
- Parse start/success/failure (artifact id, module, parser version, error if any).
- Control evaluation (control id, run id, result_status, license_status).
- Finding state change (`new → triaged → published → retest_requested → closed`).
- Customer-visibility change (finding id, old → new, actor).
- Report generation (report id, type, run id, actor, included findings count).
- Report publish (report id, recipient scope, actor, optional consultant note).
- Evidence access (drawer view of internal-only evidence by non-consultant roles).
- Settings changes (license catalog, role assignments).

### 6.2 Shape

```python
class AuditLog(Base):
    id: UUID
    organization_id: UUID
    customer_id: UUID | None
    engagement_id: UUID | None
    run_id: UUID | None
    actor_role: str
    actor_label: str       # POC: "Consultant", MVP: user upn / display name
    event_type: str        # "evidence.upload", "finding.publish", ...
    target_kind: str       # "artifact", "control", "finding", "report", "evidence", "user"
    target_id: str
    severity: enum("info", "notable", "security")
    payload: JSONB         # event-specific
    occurred_at: datetime
    ip: str | None
    user_agent: str | None
```

### 6.3 Properties

- **Append-only.** No update or delete from app code; admin cannot edit the audit log via UI.
- **Tamper-evident** at MVP+: each row carries a `prev_hash` chain so any in-place tampering is detectable.
- **Retention policy** per engagement at MVP+; POC keeps in DB until manually cleared.

---

## 7. Evidence protection

### 7.1 Upload

- Max file size enforced (200 MB default in POC).
- Magic-byte type check (ZIP / XML / JSON), not just file extension.
- Filename is **not** trusted; storage uses the SHA-256 hash, not the user filename.
- Quarantine directory; only after validation passes the artifact moves to the addressed location `evidence/<sha256[:2]>/<sha256>`.
- Manifest (where applicable) read in a sandboxed parser (no `eval`, no shell-out, no XML external entities).

### 7.2 Validation

- ZIP: count entries, cap on entry count, cap on each entry size, **no path traversal** (`..`, absolute paths rejected), **no symlinks**.
- XML (PingCastle): parsed with a hardened parser (disable DTD / external entities / network access).
- JSON: size cap, structural schema validation per module.

### 7.3 Storage

| Property | POC | MVP | Full |
|---|---|---|---|
| Filesystem (local) | ✅ | 🟡 fallback | ⬜ |
| Object storage (S3 / Azure Blob) | ⬜ | ✅ | ✅ |
| Encryption at rest | ⬜ | ✅ (cloud-managed key) | ✅ (customer-managed key option) |
| Per-tenant prefix / container | ✅ (path) | ✅ | ✅ |
| Lifecycle policies (purge after retention) | ⬜ | ✅ | ✅ |

### 7.4 Sensitive data classes

| Class | Examples | Default visibility |
|---|---|---|
| **Highly sensitive** | privileged accounts, attack paths, GPO weaknesses, Silverfort policy state, Entra app secrets, AD service accounts | `internal_only` |
| **Sensitive** | usernames, emails, group memberships, computer names | `internal_only` (POC); `customer_full` selectable by consultant |
| **Aggregate** | counts, scores, capability ownership, severity distributions | `customer_summary` allowed |

Modules declare default visibility per finding category (`customer_visibility_defaults` in the manifest). The consultant can override per finding.

---

## 8. Secure upload

- HTTPS only at MVP+.
- POST endpoint behind authn/authz at MVP+.
- POC accepts uploads on localhost only (binding 127.0.0.1 by default).
- Anti-CSRF token enforced by FastAPI form handlers.
- Rate-limit per actor at MVP+.
- Anti-virus scan **placeholder** in POC; integrate ClamAV or a cloud scanner at MVP.

---

## 9. BloodHound evidence protection

SharpHound ZIPs are uniquely sensitive — they enumerate the AD attack surface. Specifics:

- POC: synthetic only; never real customer ZIPs in repo.
- MVP: SharpHound ZIPs are stored alongside other evidence but tagged `sensitivity=high` for retention and access logs.
- Raw graph data is **never** included in customer reports. Only:
  - The path's **deterministic explanation** (consultant-reviewed).
  - The path's **identity refs** (subject to the same `customer_visibility` rules).
- Internal-only by default at finding level; consultant can downgrade to `customer_full` for the path *summary*, never for the raw graph.

---

## 10. Secrets

| Type | Where | POC | MVP | Full |
|---|---|---|---|---|
| App secret (session signing) | env var | random per dev | required via env / secret manager | required via secret manager |
| DB credentials | env var | required | required | required |
| Microsoft Graph client secret | env var | n/a | required | required |
| Silverfort API token | env var | n/a | required where applicable | required |
| Encryption-at-rest keys | KMS | n/a | cloud-managed | cloud-managed or customer-managed (BYOK) |

- POC: `.env.example` only; no real secrets committed; `.env` is gitignored.
- MVP: secret manager (Azure Key Vault or equivalent) at deployment; secrets injected at runtime, not built into images.
- Full: KMS / BYOK options for regulated customers.

---

## 11. Connector security

For future connectors:

- **Microsoft Graph:** read-only application permissions, consented once at customer admin; A-0007.
- **AD live (future):** read-only privileged account inside customer environment; toolkit runs offline; results uploaded.
- **Silverfort API:** **gated on validation** (D-0006); when implemented, narrowest read scope; rotation policy at MVP+.

Connectors **never** store credentials in plaintext. Connector health logs do not record secret material.

---

## 12. API security

- All routes that mutate state require authn (MVP+) and CSRF protection.
- Input validation via Pydantic at boundary.
- Output escaping in Jinja templates; `safe` filter never used on user-derived content.
- Rate limiting at MVP+.
- Standard headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) at MVP+.

---

## 13. GDPR

### 13.1 Lawful basis

- ACEN processes customer data under **contract** (Art. 6(1)(b)) with each engagement.
- DPA (Data Processing Agreement) executed per customer at MVP+. Sub-processors enumerated.

### 13.2 Data subjects

- Customer employees and service principals (identities, usernames, emails, group memberships).
- ACEN consultants (their own identities for audit log purposes).

### 13.3 Data minimization

- Modules ingest only what their declared controls need.
- The platform does **not** persist evidence content beyond the artifact + normalized rows the parsers produce.
- Synthetic data principle (D-0011) reduces incidental exposure in dev/test/repo.

### 13.4 Retention

| Item | POC | MVP | Full |
|---|---|---|---|
| Artifacts | until manual delete | engagement closure + N months (default 12, configurable per DPA) | per DPA |
| Normalized evidence | same as artifact | same | per DPA |
| Findings | same | same | per DPA |
| Reports | indefinite (immutable record) | engagement closure + N years (per DPA, accounting/audit) | per DPA |
| Audit log | indefinite | per DPA; tamper-evident chain | per DPA |

### 13.5 Subject rights

- **Access (Art. 15):** export of a customer's data at MVP+.
- **Rectification (Art. 16):** not applicable to evidence-derived data (read-only); rectification requests are documented and re-collection performed.
- **Erasure (Art. 17):** delete a customer's data on request (subject to retention obligations). MVP supports a "purge customer" path that removes artifacts, normalized rows, findings, and reports tied to that customer.
- **Restriction / objection / portability:** documented in DPA; supported at MVP+.

### 13.6 Cross-border transfers

- Hosting region selectable per deployment (POC: developer workstation; MVP: EU regions default).
- SCCs in place if any sub-processor is outside the EEA.

---

## 14. Data minimization, in practice

- Module manifests declare exactly which fields they read from evidence. Anything not declared is parsed-but-dropped before persistence.
- Internal logs (application logs) **never** include user identifiers, file contents, or sensitive payloads. Identifiers are referenced by UUID in logs.
- Browser-side rendering does not leak `internal_only` data into the DOM for customer roles — the server filters before render.

---

## 15. Retention

Detailed in §13.4. Implementation:

- A scheduled retention job (MVP+) reads engagement state and deletes artifacts that crossed the retention horizon.
- Reports are kept longer than evidence (legal/accounting hold) by default.
- Deletion is audited (`evidence.purge` event).

---

## 16. Export / delete

- **Export (per customer):** ZIP containing all artifacts, normalized evidence (JSON), findings (JSON), reports (HTML/PDF), and the customer-scoped audit log.
- **Delete (per customer):** purges artifacts, normalized rows, findings, reports (subject to retention hold), and records a `customer.purge` audit event. The platform retains an anonymized record of the purge (date, actor, scope).

---

## 17. Publishing controls

The `customer_visibility` flag is the gatekeeper:

- **`internal_only`** — never appears in customer-facing UI or reports.
- **`customer_summary`** — appears as executive summary; technical detail blocks suppressed.
- **`customer_full`** — full content including technical detail.

Enforcement:

| Layer | What it does |
|---|---|
| Service layer | Filters findings by `customer_visibility` and actor role before returning to UI |
| UI | Hides cards / drawers based on the filtered set; non-consultants never see `internal_only` in the DOM |
| Report renderer | Filters findings before composing template; renders technical detail only for `customer_full` |
| Audit log | Records every visibility change |

Defaults:

- New findings → `internal_only` regardless of category.
- Modules can declare safer defaults per category (e.g., raw SharpHound graph derivations always `internal_only` regardless of consultant choice).
- POC: enforcement at service layer + UI; MVP: also at DB read path via authorization helpers.

---

## 18. POC security boundaries

To keep POC small without leaking risk:

- **Runs on localhost.** App binds 127.0.0.1 by default; demo workstation only.
- **No real customer data.** Synthetic only (D-0011).
- **No outbound network calls** from the platform during the demo (no telemetry, no LLM, no Graph). Any future telemetry is opt-in.
- **Role-switcher includes audit log entry** for every role choice.
- **Visibility flag enforced** in UI and report renderer.
- **Banner** on every page during POC: "POC build — synthetic data only — not for customer use."

---

## 19. MVP security baseline

Promotions from POC at MVP:

- Real auth (OIDC against ACEN Entra), MFA via CA, session policies.
- Server-side authorization at the service layer (decorator + tests).
- Encrypted storage backend (object storage with cloud-managed encryption).
- Secret manager (Azure Key Vault or equivalent).
- HTTPS-only; CSP and standard security headers.
- Rate limiting on all routes.
- AV scanning of uploads.
- Tamper-evident audit log chain.
- Retention policy and purge job.
- Subject-rights export/delete tooling.

---

## 20. Future enhancements (Full Product)

- Row-level security (RLS) or schema-per-tenant isolation.
- Customer-managed keys (BYOK).
- Customer-bound network egress controls.
- SAML/OIDC federation for customer IdPs beyond Entra.
- Webhook signing / outbound integration security.
- Continuous monitoring posture (always-on Graph delta queries) with consent controls.
- SOC 2 / ISO 27001 readiness (audit trails, change control, vendor management).

---

## 21. Risks and mitigations

Tracked in `RISKS.md`. Key security-specific:

| Risk | Mitigation |
|---|---|
| Real customer evidence committed to repo (R-0005) | Synthetic data only; `.gitignore` rules; pre-commit hook at MVP. |
| Path-traversal via ZIP (`Zip Slip`) | Hardened ZIP extractor; entry-by-entry path checks; no symlinks. |
| XML external entity (XXE) in PingCastle XML | Hardened XML parser (DTD off, external entities off). |
| Customer accidentally sees internal-only data | Two-layer enforcement (service + UI). Default `internal_only`. |
| Audit log tampered | Tamper-evident chain at MVP; append-only DB constraints. |
| Secret leak via logs | Logging policy excludes secrets; centralized logger config. |
| Connector secret compromise | Secret manager + rotation + read-only scopes + per-tenant scoping. |
| Cross-tenant data leak | UI authz checks customer scope; MVP server-side checks + RLS at Full. |

---

*Last updated: 2026-05-15.*
