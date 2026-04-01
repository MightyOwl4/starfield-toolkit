# Research: Creations Grid Modes & Details Dialog

**Branch**: `004-creations-grid-modes` | **Date**: 2026-04-01

## R1: Reading Cache Without Session Freshness

**Decision**: Add a new `get_cached_info_any()` function in `starfield_tool/creations.py` that calls `load_cache()` directly and converts entries via `entry_to_info()` without the `is_session_fresh()` gate.

**Rationale**: The existing `get_cached_info()` and `CreationsClient.get_cached()` both gate on session freshness. For text list mode, we need author data from cache regardless of freshness — author is an immutable field that never changes after publish (documented in `_cache.py` line 11). A new function avoids modifying the existing API contract.

**Alternatives considered**:
- Modify `get_cached_info()` to accept an `ignore_freshness` parameter — rejected because it changes the semantics of an existing function used elsewhere.
- Pass a very large `session_window` — rejected because it's a hack that obscures intent.

## R2: Thumbnail Image Display in Tkinter/CustomTkinter

**Decision**: Use `urllib.request` (stdlib) to download thumbnail images, `PIL.Image` + `PIL.ImageTk` to resize and convert to Tkinter-compatible `PhotoImage` objects. Cache downloaded images in memory (dict keyed by content_id) for the session.

**Rationale**: `ttk.Treeview` cannot display images inline natively in a mixed-column layout. The rich media grid will need a custom widget approach using `CTkFrame` rows with `CTkImage`/`CTkLabel` widgets instead of a Treeview. PIL/Pillow is the standard Python image library and is already a transitive dependency of customtkinter (`CTkImage` uses it internally). `urllib.request` avoids adding httpx as a direct dependency to the UI layer.

**Alternatives considered**:
- Use `tkinter.PhotoImage` with GIF/PNG only — rejected because Bethesda thumbnails are JPEG and need resizing.
- Use httpx (already in bethesda_creations) — acceptable but `urllib.request` keeps the UI layer dependency-free from the API layer.
- Embed images in Treeview via `image` parameter — rejected because Treeview image support is limited (one image per row, no sizing control, no mixed text+image cells).

## R3: Rich Media Grid Widget Strategy

**Decision**: Replace `ttk.Treeview` with a scrollable frame of custom `CTkFrame` row widgets when in rich media mode. Each row is a horizontal frame containing: thumbnail `CTkLabel` (with `CTkImage`), a text block frame (bold name label + description label), and standard column labels matching the text list columns.

**Rationale**: `ttk.Treeview` does not support multi-line rows, inline images at arbitrary sizes, or mixed bold/regular text within cells. A custom scrollable frame with per-row widgets is the standard approach for rich list views in Tkinter/customtkinter. The text list mode continues to use the existing `ttk.Treeview` for performance and simplicity.

**Alternatives considered**:
- Use `ttk.Treeview` with custom cell rendering — rejected because Treeview lacks the required layout flexibility.
- Use a `CTkTextbox` with embedded widgets — rejected because it's harder to manage row-level interactions (click handlers, selection, scrolling).
- Use a third-party widget library — rejected per constitution (Minimal Dependencies principle).

## R4: Details Dialog Pattern

**Decision**: Create a standalone `CreationDetailsDialog(ctk.CTkToplevel)` class in a new file `src/starfield_tool/dialogs/creation_details.py`. It follows the exact same windowing pattern as `DiffDialog`: no `grab_set()`, initial `topmost` then immediate unset, no transient binding. It accepts a `CreationInfo` object (or dict) and a display name as constructor parameters — fully decoupled from any specific tab or tool.

**Rationale**: The diff dialog pattern is proven to work correctly with Windows Alt+Tab and task switching. Using the same pattern ensures consistency. Placing it in a `dialogs/` directory (separate from `tools/`) makes the reusability intent clear and avoids circular imports.

**Alternatives considered**:
- Place in `tools/` alongside diff dialog — rejected because details dialog is not a tool; it's a shared UI component.
- Use `grab_set()` for modal behavior — rejected because the diff dialog deliberately avoids this for Windows compatibility.

## R5: Loading Placeholders in Rich Media Mode

**Decision**: When cache is cold and fetch is triggered, render placeholder rows immediately: gray rectangle for thumbnail, "Loading..." text for name, empty description. Use the existing threading pattern (daemon thread + `widget.after(0, callback)`) to replace placeholders once data arrives.

**Rationale**: Follows the established threading pattern in the codebase. Placeholders provide immediate visual feedback that the mode switch was recognized.

**Alternatives considered**:
- Show a single "Loading..." overlay instead of per-row placeholders — rejected because it doesn't convey that there will be rows of content.
- Block the UI until fetch completes — rejected because it freezes the app.

## R6: Pillow Dependency

**Decision**: Pillow is acceptable as a dependency for thumbnail display. It is already a transitive dependency of customtkinter (used by `CTkImage` internally).

**Rationale**: Constitution Principle III (Minimal Dependencies) requires justification. Pillow is not a new dependency — it's already installed via customtkinter. We're using it directly for image downloading and resizing, which `CTkImage` alone doesn't handle (it needs a PIL Image input).

**Alternatives considered**:
- Download and use raw tkinter PhotoImage — rejected because it doesn't support JPEG or arbitrary resizing.
