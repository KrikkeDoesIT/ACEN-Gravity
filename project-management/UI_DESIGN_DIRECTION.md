# UI_DESIGN_DIRECTION.md

> Design language and **reusable component library** for ACEN Gravity. Built so every module reuses the same atoms and the platform feels calm, executive, and on-brand — while each module's body is free to reflect what it is fundamentally about (paths for BloodHound, coverage for Silverfort, posture for AD, license-aware tenant config for Entra).
>
> This document is **component-led** by design (per Kristof's direction): we define a shared component library first, then compose **module-specific page archetypes** from it. New components are allowed when a pattern earns its place in the library.
>
> Companion: `VISUAL_REFERENCES.md` (HTB, Fortify360, Runtime), ACEN 2025 brand guide (OneDrive), `PRODUCT_DESIGN.md` §27, `MODULE_ARCHITECTURE.md`.

---

## 1. Design goal

> **One coherent, calm, executive-grade workspace where the *frame* and the *atoms* are identical across modules, but each module's *body* reflects what it actually shows.**

The shell, header, side nav, finding drawer, publish modal, evidence drawer, status badges, and primary atoms are the same on every screen — that is what makes the platform feel like one product, not four dashboards (R-0002).

What is *not* the same is the **page body composition**: paths-led for BloodHound, coverage-led for Silverfort, posture-led for AD, license-aware-led for Entra. Forcing identical bodies would lose important domain affordances; we explicitly **do not** do that.

### The two layers

| Layer | Identical across modules? | Examples |
|---|---|---|
| **Frame** (shell, nav, header, breadcrumb, drawer/modal, finding detail, evidence drawer, publish flow, audit log) | ✅ identical | `AppShell`, `AppHeader`, `SideNav`, `Drawer`, `Modal`, finding-detail content, publish modal |
| **Atoms** (button, input, card, status badge, chip, ring, KPI, priority row, table row, divider) | ✅ identical | every component in §3 |
| **Module-specific compositions** (page-body archetypes) | ⛔ deliberately different | "Posture" (AD), "Attack-path" (BH), "Coverage" (SF), "License-aware tenant config" (Entra) — see §4.3 |
| **Module-specific named components** (built from atoms, owned by a module, registered in the library) | ⛔ different but **shared library** | `PathStepList` (BH), `CoverageMatrix` (SF), `LicenseBadge` (Entra) |

### The rule

> **Same atoms. Same frame. Module-specific compositions. New components are allowed when a pattern repeats or matters enough — they enter the shared library so future modules can reuse them.**

---

## 2. ACEN brand translation

### 2.1 Palette → tokens

Tokens are the single source of truth. Components reference tokens, never raw hex.

| Token | Hex | ACEN name | Use |
|---|---|---|---|
| `--brand-jakarta` | `#201e5c` | Jakarta | Brand deep blue (active nav, dark surfaces) |
| `--brand-bunting` | `#1b1b4c` | Bunting | Cards on dark |
| `--brand-minsk` | `#2d2d72` | Minsk | Subtle dividers, hover, badge bg |
| `--brand-gulf` | `#000162` | Gulf | Brand logo accent (sparing) |
| `--brand-gallery` | `#eaeaea` | Gallery | Light surfaces, text on dark |
| `--brand-mercury` | `#e0e0e0` | Mercury | Borders on light, muted bg |
| `--brand-white` | `#ffffff` | White | Text on dark, light surface |
| `--brand-trinidad` | `#fd5400` | Trinidad | **Reserved for critical states and the primary CTA** — see §2.4 |
| `--brand-turquoise` | `#50bfa0` | Turquoise | Positive / "ok" / secondary accent |
| `--brand-dorado` | `#595959` | Dorado | Body text on light; muted text on dark surfaces |

#### Neutral shade scale (D-0023)

UI **chrome** (surfaces, cards, dividers) uses a neutral shade scale, **not** brand-blue. Brand blues are reserved for **brand moments** (logo lockup, login splash, occasional chart series). This keeps the platform calm and makes brand colour meaningful where it appears.

| Token | Hex | Use |
|---|---|---|
| `shade-950` | `#08080d` | Deepest backdrop |
| `shade-900` | `#0e0e15` | App background base |
| `shade-850` | `#13131c` | App background top |
| `shade-800` | `#1a1a23` | Card surface (`surface-1`) |
| `shade-750` | `#22222e` | Hover / active / drawer (`surface-2`) |
| `shade-700` | `#2a2a36` | Dividers / sub-surfaces (`surface-3`) |
| `shade-600` | `#363645` | Stronger borders |
| `shade-500` | `#4a4a5c` | Muted text on dark |

Derived tokens used by components:

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0a12` (neutral dark, slight blue tint) | App background (dark theme baseline) |
| `--bg-soft` | `#13131c` | App background top of vertical gradient |
| `--surface-1` | `shade-800` `#1a1a23` | Card |
| `--surface-2` | `shade-750` `#22222e` | Active nav / hovered card |
| `--surface-3` | `shade-700` `#2a2a36` | Dividers, sub-surfaces |
| `--text` | `--brand-white` | Primary text on dark |
| `--text-muted` | `--brand-gallery` | Secondary text |
| `--text-subtle` | `rgba(234,234,234,0.6)` | Tertiary text on dark |
| `--border` | `rgba(255,255,255,0.07)` | Card borders, dividers |

**Brand moments** (where brand-blue is the right choice):
- Brand mark / logo (`brand-gulf` base, with `brand-turquoise` / `support-violet` mix-blend overlay).
- Login left splash pane: `from-brand-bunting via-brand-jakarta to-brand-gulf` gradient — the platform's identity surface.
- Optional chart series colour when "ACEN" itself is being charted.
- "ACEN" wordmark in the header / login.

**Rule:** if a brand-blue is in chrome (header bg, side nav bg, card bg, modal bg, drawer bg, page bg), the chrome has slipped off-spec and should be reverted to a `shade-*` token. D-0023.
| `--accent` | `--brand-turquoise` | **Default primary action** (calmer than Trinidad) |
| `--accent-critical` | `--brand-trinidad` | **Critical states + destructive actions** only |
| `--status-ok` | `--brand-turquoise` | OK badges |
| `--status-warn` | `#f6a623` (derived ACEN amber) | Warning badges (open question Q-0111-related) |
| `--status-critical` | `--brand-trinidad` | Critical badges |
| `--status-neutral` | `--brand-mercury` | Pending / unknown badges |

#### Supporting palette (added 2026-05-15, per D-0021)

The brand palette is deep-blue dominant with two accents. That is enough for the *frame* but not for module identity, data visualization, or nuanced status. We introduce a **supporting palette** alongside the brand tokens. Brand tokens remain the anchor; supporting tokens are used **only in defined roles** so the platform does not slide into rainbow.

| Token | Hex | Role | Allowed uses |
|---|---|---|---|
| `--support-indigo` | `#6366f1` | Data viz primary; "info" state | Chart series 1; info badges; chart axes accent |
| `--support-violet` | `#a78bfa` | Module category — Silverfort; chart series 2 | SF nav icon dot, SF page accent stripe; second chart series |
| `--support-sky` | `#38bdf8` | Module category — Entra; chart series 3 | Entra nav icon dot, Entra page accent stripe; third chart series |
| `--support-rose` | `#fb7185` | Module category — BloodHound; "high" severity tint | BH nav icon dot, BH page accent stripe; high (not critical) severity dots |
| `--support-amber` | `#f59e0b` | `--status-warn` formalized | Warning badges, "action required" states |
| `--support-slate` | `#64748b` | Muted neutrals on dark | Disabled controls, table dividers, captions |

**Module category colour map**

| Module | Category colour | Token |
|---|---|---|
| Active Directory | brand Turquoise (foundational; uses the brand colour) | `--brand-turquoise` |
| BloodHound | Rose | `--support-rose` |
| Silverfort | Violet | `--support-violet` |
| Entra | Sky | `--support-sky` |

> AD uses the brand Turquoise as its category colour deliberately — AD is the platform's foundational module, and the brand colour signals that. The other three modules get supporting colours so the four are visually distinct in the side-nav, on the overview, and in the report.

**Chart series order** (deterministic across all charts): Turquoise → Indigo → Violet → Sky → Rose → Amber → Slate. Never rainbow; never more than 4 series in a chart per `UI_DESIGN_DIRECTION.md` §2.6 (charts).

**Strict rules**

- **Trinidad and Turquoise remain the brand anchors.** Trinidad = critical/destructive only (§2.4). Turquoise = default primary action + AD module + "ok" status.
- Supporting tokens **never** replace brand tokens in chrome (nav, header, page background, primary buttons).
- A surface using a supporting token (e.g., the SF page accent stripe) is **always paired** with brand chrome so the page still reads as ACEN.
- New supporting tokens require an architecture/UX review entry in `REVIEW_NOTES.md` — we do not extend the palette by accident.

### 2.2 Typography

| Role | Font | Weight | Size | Use |
|---|---|---|---|---|
| Display | Montserrat | 700 | 32–40 px | Page title (H1) |
| Heading L | Montserrat | 700 | 24 px | Card title |
| Heading M | Montserrat | 600 | 18 px | Section title |
| Heading S (uppercase) | Montserrat | 700 (uppercase, tracked) | 12 px | Side-nav group label |
| Body | Montserrat | 500 | 14 px | Body |
| Body Small | Montserrat | 500 | 12 px | Meta, captions |
| Mono | (none in POC — use system mono) | 500 | 12 px | Identifiers, hashes, evidence IDs |
| Aptos fallback | Aptos | matching weights | — | Fallback per brand guide |

### 2.3 Spacing and radius

- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px.
- Border-radius (D-0022, amends D-0010):
  - **Brand-strict frames** (logo lockup, brand-mark geometry, decorative shapes): **0 px** (square, per ACEN brand).
  - **Small elements** (badges, status pills, severity dots, tooltips, table cells): **`rounded-xs` = 2 px**.
  - **Interactive controls** (button, input, select, chip, segmented control): **`rounded-control` = 6 px**.
  - **Cards / drawers / modals / hero containers / action panels**: **`rounded-card` = 10 px**.
  - **Rings (donut / ring charts):** circle.
- Pending brand-owner confirmation at Cycle 4 review (Q-0110 extended).

### 2.4 Trinidad orange — restraint

ACEN's Trinidad is bold. Used everywhere it becomes the brand and undermines criticality.

**Rule:** Trinidad is the colour of *attention*. Reserve it for:
- Critical severity badges and severity icons.
- Destructive actions (delete, purge).
- One "key action" CTA per page (e.g., "Generate Report" on the Reports page).

For default primary actions on every other page (Save, Apply, Confirm), use `--accent` (Turquoise). This keeps pages calm and makes Trinidad meaningful when it appears.

(Q-0111 captures this; final sign-off at UX review.)

### 2.5 Iconography

- Outlined icons (line icons), 1.5 stroke.
- Icons sit inside a filled circle for emphasis (per ACEN brand): circle bg = `--surface-3`, icon stroke = `--text-muted` (default), `--accent-critical` for critical contexts.
- Icon set baseline: Phosphor-icons (open licence) or Lucide; final choice in implementation.

### 2.6 Charts

- Line / area: 1.5 px stroke; subtle area fill at 12% opacity.
- Ring / donut: stroke-based; gap between segments for visual clarity.
- Bar: horizontal bars for risk lists (per Reference C); minimal axis ornament.
- Colour usage: single brand colour per chart by default; multi-series uses Turquoise → Minsk → Trinidad in that order; never rainbow.

---

## 3. Component library (reusable)

Every component is implemented as a Jinja partial under `platform_core/web/components/` and uses Tailwind utility classes referencing the tokens above. Each component has documented props, states, and accessibility notes.

> **Why "components" in HTMX/Jinja?** Components are server-rendered partials with explicit props (template variables). They can be composed into pages and into HTMX swap fragments. Alpine.js is used for tiny stateful behaviour (drawer open/close, modal). Tailwind keeps styling consistent.

### 3.1 Layout components

#### `AppShell`
- The page skeleton: `AppHeader` + `SideNav` + main content area + optional `RightRail`.
- Slots: `header_actions`, `body`, `right_rail`.

#### `AppHeader`
- Left: ACEN logomark + product wordmark "Gravity".
- Centre: customer / engagement / assessment-run breadcrumb-pickers (each opens a small popover list).
- Right: search (`⌘K`/`Ctrl+K`), notification bell, settings, role badge + avatar.
- Heights: 56 px.
- States: default · scrolled (sticky, subtle bottom border).

#### `SideNav`
- Vertical. Width: 240 px (collapsible to 64 px icon-only at < 1280 px viewport).
- Groups (uppercase 12 px labels) — see Reference B.
- Items: icon + label + optional count badge.
- Active state: `--surface-2` filled pill (`SideNavItem[state=active]`); hover: same fill at 50% opacity.

```
NAVIGATE                      ← group label, uppercase
  ▣ Overview                  ← active (Jakarta pill)
  AD
  BloodHound
  Silverfort
  Entra
WORK
  Findings  (12)
  Reports
  Audit
```

For the Customer Executive role, the side-nav collapses to a compressed set: `Overview · Findings · Reports`.

#### `PageHeader`
- H1 (Display).
- Supporting sentence (Body, muted).
- Right-aligned action slot (secondary outlined + primary filled).
- Optional breadcrumb above title.

#### `RightRail` (optional)
- 320 px column on the right; collapses below 1440 px.
- Hosts `ActionPanel` (e.g., Report Generator).

### 3.2 Surfaces

#### `Card`
- `--surface-1` background.
- 1 px border `--border`.
- 16 px padding (compact: 12 px; spacious: 24 px).
- Slots: `title`, `actions` (top-right), `body`, `footer`.
- Variants: `default` · `outlined` · `elevated` (subtle inner glow at edges — used only on hero containers per Reference C — but **without** the gamer-glow).

#### `HeroCard`
- Single instructional/empty-state card.
- H2 + body + optional small CTA.
- Used for: empty assessment runs, "no evidence uploaded yet", post-publish confirmation.

#### `Drawer`
- Slide-in from right (default) or bottom.
- Width: 480 px on desktop; full-width on mobile.
- Header: title + close button.
- Body: scrollable.
- Footer: actions.
- Closes via X, backdrop click, or `Esc`.
- Used by: Finding detail, Evidence drawer, Audit detail.

#### `Modal`
- Centered, 520 px wide.
- Used sparingly: Publish confirm, Delete confirm, Role switch.

### 3.3 Data display

#### `StatusBadge`
Pill shape, 6×10 padding, uppercase label or sentence-case label.

Variants:

| Variant | Token | Used for |
|---|---|---|
| `ok` | `--status-ok` | Compliant, Passing, Up-to-date |
| `warn` | `--status-warn` | Action Required, Partial, Misconfigured |
| `critical` | `--status-critical` | At Risk, Fail, Critical Finding |
| `pending` | `--status-neutral` | Pending Scan, Awaiting Evidence |
| `info` | `--surface-3` | Neutral states (e.g., "Licensed but not enabled") |
| `licensed` | `--accent` (Turquoise) outlined | License-aware badge `licensed_enabled` |
| `not-licensed` | `--surface-3` outlined dashed | License-aware badge `not_licensed` |
| `manual-review` | `--status-warn` outlined | Manual review required |

License-aware variants follow the 8-value enum exactly so every screen reads the same language.

#### `Tag` / `Chip`
- Small label with optional dot.
- Removable variant (with × icon) for filters.
- Tone variants match `StatusBadge`.

#### `ChipGroup` / `SegmentedControl`
- Single-select group (HTML / PDF). 32 px height; rounded 2 px.

#### `KpiCard`
- Large number (Display) + sublabel (Body small) + optional sparkline below.
- Compact (2-up): no chart.
- Wide: with chart.
- Used on Overview and module dashboards.

#### `StatusCard`
Composition (Reference B pattern): `IconCircle` + `StatusBadge` (top-right) + title + meta line + horizontal progress + right-aligned percent.

```
┌──────────────────────────────────────────────┐
│  [●]                 [ACTION REQUIRED]       │
│                                              │
│  Conditional Access                          │
│  Last sync: 10m ago                          │
│  ────────────────────────────       78%      │
└──────────────────────────────────────────────┘
```

Used on module overviews (e.g., AD has 5 of these: Health, Privileged, Kerberos, Delegation, GPO).

#### `RingChart`
- Donut chart with centred large number + sublabel.
- Stroke width: 12 px.
- Variants: `single` (one segment + remainder) · `multi` (≤ 4 segments).
- Used in: Module overview (control coverage), Overview dashboard (score breakdown).

#### `RingRow`
- Composition of 3 `RingChart` side-by-side (Reference C pattern — Published/Discovered/Shadow). Used on the BloodHound page: *Paths Detected / Paths Closed / Paths Open* equivalent.

#### `LineChart`
- Multi-series, ≤ 4 series, legend below.
- POC: used sparingly. Demo doesn't depend on time series; one line chart on Overview shows score progression across assessment runs (only if ≥ 2 runs exist).

#### `RiskBarList`
- Horizontal bars: severity colour + label + count.
- Used on: Overview "Severity distribution"; module pages secondary card.

#### `PriorityList` / `PriorityListItem`
- Plain rows (Reference B pattern). Each row:
  - Severity icon (12 px circle with severity colour).
  - Title.
  - Subtitle (small muted): e.g., `AD-PRIV-005 · 3 accounts affected · Licensed but disabled`.
  - Optional right-aligned meta (severity badge or risk score).
- No card-per-row. Dividers between rows.

#### `RankedList`
- Numbered list with avatar/icon + label + meta (Reference A pattern). Reused for "Top customers by risk", "Top findings by risk score".

#### `Table`
- Used for dense data only (e.g., Audit log, Evidence list).
- Sticky header. Sortable columns. Striped rows on hover. No row-card duplication.

### 3.4 Inputs

#### `Button`
Variants:
- `primary` — Turquoise fill, white text. Default primary action.
- `critical` — Trinidad fill, white text. Destructive / "key action" only.
- `secondary` — transparent bg, 1 px Turquoise border, Turquoise text.
- `ghost` — transparent, muted text on hover.
- Sizes: sm (28 px), md (36 px), lg (44 px).
- Loading state with spinner.
- Icon-only variant for header actions.

#### `Input`, `Select`, `Textarea`
- Dark surface (`--surface-1`).
- 1 px border `--border`; focus: 1 px `--accent`.
- 2 px radius (D-0010).

#### `SearchInput`
- Inline magnifying-glass icon left; `⌘K` keyboard hint right.

#### `FileDropzone`
- Drag-and-drop + click-to-upload.
- Shows expected file types and max size.
- Progress bar during validation.
- After upload: status badge + filename + hash (short).

#### `Tabs`
- Used inside Drawers and Module pages (sparingly).
- 1 row only; do not stack tabs.

#### `Toolbar`
- Filter chip set + search + sort dropdown for list pages (Findings workspace).

### 3.5 Module-specific compositions and components

Module pages are **not** forced into an identical body. They share the **frame** (shell, nav, header, drawer, modal, finding-detail, evidence drawer, publish flow) and the **atoms** above, then compose a body that reflects what each module is fundamentally about.

#### Module-specific touches at the page level
- Module icon (side-nav + module page header).
- Module-specific data inside generic atoms (e.g., BloodHound `PriorityList` row shows path category + length + risk score; Silverfort `PriorityList` row shows coverage gap + affected count).
- A **page archetype** per module — see §4.3 for the four POC archetypes.

#### Module-specific named components (in the shared library)

When a pattern recurs inside a module or matters enough domain-wise, it gets its own named component, **registered in the shared library** so future modules can adopt it. These are first-class components, not one-off snippets.

| Component | Owner | Purpose | Used on |
|---|---|---|---|
| `PathStepList` | BloodHound | Vertical chain of identity → edge-type → identity → ... with severity colour per edge. Replaces a free-form graph canvas in POC. | BH module page + Finding drawer for BH findings |
| `CoverageMatrix` | Silverfort | Grid view: rows = covered targets (privileged groups, Tier 0 assets, service accounts), columns = policies, cells = covered / excluded / gap (with hover detail). | SF module page; reusable by future modules with policy-to-target coverage patterns (e.g., Defender XDR coverage). |
| `LicenseBadge` | Entra (+ Silverfort) | Compact badge variant of `StatusBadge` that surfaces all 8 license_status values consistently, with a tooltip explaining the SKU/capability gap. | Anywhere a control or finding carries a license status (Entra page, SF page, Finding drawer, Reports). |
| `CapabilityTooltip` | Entra | The tooltip body invoked from `LicenseBadge`. Explains *which* SKU is required and *why* it does not affect the Current License Score. | Triggered by `LicenseBadge`. |

**Rule for promoting a one-off into a named component:** if the same pattern appears in a second module *or* is on the demo journey, it gets named, documented in this section, and added to the component-library deliverable (§20). One-off micro-bits stay inside `modules/<module>/ui/` and do not graduate.

### 3.6 Action panels

#### `ActionPanel`
Right-rail action surface (Reference B "Report Generator"). Heading + form fields (`Select`, `ChipGroup`, checkboxes) + primary CTA at the bottom.

Used on:
- Reports page (report type, format, options).
- Publishing modal (visibility scope, consultant note).
- Audit filter rail.

---

## 4. Page templates (composed)

Five page templates carry the platform. Module pages reuse template `M`.

### 4.1 `L` — Login (POC only)
- `AppShell` minimal (no SideNav).
- HeroCard with role-switcher + customer dropdown + Continue button.
- POC banner: "POC build — synthetic data only — not for customer use."

### 4.2 `O` — Overview dashboard
- `PageHeader`: customer name + supporting sentence.
- Row 1: two `KpiCard` (Current License Score, Target Posture Score) + one `KpiCard` (Opportunity gap).
- Row 2: 4 `StatusCard` (one per module: AD, BloodHound, Silverfort, Entra).
- Row 3: `RingChart` (control coverage) + `PriorityList` (Top findings) + `RiskBarList` (severity distribution).
- Right rail: optional `ActionPanel` (Quick actions: Upload evidence, Generate report).

### 4.3 Module page archetypes

Each module gets a **page archetype** that fits its domain. All archetypes use the same `AppShell`, `AppHeader`, `SideNav`, `PageHeader`, `Drawer`, `Modal`, `Toolbar`, and `Finding detail drawer`. What differs is the **body composition** — and that is deliberate.

The four POC archetypes:

| Module | Archetype | Body is led by | Why this body |
|---|---|---|---|
| AD | **Posture** | Categorical status cards + control-coverage ring + priority findings | AD is a *configuration baseline* problem — every category (Health, Privileged, Kerberos, Delegation, GPO) is a posture surface scored against the baseline. |
| BloodHound | **Attack-path** | Ranked paths list + path-detail drawer with `PathStepList` | BH is a *graph / path* problem. The natural unit is a critical path, not a control. Findings are paths. |
| Silverfort | **Coverage** | `CoverageMatrix` (policy × target) + coverage-gap priority list | SF is a *coverage* problem — the question is "what is *not* protected?". A matrix shows it directly. |
| Entra | **License-aware tenant config** | License-aware status cards (with `LicenseBadge`) + finding list | Entra is fundamentally license-gated. Every card must surface ownership + configuration state simultaneously. |

> **The frame is the same on all four.** Only the body composition differs. The same `Card`, `StatusBadge`, `PriorityList`, `Button`, `Drawer`, `Finding detail`, and `Publish modal` are used on every page.

#### 4.3.1 AD — *Posture* archetype

- `PageHeader`: "Active Directory · {customer name}" · supporting sentence · secondary actions (Upload evidence · Re-evaluate · Open PingCastle XML).
- Row 1: 4–5 `StatusCard` — Health · Privileged · Kerberos · Delegation · GPO (per `AD_MODULE_DESIGN.md`).
- Row 2 (split):
  - Left: `RingChart` (control coverage — pass / partial / fail / not-applicable / unknown).
  - Right: `PriorityList` (top AD findings ranked by risk score).
- Row 3 (optional, posture detail):
  - `Table` of privileged group membership (Domain Admins / Enterprise Admins / Schema Admins / built-in / krbtgt / Cert Publishers) with counts and a "Tier 0 reachability" `RiskBarList`.
- Right rail (optional): `ActionPanel` — Upload AD toolkit ZIP · Upload PingCastle XML.

This is the closest archetype to "the original M template". It works because AD genuinely *is* a multi-category posture view.

#### 4.3.2 BloodHound — *Attack-path* archetype

- `PageHeader`: "BloodHound · Attack Paths" · supporting sentence (e.g., "Top 5 critical paths to Tier 0") · secondary actions (Upload SharpHound ZIP · Re-analyze).
- Row 1 (context, kept lean — 3 `StatusCard`):
  - Tier 0 reachable from N source identities.
  - Top path category (e.g., "ACL abuse — 4 paths").
  - Highest single risk score on the run.
- Row 2 (the page): **Ranked critical paths list** — dominant column. Each row uses a `RankedList`-style row with: rank · source identity (avatar + label) · → · target (Tier 0 label) · path category badge · length · risk score · severity dot. Click → opens path drawer.
- Row 3 (optional, secondary): `RiskBarList` (paths by category).
- Path detail drawer: `PathStepList` showing each node + edge type + edge severity colour, plus the deterministic explanation template rendered as prose, plus correlation chips (AD finding / SF coverage / Entra hybrid admin).

No control-coverage ring on this page — controls are not the unit. The unit is **the path**.

#### 4.3.3 Silverfort — *Coverage* archetype

- `PageHeader`: "Silverfort · Identity Protection Coverage" · supporting sentence · connector `StatusBadge` (in POC always `pending` "Connector not configured (POC)" with explanation tooltip).
- Row 1 (context — 3 `StatusCard`): Privileged coverage % · Service-account coverage % · Enrollment completeness %.
- Row 2 (the page): **`CoverageMatrix`** — dominant. Rows = covered targets (Tier 0 group, Domain Admins, kerberoastable service accounts, ...); Columns = SF policies; Cells = `covered` (green) / `excluded` (amber) / `not_covered` (red, the gap) / `n/a`. Hover surfaces policy details, source rows surface affected identities.
- Row 3: **Coverage-gap priority list** — `PriorityList` ordered by severity, each row pointing back into the matrix and (when present) into a correlated BH path.
- Right rail (optional): `ActionPanel` — Upload manual export bundle.

The matrix replaces a control-coverage ring because *coverage* is the central question; rings would summarize away the answer.

#### 4.3.4 Entra — *License-aware tenant config* archetype

- `PageHeader`: "Entra ID · {tenant}" · supporting sentence noting the SKU profile (e.g., "E3 + standalone Entra ID P1 · no P2") · secondary actions (Upload Entra Graph bundle · Re-evaluate).
- Row 1: 6 `StatusCard`, each with a `LicenseBadge` in the top-right (variants from the 8-value enum):
  - Licensing & Capability detection
  - Conditional Access
  - Privileged Roles (incl. PIM where licensed)
  - Authentication Methods
  - Apps & Service Principals
  - Hybrid Identity
- Row 2 (split):
  - Left: `RingChart` (Entra control coverage).
  - Right: `PriorityList` of Entra findings — each row shows a `LicenseBadge` so the reader sees license context at-a-glance.
- Row 3 (optional): **Opportunity card** — top 3 capabilities the customer does not own that would close the largest score gap, with `CapabilityTooltip` explaining each.
- Right rail: collapsed in POC; reserved for license-catalog override at MVP.

This archetype is what makes the demo's license-aware story land: every card answers "do they own it?" *and* "are they using it?".

#### Shared frame on every module page

Independent of archetype, every module page has:

- The same `AppShell`, `AppHeader`, breadcrumbs, side nav with active pill.
- The same upload affordance (`FileDropzone` triggered from secondary actions).
- The same `Toolbar` shape when filters are present.
- The same `Drawer` for finding detail.
- The same `Modal` for publishing.
- The same `Evidence drawer` accessible from any finding.
- The same audit log surface.
- The same `LicenseBadge`, `StatusBadge`, severity dots, severity colours, and typography.

The platform reads as **one product**, with each module page **clearly tailored to what it shows**.

### 4.4 `F` — Findings workspace
- `PageHeader`: "Findings" + count.
- `Toolbar`: filter chips (Severity · Module · License Status · Visibility · State) + search + sort.
- `Table` of findings — columns: severity, title, module, identity refs (compact), license-status badge, risk score, state.
- Row click → opens `Drawer` with `FindingDetail`.

### 4.5 `R` — Reports
- `PageHeader`: "Reports" + Generate CTA (critical-coloured if marked as the page's key action).
- `Table` of generated reports (date, type, included findings count, generated by).
- Right rail: `ActionPanel` "Report Generator" (type, format, options, Generate).
- Report viewer (overlay) renders the HTML report inline with a toolbar (Download, Publish).

Other supporting pages: Audit, Customer page, Engagement page, Assessment-run page — composed from the same template grammar (mostly `O`/`M`).

---

## 5. Component inventory map (cross-reference)

| Pattern from VISUAL_REFERENCES.md | Component(s) | Used on pages |
|---|---|---|
| 1. Dark surface, calm whitespace | Tokens | All |
| 2. Sectioned sidebar | `SideNav` + `SideNavGroup` + `SideNavItem` | All |
| 3. Active nav pill | `SideNavItem[state=active]` | All |
| 4. Header with breadcrumb + search + bell + cog + avatar | `AppHeader` | All |
| 5. Page title + supporting sentence + actions | `PageHeader` | All |
| 6. Status card | `StatusCard` | O, M |
| 7. Status pill badge | `StatusBadge` | All |
| 8. Donut/ring + centred metric + legend | `RingChart` | O, M |
| 9. Three rings in a row | `RingRow` | M (BloodHound, Silverfort) |
| 10. Multi-series line chart | `LineChart` | O (score over time, ≥ 2 runs) |
| 11. KPI big number + sublabel + sparkline | `KpiCard` | O |
| 12. Horizontal risk-bar list | `RiskBarList` | O, M |
| 13. Vertical priority list | `PriorityList` + `PriorityListItem` | O, M |
| 14. Right-rail action panel | `ActionPanel` | O, M, R |
| 15. Outlined secondary + primary filled buttons | `Button` | All |
| 16. Filter chip / segmented control | `ChipGroup` | F, R |
| 17. Card with subtle border | `Card` | All |
| 18. Hero card | `HeroCard` | Empty states |
| 19. Numbered ranked list | `RankedList` | O (Top findings), M (BH paths) |
| 20. Dropdown select on dark | `Select` | All |
| 21. Vertical attack-path chain (node → edge → node) | **`PathStepList`** | BH page, Finding drawer (for BH findings) |
| 22. Policy × target coverage grid | **`CoverageMatrix`** | SF page; reusable by future modules with coverage patterns |
| 23. License-aware status badge with capability tooltip | **`LicenseBadge`** + **`CapabilityTooltip`** | Entra page, SF page, Finding drawer, Reports |

---

## 6. Layout principles

### 6.1 Density and breathing room
- Page max content width: 1440 px.
- Side gutters: 32 px desktop, 16 px tablet.
- Grid: 12-column with 24 px gutter.
- Vertical rhythm: section spacing 32 px, in-section 16 px.

### 6.2 Information hierarchy
- One H1 per page.
- Supporting sentence sets context.
- Above the fold: the persona's primary question is answerable.

### 6.3 Calm dashboards (no SIEM clutter)
- KPI cards per page: max **5** (compress to 4 on narrower widths).
- Charts per page: max **3** unless the page is a drill-down (where 1 dominant chart + 2 small).
- Tables and priority lists are vertically scrollable, not page-extending — they live in a fixed-height card with internal scroll if needed.

### 6.4 Drill-down depth budget
- 3 clicks from Overview to any detail finding.
- 2 clicks back to Overview from any drawer.

---

## 7. Dashboard principles

The Overview answers each persona's primary question:

| Persona | Top of the Overview |
|---|---|
| Consultant | Two scores + Top 3 findings strip + Module status row + Quick actions |
| Customer Executive | Two scores + Top 3 findings (customer-framed) + Opportunity card + "Read latest report" |
| Customer IT Lead | Top 3 findings (technical detail) + Severity distribution + "What's mine" filter chip |

Persona-aware overview templates share the same component grammar; only the slot contents differ.

---

## 8. Clean application UX rules

| Rule | Why |
|---|---|
| Loading states never blank the screen — show a skeleton or spinner | Calm, not jarring |
| Error states always offer a next action | Avoid dead ends |
| Empty states use `HeroCard` with a clear CTA | Orient the user |
| Confirmation modals only for destructive or publishing actions | Avoid modal fatigue |
| Inline validation errors near the field | Predictable forms |
| Sticky page header on long pages | Persistent context |
| Drawer overlays do not block the underlying content's keyboard navigation when closed | Accessibility |
| No animations longer than 200 ms | Calm |
| No marquee / autoplay / sound | Calm |

---

## 9. Customer screens

The Customer Executive view is the **same shell** with a compressed nav and pre-filtered data. Reuses every component above. Specifics:

- POC banner suppressed (still POC, but it would confuse the demo audience).
- Only `customer_summary` and `customer_full` findings rendered; report list shows only Customer reports.
- "Internal-only" UI elements (e.g., consultant note inputs, internal-only finding rows) are server-filtered out — they never appear in the DOM for customer roles.

---

## 10. Internal screens

Consultant view exposes:

- Visibility selector on every finding (drawer footer).
- Internal-only badge on findings still `internal_only`.
- Audit log entry on Audit page.
- Module re-evaluate, evidence re-parse actions in module page header.
- Settings (license catalog, role assignments) under a separate Admin nav.

---

## 11. Charts and data visualizations

POC visualizations are deliberately minimal:

- `RingChart` for control coverage (per module).
- `RiskBarList` for severity distribution.
- `KpiCard` (with optional sparkline) for scores.
- `LineChart` only when there are ≥ 2 assessment runs.

No: maps, treemaps, force-directed graphs, scatter plots, parallel coordinates, sunburst charts. (BloodHound path visualization in POC is a *step list*, not a free-form graph — see `BLOODHOUND_ANALYZER_DESIGN.md`.)

---

## 12. License-aware UI

- Every control/finding carries a `LicenseStatus` badge using the licensed/not-licensed variants of `StatusBadge`.
- A small `License` info-icon next to a `not_licensed` badge opens a tooltip:
  > *"This control requires Identity Protection (Entra ID P2). Your current SKUs do not include it. This does not affect your Current License Score; it counts toward the Target Posture Opportunity."*
- An **Opportunity card** on the Overview lists the top 3 capabilities the customer does not own that would close the largest score gap, with no pricing or sales framing.

---

## 13. BloodHound / Attack Path UI

In POC:

- Module page top: 4 `StatusCard` (Tier 0 Reachability, Privileged Paths, ACL Abuse, Delegation).
- Middle row: `RankedList` of top 5 critical paths.
- Path detail (drawer):
  - Header: "Critical Path #N — <source> to <target>", severity badge, risk score.
  - Body: vertical `PathStepList` (one node per row: identity icon + label + edge type to the next node).
  - Side notes: deterministic explanation (rendered markdown), template id, correlation chips (AD, SF, Entra).
  - Footer: visibility selector, "Generate finding" if not already.

A free-form graph canvas is **not in POC**. If management asks, the answer is "MVP".

---

## 14. Silverfort UI

- Module page top: 4 `StatusCard` (Connector, Policy Coverage, Enrollment, Service Accounts).
- Middle: `PriorityList` of coverage gaps.
- A `StatusBadge` for connector status — in POC always shows `pending` ("Connector not configured (POC)") with an explanation tooltip.

---

## 15. Entra UI

- Module page top: 6 `StatusCard` (Licensing & Capabilities, Conditional Access, Privileged Roles, Authentication Methods, Apps & Service Principals, Hybrid Identity).
- License-aware badge on at least 2 cards.
- Middle: `PriorityList` of findings.

---

## 16. Accessibility

- WCAG 2.1 AA target.
- Contrast: minimum 4.5:1 for body text. Verify Trinidad on dark surface (it passes against dark blues; verify each token at implementation).
- Keyboard navigation: all interactive components reachable, focus rings visible (2 px outline, `--accent`).
- ARIA: labels on icon-only buttons; roles on drawer/modal; live regions for toasts.
- Text size minimum 12 px; default 14 px.
- Respect `prefers-reduced-motion`.

---

## 17. What to avoid

| Anti-pattern | Replacement |
|---|---|
| Endless scrolling module pages | Fixed-height cards with internal scroll |
| KPI rows of 8+ cards | Cap at 5 |
| Per-module bespoke UI primitives (re-implementing a button, a card, a badge per module) | Reuse the library atoms; module-specific named components like `PathStepList` / `CoverageMatrix` / `LicenseBadge` are **welcome** but they live in the shared library (§3.5), not inside `modules/<m>/ui/` in a hidden way |
| Forcing identical body layouts across all module pages | Embrace **module-specific archetypes** (§4.3): Posture / Attack-path / Coverage / License-aware tenant config |
| Trinidad on every CTA | Reserve Trinidad for criticals (§2.4) |
| Heavy outer glow on cards (Reference C edges) | Subtle border + 1 px shadow at most |
| Multi-row tab bars | One row max; otherwise restructure |
| Marketing-style hero on internal pages | Calm `PageHeader` |
| Auto-refreshing dashboards in POC | Manual refresh only; no polling |
| Customer view leaking internal-only DOM | Server-side filter before render |

---

## 18. POC mockup requirements

These are the wireframes the developer needs to start work (T-4002 in `TASKS.md`):

1. Login (role + customer) — S-01.
2. Overview — S-02 (Consultant + Customer Executive variants).
3. AD module page — S-06.
4. BloodHound module page with critical paths panel — S-07.
5. Silverfort module page — S-08.
6. Entra module page with license-aware UI — S-09.
7. Findings workspace — S-10.
8. Finding detail drawer (with correlation chips + visibility selector) — S-11.
9. Evidence drawer — S-12.
10. Reports page + Report viewer overlay — S-13.
11. Publishing modal — S-14.
12. Audit log — S-15.

Format for POC: ASCII or markdown sketches per page (no Figma in POC scope). High-fidelity mocks are MVP.

---

## 19. Example screen — Overview (Consultant)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  ●ACEN  Gravity     [Contoso Corp ▾] [Q2 2026 Identity Review ▾] [2026-05-15 ▾]   🔍  🔔 ⚙ ◆KL│
├──────────┬─────────────────────────────────────────────────────────────────────────────┤
│ NAVIGATE │  Contoso Corp · Identity Security Posture                                   │
│  ▣ Over… │  Assessment 2026-05-15  ·  Engagement: Q2 2026 Identity Security Review     │
│   AD     │                                                                             │
│   Blood… │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                            │
│   Silv…  │  │   58 / 100  │ │  76 / 100   │ │  +18        │                            │
│   Entra  │  │ Current Lic │ │ Target Post │ │ Opportunity │                            │
│ WORK     │  └─────────────┘ └─────────────┘ └─────────────┘                            │
│   Findi… │                                                                             │
│   Repor… │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                │
│   Audit  │  │[●] CRITIC. │ │[●] ACTION  │ │[●] PENDING │ │[●] ACTION  │                │
│          │  │ AD         │ │ BloodHound │ │ Silverfort │ │ Entra      │                │
│          │  │ 54/100     │ │ 47/100     │ │ no evidnc  │ │ 71/100     │                │
│          │  │ ███▒▒▒ 54% │ │ ██▒▒▒▒ 47% │ │ ░░░░░░  -  │ │ █████▒ 71% │                │
│          │  └────────────┘ └────────────┘ └────────────┘ └────────────┘                │
│          │                                                                             │
│          │  ┌────────────────────────┐  ┌───────────────────────────────────────────┐  │
│          │  │      Control coverage  │  │   Top findings                            │  │
│          │  │         ┌──────┐       │  │   ● Critical · BH path → DA (CORR-...)    │  │
│          │  │       72%  ↓           │  │   ● Critical · AD-PRIV-005 Privileged…    │  │
│          │  │   passing / failing /  │  │   ● High     · ENTRA-CA-003 Legacy auth   │  │
│          │  │   n/a / unknown        │  │   ● High     · SF-POL-002 Tier 0 cover…   │  │
│          │  └────────────────────────┘  └───────────────────────────────────────────┘  │
│          │                                                                             │
└──────────┴─────────────────────────────────────────────────────────────────────────────┘
```

(Wireframe-only; component composition demonstrated, not a final pixel layout.)

---

## 20. Component library deliverables (for build phase)

- `platform_core/web/components/` directory with one Jinja partial per component listed in §3.
- A `_components_demo.html` page that renders every component in every state for visual QA during build.
- A `tokens.css` (or Tailwind config) containing every token in §2.
- A Tailwind preset extension for component variants.
- Per-component tests for: server-side rendering with default props, state variants, accessibility attributes.

---

*Last updated: 2026-05-15.*
