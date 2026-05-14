# BLOODHOUND_ANALYZER_DESIGN.md

> Design for the BloodHound Analyzer module of ACEN Gravity. Defines how SharpHound CE evidence is ingested, modelled as a graph, traversed deterministically to detect critical paths to Tier 0, categorized, scored, explained, and correlated with the AD, Silverfort, and Entra modules.
>
> This document is **design-only**. No code. Algorithms are described in numbered steps where helpful, never as runnable functions.
>
> Companion documents: `PRODUCT_DESIGN.md` §21, `POC_V1_SCOPE.md` §4 (steps 5 + 8), §5.4 and §11, `MODULE_ARCHITECTURE.md` §10 (Finding shape), §11 (correlations), §12 (scoring), `LICENSE_MODEL.md` §3 (license_status enum), `SECURITY_AND_GDPR.md` §9 (BloodHound evidence protection), `UI_DESIGN_DIRECTION.md` §13 (BloodHound / Attack Path UI), `DECISIONS.md` (D-0005), `ASSUMPTIONS.md` (A-0005, A-0011, A-0015), `RISKS.md` (R-0004, R-0008).

---

## 1. Purpose

### 1.1 What the analyzer is

The BloodHound Analyzer is the ACEN Gravity module that turns a SharpHound CE evidence ZIP into a small, ordered, defensible list of **critical attack paths to Tier 0**, each presented as one Finding with the same shape used by every other module.

It must answer three questions for the consultant and the customer, in this order:

1. *Where can an attacker reach Tier 0 from inside your environment today?*
2. *Why is that path possible — node by node, edge by edge?*
3. *What is the smallest, defensible change that closes it?*

It must answer those questions **without an AI judging the path** (D-0005). The analyzer is the part of the platform where determinism is most strictly enforced, because BloodHound output is what consultants and customers will most directly challenge.

### 1.2 What the analyzer is not

- **Not a graph database.** (POC; revisited at MVP — see §22.)
- **Not a free-form graph canvas.** (POC; the UI is a vertical `PathStepList` — see `UI_DESIGN_DIRECTION.md` §13.)
- **Not an LLM that "reads" the graph.** Detection, ranking, scoring, correlation, and the *initial* explanation are deterministic and template-based (D-0005).
- **Not a BloodHound replacement.** It consumes SharpHound CE output; it does not collect data, query the AD/Entra graph live, or replicate BloodHound's interactive analyst UX.
- **Not a path discovery experiment.** The analyzer enumerates a bounded, ranked set of paths to a deterministic Tier 0 target set; it does not freely search "interesting" subgraphs.

### 1.3 Position in the platform

The analyzer is an **Evidence Module** (per `MODULE_ARCHITECTURE.md` §2). It follows the single shared lifecycle: *evidence → parse → normalize → evaluate → finding → publish → report*. It reuses the core `Identity` entity, the shared `Finding` shape, the 8-value `license_status` enum, and the standard UI components.

---

## 2. Why it works without AI (D-0005)

D-0005 is the most important constraint on this module. It states that **detection, ranking, scoring, correlation, and the initial explanation are deterministic and template-based**. AI may polish language at a later stage, only after a consultant has reviewed the deterministic output.

### 2.1 Why determinism matters here

| Reason | Concretely, in this module |
|---|---|
| **Auditability** | A consultant must be able to re-derive a path's score and explanation from the same evidence ZIP, byte-for-byte. AI outputs are non-deterministic and not reproducible across model versions. |
| **Defensibility (consultant trust)** | When a customer asks "why is this Critical?", the consultant must answer with the formula and the inputs. "The model said so" is not defensible. |
| **Defensibility (customer trust)** | The customer is being told to fund remediation. They must see the chain (source → ... → Tier 0 target) and the rule that made each edge dangerous. Black-box scoring breaks the commercial conversation. |
| **GDPR / privacy posture** | Sending raw SharpHound graph data to an external model is a sensitive-data leak (see `SECURITY_AND_GDPR.md` §9). Determinism avoids inventing reasons to call out. |
| **Regression safety** | A deterministic analyzer can be unit-tested. An LLM-backed analyzer cannot, in any reproducible sense. |
| **Drift control** | Without this constraint, the module slides toward "AI does it" under deadline pressure (R-0004). |

### 2.2 What AI may *eventually* polish (MVP/Full, post-review only)

After the consultant has reviewed the deterministic finding, AI may be used (MVP/Full, optional) **only** to:

- **Improve the readability of the customer-facing summary** (`summary_customer`) — rewording, tone, sentence flow.
- **Soften the internal summary** (`summary_internal`) into executive language **after** the consultant has confirmed the template output is correct.
- **Suggest alternative phrasings** for the `remediation` block (still based on the deterministic template; the consultant accepts/rejects).

The AI must operate on **already-redacted text** (no raw SIDs, no node ids), and its output must be displayed in a review pane that visibly distinguishes "deterministic" from "polish suggestion" before publication.

### 2.3 What AI will *never* do

- **Path discovery.** Paths are enumerated by graph algorithms, not by LLM reasoning.
- **Tier 0 / target classification.** Targets are deterministically derived from §9 rules + per-engagement overrides.
- **Edge severity assignment.** Edge severities come from the §8 table; they are not "judged" per case.
- **Risk scoring.** The §13 formula is the only source of `risk_score`.
- **Correlation.** Correlation hits are produced by the rules in §16–§18 against normalized data, not by AI matching.
- **Initial explanation generation.** The first explanation a consultant sees is rendered from §15 templates, deterministically.

This applies at **POC**, **MVP**, and **Full Product**. The constraint never softens with tier; only the surface area of allowed *polish* widens (and only post-review).

### 2.4 How this constraint is enforced in the design

- The analyzer pipeline (§11–§15) has **no LLM call**. (POC, MVP, Full.)
- The Finding render (`summary_internal`, `summary_customer`, `remediation`, `validation_method`) is produced by template substitution against deterministic inputs. (POC.)
- A future "polish" surface (MVP/Full) is a **separate, optional, post-review step**, gated by `state ∈ {triaged, published}` and `consultant_review_status = approved`. It is **not** in the path detection or scoring code paths.
- This constraint is re-stated in §11 (Critical path detection), §13 (Risk scoring), and §15 (Template explanations) — every place where a developer might be tempted to "let the model do it".

---

## 3. POC / MVP / Full scope

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| Parse SharpHound CE ZIP (current schema, A-0005) | ✅ | ✅ | ✅ |
| Parse legacy BloodHound 4.x ZIP | ⬜ (best-effort note; Q-0060) | 🟡 if customers need it | 🟡 |
| In-memory NetworkX graph | ✅ | ✅ | 🟡 (may be replaced; see §22) |
| Deterministic Tier 0 identification | ✅ | ✅ | ✅ |
| Per-engagement Tier 0 override (Q-0053) | ✅ (advisory, consultant-set) | ✅ | ✅ |
| Shortest-path enumeration to Tier 0 | ✅ | ✅ | ✅ |
| Path categories: group nesting, ACL abuse, unconstrained delegation | ✅ | ✅ | ✅ |
| Path categories: constrained delegation, RBCD, DCSync, GPO control | ⬜ | ✅ | ✅ |
| Path categories: AD CS (ESC1–ESC8) (Q-0062) | ⬜ | 🟡 (subset) | ✅ |
| Path categories: trust paths, hybrid identity paths | ⬜ | ✅ | ✅ |
| Session/local admin paths (HasSession, AdminTo) | ⬜ (A-0015 — no sessions in sample data) | ✅ | ✅ |
| Deterministic risk scoring (formula in §13) | ✅ | ✅ | ✅ |
| Template-based step-by-step explanations | ✅ | ✅ | ✅ |
| Correlation with AD module | ✅ | ✅ | ✅ |
| Correlation with Silverfort module | ✅ (sf_protected flag) | ✅ | ✅ |
| Correlation with Entra module | ✅ (hybrid admin flag) | ✅ | ✅ |
| Graph visualization (canvas) (Q-0063) | ⬜ (PathStepList only) | 🟡 optional | ✅ |
| Cypher / BloodHound CE backend (alternative B in §22) | ⬜ | 🟡 evaluated | 🟡 |
| Own graph database (Neo4j / memgraph) (alternative C in §22) | ⬜ | ⬜ | 🟡 only if needed |
| AI language polish (post-review) | ⬜ never in critical path | 🟡 optional | 🟡 optional |
| Path enumeration cap | top N=50 considered, top 5 reported (POC) | configurable | configurable |

Legend: ✅ in scope, ⬜ out of scope, 🟡 partial / gated.

---

## 4. ZIP structure (SharpHound CE)

### 4.1 Expected files

A SharpHound CE collection produces a ZIP containing JSON files, one per object class. Naming varies slightly across SharpHound versions; the parser matches by JSON content **kind**, not by filename alone.

