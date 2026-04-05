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

# Download LOOT masterlist for bundling
LOOT_MASTERLIST="$BUILD_ROOT\\loot_masterlist.yaml"
echo "Downloading LOOT Starfield masterlist..."
curl -sL "https://raw.githubusercontent.com/loot/starfield/v0.21/masterlist.yaml" \
    -o "$LOOT_MASTERLIST" || echo "Warning: Failed to download LOOT masterlist"

LOOT_DATA_FLAG=""
if [ -f "$LOOT_MASTERLIST" ]; then
    LOOT_DATA_FLAG="--add-data ${LOOT_MASTERLIST}${PATHSEP}data"
    echo "LOOT masterlist bundled."
else
    echo "Warning: Building without LOOT masterlist."
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
    $LOOT_DATA_FLAG \
    "$PROJECT_ROOT\\src\\starfield_tool\\__main__.py"

echo "=== Build complete: $DIST_DIR\\StarfieldToolkit.exe ==="

# Restore dev version
echo '__version__ = "dev"' > "$PROJECT_ROOT\\_version.py"
