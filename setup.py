#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gettext
gettext.install("pychess", localedir="lang", unicode=1)

from lib.pychess.System import myconf
from lib.pychess.Utils.const import VERSION

myconf.set("combobox6", 1)
myconf.set("spinbuttonM", 10)

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

os.chdir(os.path.abspath(os.path.split(__file__)[0]))

DATA_FILES = [("", ["README", "AUTHORS", "LICENSE"])]

# UI
DATA_FILES += [("glade", glob('glade/*.glade'))]
DATA_FILES += [("glade", glob('glade/*.png'))]

# Sidepanel (not a package)
DATA_FILES += [("sidepanel", glob('sidepanel/*.glade'))]
DATA_FILES += [("sidepanel", glob('sidepanel/*.py'))]

# Main modules
DATA_FILES += [("", glob("*.py"))]

# Opening book
DATA_FILES += [("Utils", glob('Utils/open.db'))]

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

PACKAGES = ["gfx", "Players", "Savers", "System", "Utils", "widgets"]

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
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess']
)
