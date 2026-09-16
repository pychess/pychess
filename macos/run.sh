#!/usr/bin/env bash
# macOS launcher for PyChess.
#
# PyChess is a GTK/PyGObject application. On macOS the GTK typelibs, icon
# themes and GSettings schemas live under the Homebrew prefix, which is not on
# the default search paths. This wrapper detects the Homebrew prefix
# (Apple Silicon: /opt/homebrew, Intel: /usr/local), exports the environment
# variables GTK needs, and launches PyChess from the source tree.
set -euo pipefail

# Locate the Homebrew prefix.
if [ -d "/opt/homebrew" ]; then
    BREW_PREFIX="/opt/homebrew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW_PREFIX="/usr/local"
elif command -v brew >/dev/null 2>&1; then
    BREW_PREFIX="$(brew --prefix)"
else
    BREW_PREFIX=""
fi

if [ -n "$BREW_PREFIX" ]; then
    export GI_TYPELIB_PATH="${BREW_PREFIX}/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
    export DYLD_FALLBACK_LIBRARY_PATH="${BREW_PREFIX}/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
    export XDG_DATA_DIRS="${BREW_PREFIX}/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
    export GTK_PATH="${BREW_PREFIX}${GTK_PATH:+:$GTK_PATH}"
    export PATH="${BREW_PREFIX}/bin:${PATH}"
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

# Prefer the virtual environment from INSTALL_MACOS step 2, then the Homebrew
# Python: PyGObject is built against the latter, so the macOS system Python
# cannot import Gtk even when the Homebrew formulae are installed.
if [ -x "$HERE/.venv/bin/python" ]; then
    PY="$HERE/.venv/bin/python"
elif [ -n "$BREW_PREFIX" ] && [ -x "${BREW_PREFIX}/bin/python3" ]; then
    PY="${BREW_PREFIX}/bin/python3"
else
    PY="python3"
fi

exec "$PY" pychess "$@"
