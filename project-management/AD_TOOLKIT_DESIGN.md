# AD_TOOLKIT_DESIGN.md

> Design specification for the **ACEN AD Assessment Toolkit** — the read-only, offline, manually-executed PowerShell-based evidence collector that produces the `ad-toolkit-zip` artifact consumed by the AD module (see `AD_MODULE_DESIGN.md`).
>
> The toolkit is the *only* sanctioned mechanism by which ACEN gathers raw AD evidence for the platform. Any future automated/agent collector is treated as a distinct workstream and is out of scope here.
>
> Companion documents: `AD_MODULE_DESIGN.md`, `MODULE_ARCHITECTURE.md` §7 (evidence model), `SECURITY_AND_GDPR.md` §7 (evidence handling) and §9 (BloodHound evidence), `POC_V1_SCOPE.md` §5.3, `LICENSE_MODEL.md`, `DECISIONS.md` (D-0011 synthetic data, D-0009 explicit publishing), `ASSUMPTIONS.md` (A-0004 PingCastle canonical, A-0009 manual upload).

---

## 1. Purpose

The AD toolkit is a **self-contained, offline, read-only evidence collector** that an ACEN consultant runs inside a customer's Active Directory environment to produce a single ZIP artifact uploaded to the Gravity platform.

It exists because:

- The Gravity platform itself does **not** reach into customer infrastructure (POC, MVP). All evidence flows in via consultant upload (A-0009).
- AD configuration data spans many sources (LDAP, PowerShell modules, third-party tooling like PingCastle, optional BloodHound). One curated, versioned bundle is far easier to handle than five separate uploads.
- Consultants need a **repeatable, defensible, audit-trail-friendly** collection mechanism — a single command, a known output shape, no automation surprises.

The toolkit is the producer of the `ad-toolkit-zip` evidence type declared in `MODULE_ARCHITECTURE.md` §7.2. Everything the AD module evaluates is derived from this artifact (plus optional PingCastle XML embedded inside it).

### 1.1 Scope per tier

| Tier | Toolkit role |
|---|---|
| **POC** | Document the design only. Synthetic ZIPs authored by the team are used in the demo (D-0011, A-0012). No actual PowerShell collector is shipped or run against a customer. |
| **MVP** | Toolkit is implemented (PowerShell modules + manifest builder), Authenticode-signed, run manually by consultants in customer environments, and packaged in the ACEN delivery process (Q-0051). |
| **Full** | Toolkit additionally supports scheduled re-collection (consultant-initiated, not platform-initiated), version-channel updates, and per-customer pre-configured collection profiles. |

---

## 2. Principles

Non-negotiable, in this order:

1. **Read-only.** The toolkit never writes to AD. No `Set-AD*` cmdlets. No registry writes. No GPO modification. No reset-password operations. No account creation.
2. **Offline.** The toolkit runs in the customer environment and writes a single ZIP to a local path. It does **not** call out to the Gravity platform, ACEN servers, or the internet. Evidence transport is the consultant's responsibility (see §15 Upload flow).
3. **Non-destructive.** The toolkit must never affect AD performance materially (no replication storms, no expensive global searches without paging), and must not lock accounts, change ACLs, or trigger SACL-based alerting beyond what a normal LDAP read does.
4. **No exploitation.** The toolkit never demonstrates a vulnerability (no test pass-the-hash, no Kerberoasting attempt, no DC enumeration via SMB null sessions, no SPN abuse). Detection is a *configuration audit*, not an offensive test.
5. **No password dumping.** No `NTDS.dit` extraction. No DCSync. No DSRM password export. No LSASS interaction. No `secretsdump`. The toolkit reads metadata (e.g., `pwdLastSet`, `LastLogonTimestamp`, `userAccountControl` flags) — never password material.
6. **No automatic remediation.** The toolkit only collects; it never proposes, queues, or executes a remediation. Remediation belongs to the Gravity platform's finding lifecycle and is consultant-driven.
7. **Designed for future signing.** The toolkit is structured so that every shipped script + binary can be Authenticode-signed end-to-end (MVP, Q-0051). POC documents this; signing is implemented at MVP.
8. **Single output.** One run produces one ZIP. No partial uploads, no streaming, no in-flight artifacts. Either the run succeeds and produces a ZIP, or it fails and emits a clear error.
9. **Manifested.** Every output ZIP carries a `manifest.json`, a `collector-version.json`, a `checksums.sha256` file, and a `collection-log.txt`. Anything not described in the manifest is rejected by the Gravity uploader.
10. **Deterministic.** Same environment + same toolkit version + same operator → comparable output. No random ordering of records, no machine-local-timezone surprises (timestamps are ISO-8601 UTC).
11. **Least privilege.** The toolkit runs under a **read-only delegated or administrative** account; see §6 Permissions.
12. **Auditable on both sides.** The toolkit's `collection-log.txt` and `manifest.json` are sufficient to reconstruct *what was collected, when, by whom, from where*, and to match it against the platform-side audit log (see `SECURITY_AND_GDPR.md` §6).

