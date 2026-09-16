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
elif [ -d "/usr/local" ] && [ -x "/usr/local/bin/brew" ]; then
    BREW_PREFIX="/usr/local"
elif command -v brew >/dev/null 2>&1; then
    BREW_PREFIX="$(brew --prefix)"
else
    BREW_PREFIX=""
fi

if [ -n "$BREW_PREFIX" ]; then
    export GI_TYPELIB_PATH="${BREW_PREFIX}/lib/girepository-1.0:${GI_TYPELIB_PATH:-}"
    export DYLD_FALLBACK_LIBRARY_PATH="${BREW_PREFIX}/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
    export XDG_DATA_DIRS="${BREW_PREFIX}/share:${XDG_DATA_DIRS:-}"
    export GTK_PATH="${BREW_PREFIX}:${GTK_PATH:-}"
    export PATH="${BREW_PREFIX}/bin:${PATH}"
fi

# Prefer the Homebrew Python: PyGObject is built against it, so the system
# Python cannot import Gtk even when the brew formulae are installed.
if [ -n "$BREW_PREFIX" ] && [ -x "${BREW_PREFIX}/bin/python3" ]; then
    PY="${BREW_PREFIX}/bin/python3"
else
    PY="python3"
fi

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

exec "$PY" pychess "$@"
