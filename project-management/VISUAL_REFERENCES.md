# VISUAL_REFERENCES.md

> Visual references Kristof shared on 2026-05-15 as direction for the ACEN Gravity UI. **Goal: reusable components (design-wise)** — translate the patterns common across these references into a small, consistent component library mapped to the ACEN palette and applied identically across modules.
>
> These are inspiration only. The brand source of truth is the ACEN 2025 Huisstijlgids (NL/EN) on OneDrive. Where references conflict with the ACEN brand, the ACEN brand wins. Where references *complement* the brand (component patterns, layout density, status badges), we adopt the pattern and recolour to ACEN tokens.

---

## 1. References

### Reference A — Hack The Box dashboard
- Very dark background; vivid neon-green accent on the **active nav pill**.
- Sidebar with section labels (`Menu`, `My LABS`, `LABS`) and grouped items beneath each.
- Cards on a near-black surface; subtle inner borders; soft gradient-like depth.
- Hero block "Explore Products" — single instructional card with title + body + (no CTA visible).
- Mixed-size card grid (Invite, Practice, Learn, Leaderboard, My Progress).
- Leaderboard component: numbered avatars + name + points; "Your position" highlighted.
- Calm, executive feel despite being dark.

### Reference B — Fortify360 Compliance Engine
- Dark navy/purple background; lighter card surfaces.
- **Left sidebar** organized by section: `GENERAL`, `COMPLIANCE`, `GOVERNANCE`, `OPERATIONS` — each with icon + label rows. Selected nav row uses a filled darker pill.
- **Top header:** breadcrumb (`Enterprise Suite > Compliance & Reports`), global search, notification bell, settings cog, user avatar.
- **Page title** + supporting sentence + **secondary actions** ("Force Global Rescan", "Export Data") to the right.
- **Status cards row** (5 cards): icon + status pill (COMPLIANT / ACTION REQUIRED / AT RISK / PENDING SCAN) + title + "Last sync" timestamp + horizontal progress bar + percent right-aligned. Status colours: green / amber / green / red / muted grey.
- **Donut gauge** with centred big number ("84%") + "OVERALL MAPPED" label + legend below (Mapped & Passing / Mapped & Failing / Unmapped Controls + counts).
- **Priority list** ("Remediation Priority Queue"): row = severity icon + title + small subtitle ("Affects PCI-DSS CC 3.4.1 · Access Control"). Plain rows, no card-per-row.
- **Right rail action panel** ("Report Generator"): label + dropdown ("Executive Summary") + chips (PDF / CSV) + checkboxes + primary CTA ("Generate Report").
- Typography: bold large page title; sentence-case body; UPPERCASE section labels.

### Reference C — Runtime dashboard
- Dark background with a faint cyan gradient at edges; **bordered card** with a glowing edge.
- Inside: title + "New as of 24h" filter pill + "Create Ad-Hoc Report" outlined button.
- API Hosts dropdown.
- **Three ring charts side by side** with centred bold number + sublabel (Published / Discovered / Shadow).
- Multi-series **line chart** with legend below.
- Sub-card: big number (`408.5k`) + sublabel ("New in the last 24 hours") + thin sparkline-style line chart.
- "API Endpoint Risk Levels" = **horizontal bar list** with severity colour + count, plus a legend.

---

## 2. Patterns common to all three (component anchors)

These are the patterns we **adopt as reusable components** in ACEN Gravity:

| # | Pattern | Where seen | Component name in our library |
|---|---|---|---|
| 1 | Dark surface, calm whitespace | A, B, C | `Surface` (base background tokens) |
| 2 | Sectioned sidebar with grouped nav items | A, B | `SideNav` + `SideNavGroup` + `SideNavItem` |
| 3 | Active nav pill (highlighted row) | A, B | `SideNavItem[state=active]` |
| 4 | Header with breadcrumb + global search + notifications + settings + avatar | B | `AppHeader` |
| 5 | Page title block: H1 + supporting sentence + secondary actions | B | `PageHeader` |
| 6 | Status card: icon · status pill · title · meta · progress · percent | B | `StatusCard` |
| 7 | Status pill badge (COMPLIANT/ACTION REQUIRED/AT RISK/...) | B | `StatusBadge` (variants: ok, warning, critical, pending, neutral) |
| 8 | Donut/ring chart with centred metric + legend below | B, C | `RingChart` |
| 9 | Three rings in a row for category counts | C | `RingRow` (composition of 3 × `RingChart`) |
| 10 | Multi-series line chart with legend below | C | `LineChart` |
| 11 | KPI card (big number + sublabel + tiny chart) | C | `KpiCard` |
| 12 | Horizontal risk-bar list (severity colour, count, legend) | C | `RiskBarList` |
| 13 | Vertical priority list (icon + title + subtitle, plain rows) | B | `PriorityList` + `PriorityListItem` |
| 14 | Right-rail action panel (form-like, ends in CTA) | B | `ActionPanel` |
| 15 | Outlined secondary action button + primary filled CTA | B, C | `Button[variant=primary|secondary|ghost]` |
| 16 | Filter chip / segmented control (PDF / CSV) | B, C | `ChipGroup` |
| 17 | Card with subtle border + soft inner glow | A, B, C | `Card` (default) |
| 18 | Empty/instructional hero card with title + body | A | `HeroCard` |
| 19 | Numbered list with avatars (leaderboard style) | A | `RankedList` (reuse for "Top customers" / "Top findings") |
| 20 | Dropdown select on dark surface | B, C | `Select` |