| Logical file | Content kind | Typical name pattern | POC required |
|---|---|---|:---:|
| Users | `users` | `*_users.json` | ✅ |
| Groups | `groups` | `*_groups.json` | ✅ |
| Computers | `computers` | `*_computers.json` | ✅ |
| OUs | `ous` | `*_ous.json` | ✅ |
| GPOs | `gpos` | `*_gpos.json` | ✅ |
| Containers | `containers` | `*_containers.json` | ✅ |
| Domains | `domains` | `*_domains.json` | ✅ |
| Sessions | `sessions` | `*_sessions.json` | ⬜ (A-0015) |
| AdLocalGroups (local admins) | `ad_local_groups` | `*_ad_local_groups.json` | ⬜ (MVP) |
| Certificate objects (CertTemplates, CAs, NTAuthStore, RootCAs, IssuancePolicies, EnterpriseCAs) | `cert*` | `*_cert*.json` | ⬜ (MVP — AD CS) |

### 4.2 Legacy BH 4.x (A-0005, Q-0060)

Legacy BloodHound 4.x ZIPs may be ingested on a **best-effort** basis at MVP+. The parser is structured so a 4.x adapter can be added without changing the graph model.

- **POC:** rejected with a clear error: *"BloodHound 4.x format not supported in POC; please re-collect with SharpHound CE."*
- **MVP:** opt-in adapter; tagged as `parser_version="bh4-legacy"` in `Evidence.payload`; mapped to the same internal model.

### 4.3 Required vs optional

- `users`, `groups`, `computers`, `domains` are **required**. If any is missing, the parser returns `unknown` and emits no findings.
- `ous`, `gpos`, `containers` are **strongly recommended** for path categorization; their absence downgrades category detection accuracy.
- `sessions`, `ad_local_groups`, `cert*` are **optional**. In POC sample data, sessions are omitted by A-0015.

### 4.4 ZIP-level validation

Per `SECURITY_AND_GDPR.md` §7.2:

- **No path traversal** (`..`, absolute paths inside ZIP entries — rejected).
- **No symlinks** inside ZIP — rejected.
- **Entry count cap** (configurable; default 10,000).
- **Per-entry size cap** (configurable; default 100 MB after decompression).
- **Total decompressed size cap** (configurable; default 1 GB).
- **Magic-byte check** for `.zip` at upload boundary (already enforced by core).

If any check fails, the artifact is marked `parse_failed` and an audit entry is written (`evidence.parse.failed`). The analyzer does not emit partial findings (per `MODULE_ARCHITECTURE.md` §3 failure rules).

---

## 5. Parsing model

### 5.1 Streamed parsing

- ZIPs may be large; the parser **streams** JSON entries (does not load full file content into memory unless required).
- Each JSON entry is validated against a per-kind structural schema (see §5.3).
- Object data is appended into kind-keyed in-memory collections that feed the graph builder (§6).

### 5.2 Sandboxing

- JSON parsing uses a hardened JSON parser (no eval, no custom decoders that execute code).
- No file content is interpreted as a path or a command.
- File names inside the ZIP are **never** rendered as is in the UI — only the recognized kind is shown.
- No outbound network call is made during parse (per `SECURITY_AND_GDPR.md` §18).

### 5.3 Per-file JSON schema validation

For each kind, the parser validates the top-level shape and each object's required fields:

| Kind | Required object fields (POC) |
|---|---|
| `users` | `ObjectIdentifier` (SID), `Properties.name`, `Properties.domain`, `Properties.enabled`, `PrimaryGroupSID`, `Aces` |
| `groups` | `ObjectIdentifier`, `Properties.name`, `Properties.domain`, `Members`, `Aces` |
| `computers` | `ObjectIdentifier`, `Properties.name`, `Properties.domain`, `Properties.enabled`, `LocalAdmins`, `RemoteDesktopUsers`, `DcomUsers`, `PSRemoteUsers`, `Sessions` (optional), `Aces` |
| `ous` | `ObjectIdentifier`, `Properties.name`, `Properties.domain`, `ChildObjects`, `Links` (GPO links), `Aces` |
| `gpos` | `ObjectIdentifier`, `Properties.name`, `Properties.gpcpath`, `Aces` |
| `containers` | `ObjectIdentifier`, `Properties.name`, `ChildObjects`, `Aces` |
| `domains` | `ObjectIdentifier`, `Properties.name`, `Trusts`, `ChildObjects`, `Aces` |
| `sessions` (optional) | `Results` (UserSID, ComputerSID) |

Unknown fields are ignored. Missing required fields cause that object to be dropped with a counter increment; the parser does not silently substitute defaults.

### 5.4 Outputs of parse

For each successful parse, the parser produces:

1. One `Evidence` row per logical kind (typed payload — see `MODULE_ARCHITECTURE.md` §7).
2. A `bh_graph_snapshot` row referencing the artifact (sha256, parsed_at, object counts per kind).
3. Upserts to core `Identity` rows (by SID and ObjectGUID where present; see `MODULE_ARCHITECTURE.md` §8).
4. Module-local normalized rows produced **later** by the analyzer pipeline (path rows; see §6.6).

Parse is **idempotent**: re-parsing the same artifact produces the same evidence rows (deduplicated by artifact hash).

---

## 6. Graph model

### 6.1 In-memory graph (POC)

The analyzer builds an **in-memory directed graph** using NetworkX. The graph exists for the duration of the analysis pipeline and is **not persisted**.

- **Nodes**: typed AD/Entra/Cert objects (see §7).
- **Edges**: typed relationships (see §8).
- **Attributes**: per-node and per-edge attribute dictionaries (see §6.4).

POC choice: NetworkX in-memory (option A in §22). Persisted output is path summaries, not the graph itself.

### 6.2 Build phases

1. **Node creation.** For each parsed user/group/computer/OU/GPO/container/domain object, a node is added with `id = ObjectIdentifier` (SID/ObjectGUID where applicable).
2. **Edge creation pass 1: containment.** OU/Container `ChildObjects` and domain `ChildObjects` produce `Contains` edges (used for GPO scope inference; not a critical-path edge).
3. **Edge creation pass 2: GPO links.** `Links` from OUs/domains to GPOs produce `GpLink` edges.
4. **Edge creation pass 3: group membership.** `Members` arrays produce `MemberOf` edges from member → group.
5. **Edge creation pass 4: ACEs.** Each `Aces` entry on every object produces a typed edge from the principal (ACE grantee) to the target object, with the ACE right mapped to an edge type (§8).
6. **Edge creation pass 5: local admin / RDP / DCOM / PSRemote.** Computer's `LocalAdmins`, `RemoteDesktopUsers`, `DcomUsers`, `PSRemoteUsers` produce `AdminTo` / `CanRDP` / `ExecuteDCOM` / `CanPSRemote` edges from principal → computer.
7. **Edge creation pass 6: sessions** (optional; not present in POC sample per A-0015). `Sessions.Results` produces `HasSession` edges from computer → user.
8. **Edge creation pass 7: delegation.** Computer/user `AllowedToDelegate` / `AllowedToAct` properties produce `AllowedToDelegate` / `AllowedToAct` edges.
9. **Edge creation pass 8: trusts.** Domain `Trusts` produce `TrustedBy` / `SameForestTrust` / `CrossForestTrust` edges.

### 6.3 Node identity

- Nodes are keyed by **AD SID** for AD principals; by **ObjectGUID** when only GUID is available; by `<kind>:<id>` for cert objects.
- Each node carries `kind`, `label` (human display), `domain`, and a copy of the relevant `Properties` subset (no PII beyond what evaluation needs).

### 6.4 Attribute storage

Per-node attributes (subset):

- `kind` (User / Group / Computer / OU / GPO / Container / Domain / AdLocalGroup / Cert*)
- `label` (display name or sAMAccountName)
- `domain`
- `enabled` (where applicable)
- `is_tier0` (computed; see §9)
- `is_crown_jewel` (consultant-flagged; see §10)
- `azure_object_id` (set when AD module has joined the identity)
- `sf_protected` (set when SF module has joined the identity)

Per-edge attributes (subset):

- `kind` (edge type id, e.g., `GenericAll`, `MemberOf`)
- `severity_weight` (from §8 table)
- `source_file` (which SharpHound JSON it came from)
- `notes` (e.g., `via_aces_entry_index=42` for traceability)

### 6.5 Why in-memory and not persisted

- The full graph contains every ACE on every object — that is exactly the highly sensitive data class flagged by `SECURITY_AND_GDPR.md` §7.4 and §9.
- Persisting the full graph creates ongoing exposure with no downstream benefit (we never need to "browse" the graph in POC; the UI shows path step lists, not graph canvases).
- Persisting paths (not graphs) keeps the database small, enables fast UI rendering, and matches the SharpHound ZIP retention model (the artifact is the source of truth; we hold derived paths).

### 6.6 Persistence plan (path summaries, not the graph)

After analysis, the analyzer persists:

- `bh_path` rows — one per ranked path (id, run_id, source_node_id, target_node_id, length, category, risk_score, severity, computed_at, evidence_artifact_id).
- `bh_path_step` rows — one per node in a path (path_id, step_index, node_kind, node_id, node_label, edge_kind_to_next, edge_severity_weight).
- One `Finding` per selected path (per §14) with the path payload embedded.

The full graph is **discarded after analysis**. Re-evaluation re-builds it from the artifact.

---

## 7. Node types