---

## 3. What the toolkit collects

The toolkit emits a known set of files into a single ZIP. Every file is one of:

- **Required** — toolkit fails if it cannot produce this file with valid content.
- **Optional** — toolkit emits a stub with `"status": "not_collected", "reason": "..."` rather than omitting the file.
- **Controlled-optional** — only included when an operator explicitly opts in at run time (see §4 BloodHound handling).

Naming convention: lowercase, hyphen-separated, `.json` or `.xml` or `.txt`. All JSON files are UTF-8, no BOM, two-space indent, sorted keys (for stable hashing).

### 3.1 Required files

| File | Description |
|---|---|
| `manifest.json` | Toolkit-level manifest: module id, toolkit version, customer id (consultant-supplied), engagement label, run id, timestamps, operator label, list of collected files with declared sizes and SHA-256s, BloodHound inclusion flag. Schema in §9. |
| `collector-version.json` | Per-collector versions: a map of collector id → version string. Allows the AD module to evaluate version-specific behaviour. |
| `checksums.sha256` | One line per file in the ZIP (excluding itself): `<sha256>  <relative_path>`. Generated by the toolkit; verified by the platform on upload. |
| `collection-log.txt` | Structured-but-human-readable run log: start time, environment summary, per-collector start/finish/status, warnings, errors. **Must not** contain secrets, full account passwords, NTDS hashes, or session ticket material. See §11. |
| `environment.json` | Run-environment metadata: forest functional level, domain functional level, AD module version, PowerShell version, OS of collection host, collection-host timezone (and confirmation that the toolkit normalized to UTC), whether the host is a DC / member server / workstation. **No machine name, no IP** (or hashed if customer wants traceability — to be confirmed Q-0050). |
| `ad-health.json` | Domain-level health: domain controllers list summary (count, FSMO holders by *role*, not by hostname unless customer opts in), replication health summary, DNS health summary, time-skew summary, AD recycle bin state, tombstone lifetime. |
| `privileged-groups.json` | Membership of well-known privileged groups (`Domain Admins`, `Enterprise Admins`, `Schema Admins`, `Administrators`, `Account Operators`, `Server Operators`, `Print Operators`, `Backup Operators`, `Replicator`, `DnsAdmins` where present, plus custom Tier 0 groups as configured per Q-0053). Members listed by SID + sAMAccountName + objectClass. Nested membership is **flattened** with explicit `direct=true|false` and `nest_path` for traceability. |
| `service-accounts.json` | Candidates: accounts with one or more SPNs, `msDS-ManagedServiceAccount` objects, gMSA (`msDS-GroupManagedServiceAccount`), and "legacy service accounts" heuristically identified (non-personal naming convention, `pwdLastSet` > N days, `dontExpirePassword=true`, etc.). The heuristics are documented in `collection-log.txt`. |
| `kerberos-config.json` | Domain-level Kerberos policy (encryption types allowed, max ticket lifetimes), per-account `msDS-SupportedEncryptionTypes` summary distribution, accounts with `DES_ONLY` or RC4 allowed, `TrustedForDelegation` flag distribution. |
| `delegation.json` | Unconstrained delegation principals, constrained delegation (S4U2Proxy) principals + their `msDS-AllowedToDelegateTo` lists, resource-based constrained delegation entries (`msDS-AllowedToActOnBehalfOfOtherIdentity`), and a derived "delegation risk class" (per `AD_MODULE_DESIGN.md` rubric). |
| `gpo-summary.json` | Per-GPO: id, display name, link scope, enabled/disabled state, WMI filters, presence of common risky settings (anonymous-access, NTLM-allow, weak password policy, restricted-groups membership of Tier 0). **Not** full GPO XML — only the per-policy *summary*. Detailed GPO inspection is a follow-up engagement. |
| `domain-controllers.json` | Per-DC: SID-derived id, FSMO roles held, OS major version, site, replication partner count, last replication success timestamp. **No hostname or IP** unless Q-0050 resolution allows. |
| `dns-health.json` | Forward and reverse zone health summary (presence, dynamic-update mode, scavenging configuration). |
| `replication-health.json` | Aggregated replication-partner success/failure counts; oldest replication-failure age. |

### 3.2 Optional file

| File | Description |
|---|---|
| `pingcastle.xml` | The raw PingCastle XML report (full report, not "healthcheck-light"). **Strongly preferred** for every run (per A-0004 PingCastle is canonical), but the toolkit accepts that PingCastle may not be installed in every environment. If absent, the toolkit emits `pingcastle.xml.missing.json` with the reason. Q-0052 resolves whether PingCastle is mandatory or "if available". |

### 3.3 Controlled-optional file

