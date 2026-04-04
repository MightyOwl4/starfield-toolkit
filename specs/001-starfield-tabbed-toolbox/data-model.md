# Data Model: Starfield Tabbed GUI Toolbox

## Entities

### GameInstallation

Represents a detected or configured Starfield installation.

| Field            | Type   | Description                                      |
| ---------------- | ------ | ------------------------------------------------ |
| game_root        | Path   | Root folder of Starfield install                 |
| data_dir         | Path   | `<game_root>/Data` — contains plugin files       |
| content_catalog  | Path   | `<game_root>/ContentCatalog.txt`                 |
| plugins_txt      | Path   | `%LOCALAPPDATA%/Starfield/Plugins.txt`           |
| source           | str    | How detected: "auto-steam", "manual", "persisted"|
| is_valid         | bool   | Whether paths exist and contain expected files    |

**Validation rules**:
- `game_root` must exist as a directory
- `data_dir` must exist and contain at least one `.esm` file
- `content_catalog` must exist (warning if missing, not blocking)
- `plugins_txt` must exist (warning if missing)

### Creation

Represents a single Bethesda Creation store item installed locally.

| Field              | Type        | Description                                    |
| ------------------ | ----------- | ---------------------------------------------- |
| content_id         | str         | Unique ID from ContentCatalog.txt              |
| display_name       | str         | Full Creation name (from ContentCatalog)       |
| author             | str         | Creation author                                |
| installed_version  | str         | Version string from ContentCatalog             |
| plugin_files       | list[str]   | Associated .esm/.esp/.esl filenames            |
| load_position      | int or None | Position in Plugins.txt load order (None if not in load order) |
| is_active          | bool        | Whether the plugin is enabled in Plugins.txt   |
| file_missing       | bool        | True if plugin file not found in Data dir      |
| available_version  | str or None | Latest version from online check (ephemeral)   |
| has_update         | bool        | True if available_version > installed_version  |

**State transitions for update check**:
- Initial: `available_version=None`, `has_update=False`
- After check: `available_version` populated, `has_update` computed
- After refresh: reset to initial (ephemeral)

### AppSettings

Persisted application configuration.

| Field           | Type      | Description                              |
| --------------- | --------- | ---------------------------------------- |
| game_path       | str/None  | Persisted Starfield installation path    |
| window_geometry | str/None  | Window size/position for restore         |

**Storage**: JSON file at `%APPDATA%/StarfieldToolkit/config.json`

**Startup role**: The bootstrapper reads this file first. If `game_path` is
set and valid, auto-detection is skipped entirely. This makes subsequent
launches fast and avoids registry/filesystem scanning on every start.

## Relationships

```
GameInstallation
  └── has many → Creation (via ContentCatalog.txt + Plugins.txt)

AppSettings
  └── references → GameInstallation.game_root (as game_path)
```

## Notes

- `Creation.available_version` and `Creation.has_update` are ephemeral —
  not persisted, computed only during "Check for Updates" action.
- `Creation.load_position` is derived by cross-referencing
  ContentCatalog.txt plugin filenames with Plugins.txt line order.
- Creations not in Plugins.txt (installed but not in load order) should
  still appear but with `load_position=None`.
