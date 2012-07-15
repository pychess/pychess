# -*- coding: utf-8 -*-
#
# require:
# gtk-dev-2.10.11-win32-1
# py2exe-0.6.6.win32-py2.5
# pygtk-2.10.6-1.win32-py2.5
# pygobject-2.12.3-1.win32-py2.5
# pycairo-1.2.6-1.win32-py2.5
#
# run:
# python setup_win32.py py2exe
#

from distutils.core import setup
import py2exe
import glob
import sys

opts = {
    'py2exe': {
        'compressed': 1,
        'optimize': 2,
        'packages': 'encodings',
        'includes': 'cairo,pangocairo,pango,atk,gobject,xml.dom,xml.dom.minidom,threading,shutil,pygtk,gtk,sys,gtk.glade',
        },
    }

PACKAGES = ["pychess", "pychess.gfx", "pychess.ic", "pychess.ic.managers",
            "pychess.Players", "pychess.Savers", "pychess.System",
            "pychess.Utils", "pychess.Utils.lutils", "pychess.widgets" ]

setup(
    name = 'PyChess',
    version = '0.8',
    description = 'Chess client for Gnome Desktop',
    author = 'Thomas Dybdahl Ahle',
    url = 'http://code.google.com/p/pychess',
    download_url = 'http://code.google.com/p/pychess/downloads/list',
    license = 'GPL2',
    windows = [{'script': 'pychess'}],
    options=opts,
    package_dir = {'': 'lib'},
    packages = PACKAGES,
    data_files=[('glade', glob.glob('glade/*.*')),
                ('sidepanel', glob.glob('sidepanel/*.*')),
                ('flags', glob.glob('flags/*.*')),
                ('gtksourceview-1.0', glob.glob('gtksourceview-1.0/*.*')),
                ('gtksourceview-1.0/language-specs', glob.glob('gtksourceview-1.0/language-specs/*.*')),
                ('lang', glob.glob('lang/*.*')),
                ('lang/pt_BR/LC_MESSAGES', glob.glob('lang/pt_BR/LC_MESSAGES/*.*')),
                # more langs
                ('lib', glob.glob('lib/*.*')),
                ('lib/pychess', glob.glob('lib/pychess/*.*')),
                ('lib/pychess/gfx', glob.glob('lib/pychess/gfx/*.*')),
                ('lib/pychess/ic', glob.glob('lib/pychess/ic/*.*')),
                ('lib/pychess/Players', glob.glob('lib/pychess/Players/*.*')),
                ('lib/pychess/Savers', glob.glob('lib/pychess/Savers/*.*')),
                ('lib/pychess/System', glob.glob('lib/pychess/System/*.*')),
                ('lib/pychess/Utils', glob.glob('lib/pychess/Utils/*.*')),
                ('lib/pychess/Utils/lutils', glob.glob('lib/pychess/Utils/lutils/*.*')),
                ('lib/pychess/widgets', glob.glob('lib/pychess/widgets/*.*')),
                ('', glob.glob('README')),
    ],
)
