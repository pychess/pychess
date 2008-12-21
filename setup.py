#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gettext
gettext.install("pychess", localedir="lang", unicode=1)

from imp import load_module, find_module
const = load_module("const", *find_module("const",["lib/pychess/Utils"]))

from distutils.core import setup
from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import sys

NAME = "pychess"
VERSION = const.VERSION

DESC = "Gnome chess game"

LONG_DESC = """PyChess is a GTK+ chess game for Linux. It is designed to at the same time be easy to use, beautiful to look at, and provide advanced functions for advanced players."""

CLASSIFIERS = [
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Intended Audience :: End Users/Desktop',
    'Development Status :: 3 - Alpha',
    'Topic :: Desktop Environment :: Gnome',
    'Topic :: Games/Entertainment :: Board Games',
    'Operating System :: POSIX',
    'Natural Language :: English',
    'Natural Language :: Danish',
    'Natural Language :: Hungarian',
    'Natural Language :: Portuguese (Brazilian)'
]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

DATA_FILES = [("share/pychess",
    ["README", "AUTHORS", "LICENSE", "open.db"])]

# UI
DATA_FILES += [("share/pychess/glade", glob('glade/*.glade'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.png'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.svg'))]
DATA_FILES += [("share/pychess/flags", glob('flags/*.png'))]

# Sidepanel (not a package)
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.glade'))]
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.py'))]
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.pyc'))]
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.pyo'))]

# Data
DATA_FILES += [('share/applications', ['pychess.desktop'])]
DATA_FILES += [('share/icons/hicolor/scalable/apps', ['pychess.svg'])]
DATA_FILES += [('share/pixmaps', ['pychess.svg'])]
DATA_FILES += [("share/pychess/sounds", glob('sounds/*.ogg'))]
DATA_FILES += [('share/icons/hicolor/24x24/apps', ['pychess.png'])]
DATA_FILES += [('share/gtksourceview-1.0/language-specs', ['gtksourceview-1.0/language-specs/pgn.lang'])]

# Manpages
DATA_FILES += [('share/man/man1', ['manpages/pychess.1.gz'])]

# Language
pofile = "LC_MESSAGES/pychess"
if sys.platform == "win32":
    argv0_path = os.path.dirname(os.path.abspath(sys.executable))
    sys.path.append(argv0_path + "\\tools\\i18n")
    import msgfmt

for dir in [d for d in listdir("lang") if d.find(".svn") < 0 and isdir("lang/"+d)]:
    if sys.platform == "win32":
        file = "lang/%s/%s" % (dir,pofile)
        msgfmt.make(file+".po", file+".mo")
    else:
        os.popen("msgfmt lang/%s/%s.po -o lang/%s/%s.mo" % (dir,pofile,dir,pofile))
    DATA_FILES += [("share/locale/"+dir+"/LC_MESSAGES", ["lang/"+dir+"/"+pofile+".mo"])]

if isfile ("MANIFEST.in"):
    notlanglines = [l for l in open("MANIFEST.in") if not l.rstrip().endswith(".po")]
    file = open ("MANIFEST.in", "w")
    for line in notlanglines:
        print >> file, line[:-1]
    for dir in [d for d in listdir("lang") if d.find(".svn") < 0 and isdir("lang/"+d)]:
        print >> file, "include lang/%s/%s.po" % (dir, pofile)
    file.close()

if isfile ("MANIFEST"):
	os.remove ("MANIFEST")

# Packages

PACKAGES = ["pychess", "pychess.gfx", "pychess.ic", "pychess.ic.managers",
            "pychess.Players", "pychess.Savers", "pychess.System",
            "pychess.Utils", "pychess.Utils.lutils", "pychess.Variants",
			"pychess.widgets", "pychess.widgets.pydock" ]
# Setup

setup (
    name             = NAME,
    version          = VERSION,
    classifiers      = CLASSIFIERS,
    description      = DESC,
    long_description = LONG_DESC,
    license          = 'GPL2',
    url              = 'http://pychess.googlepages.com/home',
    download_url     = 'http://code.google.com/p/pychess/downloads/list',
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess']
)
