#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gettext
gettext.install("pychess", localedir="lang", unicode=1)

import imp
VERSION = imp.load_module("const",
          *imp.find_module("const",["lib/pychess/Utils"])).VERSION

#from pychess.System import myconf
#from pychess.Utils.const import VERSION

#myconf.set("combobox6", 1)
#myconf.set("spinbuttonM", 10)

from distutils.core import setup
from glob import glob
from os import listdir
from os.path import isdir, isfile
import os

DESC = "Gnome chess game"

LONG_DESC = """PyChess is a gtk chessgame for Linux. It is designed to a the same time be easy to use, beautyful to look at and provide advanced functions for advanced players"""

CLASSIFIERS = [
    'License :: OSI-Approved Open Source :: GNU General Public License (GPL)',
    'Intended Audience :: by End-User Class :: End Users/Desktop',
    'Development Status :: 3 - Alpha',
    'Topic :: Desktop Environment :: Gnome',
    'Topic :: Games/Entertainment :: Board Games',
    'Operating System :: POSIX',
    'User Interface :: Graphical :: Gnome',
    'User Interface :: Graphical :: Cairo',
    'User Interface :: Toolkits/Libraries :: GTK+',
    'Translations :: English',
    'Translations :: Danish',
    'Translations :: German',
    'Translations :: Dutch'
]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

DATA_FILES = [("share/games/pychess/",
    ["README", "AUTHORS", "LICENSE", "INSTALL", "open.db"])]

# UI
DATA_FILES += [("share/games/pychess/glade", glob('glade/*.glade'))]
DATA_FILES += [("share/games/pychess/glade", glob('glade/*.png'))]

# Sidepanel (not a package)
DATA_FILES += [("share/games/pychess/sidepanel", glob('sidepanel/*.glade'))]
DATA_FILES += [("share/games/pychess/sidepanel", glob('sidepanel/*.py'))]

# Data
DATA_FILES += [('share/applications', ['pychess.desktop'])]
DATA_FILES += [('share/pixmaps', ['pychess.svg'])]

# Main modules
if os.system("chmod +x lib/pychess/Players/PyChess.py") != 0:
    print "Couldn't set execution flag for PyChess Engine. try if you can do it\
            yourself (with root access"
    # TODO: Is this a good way to handle the problem?

# Language
langdirs = []
for dir in [os.path.join("lang",f) for f in listdir("lang")]:
    if dir.find(".svn") == -1 and isdir(dir):
        langdirs.append(dir)

pofile = "LC_MESSAGES/pychess.po"
DATA_FILES += [(dir, [dir+"/"+pofile]) for dir in langdirs]

if isfile ("MANIFEST.in"):
    notlanglines = [l for l in open("MANIFEST.in") if not l.rstrip().endswith(".po")]
    file = open ("MANIFEST.in", "w")
    for line in notlanglines:
        print >> file, line[:-1]
    for dir in langdirs:
        print >> file, "include %s/%s" % (dir, pofile)
    file.close()

if isfile ("MANIFEST"):
	os.remove ("MANIFEST")

# Packages

PACKAGES = ["pychess", "pychess.gfx", "pychess.Players", "pychess.Savers",
            "pychess.System", "pychess.Utils", "pychess.widgets"]

# Setup

setup (
    name             = 'PyChess',
    version          = VERSION,
    classifiers      = CLASSIFIERS,
    description      = DESC,
    long_description = LONG_DESC,
    author           = 'Thomas Dybdahl Ahle',
    author_email     = 'lobais@gmail.com',
    license          = 'GPL2',
    url              = 'http://pychess.googlepages.com/home',
    download_url     = 'http://gnomefiles.org/app.php/pychess',
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess']
)
