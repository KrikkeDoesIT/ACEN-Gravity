# Brand asset directory

Official ACEN logo assets used by the application chrome.

## Files

| File | Source | Variant | Used by |
|---|---|---|---|
| `acen-wordmark.svg` | OneDrive: `ACEN Intranet - Branding/ACEN/Logo/svg/Logo - ACEN_Logo - ACEN - Negatief.svg` | Negatief, fill swapped to `#ffffff` for our dark theme | App header, login splash, login mobile header |
| `acen-wordmark-orange-circle.svg` | OneDrive: `…/Logo - ACEN_Logo - ACEN - Positief - Orange Circle.svg` | Positief + orange orbit | Reserved for light surfaces (e.g., Customer Summary report cover page) |

## Notes

- **Single change to the official Negatief SVG:** the path `fill` was changed from `#1d1d1b` (the file's exported near-black) to `#ffffff` so the mark renders on our `shade-*` dark chrome. The OneDrive source file is untouched.
- **Adding a light theme later** (e.g., a light Customer report variant): use `acen-wordmark-orange-circle.svg` (or copy in the Positief variant) and reference it where appropriate.
- **Trinidad-in-the-orbit clarification:** the `Orange Circle` variant uses the Trinidad-gradient orbit. This is **brand identity**, not a critical-state signal — D-0010's "reserve Trinidad" rule applies to CTAs / status surfaces / chrome accents, not to the brand mark itself (D-0023 logged this).
- **Other official variants in OneDrive** (not copied here unless needed): `Logo - ACEN.svg`, `Logo - ACEN - Positief.svg`. The original AI / EPS sources are in `Logo/eps/` and `Logo/*.ai`.
