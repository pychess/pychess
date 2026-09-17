# PyChess 1.2.0

PyChess 1.2.0 collects almost a year of development since the 1.1.0 release.

This release adds new time-control and language options, improves the built-in engine, fixes a number of long-standing analysis, PGN, variant and UI issues, modernizes support for current Python and GTK environments, improves running PyChess on macOS, and removes obsolete online services that can no longer be used.

As usual, many dependency, CI and maintenance updates also landed during this period. Routine automated dependency updates are intentionally not listed individually below.

## Highlights

### Asymmetric time controls

Local games can now use **different time controls for White and Black** (#2415).

Each side can have an independent starting time, increment/gain and move limit. Asymmetric time controls are also preserved in PGN using `WhiteTimeControl` and `BlackTimeControl` tags, while normal games continue to use the standard `TimeControl` tag.

This is useful for handicap games, training positions, engine testing and other situations where the two sides should not receive identical clock settings.

### Select the interface language in Preferences

A new **Language** option is available in Preferences (#2514).

PyChess no longer has to follow the operating system language: users can explicitly select one of the translations shipped with PyChess. The selected language takes effect after restarting the application.

### Faster built-in Python engine

The built-in PyChess engine received significant search optimizations (#2495).

A quiescence-search evaluation cache together with faster bit-count operations produced approximately a **21% speed improvement** in the benchmark used during development, making the bundled Python engine noticeably more efficient.

### Improved macOS support

Running PyChess from source on modern macOS has received a substantial refresh.

The installation documentation has been rewritten for current Homebrew and Python environments, including Apple Silicon and Intel Macs. PyChess now handles Homebrew's `gettext`/`libintl` locations correctly, provides a ready-made `macos/run.sh` launcher, and has dedicated macOS CI coverage.

Sound, translations, GTK, Stockfish and the other required Homebrew dependencies are now documented as part of a reproducible macOS setup.

## Long-standing bug fixes

### Engine analysis can be inserted from the initial position

Engine principal variations can now be inserted into the annotation tree even when no move has yet been played (#1947).

Previously, double-clicking an engine line did nothing until the game already had a move. This was particularly troublesome when analyzing a position loaded directly from a **custom FEN**.

Analysis variations can now start correctly from the initial position as well.

### PGN files with clock comments import correctly

PGN parsing has been fixed for lines beginning with `%` while inside a brace comment.

Such lines occur in exported games containing annotations such as Lichess `[%clk ...]` clock comments. PyChess previously interpreted them as PGN escape lines and could silently skip part of the game, causing imports to become truncated or incorrect.

This fixes, among other cases, the long-standing Chess960 import problem reported in #2214.

### Side panels can no longer disappear completely

Docked panels now retain their minimum GTK size instead of allowing their divider to be dragged all the way to zero (#2015).

Previously it was possible to completely hide the moves, score or other side panels and then have difficulty finding the divider required to restore them.

### Better high-DPI rendering in the Hints panel

The engine score display in the Hints panel now uses GTK/Pango's actual font metrics and DPI scaling instead of a hard-coded font size (#1958).

This fixes clipped or oversized evaluation text on high-DPI displays and improves rendering across different desktop font settings.

### Setup Position now renders the selected variant correctly

The Setup Position editor now keeps its editing behavior separate from the **variant being displayed**.

This fixes several variant-specific rendering problems when editing or pasting FEN positions.

In particular, **S-Chess/Seirawan Chess** positions now always use the appropriate piece graphics, including Hawk and Elephant pieces, independently of the user's currently selected normal chess piece set. This fixes the long-standing crash reported in #1843.

ASEAN-family variants also use their appropriate board and piece rendering when displayed in the setup editor.

## Variant correctness improvements

### Cambodian/Ouk special moves

Support for the special first-move rules of **Cambodian Chess (Ouk Chatrang)** has been completed (#2003).

The special king and queen move rights are now handled correctly as part of the position state and FEN representation. This includes losing the appropriate rights after moving or capture, the special restriction involving an opposing rook aiming along the king's rank or file, correct handling while the king is in check, position hashing, undo, and restoration of the rights from FEN.

Several edge cases in special-move generation were fixed as part of this work.

### Chess960 setup and castling

Chess960/Fischer Random castling handling in the Setup Position dialog has been substantially corrected (#2503).

PyChess now properly understands and preserves X-FEN file-letter castling rights when loading and saving custom Chess960 positions, and unusual or incomplete setup positions are handled more robustly.

## Other user-facing improvements

### Startup version checks can be disabled

Preferences now include a **Check for new versions at startup** option.

Users who do not want PyChess to contact GitHub when the application starts can disable the check while still using the normal manual update-check functionality.

Version comparison itself has also been corrected to compare numeric version components properly.

### More reliable sound playback

Sound handling on Linux and macOS has been simplified and made more robust.

PyChess now uses GStreamer directly inside the main GTK/GLib process instead of starting a separate Python sound-player subprocess. GStreamer is initialized only when sound is first needed, and playback errors and missing sound files are handled more cleanly.

### More reliable external-engine shutdown

Fixed a long-standing issue where a paused/stopped chess engine could remain running after its game was closed (#2468).

PyChess now resumes such a process before terminating it, preventing affected engines from being left running in the background.

## Platform and packaging changes

### Python 3.10 or newer is now required

Support for Python 3.9 and older has been dropped (#2406).

The minimum supported Python version is now **Python 3.10**.

### GTK / asyncio integration modernization

PyChess now uses PyGObject's native `GLibEventLoopPolicy`, replacing the older `gbulb` integration (#2489).

This removes another aging compatibility layer and improves integration between GTK's event loop and Python's asyncio infrastructure.

### Windows packaging

Windows packaging has been updated for compatibility with current versions of `cx_Freeze`, including cx_Freeze 8 and newer (#2446).

### Linux desktop packaging

Installation and desktop metadata have received several cleanups, including replacing the obsolete `gnome-icon-theme` dependency with `adwaita-icon-theme` and modernizing the AppStream metadata.

## Removed obsolete online and remote-game services

Several online chess services and remote-game providers used by PyChess have disappeared, changed their APIs, or stopped providing the interfaces that PyChess relied on.

Their non-functional integrations have therefore been removed rather than kept as broken options.

### ICC online play

**ICC (Internet Chess Club) online play is no longer supported.**

ICC stopped providing the legacy telnet server used by traditional third-party chess clients such as PyChess. The now-unusable ICC connection, timestamp and datagram protocol implementation has therefore been removed from PyChess.

**FICS online play remains supported, including Timeseal.**

### Removed remote-game providers

The obsolete game-retrieval integrations for the following services have also been removed:

- FICGS.com (#2400)
- ICCF.com (#2434)
- Chess Samara (#2467)
- PlayOK (#2526)
- ChessPastebin.com and GameKnot.com (#2533)

These were remote-game loading integrations rather than PyChess's normal local game functionality.

## Development and maintenance

The project's development environment has been significantly modernized (#2483).

Project and dependency configuration is now centered around `pyproject.toml`, `uv` is supported for creating and running the development environment, Ruff is used for formatting and linting, and Pyright provides gradual static type checking.

The test suite has also gained regression coverage for several of the fixes above, including Cambodian special moves, analysis variations starting from custom FEN positions, variant-specific piece rendering, PGN comments, dock sizing and GStreamer behavior.

CI and packaging infrastructure have received numerous reliability and compatibility improvements, including explicit runtime limits to prevent jobs from becoming stuck indefinitely.

Many Python packages, GitHub Actions and development tools have been updated since 1.1.0. Routine automated dependency bumps are intentionally omitted from this changelog.

## Thanks

Thanks to everyone who contributed code, translations, bug reports and testing since PyChess 1.1.0.

Several bugs fixed in this release had remained open for years, so special thanks also go to the users who originally reported them and provided reproducible examples.