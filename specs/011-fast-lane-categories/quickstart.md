# Quickstart: Fast Lane Category-Based Classification Refinement

**Date**: 2026-04-13 | **Branch**: `011-fast-lane-categories`

## What this feature changes

- Creations whose API categories are all in a **SAFE** set (Skins, Apparel, Body, Photo Mode, Audio) are marked Unaffected, not scary yellow "Not updated".
- Creations whose categories include a **LOW_RISK** member (Weapons, Gear, Ships) show a softer amber "Low risk" instead of the full warning — but only if the strict combination check passes.
- PS-support override (Likely updated) beats Low-risk when both apply.
- No baseline file regeneration; no new dialogs.

## How to exercise

### 1. Automated tests

```
.venv/Scripts/python.exe -m pytest tests/ -x -q
.venv/Scripts/python.exe -m ruff check .
```

Expect all prior tests + the new category-classification tests to pass; no new lint warnings.

### 2. Manual UI walkthrough

1. Launch the app → Fast Lane Creation Check tab.
2. Click **Import Installed creations** → **Check**.
3. Scroll through the results. Verify:
   - Any row whose creation only has Skins / Apparel / Body / Photo Mode / Audio categories is **grey** with `⚠ Unaffected (<category>)` status text — regardless of version.
   - Any row whose creation has only Weapons / Gear / Ships (no PS support, version == baseline) is **muted amber** with `Not updated (<category> — low risk)`.
   - Same Weapons/Gear/Ships creation with PS5 platform listed → **green** `Likely updated (PS)` — PS override wins.
   - A Quests creation with unchanged version → still **yellow** `Not updated` — no change from pre-011.
   - A creation with mixed `[Weapons, Quests]` tags, version unchanged → still **yellow** `Not updated` — strict combination rejects the mix.
   - A creation with mixed `[Apparel, Lore Friendly]` → Unaffected (meta-tag stripped).
4. Summary line at the top shows all six counters:
   ```
   N total | X not updated | X low risk | X likely updated |
   X updated | X unknown | X unaffected
   ```
5. Row sort order (top to bottom): Not updated → Unknown → Low risk → Likely updated → Unaffected → Updated.

### 3. Regression checks

- Previously-excluded Skins still show as Unaffected (label text may change to `⚠ Unaffected (Skin)`, tag grey).
- All existing test files still pass — `STATUS_SKIN` import sites have been renamed to `STATUS_UNAFFECTED`.

## Troubleshooting

- **A weapon/ship/gear mod shows yellow Not updated instead of Low risk**: its category list from the API likely contains a non-safe tag (e.g., `[Ships, Gameplay]`). Strict combination rejects the mix. Inspect via the row's ⓘ to see the full category list.
- **A cosmetic mod shows yellow Not updated**: either its API data is missing entirely (falls back to baseline `s` flag, which only covers Skins) or its category list includes a non-safe tag. Try clearing the creations cache (`Settings → Clear creations cache`) and re-running the check.
- **Summary counts don't add up to total**: the six counters sum to total. If they don't, there's a bug — please report. (The seven statuses include `NOT_CHECKED` rows from before the check was run, which shouldn't appear after Check has completed.)

## Dev references

- Feature spec: `spec.md`
- Plan: `plan.md`
- Research: `research.md`
- Data model: `data-model.md`
- Tasks (generated next): `tasks.md`
