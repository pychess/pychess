#! /usr/bin/env python3

from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import site
import sys
import subprocess

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path = [os.path.join(this_dir, "lib")] + sys.path


msi = False
if "bdist_msi" in sys.argv[1:]:
    try:
        from cx_Freeze import setup, Executable

        msi = True
    except ImportError:
        print("ERROR: can't import cx_Freeze!")
        sys.exit(1)
else:
    from setuptools import setup

if sys.version_info < (3, 8, 0):
    print("ERROR: PyChess requires Python >= 3.8.0")
    sys.exit(1)

if sys.platform == "win32":
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        print(
            "Gtk verion is %s.%s.%s",
            (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION, Gtk.MICRO_VERSION),
        )
    except ImportError:
        print("ERROR: PyChess in Windows Platform requires to install PyGObject.")
        print("Installing from http://sourceforge.net/projects/pygobjectwin32")
        sys.exit(1)

import importlib.util
import importlib.machinery

spec = importlib.machinery.PathFinder().find_spec("pychess", ["lib"])
pychess = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pychess)

VERSION = pychess.VERSION

NAME = "pychess"

DESC = "Chess client"

LONG_DESC = """PyChess is a chess client for playing and analyzing chess games. It is
intended to be usable both for those totally new to chess as well as
advanced users who want to use a computer to further enhance their play.

PyChess has a builtin python chess engine and auto-detects most
popular chess engines (Stockfish, Rybka, Houdini, Shredder, GNU Chess,
Crafty, Fruit, and many more). These engines are available as opponents,
and are used to provide hints and analysis. PyChess also shows analysis
from opening books and Gaviota end-game tablebases.

When you get sick of playing computer players you can login to FICS (the
Free Internet Chess Server) and play against people all over the world.
PyChess has a built-in Timeseal client, so you won't lose clock time during
a game due to lag. PyChess also has pre-move support, which means you can
make (or start making) a move before your opponent has made their move.

PyChess has many other features including:
- CECP and UCI chess engine support with customizable engine configurations
- Polyglot opening book support
- Hint and Spy move arrows
- Hint, Score, and Annotation panels
- Play and analyze games in separate game tabs
- 18 chess variants including Chess960, Suicide, Crazyhouse, Shuffle, Losers, Piece Odds, and Atomic
- Reads and writes PGN, EPD and FEN chess file formats
- Undo and pause chess games
- Move animation in games
- Drag and drop chess files
- Optional game move and event sounds
- Chess piece themes with 40 built-in piece themes
- Legal move highlighting
- Direct copy+paste pgn game input via Enter Game Notation open-game dialog
- Internationalised text and Figurine Algebraic Notation (FAN) support
- Translated into 38 languages (languages with +5% strings translated)
- Easy to use and intuitive look and feel"""

CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Environment :: X11 Applications :: GTK",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: POSIX",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Games/Entertainment :: Board Games",
]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

# save
stderr = sys.stderr
stdout = sys.stdout

if not isfile("eco.db"):
    print(
        "ERROR: File 'eco.db' is missing, please generate using command:\n"
        "       # PYTHONPATH=lib python3 pgn2ecodb.py",
        file=sys.stderr,
    )
    sys.exit(1)

if not isfile(os.path.abspath("pieces/Spatial.png")):
    print(
        "ERROR: Preview images of pieces themes are missing, please generate using command:\n"
        "       # PYTHONPATH=lib python3 create_theme_preview.py",
        file=sys.stderr,
    )
    sys.exit(1)

# restore
sys.stderr = stderr
sys.stdout = stdout

DATA_FILES = [
    (
        "share/pychess",
        [
            "README.md",
            "AUTHORS",
            "ARTISTS",
            "DOCUMENTERS",
            "LICENSE",
            "TRANSLATORS",
            "pychess_book.bin",
            "eco.db",
        ],
    )
]

# UI
DATA_FILES += [("share/pychess/glade", glob("glade/*.glade"))]
DATA_FILES += [("share/pychess/glade", ["glade/background.jpg"])]
DATA_FILES += [("share/pychess/glade", glob("glade/*.png"))]
DATA_FILES += [("share/pychess/glade/16x16", glob("glade/16x16/*.png"))]
DATA_FILES += [("share/pychess/glade/48x48", glob("glade/48x48/*.png"))]
DATA_FILES += [("share/pychess/glade", glob("glade/*.svg"))]
DATA_FILES += [("share/pychess/flags", glob("flags/*.png"))]
DATA_FILES += [("share/pychess/boards", glob("boards/*.png"))]

