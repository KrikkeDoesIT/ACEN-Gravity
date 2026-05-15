# Contoso Corp — synthetic demo dataset (POC V1)

Fictional company used to demonstrate the vertical slice and the full POC V1
demo journey. **No real customer data** — D-0011 / A-0012.

## Headline attack path (what the BloodHound analyzer should surface)

```
contractor.john          (regular contractor user)
   └─ MemberOf  →  Helpdesk            (regular group)
                       └─ GenericAll →  svc-backup          (privileged service account)
                                            └─ MemberOf  →  Domain Admins         (TIER 0)
```

Three edges, four nodes. Demonstrates **ACL abuse** (Helpdesk → svc-backup),
**group nesting** to Tier 0, and **service-account exposure** simultaneously
— three of the most common attack patterns ACEN consultants surface in real
AD security reviews.

The deterministic shortest path detector should find this path; the Finding
generator should produce one Critical-severity finding with the template
`bh-acl-abuse-via-service-account-to-tier0`.

## Identities

| sAMAccountName | Kind | Privileged | Tier 0 | Notes |
|---|---|:---:|:---:|---|
| contractor.john | user | ⛔ | ⛔ | Source of the headline attack path |
| regular.user.alice | user | ⛔ | ⛔ | Regular user, not involved |
| helpdesk.bob | user | ⛔ | ⛔ | Member of Helpdesk |
| it.admin.kristof | user | ✅ | ✅ | Domain Admin |
| svc-backup | user (service account) | ✅ | ✅ | Domain Admin, **on the path** |
| Helpdesk | group | ⛔ | ⛔ | Has GenericAll on `svc-backup` (the gap) |
| Domain Admins | group (well-known RID 512) | ✅ | ✅ | Tier 0 |
| Enterprise Admins | group (RID 519) | ✅ | ✅ | Tier 0 |
| Domain Controllers | group (RID 516) | ✅ | ✅ | Tier 0 |
| DC01 | computer | ✅ | ✅ | Domain Controller |
| Workstation01 | computer | ⛔ | ⛔ | Regular workstation |

Domain SID base: `S-1-5-21-1234567890-1234567890-1234567890`.

## Files

```
contoso/
├── README.md              (this file)
├── customer.json          metadata: name / slug / engagement / run
├── ad/
│   ├── manifest.json      AD toolkit manifest (per AD_TOOLKIT_DESIGN.md)
│   └── privileged-groups.json
└── sharphound/
    ├── users.json         SharpHound CE format (meta.version = 6)
    ├── groups.json        ↳ with `Members` list (group → user/group)
    ├── computers.json
    └── domains.json       SharpHound domain object
```

## Loading the fixture

```
gravity demo load
```

Idempotent — clears the existing Contoso Corp data and reloads. Implemented
in `src/platform_core/cli.py`.