| Node id (kind) | Source file (SharpHound) | Key attributes | Notes |
|---|---|---|---|
| `User` | `users.json` | SID, sAMAccountName, UPN, ObjectGUID, enabled, domain, primaryGroupSID, hasSPN, dontReqPreauth | Joined to core `Identity` by SID and ObjectGUID |
| `Group` | `groups.json` | SID, name, domain, members, well-known SID flag | Used for Tier 0 detection (well-known SIDs) |
| `Computer` | `computers.json` | SID, name, domain, enabled, operatingSystem, isDomainController, unconstrainedDelegation flag | DCs are auto-flagged Tier 0 (§9) |
| `OU` | `ous.json` | ObjectGUID, name, domain, links, childObjects | GpLink and containment edges |
| `GPO` | `gpos.json` | ObjectGUID, name, gpcpath | Targets of `GenericAll`/`GenericWrite` matter — see §8 |
| `Container` | `containers.json` | ObjectGUID, name, childObjects | E.g., `AdminSDHolder` is a critical Container (§9) |
| `Domain` | `domains.json` | SID, name, trusts | Edge endpoint for trust paths (MVP) |
| `AdLocalGroup` | `ad_local_groups.json` (MVP) | composite id (computer SID + group RID), name | Local admin sub-graph (MVP) |
| `CertTemplate` | `cert_templates.json` (MVP, AD CS) | ObjectGUID, name, requiresManagerApproval, enrolleeSuppliesSubject, etc. | ESC1–ESC8 (MVP, Q-0062) |
| `EnterpriseCA` | `cert_enterprise_cas.json` (MVP, AD CS) | ObjectGUID, name, hosting computer | AD CS path endpoint (MVP) |
| `NTAuthStore`, `RootCA`, `IssuancePolicy` | `cert_*.json` (MVP, AD CS) | name | AD CS path endpoint (MVP) |

> **POC scope:** only `User`, `Group`, `Computer`, `OU`, `GPO`, `Container`, `Domain` are required to demonstrate the three POC path categories (§3).

---

## 8. Edge types

Each edge type has a deterministic detection rule (where it comes from in SharpHound) and a `severity_weight` used by the scoring formula (§13). Severity weights are deterministic and shared across all engagements (POC); per-engagement override is an MVP capability.

| Edge id | Severity weight | Abuse description (template-grade) | Deterministic detection rule |
|---|:---:|---|---|
| `MemberOf` | 1 | Principal is a (transitive) member of a group, inheriting its rights | From `Members` arrays on group objects |
| `AdminTo` | 9 | Principal has local administrator rights on the target computer | From `Computer.LocalAdmins` |
| `CanRDP` | 4 | Principal can RDP to the target computer (lateral movement entry) | From `Computer.RemoteDesktopUsers` |
| `ExecuteDCOM` | 4 | Principal can execute via DCOM on the target computer | From `Computer.DcomUsers` |
| `CanPSRemote` | 4 | Principal can run PSRemoting on the target computer | From `Computer.PSRemoteUsers` |
| `HasSession` (MVP/sample-data-dependent — A-0015) | 8 | An interactive session on the computer can be stolen (token theft) | From `sessions.json` (optional) |
| `GenericAll` | 10 | Full control over the target — can take over, change passwords, set DACLs, etc. | From `Aces` with `RightName=GenericAll` |
| `GenericWrite` | 9 | Write access — abuse paths include SPN write + Kerberoast, msDS-AllowedToActOnBehalfOfOtherIdentity write (RBCD), etc. | From `Aces` with `RightName=GenericWrite` |
| `WriteDacl` | 10 | Can modify the target's DACL — effectively GenericAll | From `Aces` with `RightName=WriteDacl` |
| `WriteOwner` | 9 | Can change the owner of the target — gain effective GenericAll | From `Aces` with `RightName=WriteOwner` |
| `Owns` | 8 | Already owner — can rewrite DACL | From `Aces` with `RightName=Owns` |
| `AddMember` | 9 | Can add members to the target group | From `Aces` with `RightName=AddMember` |
| `ForceChangePassword` | 9 | Can reset the target user's password | From `Aces` with `RightName=ForceChangePassword` |
| `ReadLAPSPassword` | 7 | Can read the local administrator password attribute (computer object) | From `Aces` with `RightName=ReadLAPSPassword` |
| `ReadGMSAPassword` | 7 | Can read the gMSA password blob | From `Aces` with `RightName=ReadGMSAPassword` |
| `AllowedToDelegate` | 9 | Constrained delegation — principal can impersonate any user to the listed SPN/service | From `User/Computer.AllowedToDelegate` |
| `AllowedToAct` (RBCD) | 9 | Resource-based constrained delegation — listed principal can impersonate any user *to this resource* | From `Computer.AllowedToAct` |
| `UnconstrainedDelegation` (flag, not an edge per se) | 10 | Computer/user account holding TGTs that can be replayed against any service | From `Properties.unconstrainedDelegation=true` (computer or user) |
| `DCSync` | 10 | Principal can replicate the directory and extract password hashes | From combined `Aces` `GetChanges` + `GetChangesAll` on the domain object |
| `GetChanges` | 6 | Half of DCSync; alone, partial replication | From `Aces` with `RightName=GetChanges` |
| `GetChangesAll` | 6 | Other half of DCSync; alone, partial replication | From `Aces` with `RightName=GetChangesAll` |
| `GpLink` | 5 | OU/domain is linked to a GPO that applies | From OU/domain `Links` |
| `Contains` | 1 | Containment for OU/Container/Domain (used for inference, not direct attack edge) | From `ChildObjects` |
| `TrustedBy` | 6 | Domain trust direction | From `Domain.Trusts` (MVP) |
| `ADCS-ESC1`..`ADCS-ESC8` | 8–10 | AD CS misconfigurations enabling cert-based domain takeover | From `cert_*` objects (MVP, Q-0062) |
| `HasSPN` (property, not an edge per se) | n/a — feeds Kerberoast risk on a node | n/a | From `Properties.hasspn=true` on a user |

Notes:

- The `severity_weight` is the **max edge severity** input to the scoring formula (§13).
- `Contains`, `GpLink`, and `MemberOf` are traversal edges with low individual severity but are essential to reaching higher-severity edges.
- Severities are calibrated against community-accepted abuse impact; final review by Kristof + consultant lead (logged when accepted).

---

## 9. Tier 0 identification

Tier 0 is the set of identities/computers whose compromise effectively compromises the forest. The analyzer's Tier 0 set is **deterministic** (D-0005) and **explicit** — never inferred by AI.

### 9.1 Default Tier 0 set (POC)

Per Microsoft's Enterprise Access Model and standard AD security practice, the following are Tier 0 **by default**:

- **Well-known privileged groups (by RID / well-known SID):**
  - Domain Admins (`*-512`)
  - Enterprise Admins (`*-519`)
  - Schema Admins (`*-518`)
  - Built-in Administrators (`*-544`)
  - Account Operators (`*-548`)
  - Backup Operators (`*-551`)
  - Server Operators (`*-549`)
  - Print Operators (`*-550`)
  - Domain Controllers group (`*-516`)
  - Enterprise Read-only Domain Controllers (`*-498`)
  - Read-only Domain Controllers (`*-521`)
  - Group Policy Creator Owners (`*-520`)
  - Cert Publishers (`*-517`)
  - Enterprise Key Admins (`*-527`)
  - Key Admins (`*-526`)
- **Well-known privileged accounts:**
  - `krbtgt` (`*-502`)
  - Built-in Administrator (`*-500`)
- **Computers:**
  - Any computer in the `Domain Controllers` OU (by parent OU match).
  - Any computer with `isDomainController=true`.
- **Containers / objects:**
  - `AdminSDHolder` container in each domain.
  - The domain object itself (for DCSync rule).

The set is computed once at analysis start. Every node in the set has `is_tier0=true` set.

### 9.2 Per-engagement override (Q-0053)

The consultant can override the Tier 0 set per engagement (Q-0053):

- **Add to Tier 0:** any identity/computer the consultant marks (e.g., a specific service account, an SCCM server, a tier-0-equivalent admin workstation).
- **Remove from Tier 0:** any default member the consultant excludes (rare; documented with a note).

The override is stored on the engagement, applied at analysis time, and **audited** (`bh.tier0.override`). The default set is the source of truth unless overridden.

### 9.3 What Tier 0 means in the analyzer

Tier 0 is the **target set** for path enumeration (§11). A path is "to Tier 0" if its final node is in the Tier 0 set.

A path is **also** considered Tier 0 if its final edge writes/affects a Tier 0 object's DACL (e.g., `GenericAll` on Domain Admins) — the writer effectively becomes Tier 0.

---

## 10. Crown jewel identification

Beyond Tier 0, customers care about **other crown jewels** — finance systems, HR systems, code-signing infrastructure, the EHR/PACS in healthcare, etc. The analyzer supports this via an `is_crown_jewel` flag on Identities/Computers.

### 10.1 POC scope

- POC **supports the flag** but does **not auto-detect** crown jewels.
- The flag is set by the consultant in the AD module's evidence drawer or in a small engagement-level admin screen.
- When set, a crown-jewel node behaves like a secondary high-value target: paths ending at a crown jewel are surfaced separately from Tier 0 paths and weighted at `target_criticality_score = 80` (§13.2).

