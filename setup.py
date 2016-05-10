# -*- coding: UTF-8 -*-

from __future__ import print_function

from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import site
import sys

from imp import load_module, find_module
pychess = load_module("pychess", *find_module("pychess",["lib"]))

msi =False
if len(sys.argv) > 1 and sys.argv[1] == "bdist_msi":
    try:
        from cx_Freeze import setup, Executable
        from cx_Freeze.windist import bdist_msi
        msi = True
    except ImportError:
        print("ERROR: can't import cx_Freeze!")
        sys.exit(1)

    import msilib

    # Monkeypatching cx_freezee to do per user installer
    class peruser_bdist_msi(bdist_msi):
        def add_properties(self):
            metadata = self.distribution.metadata
            props = [
                    ('DistVersion', metadata.get_version()),
                    ('DefaultUIFont', 'DlgFont8'),
                    ('ErrorDialog', 'ErrorDlg'),
                    ('Progress1', 'Install'),
                    ('Progress2', 'installs'),
                    ('MaintenanceForm_Action', 'Repair'),
                    ('ALLUSERS', '2'),
                    ('MSIINSTALLPERUSER','1')
            ]
            email = metadata.author_email or metadata.maintainer_email
            if email:
                props.append(("ARPCONTACT", email))
            if metadata.url:
                props.append(("ARPURLINFOABOUT", metadata.url))
            if self.upgrade_code is not None:
                props.append(("UpgradeCode", self.upgrade_code))
            msilib.add_data(self.db, 'Property', props)
    bdist_msi.add_properties = peruser_bdist_msi.add_properties
else:
    from distutils.core import setup

from distutils.command.register import register

if sys.version_info < (2, 7, 0):
    print('ERROR: PyChess requires Python >= 2.7')
    sys.exit(1)

if sys.platform == "win32":
    try:
        from gi.repository import Gtk
    except ImportError:
        print('ERROR: PyChess in Windows Platform requires to install PyGObject.')
        print('Installing from http://sourceforge.net/projects/pygobjectwin32')
        sys.exit(1)

VERSION = pychess.VERSION

NAME = "pychess"

# We have to subclass register command because
# PyChess from another author already exist on pypi.
class RegisterCommand(register):
    def run(self):
        self.distribution.metadata.name = "PyChess-%s" % pychess.VERSION_NAME
        register.run(self)

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
    ["README.md", "AUTHORS", "ARTISTS", "DOCUMENTERS", "LICENSE", "TRANSLATORS", "pychess_book.bin", "eco.db"])]

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
DATA_FILES += [('share/menu', ['menu/pychess'])]
DATA_FILES += [('share/pixmaps', ['pychess.svg', 'pychess.xmp'])]
if sys.platform == "win32":
    DATA_FILES += [("share/pychess/sounds", glob('sounds/*.wav'))]
    DATA_FILES += [("share/pychess/engines", glob('engines/*.*'))]
else:
    DATA_FILES += [("share/pychess/sounds", glob('sounds/*.ogg'))]
DATA_FILES += [('share/icons/hicolor/24x24/apps', ['pychess.png'])]
DATA_FILES += [('share/gtksourceview-3.0/language-specs', ['gtksourceview-3.0/language-specs/pgn.lang'])]

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

pychess_langs = []
for dir in [d for d in listdir("lang") if isdir("lang/"+d) and d != "en"]:
    if sys.platform == "win32":
        file = "lang/%s/%s" % (dir,pofile)
        msgfmt.make(file+".po", file+".mo")
    else:
        os.popen("msgfmt lang/%s/%s.po -o lang/%s/%s.mo" % (dir,pofile,dir,pofile))
    DATA_FILES += [("share/locale/"+dir+"/LC_MESSAGES", ["lang/"+dir+"/"+pofile+".mo"])]
    pychess_langs.append(dir)

PACKAGES = []

if msi:
    # TODO: cx_freeze doesn't allow letters in version
    #VERSION = "0.12.0"

    ## Get the site-package folder, not everybody will install
    ## Python into C:\PythonXX
    site_dir = site.getsitepackages()[1]
    include_dll_path = os.path.join(site_dir, "gnome")
    lang_path = os.path.join(site_dir, "gnome", "share", "locale")

    ## gtk3.0 .mo files
    gtk_mo = [f + "/LC_MESSAGES/gtk30.mo" for f in os.listdir(lang_path) if f in pychess_langs]

    ## Collect the list of missing dll when cx_freeze builds the app
    missing_dll = [f for f in os.listdir(include_dll_path) if \
                    (f.endswith(".dll") or (f.startswith("gspawn") and f.endswith(".exe")))]

    ## We need to add all the libraries too (for themes, etc..)
    gtk_libs = ['etc',
                'share/icons/adwaita',
                'share/themes/adwaita',
                'lib/gio',
                'lib/gdk-pixbuf-2.0',
                'lib/girepository-1.0',
                'share/glib-2.0'
    ]

    ## Create the list of includes as cx_freeze likes
    include_files = []
    for mo in gtk_mo:
        mofile = os.path.join(lang_path, mo)
        if os.path.isfile(mofile):
            include_files.append((mofile, "share/locale/" + mo))

    for dll in missing_dll:
        include_files.append((os.path.join(include_dll_path, dll), dll))

    ## Let's add gtk libraries folders and files
    for lib in gtk_libs:
        include_files.append((os.path.join(include_dll_path, lib), lib))

    base = None
    ## Lets not open the console while running the app
    if sys.platform == "win32":
        base = "Win32GUI"

    executables = [Executable("pychess",
                            base=base,
                            icon="pychess.ico",
                            shortcutName="PyChess",
                            shortcutDir="DesktopFolder"),
                    Executable(script="lib/__main__.py",
                            targetName="pychess-engine.exe",
                            base=base),
                            ]

    bdist_msi_options = {
        "upgrade_code": "{5167584f-c196-428f-be40-4c861025e90a}",
        "add_to_path": True}

    build_exe_options = {
        "compressed": False,
        "include_msvcr": True,
        "path": sys.path + ["lib"],
        "includes": ["gi"],
        "packages": ["gi", "pychess"],
        "include_files": include_files,
        }
else:
    PACKAGES = ["pychess", "pychess.gfx", "pychess.ic", "pychess.ic.managers",
                "pychess.Players", "pychess.Savers", "pychess.System",
                "pychess.Utils", "pychess.Utils.lutils", "pychess.Variants",
                "pychess.widgets", "pychess.widgets.pydock" ]

    build_exe_options = {}
    bdist_msi_options = {}
    executables = {}

setup (
    cmdclass         = {"register": RegisterCommand},
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
    download_url     = 'http://pychess.org/download/',
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess'],
    options          = {"build_exe": build_exe_options,
                        "bdist_msi": bdist_msi_options
                        },
    executables      = executables
)
