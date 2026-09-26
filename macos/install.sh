#!/usr/bin/env bash
#
# macos/install.sh - One-command installer for PyChess on macOS.
#
# What it does
# -------------
# 1. Installs the Xcode command line tools and Homebrew if they are missing.
# 2. Installs the GTK3 stack and supporting libraries via Homebrew (these are
#    the binary dependencies PyChess needs and which pip cannot build on macOS).
# 3. Creates a virtual environment that re-uses Homebrew's PyGObject
#    (--system-site-packages) and installs PyChess into it.
# 4. Generates the locally-built data files (opening book, piece-theme previews).
# 5. Builds a self-contained, double-clickable PyChess.app in ~/Applications.
#
# Run it from inside a PyChess source checkout:
#
#     git clone https://github.com/pychess/pychess.git
#     cd pychess
#     ./macos/install.sh
#
# The resulting app is fully self-contained: the virtual environment and a copy
# of the source live inside PyChess.app/Contents/Resources, so you can move or
# rename the .app freely. Only the GTK frameworks come from Homebrew, which is
# required on macOS for any GTK application.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Locate the source tree (parent of the directory that holds this script).
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$SOURCE_DIR/setup.py" ]; then
    echo "Error: macos/install.sh must be run from inside a PyChess source" >&2
    echo "checkout (the directory that contains setup.py)." >&2
    echo "Download the source first:" >&2
    echo "    git clone https://github.com/pychess/pychess.git && cd pychess" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Helper: print a step header.
# ---------------------------------------------------------------------------
step() {
    echo ""
    echo "==> $*"
}

# ---------------------------------------------------------------------------
# 1. Xcode command line tools + Homebrew
# ---------------------------------------------------------------------------
step "Checking Xcode command line tools"
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Installing Xcode command line tools (a GUI prompt will appear)..."
    xcode-select --install || true
    # Wait until the tools are actually present.
    for _ in $(seq 1 60); do
        xcode-select -p >/dev/null 2>&1 && break
        sleep 5
    done
    if ! xcode-select -p >/dev/null 2>&1; then
        echo "Xcode command line tools did not finish installing. Please run" >&2
        echo "    xcode-select --install" >&2
        echo "and re-run this installer once the install completes." >&2
        exit 1
    fi
fi

step "Checking Homebrew"
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing from https://brew.sh ..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Make brew available in this shell.
    if [ -d "/opt/homebrew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

# Detect the Homebrew prefix (Apple Silicon vs Intel).
if [ -d "/opt/homebrew" ]; then
    BREW_PREFIX="/opt/homebrew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_PREFIX="/usr/local"
else
    BREW_PREFIX="$(brew --prefix)"
fi
eval "$(HOMEBREW_PREFIX="$BREW_PREFIX" "$BREW_PREFIX/bin/brew" shellenv)"

# ---------------------------------------------------------------------------
# 2. Binary dependencies via Homebrew
# ---------------------------------------------------------------------------
step "Installing GTK stack and supporting libraries via Homebrew"
# NOTE: PyGObject/pycairo come from the 'pygobject3' formula (built against the
# brewed GTK), so we deliberately do NOT pip-install them -- attempting to build
# PyGObject from source on macOS is what usually breaks macOS installs.
brew install python gtk+3 pygobject3 gtksourceview4 librsvg \
             gstreamer adwaita-icon-theme gettext stockfish

# 'stockfish' is optional (only needed for analysis/play against the engine).
# Continue even if it is unavailable on this formula tap.
brew install stockfish 2>/dev/null || \
    echo "Warning: 'stockfish' not installed; engine analysis will be unavailable."

# ---------------------------------------------------------------------------
# 3. Virtual environment (re-uses Homebrew's PyGObject)
# ---------------------------------------------------------------------------
APP_DIR="$HOME/Applications/PyChess.app"
VENV="$APP_DIR/Contents/Resources/venv"
SRC_DIR="$APP_DIR/Contents/Resources/src"

step "Preparing $APP_DIR"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/Resources"
mkdir -p "$APP_DIR/Contents/MacOS"

# Copy the source into the app (exclude VCS / build artefacts).
echo "Copying source tree into the app bundle..."
rsync -a --exclude='.git' --exclude='.venv' --exclude='build' \
         --exclude='dist' --exclude='*.egg-info' --exclude='__pycache__' \
         "$SOURCE_DIR/" "$SRC_DIR/"

step "Creating virtual environment"
# --system-site-packages lets the venv import Homebrew's 'gi' module instead of
# trying (and failing) to build PyGObject from source.
"$BREW_PREFIX/bin/python3" -m venv --system-site-packages "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel

step "Installing PyChess (editable, no build isolation)"
# --no-build-isolation avoids spinning up a fresh build env that would try to
# fetch PyGObject from PyPI. The brewed PyGObject satisfies setup.py's
# unpinned 'PyGObject' requirement.
pip install --no-build-isolation -e "$SRC_DIR"

step "Installing pinned pure-Python dependencies"
# Install the exact pins from requirements.txt, but skip PyGObject/pycairo
# (provided by the brewed 'pygobject3' formula).
TMP_REQ="$(mktemp)"
grep -viE '^(PyGObject|pycairo)==' "$SRC_DIR/requirements.txt" > "$TMP_REQ" || true
pip install -r "$TMP_REQ" || \
    echo "Warning: some pinned dependencies could not be installed; continuing."
rm -f "$TMP_REQ"

# ---------------------------------------------------------------------------
# 4. Locally-built data files
# ---------------------------------------------------------------------------
step "Generating opening book and piece-theme previews"
cd "$SRC_DIR"
PYTHONPATH=lib python pgn2ecodb.py
PYTHONPATH=lib python create_theme_preview.py

# ---------------------------------------------------------------------------
# 5. Build the .app wrapper
# ---------------------------------------------------------------------------
step "Writing PyChess.app"
# Version comes from the source.
PYCHESS_VERSION="$(grep -m1 '^VERSION' "$SRC_DIR/lib/pychess/__init__.py" | sed -E 's/.*"([^"]+)".*/\1/')"
sed "s/__PYCHESS_VERSION__/${PYCHESS_VERSION}/g" \
    "$SCRIPT_DIR/PyChess.app/Contents/Info.plist" \
    > "$APP_DIR/Contents/Info.plist"
cp "$SCRIPT_DIR/PyChess.app/Contents/MacOS/PyChess" \
   "$APP_DIR/Contents/MacOS/PyChess"
chmod +x "$APP_DIR/Contents/MacOS/PyChess"

step "Done"
cat <<EOF

PyChess $PYCHESS_VERSION is installed at:
    $APP_DIR

You can now launch it from Launchpad / Finder (Applications > PyChess),
or run it directly:
    open "$APP_DIR"

To run from a terminal instead:
    "$VENV/bin/python" -m pychess

Notes:
  * The GTK libraries are provided by Homebrew; keep them installed.
  * To uninstall, just drag $APP_DIR to the Trash.
  * Re-run this script any time to rebuild the app after updating the source.
EOF
