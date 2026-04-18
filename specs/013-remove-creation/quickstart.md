# Quickstart: Remove Creation

## Enable the feature

1. Open the app, go to Settings.
2. Tick **Enable dangerous operations**. (Unticked is the default.)

## Remove a Creation

1. Ensure Starfield and the Bethesda launcher are fully closed.
2. Go to the **Installed Creations** tab.
3. Double-click a Creation (or click the ⓘ icon) to open its details dialog.
4. Click **Remove**. The details dialog closes and a confirmation dialog opens, listing:
   - The Plugins.txt line(s) that will be stripped (if any).
   - The files in the Data directory that will be deleted.
5. Review the list. If it looks wrong (e.g. an "out of tree" warning appears), click **Cancel**.
6. Otherwise click **Confirm**.
7. When the operation completes, a result dialog summarises what happened. The Installed Creations list refreshes automatically.

## What if the game was running?

The operation is refused at Confirm time with a clear message. Nothing is changed. Close Starfield / the launcher and try again.

## What if a file was locked?

Every unlocked file is still deleted and Plugins.txt is still updated. The result dialog names the locked file(s) and the OS reason. Close any process that might be holding the file (antivirus, explorer preview, stale game window) and retry — the operation is idempotent.

## Verify the tests

```bash
uv run pytest -x -q
```

All tests (pre-existing + new in `tests/test_removal.py` and `tests/test_game_process.py`) must pass.