# Data
DATA_FILES += [("share/mime/packages", ["pychess.xml"])]
DATA_FILES += [("share/metainfo", ["pychess.metainfo.xml"])]
DATA_FILES += [("share/applications", ["pychess.desktop"])]
DATA_FILES += [("share/icons/hicolor/scalable/apps", ["pychess.svg"])]
if sys.platform == "win32":
    DATA_FILES += [("share/pychess/sounds", glob("sounds/*.wav"))]
    DATA_FILES += [("share/pychess/engines", glob("engines/*.*"))]
else:
    DATA_FILES += [("share/pychess/sounds", glob("sounds/*.ogg"))]
DATA_FILES += [("share/icons/hicolor/24x24/apps", ["pychess.png"])]
DATA_FILES += [
    (
        "share/gtksourceview-3.0/language-specs",
        ["gtksourceview-3.0/language-specs/pgn.lang"],
    )
]

# Piece sets
DATA_FILES += [("share/pychess/pieces", glob("pieces/*.png"))]

if not isfile(os.path.abspath("learn/puzzles/mate_in_4.sqlite")):
    from pychess.Savers.pgn import PGNFile
    from pychess.System.protoopen import protoopen

    # Lectures, puzzles, lessons
    for filename in glob("learn/puzzles/*.pgn"):
        chessfile = PGNFile(protoopen(filename))
        chessfile.init_tag_database()

    for filename in glob("learn/lessons/*.pgn"):
        chessfile = PGNFile(protoopen(filename))
        chessfile.init_tag_database()

DATA_FILES += [("share/pychess/learn/puzzles", glob("learn/puzzles/*.olv"))]
DATA_FILES += [("share/pychess/learn/puzzles", glob("learn/puzzles/*.pgn"))]
DATA_FILES += [("share/pychess/learn/puzzles", glob("learn/puzzles/*.sqlite"))]
DATA_FILES += [("share/pychess/learn/lessons", glob("learn/lessons/*.pgn"))]
DATA_FILES += [("share/pychess/learn/lessons", glob("learn/lessons/*.sqlite"))]
DATA_FILES += [("share/pychess/learn/lectures", glob("learn/lectures/*.txt"))]

for dir in [d for d in listdir("pieces") if isdir(os.path.join("pieces", d))]:
    DATA_FILES += [("share/pychess/pieces/" + dir, glob("pieces/" + dir + "/*.svg"))]

# Manpages
DATA_FILES += [("share/man/man1", ["manpages/pychess.1.gz"])]

# Language
pofile = "LC_MESSAGES/pychess"
if sys.platform == "win32":
    argv0_path = os.path.dirname(os.path.abspath(sys.executable))
    if pychess.MSYS2:
        major, minor, micro, releaselevel, serial = sys.version_info
        msgfmt_path = argv0_path + "/../lib/python{}.{}/tools/i18n/".format(
            major, minor
        )
    else:
        msgfmt_path = argv0_path + "/tools/i18n/"
    msgfmt = f"{os.path.abspath(sys.executable)} {msgfmt_path}msgfmt.py"
else:
    msgfmt = "msgfmt"

pychess_langs = []
for dir in [d for d in listdir("lang") if isdir("lang/" + d) and d != "en"]:
    if sys.platform == "win32":
        command = f"{msgfmt} lang/{dir}/{pofile}.po"
    else:
        command = "{} lang/{}/{}.po -o lang/{}/{}.mo".format(
            msgfmt, dir, pofile, dir, pofile
        )
    subprocess.call(command.split())
    DATA_FILES += [
        ("share/locale/" + dir + "/LC_MESSAGES", ["lang/" + dir + "/" + pofile + ".mo"])
    ]
    pychess_langs.append(dir)

PACKAGES = []

