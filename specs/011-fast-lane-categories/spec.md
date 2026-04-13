# Feature Specification: Fast Lane Category-Based Classification Refinement

**Feature Branch**: `011-fast-lane-categories`
**Created**: 2026-04-13
**Status**: Draft
**Input**: User description: "Fast Lane category-based classification refinement: add two category sets ('safe' and 'low-risk') so cosmetic and additive-content creations don't trigger false-positive 'Not updated' warnings. SAFE categories (Skins, Apparel, Body, Photo Mode, Audio) skip the check entirely — mark as unaffected, no warning. LOW_RISK categories (Weapons, Gear, Ships) still run the check, and if the result would be 'Not updated' (version matches baseline, no PS support), annotate as 'Low risk' instead — visually softer than the scary yellow, letting the user decide. Meta-tags (Load Order Neutral, Lore Friendly, Work in Progress) are ignored when evaluating either set. Combination logic for both sets is strict: ALL non-meta categories of a creation must be in the relevant set (any mixed-category mod with a non-safe tag like Quests stays in the full-warning bucket). The PS-support override (Likely updated) applies BEFORE the low-risk annotation, so a weapon mod with PS5 support shows as Likely updated, not Low risk. Categories come from CreationInfo.categories populated by the API; the baseline file's single-bit 's' skin flag stays as a fallback for entries where API data is missing. No baseline regeneration needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cosmetic creations are silently excluded from the warning (Priority: P1)

A user runs the Fast Lane Creation Check with a typical load order that includes dozens of cosmetic and character-visual creations (outfits, skins, body morphs, photo mode tweaks, audio replacers). Today any such creation whose version still matches the baseline snapshot is flagged yellow "Not updated" — alarming the user about mods that couldn't possibly have been broken by the Free Lanes update. With this change, creations whose categories indicate they are purely cosmetic are marked as "Unaffected" (grey, no warning color) and counted separately, regardless of whether they appear to have been updated.

**Why this priority**: This is the biggest source of user-facing false positives — character and visual mods typically have long versions and low update cadence, and they are dramatically overrepresented in load orders. Removing them from the warning bucket makes the real "Not updated" warnings far more trustworthy.

**Independent Test**: Run the check on a load order containing at least one Skins, Apparel, Body, Photo Mode, and Audio creation whose version is identical to its baseline value. Every one of those rows must show as "Unaffected" (grey) and not "Not updated" (yellow). Running without this change would flag them yellow.

**Acceptance Scenarios**:

1. **Given** a creation tagged only as Apparel whose current version matches the baseline, **When** the user runs the check, **Then** the row is marked Unaffected (grey) and excluded from the "not updated" count.
2. **Given** a creation tagged as Skins with an `s=1` baseline flag but without any API category data, **When** the check runs, **Then** the row is still marked Unaffected (the baseline flag remains a reliable fallback).
3. **Given** a creation tagged as Apparel plus the Lore Friendly meta-tag, **When** the check runs, **Then** the meta-tag is ignored and the row is marked Unaffected.

---

### User Story 2 - Additive-content creations are annotated as low-risk instead of scary yellow (Priority: P1)

A user runs the check with a load order full of ship-part mods and weapon mods. Most of these authors haven't bumped their version since the Free Lanes update — not because they're broken, but because the update didn't touch weapons or the existing ship builder records. Today all of them show yellow "Not updated" warnings that waste the user's time. With this change, such creations are labelled "Low risk" with softer styling: the user is informed ("this kind of mod is unlikely to have been affected") but the decision whether to verify is theirs.

**Why this priority**: This is the second most common false-positive source. Weapons, Gear, and Ships (ship parts) are high-volume categories where author update patterns lag but actual compatibility is rarely an issue. A softer signal converts dozens of alarming yellow rows into a "probably fine, but verify if you like" secondary tier.

**Independent Test**: Run the check on a load order with at least one Weapons, one Gear, and one Ships creation whose version equals the baseline and whose API platform list does NOT include PS4/PS5. Each must show as "Low risk" with softer styling (not the scary yellow used for Not updated). A Quests creation in the same list must still show scary yellow.

