#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# mocking C extension modules we use in pychess
# Currently looks like unittest.mock is broken in python 3.5
# had to 'pip install -U mock' to get this to work
if sys.version_info < (3,5):
    from unittest.mock import MagicMock
else:
    from mock import Mock as MagicMock

class GObjectMock(MagicMock):
    class GObject():
        def connect(*args):
            pass

class GtkMock(MagicMock):
    class Alignment:
        pass
    class Notebook:
        def set_show_border(*args):
            pass
        def set_show_tabs(*args):
            pass
    class ScrolledWindow:
        pass

class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        if name == "GObject":
            return GObjectMock()
        elif name == "Gtk":
            return GtkMock()
        else:
            return Mock()

MOCK_MODULES = ['cairo', 'gi', 'gi.repository', 'gi.repository.GdkPixbuf',
                'sqlalchemy', 'sqlalchemy.exc', 'sqlalchemy.schema']
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)


# fix environment
sys.path.insert(0, os.path.abspath('../lib'))
sys.path.insert(0, os.path.abspath('../sidepanels'))

import pychess

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

#intersphinx_mapping = {'Gtk' : ('http://lazka.github.io/pgi-docs/#Gtk-3.0/', None )}

# Sort members by type
autodoc_member_order = 'groupwise'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'pychess'
author = "PyChess team"
copyright = '2006-2015, PyChess team'

version = pychess.VERSION
release = pychess.VERSION

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'