| File | Description |
|---|---|
| `bloodhound.zip` | A SharpHound CE output ZIP, included **only** when the operator explicitly opts in via a run-time flag (e.g., `-IncludeBloodHound`) **and** provides the path to an already-collected SharpHound output. The toolkit does **not** run SharpHound automatically. See §4. |

### 3.4 Stable file order in the manifest

The `manifest.json` lists files in a fixed canonical order (required first, optional second, controlled-optional last). This keeps consecutive runs diff-friendly and makes the hash chain deterministic.

---

## 4. BloodHound handling

BloodHound (specifically SharpHound CE collection output) is a uniquely sensitive evidence type. SharpHound enumerates the AD attack surface in detail; raw SharpHound output is "internal_only" by default in the platform (see `SECURITY_AND_GDPR.md` §9).

The toolkit's relationship to BloodHound is **controlled, optional, and never automatic**:

| Rule | Detail |
|---|---|
| The toolkit does **not** run SharpHound | No SharpHound binary is bundled. The toolkit does not invoke `SharpHound.exe`, `Invoke-BloodHound`, or any equivalent. |
| The toolkit does **not** download SharpHound | No outbound network call (per §2 principle 2). |
| Operator opts in | A run-time flag (`-IncludeBloodHound <path-to-sharphound-zip>`) is required. Default is *no inclusion*. |
| Pre-existing collection required | The operator must already have a SharpHound ZIP, produced by their normal AD-assessment workflow (consultant-led, audit-trailed in the consultant's own engagement records). |
| Inclusion is a bundle action | The toolkit copies the SharpHound ZIP into the output ZIP under `bloodhound.zip`, hashes it into `checksums.sha256`, and records `bloodhound.included = true` in `manifest.json` with the SharpHound source filename. |
| No content modification | The toolkit does not unpack, re-pack, or alter the SharpHound ZIP in any way. The platform's BloodHound module is the only consumer of the inner content. |
| Platform-side ownership | Parsing of `bloodhound.zip` is performed by the BloodHound module, not the AD module (see `MODULE_ARCHITECTURE.md` §11 / §15). The AD module *consumes* BloodHound findings via correlation only. |
| Visibility default | `bloodhound.included = true` causes the platform to default-tag all derived findings as `internal_only` regardless of category-specific defaults. |

This separation means the AD module remains coherent without BloodHound (toolkit ZIP alone is sufficient), and BloodHound remains a first-class evidence type rather than an AD subcomponent.

---

## 5. What the toolkit must NOT do

Explicit prohibitions (any of which is treated as a defect):

| Prohibited | Reason |
|---|---|
| Modify AD objects (write to any attribute) | Read-only principle. |
| Run as `SYSTEM` or `Local System` | Forces explicit operator identity in the audit chain. |
| Install services, scheduled tasks, agents, or drivers | Toolkit must leave no residue. |
| Persist anything outside the operator-specified output directory | No `%TEMP%` leftovers, no `%APPDATA%` cache. |
| Make outbound network calls (HTTP, HTTPS, DNS exfil, SMB to non-customer hosts) | Offline principle. |
| Connect to external KMS, telemetry, license-check, update-check servers | Offline principle. |
| Run SharpHound, Mimikatz, Rubeus, Kerberoaster, BloodHound CE collector, ADExplorer, or any other third-party binary | No exploitation; controlled BloodHound handling per §4. |
| Read or copy `NTDS.dit`, registry SAM hives, LSASS memory, or any DSRM key material | No password dumping. |
| Attempt to crack, replay, or validate any credential | No exploitation. |
| Resolve user-supplied SIDs against the internet | No third-party telemetry. |
| Embed customer secrets, plaintext passwords, or hashes in any output file | No secret material in the bundle (§11). |
| Auto-update itself | Versioning is controlled at consultant-engagement level. |
| Print or log decrypted session tickets, NTLM challenges, Kerberos AS-REP packets | No raw protocol material. |
| Trigger AV / EDR detections deliberately | The toolkit's signature must be clean and signed (MVP). |
| Mutate the running process token or impersonate other accounts | Runs under the operator's chosen account, no token theft. |
| Open ports, accept inbound connections | Toolkit is single-shot CLI, no service surface. |

---

## 6. Permissions

The toolkit runs **manually** under a deliberate account context.

| Tier | Required account |
|---|---|
| Minimum | A **read-only delegated account** in the customer's AD (members of `Domain Users` plus targeted read delegations on the domain root, on the privileged group containers, and on the GPO container). |
| Pragmatic for consultant engagement | A **Domain Admin or Enterprise Admin** account, *only* because most LDAP attributes the toolkit reads (e.g., FSMO holders, replication health, AD recycle bin state, full Kerberos config) require Domain Admin in default-permissioned environments. Where read-only delegation can be configured ahead of the engagement, that is preferred. |
| Not acceptable | `SYSTEM`, `Local System`, `NetworkService`, or scheduled-task-as-system contexts. |

Operator identity discipline:

- The toolkit reads the current Windows identity at start and writes it as `operator.upn` and `operator.sid` in `manifest.json` and in the first line of `collection-log.txt` (see §11).
- If the operator account is itself a privileged Tier 0 account (which it typically will be), the toolkit warns in the log and recommends that the operator rotate the password and review sign-in logs after the engagement (privileged-account hygiene, §18).
- No credential is ever stored by the toolkit; it inherits the operator's logon session.
- No service install means no service account is created or required.

Q-0050 resolution will lock the recommended account model. POC documents the design only.

---

## 7. Offline model

The toolkit is designed to run in one of three locations, in order of preference:

| Location | Pros | Cons | Recommendation |
|---|---|---|---|
| Customer **management server** (jump box, PAW) | No DC interference; standard AD remoting tooling; matches Tier 0 admin hygiene | Requires Remote Server Administration Tools (RSAT) and the AD PowerShell module installed | **Preferred** for MVP. |
| Customer **domain controller** | Direct LDAP access; no remoting hop; PingCastle / collectors run locally | DC is Tier 0; running tooling on a DC requires extra hygiene; AV/EDR may flag tools | Acceptable where management server is unavailable. |
| Consultant **workstation** (joined to customer domain) | Easy for the consultant; isolates collection from customer servers | Workstation must be domain-joined and reachable to DCs; trust posture variable | Acceptable only when sanctioned by the customer. |

In all three locations:

- The toolkit emits the output ZIP to an operator-specified local path. Nothing is written to a network share by default.
- No outbound calls from the run host (firewall-friendly).
- The toolkit checks at start that the host can reach a DC over LDAP; if not, it fails fast with a clear error.

---

## 8. ZIP structure

A successful toolkit run produces a single ZIP named:

```
acen-ad-toolkit_<customer-short>_<engagement-short>_<UTC-timestamp>.zip
```

Where:

- `<customer-short>` is a consultant-provided slug (lowercase, alphanumeric + hyphen, ≤ 32 chars), used only in the filename. The platform does not trust the filename for identity (see `SECURITY_AND_GDPR.md` §7.1 — storage uses SHA-256).
- `<engagement-short>` is a slug for the engagement.
- `<UTC-timestamp>` is `YYYYMMDDTHHMMSSZ`.

Internal structure (all paths relative to ZIP root, forward slashes):

```
acen-ad-toolkit_<...>.zip
├── manifest.json
├── collector-version.json
├── checksums.sha256
├── collection-log.txt
├── environment.json
├── collectors/
│   ├── ad-health.json
│   ├── privileged-groups.json
│   ├── service-accounts.json
│   ├── kerberos-config.json
│   ├── delegation.json
│   ├── gpo-summary.json
│   ├── domain-controllers.json
│   ├── dns-health.json
│   └── replication-health.json
├── pingcastle/
│   └── pingcastle.xml             (or pingcastle.xml.missing.json)
└── bloodhound/
    └── bloodhound.zip             (controlled-optional; absent by default)
```

Rules:

- **No empty directories.** A directory exists only if it contains files.
- **No symlinks.** Symlinks are rejected by the platform's hardened ZIP extractor (`SECURITY_AND_GDPR.md` §7.2).
- **No absolute paths, no `..` traversal.** Rejected by the platform.
- **Entry count cap.** Toolkit produces ≤ 64 entries (the platform's hardened extractor caps total entries lower than its global cap for `ad-toolkit-zip`).
- **Total uncompressed size cap.** Toolkit aborts if total uncompressed payload would exceed 200 MB (POC platform default; MVP cap configurable). Per-entry cap 50 MB by default. SharpHound ZIPs, when included, count toward both caps.

---

## 9. Manifest schema

`manifest.json` is the platform-side entry point for validation. Schema (JSON Schema-style, abbreviated):

```json
{
  "schema_version": "1",
  "module": "ad",
  "toolkit_version": "1.0.0",
  "customer": {
    "label": "contoso-corp",
    "engagement_label": "q2-2026-identity-review"
  },
  "run": {
    "id": "0e7f1c8a-8b58-4a6f-8e0a-30e9bb1e0a2b",
    "started_at_utc": "2026-05-15T09:21:04Z",
    "finished_at_utc": "2026-05-15T09:34:51Z",
    "duration_seconds": 827,
    "host_role": "management_server"
  },
  "operator": {
    "label": "consultant-001",
    "upn_present": true,
    "sid_present": true,
    "is_privileged": true,
    "hygiene_warning_emitted": true
  },
  "checksums_file": "checksums.sha256",
  "files": [
    { "path": "collectors/ad-health.json",          "sha256": "…", "bytes": 12834, "required": true,  "status": "ok" },
    { "path": "collectors/privileged-groups.json",  "sha256": "…", "bytes": 90212, "required": true,  "status": "ok" },
    { "path": "collectors/service-accounts.json",   "sha256": "…", "bytes": 54211, "required": true,  "status": "ok" },
    { "path": "collectors/kerberos-config.json",    "sha256": "…", "bytes":  6712, "required": true,  "status": "ok" },
    { "path": "collectors/delegation.json",         "sha256": "…", "bytes":  8290, "required": true,  "status": "ok" },
    { "path": "collectors/gpo-summary.json",        "sha256": "…", "bytes": 31102, "required": true,  "status": "ok" },
    { "path": "collectors/domain-controllers.json", "sha256": "…", "bytes":  4001, "required": true,  "status": "ok" },
    { "path": "collectors/dns-health.json",         "sha256": "…", "bytes":  2899, "required": true,  "status": "ok" },
    { "path": "collectors/replication-health.json", "sha256": "…", "bytes":  3502, "required": true,  "status": "ok" },
    { "path": "environment.json",                   "sha256": "…", "bytes":   712, "required": true,  "status": "ok" },
    { "path": "collector-version.json",             "sha256": "…", "bytes":   523, "required": true,  "status": "ok" },
    { "path": "pingcastle/pingcastle.xml",          "sha256": "…", "bytes":2104000, "required": false, "status": "ok" },
    { "path": "bloodhound/bloodhound.zip",          "sha256": "…", "bytes":4521900, "required": false, "status": "ok", "source_filename": "20260515091000_BloodHound.zip" }
  ],
  "bloodhound": {
    "included": true,
    "source_filename": "20260515091000_BloodHound.zip",
    "operator_acknowledged_sensitivity": true
  },
  "pingcastle": {
    "included": true,
    "engine_version": "3.2.0.0"
  },
  "signature": {
    "scheme": "authenticode",
    "present": false,
    "note": "Signing applied at MVP (Q-0051). POC manifests are unsigned."
  },
  "created_at_utc": "2026-05-15T09:34:51Z"
}
```

Validation rules enforced by the platform:

- `schema_version` is a known version (current: `"1"`).
- `module = "ad"`.
- `toolkit_version` matches a semver and is on the platform's accepted version list.
- `run.id` is a UUID.
- `files[]` entries are de-duplicated by `path` and match exactly the files present in the ZIP (no missing, no extra).
- For every `required: true` entry, `status` must be `"ok"`. Otherwise the upload is rejected.
- The sum of declared `bytes` matches the uncompressed sizes of ZIP entries (within a small tolerance for encoding).
- `bloodhound.included = true` requires the presence of `bloodhound/bloodhound.zip`.
- `pingcastle.included = false` requires `pingcastle/pingcastle.xml.missing.json` to be present.

---

## 10. Checksums

Algorithm: **SHA-256**, lowercase hex.

`checksums.sha256` format (one line per file, two spaces between hash and path, matching `sha256sum --check` syntax):

```
3f4a... collectors/ad-health.json
8b21... collectors/privileged-groups.json
…
```

Rules:

- `checksums.sha256` itself is **not** listed inside `checksums.sha256` (cannot self-reference).
- `manifest.json` **is** listed (the manifest's hash anchors the bundle).
- The toolkit computes hashes after all per-collector files are written, then writes `manifest.json` (which embeds the same hashes), then writes `checksums.sha256` last.
- The platform recomputes all hashes on upload and rejects the bundle if any hash mismatches what `manifest.json` claims.
- `checksums.sha256` is informational redundancy; `manifest.json` is the authoritative hash record.

---

## 11. Logs (`collection-log.txt`)

`collection-log.txt` is the single human-readable run trace. It is **append-only during the run** and **finalized at run end**.

### 11.1 Format

Plain text, UTF-8, one event per line, ISO-8601 UTC timestamp prefix:

```
2026-05-15T09:21:04Z [info]    toolkit start version=1.0.0 schema_version=1
2026-05-15T09:21:04Z [info]    operator label=consultant-001 is_privileged=true
2026-05-15T09:21:04Z [warn]    operator account is privileged; password rotation recommended after engagement
2026-05-15T09:21:04Z [info]    host_role=management_server os=Windows Server 2022 pwsh=5.1
2026-05-15T09:21:05Z [info]    collector=ad-health start
2026-05-15T09:21:11Z [info]    collector=ad-health finish status=ok bytes=12834
…
2026-05-15T09:34:50Z [info]    bundle hashing complete
2026-05-15T09:34:51Z [info]    toolkit finish status=ok files=13 zip_bytes=6 942 113
```

### 11.2 What is logged

- Toolkit start/finish with version, schema version, run id.
- Operator label + privileged-flag + hygiene warning.
- Host role and PowerShell / OS version (no machine name unless Q-0050 allows it).
- Per-collector start/finish/status and byte count.
- Warnings (e.g., "PingCastle not installed; emitting pingcastle.xml.missing.json").
- Errors (with a *summary* — never a stack trace containing AD object DNs of every member of Domain Admins).
- Bundle hashing completion.
- BloodHound inclusion acknowledgement (filename, size, operator-confirmed sensitivity flag).

### 11.3 What is NOT logged

Strict prohibitions (any of which is a defect):

- Passwords (plain, hashed, or otherwise). The toolkit never reads password material; logs must not contain any string presented to or by `Set-ADAccountPassword`, `Get-ADUser -Properties pwd*`, etc.
- NTDS hashes, Kerberos keys, NTLM challenges, AS-REP packets, TGT/TGS ticket material.
- Full DN listings of all members of a privileged group (the JSON files carry that; the log carries counts and per-collector summaries only).
- Full email addresses or UPNs of unprivileged users (UPNs of privileged operators are allowed because the operator opted in to identify themselves).
- IP addresses (host or DC) unless Q-0050 allows.
- Customer-confidential strings (engagement code names that should not be in plaintext, etc.).
- Any string captured from session tickets, NTDS dumps, or LSASS.
- Exception stack traces that include LDAP query strings containing PII.

If a collector wants to log an error that would normally include a sensitive substring, it logs the *category* of the error and a `details_redacted=true` flag, and writes the redacted detail (with consultant-only context) into a separate `collectors/<name>.error.json` referenced from the manifest.

### 11.4 Length and integrity

- Log file capped at 2 MB; truncation noted in the final line with `truncated=true`.
- Log is **not signed** in POC; at MVP the toolkit signing process covers the whole bundle (§13).

---

## 12. Versioning

### 12.1 Toolkit version

A single semver applied to the toolkit as a whole: `toolkit_version` in `manifest.json` and `collector-version.json`. Examples: `1.0.0`, `1.1.0`, `1.1.1`.

- **Major** bump: breaking change to ZIP structure or schema (e.g., adding a required file, renaming a JSON path).
- **Minor** bump: additive, backward-compatible (new optional file, new field in an existing file).
- **Patch** bump: bug-fix only; no schema change.

### 12.2 Per-collector version

`collector-version.json` carries a map of each collector → its own semver:

```json
{
  "ad-health": "1.0.0",
  "privileged-groups": "1.1.0",
  "service-accounts": "1.0.2",
  "kerberos-config": "1.0.0",
  "delegation": "1.0.1",
  "gpo-summary": "1.0.0",
  "domain-controllers": "1.0.0",
  "dns-health": "1.0.0",
  "replication-health": "1.0.0"
}
```

This allows the AD module to evaluate version-specific control behaviour (e.g., a new field introduced in `privileged-groups@1.1.0`) without requiring a toolkit major bump.

### 12.3 Platform-side acceptance

The platform maintains an **accepted toolkit version range** (e.g., `>=1.0.0,<2.0.0`). Uploads from out-of-range toolkit versions are rejected with a clear error: "Toolkit version X is older/newer than this platform supports. Update the toolkit." The acceptance range is part of the AD module manifest (see `MODULE_ARCHITECTURE.md` §6).

---

## 13. Future signing (MVP, Q-0051)

POC ships unsigned (`signature.present = false` in `manifest.json`). At MVP, the toolkit is **Authenticode-signed** end-to-end.

### 13.1 What gets signed

| Artifact | Signing at MVP |
|---|---|
| Toolkit launcher (`acen-ad-toolkit.ps1` / `.exe` wrapper) | Authenticode (ACEN code-signing certificate) |
| Each PowerShell collector module (`.psm1`) | Authenticode |
| Toolkit configuration files | Not signed; hashed into manifest |
| Output `manifest.json` | Detached signature `manifest.json.sig` (cms-style or PKCS#7) — Future, Q-0051 |
| Output `checksums.sha256` | Not separately signed; covered by manifest signature |

### 13.2 Code-signing process (Q-0051)

The process to be established (MVP, Q-0051):

- ACEN obtains and operates a code-signing certificate (EV preferred for SmartScreen reputation).
- Build pipeline signs scripts in a controlled environment; signing keys live in a key vault.
- Customers' execution policies (`Set-ExecutionPolicy AllSigned` or `RemoteSigned`) accept the signed toolkit without prompts.
- Every released toolkit version is published with a known SHA-256 on an ACEN-internal signed manifest; customers can verify they received an authentic toolkit.
- Revocation procedure documented.

### 13.3 Why this matters

- Customer execution policies often require signed scripts; an unsigned toolkit blocks adoption.
- Authenticode signing provides tamper evidence between the toolkit author and the operator host.
- Combined with `manifest.json` hashing, it gives a two-layer integrity chain: signer integrity (Authenticode) and content integrity (SHA-256 + future signed manifest).

---

## 14. Validation rules (platform-side)

Performed by `platform_core/lifecycle/upload.py` and `platform_core/evidence/validation.py` (see `MODULE_ARCHITECTURE.md` §7.3 and `SECURITY_AND_GDPR.md` §7.2). Toolkit-specific:

| Check | Action on failure |
|---|---|
| ZIP has valid magic bytes | Reject upload. |
| Hardened ZIP extraction (no traversal, no symlinks, entry/size caps) | Reject upload. |
| `manifest.json` present and parses as JSON | Reject upload. |
| `manifest.json` schema valid (`schema_version`, `module`, required fields) | Reject upload. |
| `module = "ad"` | Reject upload. |
| `toolkit_version` within platform's accepted range | Reject upload with version mismatch message. |
| All `required: true` files in manifest exist in ZIP with matching `sha256` and `bytes` | Reject upload. |
| `checksums.sha256` consistent with `manifest.json` | Reject upload. |
| No file in ZIP missing from manifest | Reject upload. |
| `collection-log.txt` does not contain known sensitive markers (heuristic guard: no `-Password`, no `NTLM:` string, no `aes256-cts-hmac-sha1-96:` etc.) | Mark upload "suspicious"; quarantine for consultant review (MVP). |
| MVP only: Authenticode signature on `manifest.json.sig` valid against ACEN code-signing cert | Reject upload. |
| MVP only: artifact size within the storage-tier configured cap | Reject upload. |

Only when **all** checks pass is the artifact moved from quarantine to addressed storage (`evidence/<sha256[:2]>/<sha256>`), and the AD module's `toolkit_zip.py` parser invoked.

---

## 15. Upload flow

The consultant operates this flow:

1. **Run the toolkit** on a sanctioned host under the chosen operator account.
2. **Transport** the output ZIP off the customer environment via the consultant's standard secure means (encrypted USB, secure file transfer, MDM-managed device). The toolkit itself does not upload anywhere.
3. **Open Gravity** and navigate to the customer → engagement → assessment run.
4. **Upload via the `FileDropzone` component** (see `UI_DESIGN_DIRECTION.md` §3.4) on the AD module page or on the assessment-run page.
5. **Platform validation** runs synchronously in POC (see `MODULE_ARCHITECTURE.md` §3, D-0004). The UI shows a progress indicator only.
6. **Manifest preview** — the upload step renders a server-side preview of the manifest (operator label, toolkit version, BloodHound inclusion flag, file list) **before** the artifact is accepted. The consultant confirms.
7. **Acceptance** — on confirmation, the artifact is moved to addressed storage, a `parse` event is dispatched, and the AD module's `toolkit_zip.py` parser produces `Evidence` rows and updates `Identity` (see `MODULE_ARCHITECTURE.md` §7.1).
8. **Audit log entries** captured: `evidence.upload`, `evidence.parse.start`, `evidence.parse.success` (or `evidence.parse.failure`). See `SECURITY_AND_GDPR.md` §6.

At POC, all of this is on localhost (`SECURITY_AND_GDPR.md` §18). At MVP, the upload is over HTTPS behind auth + CSRF (`SECURITY_AND_GDPR.md` §8).

---

## 16. Security (toolkit run + bundle handling)

### 16.1 During the toolkit run

| Concern | Approach |
|---|---|
| Privileged-account hygiene | Toolkit warns when operator is privileged; the consultant must rotate the operator account password after the engagement per ACEN's internal hygiene rules. |
| Credentials at rest | None. Toolkit reads from the operator's current logon session; no credential file, no Kerberos cache export, no DPAPI material. |
| Output location | Operator-specified local path. Toolkit refuses to write to a network share by default. |
| AV / EDR | Toolkit runs are tagged in the consultant's engagement notes so customer SOC teams can be pre-informed. At MVP, signed binaries reduce false positives. |
| Telemetry | None. The toolkit emits nothing to ACEN servers during the run. |
| Logs on host | Toolkit cleans up no system logs (it didn't create any beyond Windows-native PowerShell logs, which are the customer's record). |

### 16.2 During bundle handling

| Concern | Approach |
|---|---|
| Transport | Consultant's standard secure means; never email of plain ZIP. |
| At rest before upload | Operator handles per ACEN engagement data-handling rules. |
| At rest after upload | Platform stores at `evidence/<sha256[:2]>/<sha256>`; encryption at rest is MVP (see `SECURITY_AND_GDPR.md` §7.3). |
| Access control on platform | POC: role-switcher + UI hide. MVP: server-side authz. (See `SECURITY_AND_GDPR.md` §4.) |
| Customer visibility | All AD-toolkit-derived findings default to `internal_only`; consultant must explicitly publish (D-0009). |
| BloodHound sub-bundle | Marked `sensitivity=high` on platform side (`SECURITY_AND_GDPR.md` §9). Raw graph data never enters customer reports. |

### 16.3 No secrets in the bundle

The toolkit emits no:

- Plain passwords
- Password hashes
- Kerberos keys
- Session tickets
- API tokens
- LSASS-derived material
- Connection strings with credentials
- Any string that would appear in a `secretsdump` or `Mimikatz` output

If a future collector requires reading something that could leak a secret (extremely unlikely for AD configuration data), it must be reviewed and approved by the Security & GDPR review (see `SECURITY_AND_GDPR.md`).

---

## 17. POC / MVP / Full scope table

| Capability | POC | MVP | Full |
|---|:---:|:---:|:---:|
| Documented design (this doc) | ✅ | ✅ | ✅ |
| Synthetic ZIPs author by team (D-0011, A-0012) | ✅ | ⬜ replaced by real runs | ⬜ replaced |
| Real PowerShell collectors implemented | ⬜ | ✅ | ✅ |
| Authenticode signing | ⬜ | ✅ | ✅ |
| Signed `manifest.json.sig` | ⬜ | 🟡 stretch | ✅ |
| Manifest schema v1 | ✅ | ✅ | 🟡 v2 if needed |
| Per-collector versioning | ✅ design | ✅ | ✅ |
| PingCastle XML embedded (Q-0052) | ⬜ design | ✅ when available | ✅ |
| BloodHound controlled-optional inclusion | ✅ design | ✅ | ✅ |
| Hardened ZIP extractor on upload | ✅ design | ✅ implemented | ✅ |
| Manifest preview before acceptance (UI) | ✅ | ✅ | ✅ |
| Toolkit auto-update | ⬜ | ⬜ | 🟡 manual-channel; never auto |
| Per-customer collection profiles | ⬜ | 🟡 basic | ✅ |
| Scheduled re-collection (consultant-initiated) | ⬜ | ⬜ | ✅ |
| Run on management server | ⬜ design | ✅ recommended | ✅ |
| Run on DC | ⬜ design | ✅ acceptable | ✅ acceptable |
| Run on consultant workstation | ⬜ design | ✅ where sanctioned | ✅ |

---

## 18. Open questions (carried verbatim)

These are open questions specific to the AD toolkit. Tracked in `OPEN_QUESTIONS.md` §6. Reproduced here for the design reviewer's convenience.

- **Q-0050 | POC | Kristof** — Confirm the AD toolkit runs **manually** under a delegated read-only privileged account, with no service install and no automation. *Why it matters:* security posture and customer onboarding friction.
- **Q-0051 | MVP | Kristof** — Should the toolkit be **digitally signed** by ACEN, and if so, is a code-signing process in place? *Why it matters:* customer execution policy.
- **Q-0052 | POC | Kristof** — PingCastle: do we always require a PingCastle run as part of evidence, or only "if available"? *Why it matters:* completeness of AD controls.
- **Q-0053 | POC | Kristof** — Tier 0 boundary: do we follow Microsoft's Enterprise Access Model definition strictly, or accept a customer-specified Tier 0 list per engagement? *Why it matters:* control results and BloodHound target set.

---

## 19. Risks (toolkit-specific)

Tracked in `RISKS.md`. Toolkit-specific concerns:

| Risk | Mitigation |
|---|---|
| AV/EDR flags the toolkit and blocks the run | MVP: Authenticode signing + EV cert; pre-engagement coordination with customer SOC. |
| Operator runs the toolkit under `SYSTEM` accidentally (e.g., via scheduled task) | Toolkit refuses to run as `SYSTEM` / `LocalSystem`; emits a clear error. |
| Operator forgets to rotate the privileged account password after the engagement | Toolkit log emits a `[warn]` line; consultant engagement checklist enforces rotation. |
| BloodHound ZIP included by mistake | `bloodhound.included` requires explicit flag + operator confirmation prompt; platform-side `internal_only` default for all derived findings. |
| Toolkit version drift causes parser confusion | Platform-side `toolkit_version` acceptance range; clear error on mismatch. |
| PingCastle version drift causes inconsistent XML parsing | `pingcastle.engine_version` recorded in manifest; AD module logs unsupported PingCastle version and downgrades affected controls to `unknown`. |
| ZIP exceeds platform caps (very large customer) | Toolkit aborts with clear error; consultant collects in scoped passes or asks platform admin to raise the cap. |
| Operator's machine writes the ZIP to OneDrive sync folder | Documented as a hygiene risk in consultant runbook; not enforceable by the toolkit. |
| Toolkit network calls leak through a future dependency update | Build-time policy: no outbound calls; CI test asserts absence of `Invoke-WebRequest`, `Invoke-RestMethod`, `New-Object Net.WebClient` in any shipped script. |
| Future collector inadvertently captures secret material | Code review gate + automated lint pattern for known sensitive cmdlets; sample-data redaction tests at MVP. |

---

*Last updated: 2026-05-15. Phase: Module deep dive #1 (Stage 3, Cycle 3).*