if msi:
    if pychess.MSYS2:
        gtk_data_path = sys.prefix
        gtk_exec_path = os.path.join(sys.prefix, "bin")
        lang_path = os.path.join(sys.prefix, "share", "locale")
    else:
        # Get the site-package folder, not everybody will install
        # Python into C:\PythonXX
        site_dir = site.getsitepackages()[1]
        gtk_data_path = os.path.join(site_dir, "gnome")
        gtk_exec_path = os.path.join(site_dir, "gnome")
        lang_path = os.path.join(site_dir, "gnome", "share", "locale")

    # gtk3.0 .mo files
    gtk_mo = [
        f + "/LC_MESSAGES/gtk30.mo" for f in os.listdir(lang_path) if f in pychess_langs
    ]

    # Collect the list of missing dll when cx_freeze builds the app
    gtk_exec = [
        "libgtksourceview-3.0-1.dll",
        "libjpeg-8.dll",
        "librsvg-2-2.dll",
        "libwinpthread-1.dll",
    ]

    # We need to add all the libraries too (for themes, etc..)
    gtk_data = [
        "etc",
        "lib/gdk-pixbuf-2.0",
        "lib/girepository-1.0",
        "share/icons/Adwaita/icon-theme.cache",
        "share/icons/Adwaita/index.theme",
        "share/icons/Adwaita/16x16",
        "share/icons/Adwaita/scalable",
        "share/glib-2.0",
    ]

    # Create the list of includes as cx_freeze likes
    include_files = []
    for mo in gtk_mo:
        mofile = os.path.join(lang_path, mo)
        if os.path.isfile(mofile):
            include_files.append((mofile, "share/locale/" + mo))

    for dll in gtk_exec:
        include_files.append((os.path.join(gtk_exec_path, dll), dll))

    # Let's add gtk data
    for lib in gtk_data:
        include_files.append((os.path.join(gtk_data_path, lib), lib))

    base = None
    # Lets not open the console while running the app
    if sys.platform == "win32":
        base = "Win32GUI"

    executables = [
        Executable(
            "pychess",
            base=base,
            icon="pychess.ico",
            shortcut_name="PyChess",
            shortcut_dir="DesktopFolder",
        ),
        Executable(
            script="lib/__main__.py", target_name="pychess-engine.exe", base=base
        ),
    ]

    bdist_msi_options = {
        "upgrade_code": "{5167584f-c196-428f-be40-4c861025e90a}",
        "add_to_path": False,
    }

    perspectives = ["pychess.perspectives"]
    for persp in ("welcome", "games", "fics", "database", "learn"):
        perspectives.append("pychess.perspectives.%s" % persp)

    build_exe_options = {
        "path": sys.path + ["lib"],
        "includes": ["gi"],
        "packages": [
            "asyncio",
            "gi",
            "sqlalchemy.dialects.sqlite",
            "sqlalchemy.sql.default_comparator",
            "pexpect",
            "pychess",
        ]
        + perspectives,
        "include_files": include_files,
    }
    if pychess.MSYS2:
        build_exe_options["excludes"] = ["tkinter"]
    else:
        build_exe_options["include_msvcr"] = True

    kwargs = dict(
        options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
        executables=executables,
    )

else:
    PACKAGES = [
        "pychess",
        "pychess.gfx",
        "pychess.ic",
        "pychess.ic.managers",
        "pychess.Players",
        "pychess.Savers",
        "pychess.System",
        "pychess.Utils",
        "pychess.Utils.lutils",
        "pychess.Variants",
        "pychess.Database",
        "pychess.widgets",
        "pychess.widgets.pydock",
        "pychess.perspectives",
        "pychess.perspectives.welcome",
        "pychess.perspectives.games",
        "pychess.perspectives.fics",
        "pychess.perspectives.database",
        "pychess.perspectives.learn",
        "pychess.external",
    ]

    kwargs = {}

setup(
    name=NAME,
    version=VERSION,
    author="Pychess team",
    author_email="pychess-people@googlegroups.com",
    maintainer="Thomas Dybdahl Ahle",
    classifiers=CLASSIFIERS,
    keywords="python gtk chess xboard gnuchess game pgn epd board linux",
    description=DESC,
    long_description=LONG_DESC,
    license="GPL3",
    url="https://pychess.github.io/",
    download_url="https://github.com/pychess/pychess/releases",
    python_requires=">=3.8",
    install_requires=[
        "pexpect",
        "psutil",
        "pycairo",
        "PyGObject",
        "SQLAlchemy>=2",
        "websockets",
    ],
    extras_require={
        "gbulb": [
            "gbulb",
        ],
    },
    package_dir={"": "lib"},
    packages=PACKAGES,
    data_files=DATA_FILES,
    scripts=["pychess"],
    **kwargs,
)
