# Creations Cleanup Tool — Forward Research

**Date**: 2026-04-12

## Motivation

After a Starfield update, many players report broken games and reach for "nuke and reinstall." A cleanup tool in the toolkit could offer a targeted alternative: wipe all non-vanilla creation files from `Data/` and trim `Plugins.txt` / `ContentCatalog.txt`, without touching the base game install. Faster than a Steam verify + manual deletion; safer than a full reinstall.

## Why this was initially dismissed

The natural approach — "use the Creations API's `summaryPC.json` to enumerate every file belonging to each creation, then delete those" — fails for **paid creations**. Bethesda's API returns the file list only for free creations; for paid ones the `download_url` in the `summary` slot is an empty string (verified live against the API). Paid creations are also the biggest (Watchtower 1.47 GB, Trackers Alliance, etc.), so API-derived cleanup would miss the files that most deserve cleaning.

Additional concern raised by Kinggath: `summaryPC.json` can desync from the actual published archive anyway — one updates without the other. So even for free creations, the API is not a reliable source of truth.

## Why it's still achievable — disk-driven approach

API coverage is **not required**. The Starfield naming convention is consistent enough that we can derive every file belonging to a plugin from the plugin's basename + the Data/ directory listing:

```
<PluginBase>.esm            ← the plugin itself
<PluginBase>.cdx            ← container index (optional)
<PluginBase> - Main.ba2     ← main archive
<PluginBase> - Textures.ba2 ← textures archive
<PluginBase> - Voices_*.ba2 ← voice archives
<PluginBase> - *.ba2        ← any other per-plugin BA2
```

This works for paid and free creations alike — no API calls, no authentication gating.

## Proposed algorithm

1. **Load Plugins.txt** → collect every `*.esm`/`*.esp`/`*.esl` name.
2. **Filter out vanilla masters** against a hardcoded allowlist:
   - `Starfield.esm`
   - `Constellation.esm`
   - `OldMars.esm`
   - `ShatteredSpace.esm`
   - `BlueprintShips-Starfield.esm`
   - `SFBGS00x.esm` (any BGS marketplace base)
   - Anything shipped in the base game's own `Data/` before any creation installs
   - Safest source of truth: whatever `Data/` contained *before* any creations were added. We can snapshot that at first-run or bundle a known list.
3. **For each non-vanilla plugin basename**, collect and preview deletion candidates:
   - `Data/<basename>.esm`
   - `Data/<basename>.cdx`
   - Glob `Data/<basename> - *.ba2`
4. **Handle loose-file creations** (rare — <1%):
   - If the creation *is* in our catalogue AND has a `plugin_summary.Files` list available, cross-reference any non-`.ba2` / non-`.esm` entries in that list and include them in the deletion set.
   - For creations with no summary data (paid ones), we can't clean loose files they might ship. Accept this as a known gap — surface it in the dry-run report so the user can finish manually.
5. **Trim Plugins.txt** by removing every non-vanilla entry.
6. **Trim ContentCatalog.txt** in `Documents/My Games/Starfield/` (remove the non-vanilla creation entries; keep the file with just vanilla content).
7. **Preserve `Saves/`** — saves referencing the removed plugins will have orphan references, but that's the user's choice; saves are never deleted by a cleanup tool.

## UX shape

- **Dry-run first, always**: preview dialog shows a categorized list:
  - Plugins to remove (N)
  - BA2 archives to remove (N, total size)
  - Plugins.txt entries to trim (N)
  - ContentCatalog.txt entries to trim (N)
  - Loose files we can't verify (N) — manual follow-up suggested
- **Confirmation**: explicit typed confirmation (e.g., type "WIPE" to proceed) for destructive scope.
- **Backup option**: copy `Plugins.txt` and `ContentCatalog.txt` to `Data/_toolkit_backup/` before editing, so the user can undo the metadata side even if files are already gone.
- **No uninstall of the paid entitlement**: we cannot and should not remove the user's ownership record. Re-downloading is a Steam/Creations UI action.

## Known limitations

- **Shared BA2s**: multi-plugin creations that bundle their own BA2s work fine (each has its own namespace). True cross-creation BA2 sharing is not a documented pattern in Starfield.
- **Edit-in-place vs create-new**: some creations use Creation Kit plugins that reference assets in base-game BA2s. We never touch those.
- **Script Extender and community tools**: a full wipe also removes SFSE's installed plugins (`*.dll` in `SFSE/Plugins/`) only if SFSE is loaded via a plugin entry — otherwise those live outside `Data/` and are unaffected. Consider surfacing this in the preview.
- **Documents/My Games state**: we trim ContentCatalog.txt but don't touch `LOOrder.txt`, `Starfield.ccc`, etc. Needs validation — some of these regenerate on next launch.

## Scope estimate

Small-to-medium feature:
- ~1 day for the scan+preview logic
- ~1 day for the dialog and backup flow
- ~1 day for testing (multiple install states — fresh, partial, full, broken)

Reasonable to lift into `specs/NNN-creations-cleanup/` when there's appetite.

## Decision deferred

Not blocking anything. Leaving this here for when the toolkit matures to the "post-install maintenance" phase. The API-coverage limitation does not prevent the tool from working — it only limits our ability to handle the rare loose-file case for paid creations, which is an acceptable trade-off if the alternative is "wipe everything manually."