---

## 3. ACEN translation

These references are dark. The ACEN palette is built for dark surfaces (Jakarta `#201e5c`, Bunting `#1b1b4c`, Minsk `#2d2d72`, Gulf `#000162`). That means we can **adopt the dark-surface direction** without breaking brand — we just retoken.

Token mapping (working proposal; finalized in `UI_DESIGN_DIRECTION.md`):

| Token | Value | Used for |
|---|---|---|
| `--bg` | `#0e0e2e` (slightly darker than Bunting, defined in app — keeps brand colours readable above it) | App background |
| `--surface-1` | `#1b1b4c` (Bunting) | Card surfaces (level 1) |
| `--surface-2` | `#201e5c` (Jakarta) | Active nav, hovered cards |
| `--surface-3` | `#2d2d72` (Minsk) | Subtle dividers, pills |
| `--brand` | `#000162` (Gulf) | Brand accent in logo/marks |
| `--accent` | `#fd5400` (Trinidad) | Primary actions, critical states (use sparingly) |
| `--accent-2` | `#50bfa0` (Turquoise) | Secondary accents, positive/ok states |
| `--text` | `#ffffff` (white) | Body text on dark |
| `--text-muted` | `#eaeaea` (Gallery) | Secondary text |
| `--text-subtle` | `#595959` (Dorado) | Tertiary text (use against light surfaces only) |
| `--divider` | rgba(255,255,255,0.08) | Borders/dividers on dark |

Status badges (Reference B):
- `ok` / "Compliant" → Turquoise `#50bfa0`
- `warning` / "Action Required" → ACEN amber needed (propose `#f6a623` as a derived token, since brand lacks an explicit amber)
- `critical` / "At Risk" → Trinidad `#fd5400`
- `pending` / `neutral` → Mercury `#e0e0e0` or muted Minsk

> **Open question Q-0111 stands:** Trinidad orange is the brand's primary accent. We must decide if it's also the *button* accent or reserved for criticals. The references put critical = red/orange and primary actions = blue/purple. Recommendation: **reserve Trinidad for critical/alert; use a calmer brand-blue tint for primary CTAs** so the page does not glow orange.

---

## 4. Anti-patterns from the references we will NOT adopt

| Anti-pattern | Why we avoid it |
|---|---|
| Heavy outer glow on cards (Reference C edges) | Brand calls for calm, executive feel; glow looks gamer-ish |
| Neon green active highlight (Reference A) | Off-brand colour; we use Turquoise or surface-2 fill |
| Cluttered KPI strips (5+ status cards in a row) | Brand says calm whitespace; we cap at 4 status cards in a row, scale down at narrower widths |
| Section-label uppercase styling on every sidebar group | Acceptable, but we use only when there are ≥ 3 items in the group; otherwise collapse |
| Bell + cog + avatar density in header | Adopt, but cap at 3 icons; we do not add quick-actions next to them |
| Dark-only — no light theme | We intentionally start dark to align with brand and references. Light theme is a Full-Product decision (not POC). |

---

## 5. Layout density (calm, not SIEM-like)

From combining A and B:

- One H1 per page.
- One supporting sentence beneath the H1.
- At most 4 stat cards above the fold.
- At most one primary visualization (donut or chart) per content row.
- At most one "right rail" panel per page; rail is optional (collapses on narrow widths).
- Lists prefer plain rows over card-per-row to keep dense data scannable (Reference B Priority Queue).

---

## 6. Where these references shape our docs

These notes feed:

- `UI_DESIGN_DIRECTION.md` — component inventory (next pass restructures the doc to lead with components).
- `MODULE_ARCHITECTURE.md` — reinforces "every module reuses the same UI patterns" rule.
- `PRODUCT_DESIGN.md` §27 (ACEN UI principles).
- `TASKS.md` — UI shell tasks reference these component names.

---

*Last updated: 2026-05-15.*
