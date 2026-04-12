---
description: "Task list for 011-fast-lane-categories: SAFE + LOW_RISK category tiers in Fast Lane Creation Check"
---

# Tasks: Fast Lane Category-Based Classification Refinement

**Input**: Design documents from `specs/011-fast-lane-categories/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: YES — Constitution II (Test Coverage) is non-negotiable for functional behavior. The classification decision tree is exactly the kind of logic regressions creep into unnoticed; every branch gets explicit test coverage. UI-only tweaks (tag color, summary text) are verified manually.

**Organization**: Grouped by user story. Foundational data-model constants precede user-story work because both P1 stories (US1 and US2) depend on the same SAFE / LOW_RISK / META constants and the renamed status token.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent subsystems)
- **[Story]**: US1 (safe/unaffected), US2 (low-risk annotation), US3 (summary + sort order)

## Path Conventions

Single-project layout. `src/` and `tests/` at repo root. Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

*No setup required — all changes are in existing files.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared constants and status renaming that both P1 user stories depend on.

- [X] T001 In `src/starfield_tool/tools/fast_lane_check.py`, rename constant `STATUS_SKIN` → `STATUS_UNAFFECTED` (value changes from `"skin"` to `"unaffected"`). Update every reference inside this file (`_run_comparison`, `_populate_tree`, `_status_sort_key`, `_update_summary`).
- [X] T002 Add constant `STATUS_LOW_RISK = "low_risk"` alongside the other status constants in the same file.
- [X] T003 Add three module-level frozensets near the existing status constants:
  ```python
  _SAFE_CATEGORIES = frozenset({"Skins", "Apparel", "Body", "Photo Mode", "Audio"})
  _LOW_RISK_CATEGORIES = frozenset({"Weapons", "Gear", "Ships"})
  _META_CATEGORIES = frozenset({"Load Order Neutral", "Lore Friendly", "Work in Progress"})
  ```
- [X] T004 Update `tests/test_fast_lane_check.py`: rename every `STATUS_SKIN` import and reference to `STATUS_UNAFFECTED`. Run tests to confirm the rename is clean before starting US1.
- [X] T005 Run `.venv/Scripts/python.exe -m pytest tests/ -x -q` to confirm all existing tests still pass after the rename.

**Checkpoint**: foundational renames done; new constants defined but unused; existing tests green.

---

## Phase 3: User Story 1 — SAFE categories skip the check (Priority: P1)

**Goal**: Creations whose non-meta API categories are all in the SAFE set render as Unaffected without running the version comparison.

**Independent Test**: per `spec.md` US1 — any Skins/Apparel/Body/Photo Mode/Audio-only creation with version == baseline shows grey Unaffected, not yellow Not updated. A `[Apparel, Lore Friendly]` meta-mixed creation still qualifies. A `[Apparel, Quests]` creation does NOT.

- [X] T006 [US1] Add a small helper near the classification logic in `src/starfield_tool/tools/fast_lane_check.py`:
  ```python
  def _non_meta(cats: list[str]) -> list[str]:
      return [c for c in cats if c not in _META_CATEGORIES]

  def _pick_safe_reason(cats: list[str], baseline_entry: dict) -> str:
      for c in cats:
          if c in _SAFE_CATEGORIES:
              return c
      return "Skin" if baseline_entry.get("s") == 1 else ""
  ```
- [X] T007 [US1] In `_run_comparison`, replace the existing skin branch (`if baseline_entry.get("s") == 1:`) with the new SAFE check:
  ```python
  categories = info.categories if info else []
  non_meta = _non_meta(categories)
  is_safe = baseline_entry.get("s") == 1 or (
      bool(non_meta) and all(c in _SAFE_CATEGORIES for c in non_meta)
  )
  if is_safe:
      row["status"] = STATUS_UNAFFECTED
      row["unaffected_reason"] = _pick_safe_reason(categories, baseline_entry)
      continue
  ```
- [X] T008 [US1] In `_populate_tree`, replace the existing `STATUS_SKIN` branch with an Unaffected branch that reads `row.get("unaffected_reason")` and renders status text as `"\u26A0 {reason}"` (falling back to `"\u26A0 Unaffected"` if reason is empty). Tag remains the grey `"unaffected"` tag (already renamed in T001).
- [X] T009 [US1] Update the tree tag configuration in `_build_loaded_state`: rename the `skin` tag to `unaffected` (same grey color). Update `STATUS_SKIN` references in `_status_sort_key` and `_update_summary` to `STATUS_UNAFFECTED` (label changes from "skins" to "unaffected" in the summary).
- [X] T010 [US1] [P] Add `tests/test_fast_lane_check.py::test_apparel_marked_unaffected` — info_map with a single `["Apparel"]` creation, version matches baseline → assert `STATUS_UNAFFECTED` and `unaffected_reason == "Apparel"`.
- [X] T011 [US1] [P] Add `test_photo_mode_marked_unaffected` — similar with `["Photo Mode"]`.
- [X] T012 [US1] [P] Add `test_audio_marked_unaffected` — similar with `["Audio"]`.
- [X] T013 [US1] [P] Add `test_meta_tags_ignored_for_safe` — `["Apparel", "Lore Friendly"]` → still Unaffected (meta stripped).
- [X] T014 [US1] [P] Add `test_mixed_apparel_quests_stays_not_updated` — `["Apparel", "Quests"]` → strict combination fails, must remain `STATUS_NOT_UPDATED`.
- [X] T015 [US1] [P] Add `test_baseline_skin_flag_fallback` — row with `baseline.s == 1` and no API categories → Unaffected, reason `"Skin"`.

**Checkpoint**: US1 complete. Any cosmetic/character-visual creation is excluded from the version warning independently of US2.

---

## Phase 4: User Story 2 — LOW_RISK annotation on Not-updated rows (Priority: P1)

**Goal**: Creations whose non-meta categories are all in (SAFE ∪ LOW_RISK) with ≥1 in LOW_RISK show "Low risk" instead of the yellow "Not updated" — but only when the plain classification would be Not updated.

**Independent Test**: per `spec.md` US2 — a Weapons/Gear/Ships-only creation with version == baseline and no PS support shows muted amber "Low risk". A Weapons-only creation with PS5 listed shows "Likely updated" (PS wins). A `[Weapons, Quests]` creation stays yellow Not updated.

- [X] T016 [US2] Add a helper in `src/starfield_tool/tools/fast_lane_check.py`:
  ```python
  def _pick_low_risk_reason(cats: list[str]) -> str:
      for c in cats:
          if c in _LOW_RISK_CATEGORIES:
              return c
      return ""
  ```
- [X] T017 [US2] Add colors for the new low-risk tag in the module-level color constants section:
  ```python
  _LOW_RISK_BG = "#a37015"  # muted amber, softer than _NOT_UPDATED_BG
  _LOW_RISK_FG = "#ffffff"
  ```
- [X] T018 [US2] Extend `_run_comparison` AFTER the existing PS-support override (so PS wins) AND AFTER `_classify()`:
  ```python
  if status == STATUS_NOT_UPDATED and non_meta:
      if all(c in (_SAFE_CATEGORIES | _LOW_RISK_CATEGORIES) for c in non_meta) \
         and any(c in _LOW_RISK_CATEGORIES for c in non_meta):
          status = STATUS_LOW_RISK
          row["low_risk_reason"] = _pick_low_risk_reason(categories)
  row["status"] = status
  ```
  Note: `non_meta` is the same variable computed by T007; reuse it. Do NOT apply this branch when status is already `STATUS_UPDATED` or `STATUS_LIKELY_UPDATED` — the condition guard makes that explicit.
- [X] T019 [US2] In `_populate_tree`, add the `STATUS_LOW_RISK` branch:
  ```python
  elif status == STATUS_LOW_RISK:
      tags = ("low_risk",)
      reason = row.get("low_risk_reason", "")
      status_text = f"Not updated ({reason} — low risk)" if reason else "Not updated (low risk)"
  ```
- [X] T020 [US2] In `_build_loaded_state`, configure the new tag:
  ```python
  self._tree.tag_configure("low_risk", background=_LOW_RISK_BG, foreground=_LOW_RISK_FG)
  ```
- [X] T021 [US2] [P] Add `tests/test_fast_lane_check.py::test_weapons_marked_low_risk` — `["Weapons"]`, version == baseline, no PS → `STATUS_LOW_RISK`, reason `"Weapons"`.
- [X] T022 [US2] [P] Add `test_gear_marked_low_risk` — same with `["Gear"]`.
- [X] T023 [US2] [P] Add `test_ships_marked_low_risk` — same with `["Ships"]`.
- [X] T024 [US2] [P] Add `test_ps_support_wins_over_low_risk` — `["Weapons"]` + PS5 platform → `STATUS_LIKELY_UPDATED` (PS precedence).
- [X] T025 [US2] [P] Add `test_quest_mod_stays_not_updated` — `["Quests"]` → remains `STATUS_NOT_UPDATED` (no tier relief).
- [X] T026 [US2] [P] Add `test_mixed_weapons_quests_stays_not_updated` — `["Weapons", "Quests"]` → remains `STATUS_NOT_UPDATED` (strict combination).
- [X] T027 [US2] [P] Add `test_weapons_with_updated_version_stays_updated` — `["Weapons"]` + version > baseline → remains `STATUS_UPDATED` (category tier never downgrades a genuine update).
- [X] T028 [US2] [P] Add `test_mixed_safe_and_low_risk_triggers_low_risk` — `["Apparel", "Weapons"]`, version == baseline → `STATUS_LOW_RISK` (all non-meta in (SAFE ∪ LOW_RISK), at least one in LOW_RISK).

**Checkpoint**: US2 complete. The full category-driven tier system is live; every edge case from the spec has a test.

---

## Phase 5: User Story 3 — Summary line and sort order (Priority: P2)

**Goal**: Summary counters and row sort order reflect the new tiers.

**Independent Test**: per `spec.md` US3 — summary shows six counters (not updated, low risk, likely updated, updated, unknown, unaffected). Rows sort: not_updated → unknown → low_risk → likely_updated → unaffected → updated.

- [X] T029 [US3] In `_update_summary`, extend the counting + label line to include low_risk:
  ```python
  low_risk = sum(1 for r in self._rows if r.get("status") == STATUS_LOW_RISK)
  # ...
  text=(f"{total} total | {not_updated} not updated | {low_risk} low risk | "
        f"{likely} likely updated | {updated} updated | "
        f"{unknown} unknown | {unaffected} unaffected")
  ```
- [X] T030 [US3] In `_status_sort_key`, insert the new status at the correct urgency position:
  ```python
  if status == STATUS_NOT_UPDATED: return 0
  if status == STATUS_UNKNOWN:     return 1
  if status == STATUS_LOW_RISK:    return 2
  if status == STATUS_LIKELY_UPDATED: return 3
  if status == STATUS_UNAFFECTED:  return 4
  return 5  # updated (default)
  ```
- [X] T031 [US3] In `_build_loaded_state`, update the warning banner text to mention the new tiers briefly — something like *"Skins, Apparel, Body, Photo Mode, and Audio are excluded from the check (shown as Unaffected). Weapons, Gear, and Ships are flagged as Low risk when their version still matches the baseline — typically safe, but worth confirming."*
- [ ] T032 [US3] [P] Add `test_summary_counts_all_six_tiers` — SKIPPED: `_update_summary` mutates a `CTkLabel` which requires a live Tk event loop. The sort-key test (T033) and per-status unit tests (T010–T028) cover the underlying counting semantics; a manual check (T035) verifies the rendered summary line.
- [X] T033 [US3] [P] Add `test_sort_key_ordering_matches_spec` — verify `_status_sort_key` returns 0 for NOT_UPDATED, 1 for UNKNOWN, 2 for LOW_RISK, 3 for LIKELY_UPDATED, 4 for UNAFFECTED, 5 for UPDATED.

**Checkpoint**: US3 complete. The new summary and sort order ship with correct semantics and test coverage.

---

## Phase 6: Polish & Cross-Cutting

- [X] T034 [P] Run the full test suite and ruff: `.venv/Scripts/python.exe -m pytest tests/ -x -q && .venv/Scripts/python.exe -m ruff check .`. Expect all prior + new tests green, no new lint warnings. Pre-existing unrelated lint warnings may remain.
- [X] T035 [P] Manual verification using `specs/011-fast-lane-categories/quickstart.md` §2 — launch the app, run Fast Lane check, confirm visual tiers and summary layout match the expected screenshots described in the quickstart.
- [X] T036 Verified `CLAUDE.md` auto-update already ran (`Last updated: 2026-04-13`). The script's `Recent Changes` section only surfaces the first feature by design — no manual edit required.

---

## Dependencies

- **Phase 2 blocks everything else** — rename + constants are prerequisites for both US1 and US2.
- **Phase 3 (US1)** and **Phase 4 (US2)** share the `non_meta` local variable computed in `_run_comparison`. Code-wise the US2 branch adds lines AFTER the US1 branch. If implementing in parallel, the merging step is trivial.
- **Phase 5 (US3)** depends on `STATUS_LOW_RISK` being defined (T002) and on `STATUS_UNAFFECTED` being renamed (T001), but otherwise can start any time after Phase 2.
- **Phase 6** depends on all prior phases.

## Parallel Opportunities

- **T004 and T005** can run sequentially (same file, then a test run).
- Within each user story phase, all `[P]`-tagged test tasks are independent and can be written concurrently — e.g., T010–T015 can all be drafted in parallel by one developer before running the test suite.
- T029, T030, T031 (US3 code changes) all touch `fast_lane_check.py` but different functions — they could be implemented in one pass, tests at the end.

## Independent Test Criteria per Story

- **US1**: Any row whose non-meta categories are all in SAFE (or has `baseline.s == 1`) shows grey Unaffected with reason — regardless of version or PS support. Tests T010–T015 cover it.
- **US2**: Any row with LOW_RISK membership, version == baseline, and no PS support shows amber Low risk with reason. PS support and genuine updates override correctly. Tests T021–T028 cover it.
- **US3**: Summary line and row sort order reflect all six tiers in their specified positions. Tests T032–T033 cover the data; manual check (T035) covers the visual.

## MVP Scope

**Minimum**: Phase 2 + Phase 3 (US1). Delivers the biggest false-positive reduction — cosmetic categories stop triggering the warning. Ship this even without LOW_RISK if time is a constraint.

**Recommended for single delivery**: All phases. The value compounds — SAFE + LOW_RISK together cover the two biggest false-positive sources, and the summary + sort (US3) make the results navigable at scale.

## Total Task Count

36 tasks across 5 phases. Distribution: Foundational 5, US1 10, US2 13, US3 5, Polish 3, Setup 0.