**Acceptance Scenarios**:

1. **Given** a creation tagged only as Weapons whose version matches the baseline and with no PS4/PS5 in its platform list, **When** the check runs, **Then** the row is marked "Low risk" with a distinct color softer than the "Not updated" warning.
2. **Given** a creation tagged as Ships with the same conditions, **When** the check runs, **Then** the row is marked "Low risk".
3. **Given** a creation tagged as Weapons with PS5 listed in its platforms, **When** the check runs, **Then** the row is marked "Likely updated" (the PS-support signal wins over the low-risk annotation).
4. **Given** a creation tagged as both Weapons and Quests whose version matches the baseline, **When** the check runs, **Then** the row is marked "Not updated" (the non-safe Quests tag keeps the full warning — strict combination).
5. **Given** a creation tagged as Gear with a version newer than the baseline, **When** the check runs, **Then** the row is marked "Updated" (the category tier doesn't override a genuine update).

---

### User Story 3 - Summary line and sorting reflect the new tiers (Priority: P2)

When the check completes, the summary line at the top of the results shows counters for every classification tier, and rows are sorted so the most urgent warnings appear first. With the new tiers, the user can see at a glance "I have 4 not-updated, 18 low-risk, 5 likely-updated, 150 updated, 12 unknown, and 73 unaffected" — a far richer breakdown than today's binary warn/safe split.

**Why this priority**: The summary and sort order are what make the feature *usable* at scale. With a typical 200+ creation load order, a flat list of rows is hard to navigate; tiered sorting surfaces the rows the user actually needs to inspect.

**Independent Test**: Import a diverse load order, run the check, and inspect the summary line and row order. All six classifications must appear in the summary with correct counts. Rows must be grouped as: not-updated first (top), then unknown, then low-risk, then likely-updated, then unaffected, then updated (bottom).

**Acceptance Scenarios**:

1. **Given** a load order with representatives of every status, **When** the check completes, **Then** the summary line lists six counters: not updated, low risk, likely updated, updated, unknown, unaffected.
2. **Given** the results tree after a check, **When** rows are sorted by status, **Then** not-updated rows appear first, low-risk rows appear after unknown, and unaffected rows appear just before updated.

---

### Edge Cases

- A creation has an empty categories list (no category data from the API) → falls back to the baseline `s` flag only; if the flag is absent, the row follows the normal version comparison path (Not updated / Updated / etc.).
- A creation's API data could not be fetched at all → baseline `s` flag is the only signal available; treated as Skin/Unaffected only if flag is set, otherwise follows the standard path.
- A creation has every category in the SAFE set except for a single non-safe tag like Miscellaneous → strict combination fails, row follows standard path. Documented as an explicit choice rather than a loophole.
- A creation has all categories in LOW_RISK but a version newer than baseline → marked "Updated" (the category-based tiering only refines the NOT_UPDATED result, never downgrades a genuine update).
- The PS-support override and the low-risk annotation both apply to the same row → PS override wins because platform presence is stronger evidence (PS listing proves post-Free-Lanes republish) than category inference (argues about what *probably* isn't affected).
- A creation has only meta-tags (Load Order Neutral only) with no real category → strict combination requires at least one non-meta category matching the set, so it doesn't qualify for unaffected or low-risk; follows standard path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST classify each moved/compared row into exactly one of six statuses: Updated, Likely updated (PS), Low risk, Not updated, Unknown, or Unaffected.
- **FR-002**: A creation MUST be classified Unaffected when either (a) its baseline entry has the `s=1` flag, or (b) all of its non-meta API categories are members of a defined SAFE set.
- **FR-003**: The SAFE set MUST contain exactly: Skins, Apparel, Body, Photo Mode, Audio.
- **FR-004**: Unaffected rows MUST skip all subsequent classification steps (version comparison, PS-support override, low-risk check).
- **FR-005**: A creation whose plain classification would be Not updated MUST be reclassified as Low risk when all of its non-meta categories are members of (SAFE ∪ LOW_RISK) AND at least one non-meta category is in the LOW_RISK set.
- **FR-006**: The LOW_RISK set MUST contain exactly: Weapons, Gear, Ships.
- **FR-007**: The system MUST evaluate the PS-support override (Likely updated) BEFORE the Low-risk annotation, so a creation with PS support takes precedence over a low-risk tag match.
- **FR-008**: Meta-tags (Load Order Neutral, Lore Friendly, Work in Progress) MUST be excluded from category-set membership checks — they are auxiliary descriptors, not gameplay classifications.
- **FR-009**: Combination logic for both sets MUST be strict: ALL non-meta categories must be in the relevant set. A single non-member category must disqualify the creation from the tier.
- **FR-010**: The results grid MUST display Unaffected rows with grey foreground (consistent with the previous skin styling) and Low-risk rows with a color visually softer than the "Not updated" warning color, distinguishable from all other tiers.
- **FR-011**: The results grid MUST display a reason token in the status text for Unaffected and Low-risk rows identifying the matching category (e.g., "Unaffected (Skin)", "Low risk (Weapons)").
- **FR-012**: The summary line MUST show a counter for every status including the new Low-risk and Unaffected tiers.
- **FR-013**: The sort order for result rows MUST be: Not updated → Unknown → Low risk → Likely updated → Unaffected → Updated (most-urgent to least-urgent).
- **FR-014**: The baseline file format MUST remain unchanged — no regeneration or schema migration is required. The `s=1` flag continues to work as a fallback when API categories are unavailable.
- **FR-015**: When the user previously saw a yellow "Not updated" row for a cosmetic or additive-content creation, the new classification MUST replace that with the appropriate softer tier (no ambiguous overlap where a row shows both warnings simultaneously).

### Key Entities

- **Classification status**: A single label applied to each compared row, drawn from a fixed enumerated set of six values (Updated, Likely updated, Low risk, Not updated, Unknown, Unaffected).
- **Category set**: A named, fixed list of Bethesda API category names. Two sets are defined: SAFE and LOW_RISK. Meta-tag list is a third set used only to strip auxiliary descriptors before evaluation.
- **Reason token**: A short label derived from the matching category name (or "Skin" from the baseline flag), displayed alongside Unaffected and Low-risk statuses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users running the Fast Lane check on a typical load order see the "Not updated" count decrease meaningfully (commonly 50%+) compared to the previous behavior, because cosmetic and additive-content creations now populate the Unaffected and Low-risk tiers instead.
- **SC-002**: Users reviewing the results can determine at a glance whether a flagged creation is purely cosmetic or additive-content without opening any additional dialogs — the reason token makes the category visible in the row itself.
- **SC-003**: No Quest, Overhaul, World, Planets, Gameplay, Immersion, Dungeons, Creatures, Followers, Outpost, Cheats, UI, Visuals, Environmental, Homes, Vehicles, or Miscellaneous creation is ever classified as Unaffected or Low-risk — the stricter tiers are reserved for the enumerated safe and low-risk categories only.
- **SC-004**: A creation whose API data is unavailable continues to be classifiable using only the baseline file — at minimum the `s` flag still produces Unaffected for skins.
- **SC-005**: Existing user behavior (clicking Import → Check → review) is unchanged except for the display of new tiers; no new workflow steps, dialogs, or user input are introduced.

## Assumptions

- The Bethesda API's category tagging is reasonably accurate — if a mod is labeled "Skins" it is genuinely a skin mod. The feature relies on category tagging quality; a badly tagged mod is a pre-existing data-quality issue.
- Most creations in a typical load order have at least one non-meta category in their API data. The fallback paths for zero-category rows exist but are expected to be rare.
- The SAFE and LOW_RISK lists are chosen based on April 2026 Free Lanes update scope and will remain appropriate until the next major game update meaningfully changes what's at risk. Updating the lists later is a simple change, not a design break.
- Users understand that "Low risk" means "you probably don't need to worry about this but verify if you want" — not a guarantee of compatibility.
- The existing `s=1` baseline flag convention is kept intact and remains a trustworthy fallback for skins where the live API can't be queried.
- Screenshots, dialogs, and color styling conventions match the rest of the tool's dark-theme-only presentation already established in prior features.
