# Quickstart: Detect Broken Updates

## Open the tab

1. Launch the app.
2. Click the **Detect Broken Updates** tab in the top tab strip.

## Scan

1. Click **Scan**. The tool reads ContentCatalog, Plugins.txt, and the Data directory.
2. After ~1 second, either:
   - The flagged list appears — each row shows position, name, author, version, date, and the reason(s) it was flagged (partial files / esm without plugins.txt line / mtime skew / out of tree).
   - Or an empty-state message says no broken updates were detected.

## Delete

1. Close Starfield and the Bethesda launcher (completely, not just to the main menu).
2. In the flagged list, select one or more rows. Shift+click / Ctrl+click to multi-select.
3. Click **Delete**.
4. A confirmation dialog opens showing:
   - Every file that will be deleted, grouped by Creation.
   - Every Plugins.txt line that will be stripped.
   - A prominent warning: **this operation does NOT perform a dependency check — it is your responsibility to ensure your load order still works after these Creations are gone**.
5. Read the list. Click **Cancel** if anything looks wrong.
6. Click **Confirm** to proceed.
7. The result dialog shows:
   - An alphabetical (case-insensitive) list of the Creations that were processed, in a selectable text area. Copy this to paste into the in-game Creations menu when you re-install.
   - Per-Creation outcomes for each file: deleted, already gone, or failed with the OS reason.

## What if Starfield or the launcher was running?

Delete is refused at Confirm time with a clear error; no file or Plugins.txt line is touched. Close both and retry.

## What if a file was locked?

Every unlocked file is still deleted and Plugins.txt is still updated. The result dialog names the locked file(s) so you can free them (close the process holding them, e.g. antivirus scan) and retry — the operation is idempotent.

## Verify the tests

```bash
uv run pytest -x -q
```

All tests (pre-existing + `tests/test_broken_scan.py`) must pass.