### 10.2 MVP+

- Auto-detect via integration with the AD module's normalized data (privileged groups beyond Tier 0, service accounts flagged by the consultant, computers with high-value AD attributes).
- Pull customer-defined business-critical asset lists where available.
- Surface a "Crown Jewels" status card on the BloodHound page (MVP, in addition to Tier 0 Reachability).

---

## 11. Critical path detection

### 11.1 Approach

Deterministic shortest-path enumeration. **No AI.** (D-0005.)

The analyzer treats path detection as a **bounded weighted-edge shortest-path problem** on the directed graph:

- **Source set (POC):** every enabled `User` and `Computer` node that is **not** itself in Tier 0. (Including non-privileged service accounts, contractor accounts, generic accounts, etc.)
- **Target set:** the Tier 0 set (§9), plus crown-jewel nodes (§10) when flagged.
- **Algorithm:** weighted BFS / Dijkstra over edges with weight `1 / severity_weight` (or equivalent — higher-severity edges are "shorter"). Configurable in code; the default produces shorter paths through higher-severity edges, which matches consultant intuition.
- **Path length cap:** maximum 8 hops (configurable). Paths beyond the cap are not enumerated.
- **Per-source cap:** the top K=3 paths per source (avoid drowning a single account in trivial variants).
- **Global cap:** top N=50 paths considered for ranking.
- **POC reporting cap:** top 5 paths reported as Findings (POC; configurable at MVP).

### 11.2 Numbered enumeration steps

1. Build the graph (§6).
2. Compute the Tier 0 set (§9) and the crown-jewel set (§10).
3. For each Tier 0 (or crown-jewel) target node, compute a reverse-direction Dijkstra / BFS to all enabled non-Tier 0 source candidates (or run forward Dijkstra from each source; equivalent up to choice of implementation).
4. For each (source, target) pair with a path within the length cap, collect the path as a sequence of `(node, edge_to_next)` tuples.
5. De-duplicate paths that share the same node sequence (same chain via different ACE entries — keep one, attach a note).
6. Apply per-source cap (top K paths per source).
7. Score every collected path (§13).
8. Sort by `risk_score` descending; apply global cap N=50.
9. Categorize every kept path (§12).
10. Select the top 5 (POC) for finding generation (§14).

### 11.3 Edge weighting note

The "shorter through higher severity" weighting is deterministic and documented:

- Edge weight = `max_severity_weight + 1 - edge.severity_weight` (so high-severity edges become low-weight, i.e., preferred by shortest-path).
- All weights are integers; ties broken by path length, then by lex order of node ids (for reproducibility).

### 11.4 What this is *not*

- Not "find the most interesting subgraph" (no AI judgment).
- Not "explore all paths" (bounded by §11.1 caps).
- Not "score via correlation alone" (correlation is a §13 input, not the only signal).
- Not "let the analyst graph-traverse interactively" (POC; that is the BloodHound product itself).

---

## 12. Classification

Each enumerated path is **categorized** by inspecting its edge sequence against a deterministic rule set. A path may match more than one category; the **primary category** is the first match in order below (higher-priority categories listed first). Secondary categories are stored on the path payload.

### 12.1 Category list

| Category id | Title | Primary rule (deterministic) | POC | MVP | Full |
|---|---|---|:---:|:---:|:---:|
| `bh.path.privesc.group-nesting` | Privilege escalation via group nesting | Path contains ≥ 2 `MemberOf` edges culminating in a Tier 0 group, with no other "abusive" edge type | ✅ | ✅ | ✅ |
| `bh.path.acl-abuse` | ACL abuse | Path contains ≥ 1 ACL abuse edge (`GenericAll`, `GenericWrite`, `WriteDacl`, `WriteOwner`, `Owns`, `AddMember`, `ForceChangePassword`) | ✅ | ✅ | ✅ |
| `bh.path.delegation.unconstrained` | Unconstrained delegation | Path target/intermediate has `unconstrainedDelegation=true` and is reached by a non-trivial principal | ✅ | ✅ | ✅ |
| `bh.path.delegation.constrained` | Constrained delegation | Path contains `AllowedToDelegate` edge | ⬜ | ✅ | ✅ |
| `bh.path.delegation.rbcd` | Resource-based constrained delegation (RBCD) | Path contains `AllowedToAct` edge with writable target | ⬜ | ✅ | ✅ |
| `bh.path.session-localadmin` | Session / local admin path | Path contains `HasSession` or `AdminTo` edges chaining to Tier 0 | ⬜ (A-0015) | ✅ | ✅ |
| `bh.path.gpo-control` | GPO control | Path contains write/control over a GPO linked to an OU containing Tier 0 computers | ⬜ | ✅ | ✅ |
| `bh.path.dcsync` | DCSync | Path ends with `GetChanges` + `GetChangesAll` or `DCSync` on a domain object | ⬜ | ✅ | ✅ |
| `bh.path.adcs` | AD CS misconfiguration (ESC1–ESC8) | Path ends through a misconfigured `CertTemplate` to a Tier 0 enrollee path | ⬜ | 🟡 (subset; Q-0062) | ✅ |
| `bh.path.trust` | Cross-domain / cross-forest trust path | Path contains a `TrustedBy` cross-forest or cross-domain edge | ⬜ | ✅ | ✅ |
| `bh.path.hybrid-identity` | Hybrid identity path | Path target identity has `azure_object_id` set and an Entra-privileged role assignment | ⬜ (correlation in POC; full category MVP) | ✅ | ✅ |
| `bh.path.compensating-control-gap` | Compensating control gap | Path target is not protected by Silverfort policy AND not covered by AD MFA / lockout | ⬜ (correlation chip in POC) | ✅ | ✅ |

### 12.2 Why "first-match" ordering matters

A path might involve both group nesting and ACL abuse. The primary category is the one that **most distinctively describes the attack** — typically the most severe edge family in the chain. The ordering above puts the most distinctive category first.

---

## 13. Risk scoring (deterministic formula)

Per D-0005, the scoring formula is **deterministic**, **documented**, and **reproducible** — given the same evidence and engagement settings, the analyzer always produces the same scores.

### 13.1 Inputs

| Input | Source | Range | Notes |
|---|---|---|---|
| `target_criticality_score` | Tier 0 / crown jewel set | {0, 60, 80, 100} | Tier 0 = 100; crown jewel = 80; privileged but not Tier 0 = 60; otherwise 0 |
| `source_exposure_score` | Source node attributes | 0–100 | Interactive-logon population estimate, contractor flag, service-account flag |
| `path_length_factor` | Path length | 0.4–1.0 | Shorter paths score higher (see 13.2) |
| `max_edge_severity` | Max severity weight on any edge in the path | 1–10 | From §8 |
| `alternative_paths_present` | Count of distinct independent paths between same source-target pair | adjusts ±0–10 | If many independent paths exist, slight risk *decrease* on a single path (the customer has a broader blast surface elsewhere; the single path is not the bottleneck) |
| `silverfort_protection_factor` | SF correlation (target is covered by SF policy) | adjusts −0–15 | If SF covers target, risk drops by up to 15 points (depending on policy strength) |
| `entra_privileged_involvement_factor` | Entra correlation (target identity is hybrid admin) | adjusts +0–15 | If target is a hybrid admin, risk rises by up to 15 points |
| `previous_remediated_state` | Prior assessment for same engagement marked this path closed | adjusts −0–10 | A previously remediated path that re-appears keeps a slightly lower base; the consultant note explains |

### 13.2 Sub-formulas

- `target_criticality_score`:
  - target in Tier 0 → 100
  - target in crown jewel set (and not in Tier 0) → 80
  - target in privileged-but-not-Tier 0 (e.g., privileged group flagged by AD module) → 60
  - else → 0

- `source_exposure_score`:
  - Default = 30 (any standard user account).
  - +20 if source is in "Domain Users" only (broadly exposed).
  - +20 if source is flagged contractor / external by AD module.
  - +10 if source is a service account (often broadly used; AD-PRIV-005 / AD-DELEG-001 territory).
  - −10 if source is itself privileged but not Tier 0 (a privileged-but-confined principal — the attacker still has to reach it).
  - Clamped to 0–100.

- `path_length_factor`:
  - length 1 → 1.00
  - length 2 → 0.95
  - length 3 → 0.85
  - length 4 → 0.75
  - length 5 → 0.65
  - length 6 → 0.55
  - length 7 → 0.45
  - length ≥ 8 → 0.40

- `max_edge_severity`: max of `severity_weight` over edges in the path (§8).

- `alternative_paths_present`:
  - 1 path (this one) → 0
  - 2–3 alternative paths → −2
  - 4–9 alternative paths → −5
  - ≥ 10 alternative paths → −10

  Rationale: many independent paths means the environment is broadly broken; the *individual* path is less special. The correlation breadth surfaces this as a different finding (CORR-BH-AD-001 captures the privileged-account-pattern dimension).

- `silverfort_protection_factor`:
  - SF policy covers target with privileged-MFA enforcement → −15
  - SF policy covers target without privileged-MFA → −8
  - SF policy does not cover target → 0
  - SF data not available (`sf_protected=unknown`) → 0

