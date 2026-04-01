# Contract: CreationDetailsDialog

**Type**: UI Component (reusable dialog)

## Public Interface

### Constructor

```
CreationDetailsDialog(parent, display_name, info, thumbnail_image=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| parent | CTk widget | Parent window for positioning |
| display_name | str | Creation name (used as dialog title and header) |
| info | CreationInfo \| None | Cached metadata; None fields show "n/a" |
| thumbnail_image | PIL.Image \| None | Pre-downloaded thumbnail; None shows placeholder |

### Behavior

- Opens as a non-modal `CTkToplevel` window
- Visible in OS task switcher (Alt+Tab) — same pattern as DiffDialog
- No return value (informational only)
- Closes via window close button, Escape key, or "Close" button
- Can be opened multiple times concurrently (e.g., comparing two creations)

### Layout

1. **Header**: Thumbnail (if available) + Title in large bold text
2. **Metadata grid**: Author, Version, Price, Size, Created, Updated, Achievement Friendly
3. **Categories**: Tag-style display or comma-separated list
4. **Description**: Full text in scrollable area
5. **Footer**: Close button

### Price Display

| Value | Display |
|-------|---------|
| 0 | "Free" |
| > 0 | "{value} Credits" |
