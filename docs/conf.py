#!/usr/bin/env python3

import sys
import os

# mocking C extension modules we use in pychess
# Currently looks like unittest.mock is broken in python 3.5
# had to 'pip install -U mock' to get this to work
from unittest.mock import Mock as MagicMock


class GObjectMock(MagicMock):
    class GObject():
        def connect(*args):
            pass

        def connect_after(*args):
            pass


class GtkMock(MagicMock):
    class Alignment:
        def add(*args):
            pass

    class ComboBox:
        def add_attribute(*args):
            pass

        def clear(*args):
            pass

        def connect(*args):
            pass

        def get_active(*args):
            return 0

        def get_value(*args):
            return 0

        def set_value(*args):
            pass

        def pack_start(*args):
            pass

        def set_model(*args):
            pass

    class Notebook:
        def set_show_border(*args):
            pass

        def set_show_tabs(*args):
            pass

    class ScrolledWindow:
        pass

    class Slider:
        def get_value(*args):
            return 0


class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        if name == "GObject":
            return GObjectMock()
        elif name == "Gtk":
            return GtkMock()
        else:
            return Mock()


MOCK_MODULES = ['cairo', 'gi', 'gi.repository', 'gi.repository.GdkPixbuf', 'gi.repository.GLib',
                'sqlalchemy', 'sqlalchemy.engine', 'sqlalchemy.exc', 'sqlalchemy.pool',
                'sqlalchemy.ext.compiler', 'sqlalchemy.schema', 'sqlalchemy.sql.expression']
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)


# fix environment
sys.path.insert(0, os.path.abspath('../lib'))
sys.path.insert(0, os.path.abspath('../sidepanels'))

try:
    import pychess
except ImportError:
    pass

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

# intersphinx_mapping = {'Gtk' : ('http://lazka.github.io/pgi-docs/#Gtk-3.0/', None )}

intersphinx_mapping = {
    'gobject': ('http://lazka.github.io/pgi-docs/GObject-2.0', None),
    'gtk': ('http://lazka.github.io/pgi-docs/Gtk-3.0', None),
    'python': ('https://docs.python.org/3.4', None)
}

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