- `entra_privileged_involvement_factor`:
  - Target identity is Entra hybrid admin with active sign-ins → +15
  - Target identity is Entra hybrid admin (assigned, not necessarily active) → +10
  - Target identity has Entra cloud-privileged role but not synced from this AD identity → +5
  - Else → 0

- `previous_remediated_state`:
  - Same engagement, prior run marked this path `closed` and it now re-appears → −10
  - Else → 0

### 13.3 Final formula

```
raw_risk =
  0.30 * target_criticality_score          (max 30)
+ 0.20 * source_exposure_score             (max 20)
+ 0.15 * (max_edge_severity * 10)          (max 15)
+ 0.10 * (path_length_factor * 100)        (max 10)
+ alternative_paths_present                (min −10, max 0)
+ silverfort_protection_factor             (min −15, max 0)
+ entra_privileged_involvement_factor      (min 0,   max +15)
+ previous_remediated_state                (min −10, max 0)
```

Clamp to `[0, 100]`. Round to nearest integer.

Map to severity:

| risk_score | severity |
|---|---|
| 85–100 | Critical |
| 65–84 | High |
| 45–64 | Medium |
| 25–44 | Low |
| 0–24 | Info |

The mapping is deterministic and shared across all engagements (POC). At MVP the boundaries are configurable per engagement.

### 13.4 Reproducibility

Every input above is derivable from the artifact + the engagement-level settings (Tier 0 overrides, crown-jewel flags, prior runs). No randomness, no model, no time-of-day component. The same artifact + same settings always produce the same `risk_score`.

---

## 14. Finding generation

Every selected path (top 5 in POC, configurable at MVP) becomes one `Finding` using the shared Finding shape from `MODULE_ARCHITECTURE.md` §10.

### 14.1 Finding fields, source by source

