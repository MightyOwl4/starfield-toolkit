#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Convert to Windows paths if running in MSYS/Git Bash
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PROJECT_ROOT="$(cygpath -w "$PROJECT_ROOT")"
    PATHSEP=";"
else
    PATHSEP=":"
fi

BUILD_ROOT="$PROJECT_ROOT\\build"
DIST_DIR="$BUILD_ROOT\\dist"

echo "=== Building StarfieldToolkit v${VERSION} ==="

# Stamp version
echo "__version__ = \"${VERSION}\"" > "$PROJECT_ROOT\\_version.py"

# Install PyInstaller if needed
if ! uv run python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    uv pip install pyinstaller
fi

echo "Running PyInstaller..."
uv run pyinstaller \
    --onefile \
    --windowed \
    --name StarfieldToolkit \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_ROOT\\build" \
    --specpath "$BUILD_ROOT\\spec" \
    --icon "$PROJECT_ROOT\\assets\\icon.ico" \
    --add-data "$PROJECT_ROOT\\assets\\icon.ico${PATHSEP}assets" \
    --hidden-import _version \
    --add-data "$PROJECT_ROOT\\_version.py${PATHSEP}." \
    "$PROJECT_ROOT\\src\\starfield_tool\\__main__.py"

echo "=== Build complete: $DIST_DIR\\StarfieldToolkit.exe ==="

# Restore dev version
echo '__version__ = "dev"' > "$PROJECT_ROOT\\_version.py"
