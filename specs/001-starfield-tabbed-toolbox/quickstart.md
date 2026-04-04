# Quickstart: Starfield Tabbed GUI Toolbox

## Prerequisites

- Python 3.12+
- uv (install: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Windows 10/11
- make (via Git Bash or similar)

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd starfield-tool

# Install dependencies
uv sync

# Run the application
uv run python -m starfield_tool
```

## Development

```bash
# Run tests (via Makefile)
make test

# Or directly
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_parsers.py
```

## Adding a New Tool Module

1. Create `src/starfield_tool/tools/my_tool.py`:

```python
from starfield_tool.base import ToolModule, ModuleContext

class MyTool(ToolModule):
    name = "My Tool"
    description = "Does something useful"

    def initialize(self, context: ModuleContext):
        # Build your UI in context.content_frame
        # Use context.status_bar.set_task("Working...")
        pass
```

2. Register in `src/starfield_tool/tools/__init__.py`:

```python
from .my_tool import MyTool

MODULES = [
    # ... existing modules ...
    MyTool,
]
```

Done. The new tab appears automatically.

## Building the Executable

```bash
# Build via Makefile (recommended — same as CI)
make build

# Or with a specific version
bin/build-win.sh 1.2.3
```

Output: `build/win/dist/StarfieldTool.exe`

The build script:
1. Installs PyInstaller if not present
2. Stamps version into `_version.py` (from argument or "dev")
3. Runs PyInstaller `--onefile --windowed` with icon and asset bundling
4. Outputs single exe to `build/win/dist/`

## Releasing

```bash
# Tag and push to trigger GitHub Actions release
git tag 1.0.0
git push --tags
```

GitHub Actions will build the exe on `windows-latest` and attach it to
the automatically created GitHub release.

## Makefile Targets

| Target        | Description                              |
| ------------- | ---------------------------------------- |
| `make test`   | Run pytest                               |
| `make build`  | Build Windows exe via `bin/build-win.sh` |
| `make clean`  | Remove build artifacts                   |

## Project Structure

```
starfield-tool/
├── src/
│   └── starfield_tool/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       ├── app.py               # Main application shell
│       ├── base.py              # ToolModule interface, ModuleContext
│       ├── models.py            # GameInstallation, Creation, AppSettings
│       ├── steam.py             # Steam library detection
│       ├── parsers.py           # Plugins.txt + ContentCatalog.txt parsers
│       ├── config.py            # Config persistence (%APPDATA%)
│       ├── status_bar.py        # Status bar widget + API
│       ├── version_checker.py   # Online version check
│       └── tools/
│           ├── __init__.py      # Module registry (MODULES list)
│           └── creation_load_order.py  # First tool
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── fixtures/                # Test data (fake Starfield files)
│   ├── test_models.py
│   ├── test_steam.py
│   ├── test_parsers.py
│   ├── test_config.py
│   ├── test_creation_load_order.py
│   ├── test_version_checker.py
│   └── test_app.py
├── assets/
│   └── icon.ico                 # Application icon
├── bin/
│   └── build-win.sh             # Build script
├── .github/
│   └── workflows/
│       ├── test.yml             # Tests on PR/push
│       └── release-win.yml      # Build exe on tag push
├── _version.py                  # Stamped at build time
├── Makefile                     # Build entrypoint
├── pyproject.toml
├── uv.lock
└── .editorconfig
```