| Finding field | Source for a BH path finding |
|---|---|
| `id` | UUID |
| `assessment_run_id` | from current run |
| `title` | template: `"Critical Path: <source.label> → ... → <target.label> (<category title>)"` |
| `category` | the primary category from §12 (e.g., `bh.path.acl-abuse`) |
| `module_id` | `"bloodhound"` |
| `severity` | from §13.3 mapping |
| `risk_score` | from §13.3 |
| `license_status` | defaults to `licensed_enabled` (BH operates on the customer's own AD; no add-on capability required) — see §19 for license-aware correlation hooks |
| `summary_internal` | rendered from the §15 internal template for the path's category |
| `summary_customer` | rendered from the §15 customer template (executive framing) |
| `technical_detail` | full path step list + edge severities + scoring inputs (visible internally; rendered for `customer_full` only) |
| `remediation` | rendered from the §15 remediation template for the path's category |
| `validation_method` | rendered from the §15 retest template |
| `state` | `new` (POC; advances via consultant action) |
| `customer_visibility` | `internal_only` (POC default per `SECURITY_AND_GDPR.md` §9) |
| `evidence_refs` | SharpHound ZIP `Artifact` row + per-step `Evidence` references (kind = users/groups/computers/...) |
| `identity_refs` | each path step's `Identity` (when AD identity is joined) |
| `correlation_refs` | AD finding refs, SF flags, Entra flags (see §16–§18) |
| `payload` | `{path_steps: [...], scoring_inputs: {...}, category_secondary: [...], analyzer_version: "..."}` |
| `created_at`, `updated_at` | timestamps |

### 14.2 Path payload (module-specific data)

The path is **not** stored as a graph in the Finding payload; only the step list:

```jsonc
{
  "path_steps": [
    { "step_index": 0, "node_kind": "User",    "node_id": "<SID>", "node_label": "alice", "edge_kind_to_next": "MemberOf",          "edge_severity_weight": 1 },
    { "step_index": 1, "node_kind": "Group",   "node_id": "<SID>", "node_label": "Contractors", "edge_kind_to_next": "GenericAll", "edge_severity_weight": 10 },
    { "step_index": 2, "node_kind": "Group",   "node_id": "<SID>", "node_label": "Domain Admins", "edge_kind_to_next": null,        "edge_severity_weight": null }
  ],
  "scoring_inputs": {
    "target_criticality_score": 100,
    "source_exposure_score": 50,
    "path_length_factor": 0.95,
    "max_edge_severity": 10,
    "alternative_paths_present_count": 2,
    "alternative_paths_present_adjustment": -2,
    "silverfort_protection_factor": 0,
    "entra_privileged_involvement_factor": 10,
    "previous_remediated_state": 0
  },
  "category_secondary": ["bh.path.privesc.group-nesting"],
  "analyzer_version": "0.1.0"
}
```

### 14.3 Evidence refs

- The SharpHound ZIP `Artifact` is referenced by SHA-256.
- Each path step adds an `EvidenceRef` pointing to the JSON kind that proved the relevant edge (e.g., the `groups.json` evidence for a `MemberOf` edge; the `Aces` block on the relevant object for an ACL edge).
- Per `SECURITY_AND_GDPR.md` §9, raw graph derivations beyond the path step list are **never** included in customer-visible evidence; customer visibility for path findings tops out at `customer_full` for the *step list*, never for raw ACEs.

### 14.4 Business impact (template-based)

Each category has a business-impact paragraph template (see §15). The template substitutes concrete values (path length, source role, target role, edge types) into deterministic sentences. No AI rewriting.

### 14.5 Technical impact (template-based)

Each category has a technical-impact paragraph template detailing the abuse mechanics for the consultant (and for `customer_full`).

### 14.6 AD correlation (§16)

Finding's `correlation_refs` include references to any AD findings on the same Identities (`AD-PRIV-005` privileged service accounts, `AD-DELEG-001` unconstrained delegation, `AD-GPO-*` GPO control issues), produced by the AD module independently.

### 14.7 Silverfort correlation (§17)

Finding payload includes `target_silverfort_protected: true|false|unknown`. If `false` and target is in Tier 0, the analyzer **flags this finding** as a candidate for the cross-module correlation rule `CORR-BH-SF-001` (run by core; see `MODULE_ARCHITECTURE.md` §11).

### 14.8 Entra correlation (§18)

Finding payload includes `target_entra_hybrid_admin: true|false|unknown` and `target_azure_object_id`. If `true`, the analyzer flags candidacy for `CORR-BH-ENTRA-001` (the headline demo correlation; see `MODULE_ARCHITECTURE.md` §11.3).

### 14.9 Recommendation (template per category)

See §15 for one full example. The remediation template substitutes concrete identifiers but renders the same deterministic guidance per category.

### 14.10 Validation method, retest method

Each category has a `validation_method` template (how to confirm the finding is real on the customer's system without running another full BloodHound collection) and a `retest_method` template (how to re-test after remediation — typically "re-collect SharpHound; re-run analyzer; this path must not re-appear").

### 14.11 Consultant review status (POC)

- `state` starts at `new`.
- The consultant moves `new → triaged → published` via the Finding workspace UI (per `MODULE_ARCHITECTURE.md` §10).
- The consultant may edit `summary_customer`, `remediation`, and adjust `customer_visibility` before publishing.
- AI polish (MVP/Full, optional) is gated on `state = triaged` and is presented as a *suggestion*, never an auto-applied edit.

### 14.12 Customer visibility status (POC)

- Default: `internal_only` (per `SECURITY_AND_GDPR.md` §9).
- Consultant may raise to `customer_summary` (executive framing only — no SIDs, no raw nodes) or `customer_full` (full path step list, but still no raw ACEs).
- **Hard rule:** raw graph derivations (ACE rows, full edge dumps) **never** go beyond `customer_summary` regardless of consultant action. Enforced at the report renderer (per `SECURITY_AND_GDPR.md` §17).

---

## 15. Template explanations

This section shows the deterministic explanation templates for the three POC path categories. The templates are filled in by direct substitution against the path payload; no model, no rewriting.

### 15.1 Template structure

Each category has these template fields:

- `title_template` (used for `Finding.title`)
- `summary_internal_template` (used for `Finding.summary_internal`)
- `summary_customer_template` (used for `Finding.summary_customer`)
- `technical_detail_template` (used for `Finding.technical_detail`)
- `remediation_template` (used for `Finding.remediation`)
- `validation_method_template` (used for `Finding.validation_method`)
- `retest_method_template` (used for `Finding.retest_method`, surfaced from `payload`)

### 15.2 Placeholders (deterministic)

| Placeholder | Source |
|---|---|
| `{{source.label}}` | first path step's node label |
| `{{source.kind}}` | first path step's node kind |
| `{{source.role}}` | computed: `contractor` / `service_account` / `standard_user` / `privileged_user` |
| `{{target.label}}` | last path step's node label |
| `{{target.kind}}` | last path step's node kind |
| `{{target.role}}` | `tier_0` / `crown_jewel` / `privileged` |
| `{{path.length}}` | number of edges in the path |
| `{{path.steps_human}}` | human-readable step list (e.g., "alice → Contractors group → has GenericAll on → Domain Admins") |
| `{{path.edge_types}}` | distinct edge type ids in the path |
| `{{path.max_edge_severity_label}}` | `Critical` / `High` / etc. mapped from `max_edge_severity` |
| `{{risk_score}}` | the numeric score |
| `{{severity_label}}` | severity name |
| `{{correlation.ad_findings}}` | list of AD finding ids correlated |
| `{{correlation.silverfort_covered}}` | `true` / `false` / `unknown` |
| `{{correlation.entra_hybrid_admin}}` | `true` / `false` / `unknown` |

### 15.3 Category: Privilege escalation via group nesting (`bh.path.privesc.group-nesting`)

**title_template:**
> "Privilege escalation via group nesting: {{source.label}} → {{target.label}}"

**summary_internal_template (markdown):**
> A {{source.role}} account ({{source.label}}) reaches {{target.role}} ({{target.label}}) in **{{path.length}}** hops, entirely through group memberships. Group nesting is a maintenance-driven path that often grows over years without review.
>
> Steps: {{path.steps_human}}.
>
> Determinism note: this path was selected by deterministic shortest-path (severity-weighted BFS) on the SharpHound CE graph. Score inputs are recorded in the finding payload.

**summary_customer_template (markdown):**
> Through nested group memberships, an everyday {{source.role}} account ends up with the same access as {{target.role}}. This is one of the most common causes of "privileged sprawl" and is usually invisible until an attacker abuses it.

**technical_detail_template (markdown):**
> - Source: `{{source.label}}` ({{source.kind}}, {{source.role}}).
> - Path: {{path.steps_human}}.
> - Edges used: {{path.edge_types}}.
> - Max edge severity: {{path.max_edge_severity_label}}.
> - Risk score: {{risk_score}} ({{severity_label}}).

**remediation_template (markdown):**
> 1. Map every group in the chain and identify the nesting that grants the elevation.
> 2. Remove or re-scope unintended nested memberships (often a non-Tier 0 group has been added to a Tier 0 group years ago).
> 3. Where the membership is legitimate, move the affected accounts to a tightly scoped Tier 0–adjacent group with `AdminSDHolder` protection and a documented review owner.
> 4. Apply Silverfort policy coverage (or equivalent compensating MFA) on the target principal if available.

**validation_method_template:**
> Manually verify the group chain in AD Users and Computers / `Get-ADGroupMember` against the listed steps.

**retest_method_template:**
> Re-collect SharpHound CE; re-run the analyzer; this path must not re-appear in the top 50 ranked paths.

**Rendered example (end-to-end, with concrete values):**

Inputs:
- source: `User`, label `alice`, role `contractor`
- intermediate: `Group` `Contractors` (member of `Domain Admins` via legacy nesting)
- target: `Group`, label `Domain Admins`, role `tier_0`
- path.length: 2
- edges: `MemberOf`, `MemberOf`
- max_edge_severity_label: `Low`
- risk_score: 78 (High) — `target_criticality=100`, `source_exposure=50` (contractor), `path_length_factor=0.95`, `max_edge_severity=1` (MemberOf), correlations push up

Rendered `summary_customer`:
> *"Through nested group memberships, an everyday contractor account ends up with the same access as a Domain Admin. This is one of the most common causes of 'privileged sprawl' and is usually invisible until an attacker abuses it."*

Rendered `remediation`:
> *"1. Map every group in the chain and identify the nesting that grants the elevation. 2. Remove or re-scope unintended nested memberships (often a non-Tier 0 group has been added to a Tier 0 group years ago). 3. Where the membership is legitimate, move the affected accounts to a tightly scoped Tier 0–adjacent group with `AdminSDHolder` protection and a documented review owner. 4. Apply Silverfort policy coverage (or equivalent compensating MFA) on the target principal if available."*

### 15.4 Category: ACL abuse (`bh.path.acl-abuse`) — `GenericAll` on a privileged group

**title_template:**
> "ACL abuse: {{source.label}} can take over {{target.label}}"

**summary_internal_template:**
> A {{source.role}} account ({{source.label}}) holds an abusable ACL right on a Tier 0 object ({{target.label}}). With {{path.edge_types}}, the source can effectively become {{target.role}} without ever being made a member of a privileged group.
>
> Steps: {{path.steps_human}}.

**summary_customer_template:**
> An account that should not have privileged rights has been granted control over a Tier 0 object through an Access Control List entry. This is functionally equivalent to making the account a Domain Admin, but is far less visible.

**technical_detail_template:**
> - Source: `{{source.label}}`.
> - Right(s): {{path.edge_types}}.
> - Target: `{{target.label}}` ({{target.role}}).
> - Risk score: {{risk_score}} ({{severity_label}}).

**remediation_template:**
> 1. Inspect the ACL on `{{target.label}}` and identify the offending Access Control Entry granting {{path.edge_types}} to `{{source.label}}`.
> 2. Remove the ACE unless there is a documented operational reason. If there is, re-scope it (Read instead of Write, narrower right).
> 3. Re-evaluate `AdminSDHolder` coverage and ensure protected accounts inherit the canonical ACL.
> 4. Add the target identity to a Silverfort privileged-MFA policy where applicable to provide a compensating control.

**Rendered example:**

Inputs:
- source: `User`, label `svc-app01` (service account)
- target: `Group`, label `Domain Admins`
- path.length: 1
- edges: `GenericAll`
- max_edge_severity: 10
- risk_score: 92 (Critical)

Rendered `summary_internal`:
> *"A service_account account (svc-app01) holds an abusable ACL right on a Tier 0 object (Domain Admins). With GenericAll, the source can effectively become tier_0 without ever being made a member of a privileged group. Steps: svc-app01 → has GenericAll on → Domain Admins."*

### 15.5 Category: Unconstrained delegation (`bh.path.delegation.unconstrained`) — to a Tier 0 server

**title_template:**
> "Unconstrained delegation: {{target.label}} can replay any user's TGT to any service"

**summary_internal_template:**
> The computer {{target.label}} has unconstrained Kerberos delegation enabled. Any user authenticating to it (interactively or via a service ticket) leaves a forwardable TGT on the host that an attacker with local admin can replay against any service in the forest — including Tier 0.
>
> Reach from {{source.label}}: {{path.steps_human}}.

**summary_customer_template:**
> A server in the environment is configured with a legacy Kerberos feature (unconstrained delegation) that allows it to impersonate anyone who connects to it. This effectively makes the server a Tier 0 asset whether or not it was intended to be one.

**technical_detail_template:**
> - Computer: `{{target.label}}`.
> - Property: `unconstrainedDelegation=true`.
> - Reach: {{path.steps_human}}.
> - Risk score: {{risk_score}} ({{severity_label}}).

**remediation_template:**
> 1. Disable unconstrained delegation on `{{target.label}}` (`TrustedForDelegation=False`) unless explicitly required.
> 2. If delegation is required for a specific service, replace with **constrained delegation** to the minimum set of services, or with **resource-based constrained delegation (RBCD)** managed by the target service.
> 3. Add Tier 0 user accounts to the `Protected Users` group and mark them "Account is sensitive and cannot be delegated".
> 4. Where Silverfort is available, enforce a privileged-MFA policy on the target identities of likely impersonation attempts.

**Rendered example:**

Inputs:
- target: `Computer`, label `WORKSTATION-LEGACY01`, role `tier_0` (because flagged unconstrained-delegation + reachable from a broadly exposed source)
- source: `User`, label `helpdesk-user`, role `standard_user`
- path.length: 3 (helpdesk-user → MemberOf → Helpdesk → AdminTo → WORKSTATION-LEGACY01)

Rendered `summary_customer`:
> *"A server in the environment is configured with a legacy Kerberos feature (unconstrained delegation) that allows it to impersonate anyone who connects to it. This effectively makes the server a Tier 0 asset whether or not it was intended to be one."*

### 15.6 Why templates and not free-form generation

- Reproducibility (same evidence + same engagement → same text).
- Auditability (consultants can review and edit the templates once, not finding-by-finding).
- Privacy (no risk of an LLM verbalizing private SIDs / names beyond what we substituted).
- Defensibility (the customer sees the rule, not "the AI thinks…").

---

## 16. AD correlation

### 16.1 How AD correlation is read

The analyzer **does not import** the AD module (`MODULE_ARCHITECTURE.md` §18). It reads AD's normalized data via the read-only `view` passed by the core's correlation orchestrator (`MODULE_ARCHITECTURE.md` §11.1):

- `view.identities.filter(...)` — canonical `Identity` rows (kind, sid, upn, is_privileged, is_tier0).
- `view.ad.delegation()` — `ad_delegation` rows.
- `view.ad.gpo()` — `ad_gpo` rows.
- `view.findings.filter(module_id="ad")` — AD findings already produced by the AD module.

### 16.2 What the analyzer adds to a BH path finding

Per BH path finding, the analyzer attaches:

- `correlation_refs.ad_findings`: list of AD finding ids that share at least one `Identity` with the BH path's identity_refs.
- For the **headline demo** (per `POC_V1_SCOPE.md` §4 step 8 and `MODULE_ARCHITECTURE.md` §11.3), if the path target is in AD's privileged service account set (`AD-PRIV-005`), the finding is **also** a candidate input to `CORR-BH-AD-001`.

### 16.3 What the analyzer does *not* do

- Does not write to AD's normalized tables.
- Does not call AD's parsers or controls.
- Does not "re-categorize" AD findings based on BH outcomes (that is a core-orchestrated correlation rule, not an analyzer responsibility).

---

## 17. Silverfort correlation

### 17.1 sf_protected flag

For each Tier 0 / crown-jewel target identity, the analyzer reads the SF module's normalized coverage:

- `view.silverfort.covered_identity_ids()` returns the set of Identity ids covered by an active SF policy.
- `target_silverfort_protected` is set on the path payload as `true` / `false` / `unknown` (unknown when no SF evidence present).

### 17.2 Effect on scoring

`silverfort_protection_factor` in §13.1 incorporates SF coverage into the path's `risk_score`. A target protected by an active SF policy with privileged-MFA enforcement scores **lower** — the compensating control reduces real-world risk.

### 17.3 Effect on correlation findings

When `target_silverfort_protected=false` AND the target is Tier 0, the path is a candidate input to the core's `CORR-BH-SF-001` rule (`MODULE_ARCHITECTURE.md` §11.3) — produced by core, not by the analyzer.

---

## 18. Entra correlation

### 18.1 Hybrid admin overlap

For each Tier 0 / crown-jewel target identity, the analyzer reads Entra correlation data:

- `view.identities.filter(azure_object_id__isnot_null)` for hybrid identities.
- `view.entra.role_assignments(identity_id)` for Entra role assignments on the joined cloud identity.

If the target identity has both an `azure_object_id` and any active Entra cloud-privileged role assignment (Global Administrator, Privileged Authentication Administrator, Application Administrator, etc.), `target_entra_hybrid_admin=true` is set on the path payload.

### 18.2 Effect on scoring

`entra_privileged_involvement_factor` in §13.1 raises the path's `risk_score` (the path crosses the on-prem/cloud boundary, expanding blast radius).

### 18.3 Effect on correlation findings

`target_entra_hybrid_admin=true` plus an SF coverage gap is the **headline demo correlation** `CORR-BH-ENTRA-001` — produced by core's orchestrator, with the BH analyzer's path Finding as a contributor.

---

## 19. License-aware correlation

### 19.1 BH path findings are not license-gated

Per `LICENSE_MODEL.md` §10, AD and BloodHound controls are evidence-driven and rarely license-dependent. The BH path finding's `license_status` defaults to **`licensed_enabled`** (the customer's AD is something they own and run).

### 19.2 License-aware *suggestions* on correlated findings

When the analyzer detects that a target identity would benefit from a capability the customer does **not** own — for example, **Defender for Identity lateral movement detection** (`defender-identity.lateral-movement-detection`, only in `m365-e5` / `ems-e5` / standalone `defender-for-identity-standalone`) — this is reflected on the **correlated suggestion**, not on the BH finding itself.

The mechanism:

- The BH finding's `license_status` stays `licensed_enabled`.
- The remediation text suggests *additional* compensating capabilities and tags each suggestion with the corresponding `license_status` for the customer:
  - `licensed_enabled` (the customer has it; turn it on).
  - `licensed_disabled` (the customer has it; it's not configured).
  - `requires_add_on` / `available_in_higher_tier` / `not_licensed` (commercial path).
- This **never** penalizes the customer's Current License Score (per `LICENSE_MODEL.md` §3 and §7).

### 19.3 Why this matters

A customer must not see "you're vulnerable because you don't own E5". They must see "you're vulnerable; here is the fix you can apply today with what you own; here is the additional capability (X) that would harden it further if you choose to invest."

---

## 20. Dashboard (module page composition)

Composed entirely from the components in `UI_DESIGN_DIRECTION.md` — no module-specific components beyond the `PathStepList` micro-component (which is shared, not BH-exclusive, per `UI_DESIGN_DIRECTION.md` §3.5).

### 20.1 BloodHound module page layout (POC)

Per `UI_DESIGN_DIRECTION.md` §4.3 template `M`:

- **`PageHeader`**: "BloodHound" + supporting sentence + secondary actions (Upload SharpHound · Re-analyze).
- **Row 1 — `StatusCard` row** (4 cards):
  1. Tier 0 Reachability (count of distinct Tier 0 nodes reachable from a non-Tier 0 source; status pill: ok / warn / critical).
  2. Privileged Paths (count of paths in `bh.path.privesc.group-nesting` category).
  3. ACL Abuse (count of paths in `bh.path.acl-abuse`).
  4. Delegation (count of paths in `bh.path.delegation.unconstrained` + future delegation categories).
- **Row 2 — `RingChart` + `RankedList`**:
  - Left: `RingChart` showing path category distribution.
  - Right: `RankedList` of the top 5 critical paths (per `UI_DESIGN_DIRECTION.md` §13).
- **Row 3 (optional)**: `RiskBarList` of severity distribution across all enumerated paths.
- **Path detail (drawer)**: opens a `Drawer` containing:
  - Header: "Critical Path #N — `<source.label>` to `<target.label>`", severity badge, risk score.
  - Body: vertical `PathStepList` (one row per node).
  - Side: deterministic explanation (rendered markdown), template id, correlation chips (AD, SF, Entra).
  - Footer: visibility selector, "Generate finding" if not already, link to evidence drawer.

### 20.2 What is *not* in the POC UI

- No free-form graph canvas (per `UI_DESIGN_DIRECTION.md` §13 and Q-0063 — the answer is "MVP").
- No force-directed layout.
- No interactive node-click-to-expand graph.
- No 2D/3D graph rendering.

### 20.3 Reusable components used

Only components from `UI_DESIGN_DIRECTION.md` §3 are used:

- `StatusCard`, `StatusBadge`, `RingChart`, `RankedList`, `PriorityList`, `RiskBarList`, `Drawer`, `Tag`, `Chip`, `PathStepList` (the only module-specific micro-component; shared).

---

## 21. Reporting

Per `MODULE_ARCHITECTURE.md` §13 and `SECURITY_AND_GDPR.md` §9.

### 21.1 Internal Detailed report

For each BH path Finding, the internal report includes:

- Title, severity, risk_score.
- Source, target, path length, path summary, **full step list**.
- Business impact (rendered template).
- Technical impact (rendered template, including edge types and severities).
- Scoring inputs (`scoring_inputs` from §14.2).
- Evidence refs (SharpHound ZIP SHA-256, per-step JSON kind).
- AD correlation references (linked AD findings).
- Silverfort correlation status (`sf_protected` per target).
- Entra correlation status (`entra_hybrid_admin` per target).
- Recommendation, validation, retest.

### 21.2 Customer Summary report

For each BH path Finding **with `customer_visibility ∈ {customer_summary, customer_full}`** (consultant-set, default `internal_only`):

- Executive framing only (rendered from `summary_customer_template`).
- Source/target labels only — **never** raw SIDs, raw UPNs, or ObjectGUIDs.
- High-level category and severity.
- Recommendation (executive language).
- **Never**:
  - The full step list with edge-level detail (suppressed for `customer_summary`).
  - Any raw graph data, ACE detail, or scoring-input drill-down.

For `customer_full`, the path **step list** (node labels only, no SIDs) is included; raw ACE data and scoring inputs remain suppressed.

### 21.3 Raw graph data: never published

Per `SECURITY_AND_GDPR.md` §9, raw graph data — ACE rows, edge dumps, graph snapshots — is **never** included in any customer-facing report, regardless of `customer_visibility`. The report renderer enforces this independently of consultant choice.

---

## 22. Direct parser vs BloodHound CE vs graph database

Three implementation options were evaluated. The POC chooses option A; B and C remain on the table for MVP/Full.

### 22.1 Options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Direct ZIP parser in Python (NetworkX in-memory)** | Parse SharpHound JSON directly; build a graph in NetworkX in process memory; run shortest-path algorithms; persist path summaries only. | No external dependency; deterministic; transparent; testable in unit tests; aligns with synchronous parse-on-upload (D-0004); evidence stays in-process; no graph database to operate. | Memory-bound (large environments need streaming or batching at MVP+); re-builds graph on each analysis; no interactive "ad hoc exploration". |
| **B. Import into BloodHound CE; query via Cypher** | Push the SharpHound ZIP into a BloodHound CE deployment; use its Cypher API for path detection; consume results back into Findings. | Reuses the mature BH path engine (well-known queries); future-proof for AD CS, hybrid, edges added by the community. | New infrastructure (Neo4j + BH CE service); operational footprint; output is Cypher-query-shaped, not deterministic by template (still possible, but adds an abstraction layer); evidence flows into a third party service inside the platform; harder to "redact" for customer reports. |
| **C. Own graph database (Neo4j or memgraph)** | The platform owns a graph database; SharpHound data is normalized into it; we own the schema and the queries. | Full control; clean separation; allows correlation queries across modules to evolve as graph queries; could host more than BH data over time. | Significant operational and code complexity; redundant with BH CE; only justified if we end up wanting interactive customer-side graph features (Full only). |

### 22.2 Trade-off table at a glance

| Criterion | A (direct + NetworkX) | B (BloodHound CE) | C (Own graph DB) |
|---|:---:|:---:|:---:|
| Operational footprint | Lowest | Medium | Highest |
| Determinism transparency | Highest (we own every line) | Medium (BH versions evolve) | Highest |
| Edge type completeness | Manual (we add what we support) | Maximal (community-driven) | Manual |
| Customer-data containment | Highest (data never leaves the analyzer) | Medium (lives inside BH CE process) | Medium |
| Time-to-POC | Lowest | Medium | Highest |
| Path enumeration speed | Sufficient for POC sample data | Faster on large environments | Depends on impl |
| Future MVP extensibility | Good; can adopt B/C later without rewriting Finding shape | Best for path-engine evolution | Best for cross-module graph queries |
| Risk of leaking raw graph to customer | Lowest (we never export it) | Medium (BH UI exists and could be exposed by accident) | Low if firewalled |
| Maps to D-0005 (determinism) | Directly | Yes if we lock BH version + queries | Yes |
| Effort to adopt later | n/a (this is now) | Plannable at MVP | Plannable at Full |

### 22.3 Recommendation

**POC = Option A.** Explicit reasons:

1. Lowest operational footprint — no Neo4j, no BH CE service to deploy on the demo workstation.
2. Smallest blast radius on customer data — no third-party service stores the graph.
3. Highest deterministic transparency — every step is in our code, in our docs, in our tests.
4. Sufficient for the POC dataset (synthetic, A-0012).
5. The Finding shape (and persistence: path summaries, not raw graph) is **identical** regardless of which option backs the analyzer later — so adopting B or C at MVP is additive, not a rewrite.

**MVP:** revisit B if a customer-scale dataset shows that in-memory NetworkX is too slow (R-0010-like signal), and only after BH CE version pinning + query reproducibility tests.

**Full:** consider C **only** if a feature (e.g., customer-side interactive graph exploration, cross-module graph correlation as a first-class capability) actually requires a persistent graph store. Default to A or B otherwise.

---

## 23. Recommended POC approach (Option A explained)

Numbered steps for the POC pipeline. No code; design only.

1. **Upload** — Consultant drops a SharpHound CE ZIP into the evidence drawer for the active assessment run. Core handles upload, validation (size, magic bytes), SHA-256 hashing, and quarantine → addressed storage. Audit entry `evidence.upload` is written.
2. **Parse** — Core dispatches the artifact to `modules/bloodhound/parsers/sharphound_zip.py` (the parser entry point, conceptually). The parser:
   - Validates ZIP structure (§4.4).
   - Streams each JSON file and validates against the per-kind schema (§5.3).
   - Builds in-memory collections of users / groups / computers / OUs / GPOs / containers / domains.
   - Writes one `Evidence` row per kind and a `bh_graph_snapshot` row.
   - Upserts core `Identity` rows for users/computers/service accounts.
3. **Analyze** — A separate analyzer step (still synchronous in POC per D-0004):
   - Builds the NetworkX graph (§6.2).
   - Computes Tier 0 set (§9) and crown-jewel set (§10).
   - Enumerates paths with caps (§11.1, §11.2).
   - Categorizes each path (§12).
   - Computes risk scores (§13).
   - Reads correlation data via core `view` (AD §16, SF §17, Entra §18) and updates path payloads.
   - Selects top 5 (POC) for finding generation.
4. **Emit findings** — For each selected path, write one `Finding` (§14) with state=`new`, visibility=`internal_only`. Audit `finding.create`.
5. **Discard graph** — The in-memory NetworkX graph is dropped. Only the path summaries (`bh_path`, `bh_path_step` rows, Findings) persist.
6. **UI** — The BloodHound module page (§20) reads `bh_path` + Findings and renders the layout. The drawer renders the `PathStepList` and correlation chips.
7. **Consultant review** — Consultant triages, optionally edits `summary_customer` and `customer_visibility`, and publishes.
8. **Report** — Internal Detailed includes path detail; Customer Summary includes only what consultant published (per §21).
9. **Retest** — On a later assessment run, re-upload a fresh SharpHound ZIP. The analyzer re-runs and the new path findings are compared (deterministic). Paths that previously appeared and no longer do are flagged "remediated" in the engagement summary (MVP feature; POC writes the state but does not surface the diff UI).

---

## 24. How to keep UI clean

Restating the constraints already in `UI_DESIGN_DIRECTION.md` so they are unmistakable inside this module's scope:

- **No free-form graph canvas in POC.** The path UI is a vertical `PathStepList`.
- **No force-directed layout.** Path layout is vertical, top-to-bottom, deterministic.
- **No new components.** The BH page uses only components from `UI_DESIGN_DIRECTION.md` §3 (plus the shared `PathStepList` micro-component, defined once and reusable).
- **No bespoke chart types.** Path category distribution is a `RingChart`. Severity distribution is a `RiskBarList`. Top paths are a `RankedList`. Path detail is a `Drawer`.
- **No KPI clutter.** 4 `StatusCard`s on the BH page top — exactly the four named in §20.
- **No automatic graph diffing UI.** Path comparison across runs is a future surface; in POC, prior remediated-state shows up only in the `previous_remediated_state` scoring input.
- **No interactive node selection.** Step-list rows are read-only; the drawer is the interaction unit.
- **PathStepList vertical chain.** One node per row; right-side edge-type label connects to the next row.

If management asks "where is the graph?" — answer: *"MVP. POC favours one clear, defensible answer per path; a graph is helpful for analysts and harmful for executives. We'll evaluate the right canvas style at MVP."*

---

## 25. Risks and open questions

### 25.1 Carried-over open questions (verbatim)

From `OPEN_QUESTIONS.md`:

- **Q-0060 | POC | Kristof + dev** — Confirm SharpHound CE JSON format is the target format. Do we also need to support legacy BloodHound 4.x ZIPs for any current customers? *Why it matters:* parser scope.
- **Q-0061 | POC | Kristof** — How many critical path categories should POC demonstrate at minimum? Current proposal: at least 3 (privilege escalation via group nesting, ACL abuse, unconstrained delegation). *Why it matters:* demo richness vs parser scope.
- **Q-0062 | MVP | Kristof** — Should the analyzer support AD CS (ESC1–ESC8) paths in MVP, or defer? *Why it matters:* significant additional scope.
- **Q-0063 | POC | Kristof** — Should the demo include a **graph visualization** of paths, or only ranked path tables with step-by-step text explanations? *Why it matters:* UI scope.

### 25.2 Module-specific risks

- **R-0004 — BloodHound analyzer drifts to "AI does it".** *Status:* mitigating. *Mitigation:* D-0005 restated in §2, §11, §13, §15 of this document. Algorithms documented. LLM calls absent from the analyzer pipeline. AI polish (MVP/Full) is gated on consultant review and is a separate, optional surface, never in the detection/scoring/correlation/initial-explanation path. *Trigger:* an LLM call appearing in the analyzer's path detection, ranking, scoring, or initial explanation.

- **R-0008 — Cross-module correlation produces false positives.** *Status:* mitigating. *Mitigation:* deterministic identity join (A-0011); ambiguous matches surfaced for consultant review (`platform_core/identity/ambiguity.py`); BH analyzer never silently merges; correlation chip in the path drawer shows the joined identity attributes so the consultant can sanity-check. *Trigger:* a path Finding's correlation chip points at the wrong AD/Entra principal in demo or pilot.

### 25.3 Additional module-specific risks to track (carried into RISKS as needed)

| Risk | Mitigation |
|---|---|
| SharpHound CE schema drift | A-0005; per-kind structural validation; one analyzer version per CE version line; consultant warning on unknown fields beyond a threshold. |
| In-memory graph too large for big environments | POC: synthetic data only. MVP: option B (BH CE) revisit; streamed graph build; per-source caps already in §11.1. |
| Tier 0 default set incorrect for a specific customer (Q-0053) | Per-engagement override (§9.2); audited. |
| Path step list inadvertently leaks SIDs in customer report | Renderer rule in §21.2 strips SIDs and ObjectGUIDs from `customer_summary` and `customer_full`; report generation tests confirm. |
| Path enumeration drifts toward subjective "interesting subgraph" | Algorithm is bounded shortest-path with caps; no heuristic learning; reviewed at architecture review (Cycle 2). |

---

## 26. Complexity control checklist

Per `WORKING_APPROACH.md` §11.

- [x] Tier explicitly tagged (POC / MVP / Full / Not in scope) on every capability (§3 table; per-section `(POC)`/`(MVP)`/`(Full)` tags throughout).
- [x] Belongs to a single module or to core — no overlap (this module owns parsing/graph/analysis; correlation findings are owned by core per `MODULE_ARCHITECTURE.md` §11).
- [x] Reuses existing UI patterns (only `UI_DESIGN_DIRECTION.md` §3 components + shared `PathStepList`).
- [x] Reuses existing Finding shape (`MODULE_ARCHITECTURE.md` §10 verbatim).
- [x] Reuses existing license_status enum (`LICENSE_MODEL.md` §3 verbatim).
- [x] Has a clear demo path (§23 numbered steps; `POC_V1_SCOPE.md` §4 steps 5 + 8).
- [x] Has a clear "what we will NOT do" line (§1.2, §11.4, §22.3, §24).
- [x] Does not require a real connector at this tier (POC).
- [x] Does not duplicate logic from another document (cross-references rather than restating).
- [x] D-0005 unmistakable in §2, §11, §13, §15.

---

*Last updated: 2026-05-15.*
