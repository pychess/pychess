# -*- coding: UTF-8 -*-

from __future__ import print_function

from imp import load_module, find_module
pychess = load_module("pychess", *find_module("pychess",["lib"]))

from distutils.core import setup
from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import sys


if sys.version_info < (2, 6, 0):
    print('ERROR: PyChess requires Python >= 2.6')
    sys.exit(1)

# To run "setup.py register" change name to "NAME+VERSION_NAME"
# because pychess from another author already exist in pypi.
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
    'Development Status :: 3 - Alpha',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Topic :: Games/Entertainment :: Board Games',
    ]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

# save
stderr = sys.stderr
stdout = sys.stdout

if not isfile("eco.db"):
    exec(open("pgn2ecodb.py").read())

if not isfile(os.path.abspath("pieces/Pychess.png")):
    exec(open("create_theme_preview.py").read())

# restore
sys.stderr = stderr
sys.stdout = stdout

DATA_FILES = [("share/pychess",
    ["README", "AUTHORS", "ARTISTS", "DOCUMENTERS", "LICENSE", "TRANSLATORS", "pychess_book.bin", "eco.db"])]

# UI
DATA_FILES += [("share/pychess/glade", glob('glade/*.glade'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.png'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.svg'))]
DATA_FILES += [("share/pychess/flags", glob('flags/*.png'))]

# Sidepanel (not a package)
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.glade'))]
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.py'))]

# Data
DATA_FILES += [('share/appdata', ['pychess.appdata.xml'])]
DATA_FILES += [('share/applications', ['pychess.desktop'])]
DATA_FILES += [('share/icons/hicolor/scalable/apps', ['pychess.svg'])]
DATA_FILES += [('share/pixmaps', ['pychess.svg'])]
DATA_FILES += [("share/pychess/sounds", glob('sounds/*.ogg'))]
DATA_FILES += [('share/icons/hicolor/24x24/apps', ['pychess.png'])]
DATA_FILES += [('share/gtksourceview-1.0/language-specs', ['gtksourceview-1.0/language-specs/pgn.lang'])]

# Piece sets
DATA_FILES += [("share/pychess/pieces", glob('pieces/*.png'))]
DATA_FILES += [("share/pychess/pieces/ttf", glob('pieces/ttf/*.ttf'))]

for dir in [d for d in listdir('pieces') if isdir(os.path.join('pieces', d)) and d != 'ttf']:
    DATA_FILES += [("share/pychess/pieces/"+dir, glob('pieces/'+dir+'/*.svg'))]

# Manpages
DATA_FILES += [('share/man/man1', ['manpages/pychess.1.gz'])]

# Language
pofile = "LC_MESSAGES/pychess"
if sys.platform == "win32":
    argv0_path = os.path.dirname(os.path.abspath(sys.executable))
    sys.path.append(argv0_path + "\\tools\\i18n")
    import msgfmt

for dir in [d for d in listdir("lang") if d.find(".svn") < 0 and isdir("lang/"+d) and d != "en"]:
    if sys.platform == "win32":
        file = "lang/%s/%s" % (dir,pofile)
        msgfmt.make(file+".po", file+".mo")
    else:
        os.popen("msgfmt lang/%s/%s.po -o lang/%s/%s.mo" % (dir,pofile,dir,pofile))
    DATA_FILES += [("share/locale/"+dir+"/LC_MESSAGES", ["lang/"+dir+"/"+pofile+".mo"])]

# Packages

PACKAGES = ["pychess", "pychess.gfx", "pychess.ic", "pychess.ic.managers",
            "pychess.Players", "pychess.Savers", "pychess.System",
            "pychess.Utils", "pychess.Utils.lutils", "pychess.Variants",
            "pychess.widgets", "pychess.widgets.pydock" ]
# Setup

setup (
    name             = NAME,
    version          = VERSION,
    author           = 'Pychess team',
    author_email     = 'pychess-people@googlegroups.com',
    maintainer       = 'Thomas Dybdahl Ahle',
    classifiers      = CLASSIFIERS,
    keywords         = 'python gtk chess xboard gnuchess game pgn epd board linux',
    description      = DESC,
    long_description = LONG_DESC,
    license          = 'GPL3',
    url              = 'http://pychess.org',
    download_url     = 'http://code.google.com/p/pychess/downloads/list',
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess']
)
