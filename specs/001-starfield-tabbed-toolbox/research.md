# Research: Starfield Tabbed GUI Toolbox

## Decision 1: GUI Framework

**Decision**: customtkinter

**Rationale**: Best balance of KISS, modern appearance, and small PyInstaller
bundle size (~40-60 MB vs ~150-200 MB for Qt). Built on tkinter (ships with
Python), so zero heavyweight dependencies. MIT license. Provides `CTkTabview`
for tabs, standard `tkinter.filedialog` for file browsers, and `ttk.Treeview`
for list/table display. PyInstaller compatibility is excellent with no special
config needed.

**Alternatives considered**:
- tkinter/ttk: Simplest but dated appearance. Viable fallback.
- PyQt6/PySide6: Overkill, heavy bundle, licensing complexity (GPL/LGPL).
- wxPython: Aging community, no clear advantage over customtkinter.
- Dear ImGui: Not suited for traditional desktop app paradigm.

## Decision 2: Dependency Manager

**Decision**: uv (by Astral)

**Rationale**: Fastest Python dependency resolver available (Rust-based,
10-100x faster than pip/pipenv). Full lockfile support (`uv.lock`). Rapidly
becoming the de-facto standard in the Python ecosystem, replacing pipenv and
competing strongly with poetry. Excellent Windows support. Works seamlessly
with PyInstaller workflows. Single binary, minimal config via `pyproject.toml`.

**Alternatives considered**:
- pipenv: Declining adoption, very slow resolution, fair Windows support.
- poetry: Mature lockfiles but slow resolution, heavier config.
- pdm: Growing but niche. No clear advantage over uv.
- hatch: Good for publishing, but uv is faster and simpler for app dev.

## Decision 3: Starfield File Formats

### Plugins.txt

**Location**: `%LOCALAPPDATA%\Starfield\Plugins.txt`

**Format**: Plain text, one plugin filename per line. Lines prefixed with `*`
indicate the plugin is active/enabled. Lines without `*` or prefixed with `#`
are disabled or comments. The order of lines determines load order.

Example:
```
*ccBGSFO4001-PipBoy(Black).esl
*ccBGSFO4003-PipBoy(Camo01).esl
DLCRobot.esm
```

### ContentCatalog.txt

**Location**: `<Starfield Install>/Starfield/ContentCatalog.txt` (in the game
root, not the Data folder).

**Format**: JSON-like structure (actually a single-line or multi-line text
with colon-delimited entries). Each entry is keyed by a content ID and
contains fields including:
- `Title` — display name of the Creation
- `Version` — version string
- `AchievementSafe` — whether it disables achievements
- `Files` — list of associated plugin filenames

The exact format may vary between Bethesda game engine versions. The parser
should be tolerant and extract what it can.

### Steam Library Detection

**Primary method**: Read Steam's `libraryfolders.vdf` file.

**Location**: `<Steam Install>/steamapps/libraryfolders.vdf`

**Steam install location**: Found via Windows Registry at
`HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam\InstallPath` (or
`HKEY_CURRENT_USER\SOFTWARE\Valve\Steam\SteamPath`).

**Format of libraryfolders.vdf**: Valve KeyValues format (VDF). Each numbered
entry contains a `path` field pointing to a Steam library folder. Starfield's
app ID is `1716740`. Check each library's
`<path>/steamapps/common/Starfield/` for a valid installation.

## Decision 4: PyInstaller Configuration

**Decision**: Use `--onefile` mode with `--windowed`.

**Rationale**: Single exe is simpler to distribute and for users to manage.
PyInstaller is NOT a runtime dependency — it is installed dynamically at
build time only.

**Proven patterns**:
- PyInstaller installed at build time in build script, not in dependency file
- Version stamping: inject version into `_version.py` before build
- Asset bundling: `--add-data` for icon/assets, resolved at runtime via
  `sys._MEIPASS` when frozen, `Path(__file__).parent` when running from source
- Hidden imports declared for dynamically-loaded modules
- Build artifacts go in `build/` directory (not checked in)

**Windows app requirements**:
- Custom `.ico` icon via `--icon` flag and `--add-data` for runtime access
- Set `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID()` in
  the app's `__main__` to get proper taskbar grouping and icon display
- Use `--windowed` flag (no console window for GUI app)
- Asset path resolution pattern:
  ```python
  if getattr(sys, "frozen", False):
      base = Path(sys._MEIPASS) / "assets"
  else:
      base = Path(__file__).parent.parent / "assets"
  ```

**Build orchestration**: Makefile as entrypoint for both manual and CI builds,
delegating to shell scripts in `bin/`. Pattern from reference project:
- `make build` → `bin/build-win.sh` (accepts optional version argument)
- Build script: installs PyInstaller if needed, stamps version, runs build
- CI and developer use identical `make build` target

**GitHub Actions workflow**:
- Trigger on tag push matching `[0-9]*` (e.g., `git tag 1.0.0 && git push --tags`)
- Use `windows-latest` runner
- Install uv, install dependencies, run `make build`
- Rename exe with version from tag
- Upload via `softprops/action-gh-release` to attach exe to release

**Alternatives considered**:
- `--onedir`: Faster startup, fewer AV issues, but more complex distribution
  (zip of directory vs single file). Chose `--onefile` for user simplicity and
  consistency with reference project.

## Decision 5: File Change Monitoring

**Decision**: Use `watchdog` library for file system monitoring.

**Rationale**: Lightweight, well-maintained Python library for monitoring file
system events. Can watch Plugins.txt and ContentCatalog.txt for changes and
trigger a staleness indicator. Much simpler than polling. Works well on
Windows via the ReadDirectoryChangesW API.

**Alternative considered**:
- Manual polling with os.stat: Simpler but wastes CPU and has latency.
  watchdog is a justified dependency per the Minimal Dependencies principle
  because it provides significant value over manual polling.

## Decision 6: Bethesda Creation Store Version Checking

**Decision**: Web scraping of Bethesda's Creations platform.

**Rationale**: Bethesda does not provide a public API for Creation metadata.
The version check feature will need to scrape the Creations catalog page or
use any undocumented API endpoints the Bethesda.net launcher uses. This is
inherently fragile — the implementation should isolate the scraping logic
behind a clean interface so it can be swapped if an API becomes available or
the page structure changes.

**Dependencies**: `httpx` for HTTP requests (modern, async-capable,
well-maintained). Parsing with `beautifulsoup4` if HTML scraping is needed,
or plain JSON parsing if an API endpoint is found.

**Risk**: Scraping may break with site changes. The feature should degrade
gracefully (show error, don't crash). This is documented in the spec edge
cases.
