# Implementation Plan: Starfield Tabbed GUI Toolbox

**Branch**: `001-starfield-tabbed-toolbox` | **Date**: 2026-03-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-starfield-tabbed-toolbox/spec.md`

## Summary

Build a modular Python GUI application for Starfield game tools using
customtkinter. The app provides a tabbed interface where each tool is an
independent module. The first tool displays installed Bethesda Creation store
items in their load order with update checking. The architecture supports
easy addition of new tool modules via a common interface and registry pattern.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (GUI), watchdog (file monitoring),
httpx (HTTP client), beautifulsoup4 (HTML parsing for version checks)
**Storage**: JSON config file (`%APPDATA%/StarfieldToolkit/config.json`)
**Testing**: pytest
**Target Platform**: Windows 10/11
**Project Type**: Desktop GUI application
**Performance Goals**: Load order display within 3 seconds
**Constraints**: PyInstaller-compatible, single-exe distribution
**Scale/Scope**: Single-user local application, ~10-50 Creations typical
**Dependency Manager**: uv (lockfile: `uv.lock`)
**Build Tool**: PyInstaller --onefile --windowed (installed at build time, not a runtime dep)
**Build Orchestration**: Makefile → `bin/build-win.sh` (same entrypoint for manual and CI)
**CI/CD**: GitHub Actions — build exe on tag push, attach to GitHub release

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)

- **PASS**: customtkinter is the simplest framework that delivers a modern
  look. No heavyweight Qt dependency. Registry pattern for modules is a flat
  list — no plugin framework, no metaclasses, no abstract factory.
- **PASS**: Flat project structure. Models are plain dataclasses. No ORM,
  no DI container, no event bus.

### II. Test Coverage (NON-NEGOTIABLE)

- **PASS**: pytest for all functional behavior. Test strategy: unit tests
  for models/parsers/steam detection (with fixture files mimicking game
  folder structure), integration tests for the module lifecycle. GUI tests
  kept minimal — test the logic, not the pixels.
- **PASS**: Bethesda file parsers tested against real-format fixture files.

### III. Minimal Dependencies

- **PASS**: 4 runtime dependencies, each justified:
  - customtkinter: GUI framework (tkinter alone lacks modern appearance)
  - watchdog: file monitoring (significant value over manual polling)
  - httpx: HTTP client for version checks (stdlib urllib lacks modern features)
  - beautifulsoup4: HTML parsing for scraping (only if needed for version check)
- **NOTE**: beautifulsoup4 may be deferrable if a JSON API endpoint is
  found. Will evaluate during implementation.

### IV. Clear Interfaces

- **PASS**: Module interface is explicit: `name`, `description`,
  `initialize(context)`. StatusBarAPI has two methods. No hidden state.
- **PASS**: All errors surfaced to user via UI messages. No silent failures.

### Post-Design Re-check

All gates pass. No violations requiring Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/001-starfield-tabbed-toolbox/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 developer quickstart
├── contracts/
│   └── module-interface.md  # Tool module contract
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── starfield_tool/
    ├── __init__.py          # Package init, version
    ├── __main__.py          # Entry point, AppUserModelID, launch app
    ├── app.py               # Main window, tab shell, startup flow
    ├── base.py              # ToolModule ABC, ModuleContext dataclass
    ├── models.py            # GameInstallation, Creation, AppSettings
    ├── steam.py             # Steam library folder detection
    ├── parsers.py           # Plugins.txt + ContentCatalog.txt parsers
    ├── config.py            # Config load/save (%APPDATA%/StarfieldToolkit/config.json)
    ├── status_bar.py        # StatusBar widget + StatusBarAPI
    ├── version_checker.py   # Online version check (httpx + scraping)
    └── tools/
        ├── __init__.py      # MODULES registry list
        └── creation_load_order.py  # Creation Load Order tool module

tests/
├── conftest.py              # Shared fixtures, test data paths
├── fixtures/                # Test data mimicking Starfield file structure
│   ├── Plugins.txt
│   ├── ContentCatalog.txt
│   └── Data/               # Dummy .esm/.esp files
├── test_models.py           # GameInstallation, Creation model tests
├── test_steam.py            # Steam library detection tests
├── test_parsers.py          # Plugins.txt, ContentCatalog.txt parser tests
├── test_config.py           # Config persistence tests
├── test_creation_load_order.py  # Creation tool logic tests
├── test_version_checker.py  # Version check tests (mocked HTTP)
└── test_app.py              # App startup flow tests

assets/
└── icon.ico                 # Application icon (Windows .ico)

bin/
└── build-win.sh             # Build script (version stamping + PyInstaller)

.github/
└── workflows/
    ├── test.yml             # Run tests on PR/push to main
    └── release-win.yml      # Build exe on tag push, attach to release

_version.py                  # Version file (stamped at build time)
Makefile                     # Build entrypoint: make build, make test, make clean
pyproject.toml               # Project config, uv dependencies
uv.lock                      # Locked dependencies
```

**Build targets** (Makefile):
- `make test` — run pytest
- `make build` — build Windows exe via `bin/build-win.sh`
- `make clean` — remove build artifacts

**Structure Decision**: Single-package layout under `src/starfield_tool/`.
Tools live in `src/starfield_tool/tools/` as separate modules. This is the
simplest structure that supports the modular requirement. No monorepo, no
separate packages for tools. Build pattern:
Makefile delegates to shell scripts, PyInstaller installed at build time,
version stamped from git tag or "dev" default.

## Complexity Tracking

> No violations detected. All design choices pass the Constitution Check.
