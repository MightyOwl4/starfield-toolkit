# Research: Fast Lane Category-Based Classification Refinement

**Date**: 2026-04-13 | **Branch**: `011-fast-lane-categories`

## Decision 1: SAFE category list

**Decision**: The SAFE set is `{Skins, Apparel, Body, Photo Mode, Audio}`.

**Rationale**: Research on the Free Lanes update (released 2026-04-07 alongside the PS5 port) confirmed the update changed *space travel* (cruise mode, free-lanes encounters, X-Tech resource, new ship parts, Moon Jumper vehicle, HUD additions). It did not modify the character-rendering pipeline, the audio subsystem, or the photo-mode system. Creations in these categories have effectively zero intersection with the changed systems, so skipping the check entirely (rather than surfacing a Low-risk warning) is appropriate.

**Alternatives considered**:
- Include Weapons and Gear in SAFE: rejected per user direction — weapons occasionally interact with gameplay systems (aim-down-sight, reload animations) that touch adjacent code paths, so Low-risk is more honest than Unaffected.
- Include Miscellaneous: rejected — it's a catch-all with unpredictable contents, so it can't be a blanket "safe" signal.

## Decision 2: LOW_RISK category list

**Decision**: The LOW_RISK set is `{Weapons, Gear, Ships}`.

**Rationale**: These are additive-content categories. Weapons and Gear add standalone items that don't intersect with cruise mode or the free-lanes encounter system. Ships covers ship-part authors — Free Lanes added new parts to the builder library but did not alter existing part records, so existing ship-part mods remain compatible. "Low risk" communicates: "there's no plausible mechanism for this update to break this mod, but since categories can be mis-tagged, verify if you care."

**Alternatives considered**:
- Put Ships in SAFE: rejected per user direction — the user explicitly asked for Ships to be treated as Low-risk for now, pending more evidence. A ship mod could theoretically touch a record that interacts with the new space-travel systems.
- Expand to include Outpost: rejected — outposts share state with the travel/encounter systems via planet terrain and Free Lanes encounter spawns.

## Decision 3: Meta-tags to strip

**Decision**: The meta set is `{Load Order Neutral, Lore Friendly, Work in Progress}`.

**Rationale**: These are descriptive flags, not gameplay classifications. A mod labeled `["Skins", "Lore Friendly"]` should still count as a skin-only mod for SAFE-set purposes. Including meta-tags in the strict combination check would exclude many otherwise-safe creations from the tier. "Work in Progress" is a stability descriptor (Bethesda lets authors flag pre-release content), not a content-type indicator.

**Alternatives considered**:
- Treat meta-tags as always-passing (never disqualify): equivalent to stripping; implementation-wise stripping is cleaner.
- Handle meta-tags per category: rejected as overcomplicating for no user-visible benefit.

## Decision 4: Combination logic — strict (all-match)

**Decision**: A creation qualifies for a tier only when **all** non-meta categories are in that tier's set. For LOW_RISK specifically, all non-meta categories must be in (SAFE ∪ LOW_RISK) AND at least one must be in LOW_RISK.

**Rationale**: Permissive (any-match) combination would let a multi-tag mod like `[Weapons, Quests]` escape the Not-updated warning simply by having a Weapons tag — but the Quests part could genuinely be affected. Strict combination preserves the warning for mixed-category mods, and the cost (losing the tier label for a mod that has *both* a safe and a risky category) is acceptable because in practice most "safe"-looking mods only carry the safe tags.

**Alternatives considered**:
- Permissive (any-match) — rejected; false-positive rate would be too high for mixed-category mods.
- Weighted scoring — rejected as overengineered and harder to explain to users.

## Decision 5: PS-support ordering precedence

**Decision**: Apply the PS-support override (Likely updated) **before** the Low-risk annotation. A row with both PS platforms listed and matching Low-risk categories gets "Likely updated", not "Low risk".

**Rationale**: Platform listing is a stronger signal than category membership. PS support is observable evidence that the mod author did re-publish post-Free-Lanes (even without a version bump) — factually stronger than "this kind of mod is probably fine". Low-risk is an inference; PS-support is evidence.

**Alternatives considered**:
- Apply Low-risk first (and promote to Likely updated only if Low-risk wouldn't trigger): rejected — counterintuitive and produces strictly less useful labels.

## Decision 6: Baseline file format — unchanged

**Decision**: The `data/creations_baseline.json` schema is not changed. The existing `s=1` flag remains as a fallback for the SAFE check when API data is unavailable.

**Rationale**: Regenerating the baseline would require running the scraper (expensive) and bundling a larger file. The new logic reads `info.categories` from the fresh API fetch that Fast Lane already performs in the Check action. For entries where the API fetch failed or returned no categories, the `s` flag still produces Unaffected for skins — the original behavior. No regression.

**Alternatives considered**:
- Extend baseline with a category field: rejected — doubles bundle size for no user-visible benefit.
- Regenerate baseline to include a broader safe-flag: rejected — same objection, plus any change to the SAFE set would require regenerating again.

## Decision 7: Status renaming

**Decision**: Rename `STATUS_SKIN` → `STATUS_UNAFFECTED` and repurpose the existing grey tag. Add `STATUS_LOW_RISK` as a new status with a new muted-amber tag.

**Rationale**: `STATUS_SKIN` was always a misnomer — it meant "unaffected by the update", not "is a skin". Renaming aligns the constant with its semantic meaning. The tree tag configuration is also renamed (`"skin"` → `"unaffected"`) for consistency. `STATUS_LOW_RISK` is genuinely new and needs its own color.

**Alternatives considered**:
- Keep `STATUS_SKIN` and add `STATUS_UNAFFECTED`: rejected — having two statuses with the same meaning and the same rendering is confusing for future maintainers.

## Decision 8: Reason token displayed in status text

**Decision**: Each Unaffected and Low-risk row displays the matching category name (or "Skin" from the baseline flag) in its status text: e.g., `⚠ Unaffected (Apparel)`, `Not updated (Weapons — low risk)`.

**Rationale**: Without the reason, the user can't tell *why* a row was tiered down. Making the category visible in the row means they can audit the classifier at a glance and form their own judgment.

**Alternatives considered**:
- Rely on the existing ⓘ icon + details dialog to reveal categories: rejected — requires an extra click per row to understand the classification; the cost of embedding is one short token per row.

## Decision 9: Sort order — Low risk between Unknown and Likely updated

**Decision**: Sort buckets: Not updated → Unknown → **Low risk** → Likely updated → Unaffected → Updated.

**Rationale**: Low-risk rows are "you probably don't need to look, but you might want to" — more urgent than Likely updated (which has positive evidence of republish) but less urgent than the actual Not-updated warnings or Unknowns. Placing it between Unknown and Likely updated positions it correctly on the concern axis.

**Alternatives considered**:
- Below Likely updated: rejected — Likely updated has stronger evidence of safety than Low risk, so it should rank as safer.
- Between Not updated and Unknown: rejected — Low risk is definitely less urgent than Unknown (where we have no signal at all).
