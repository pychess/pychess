import unittest

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from pychess.widgets.pydock import EAST, WEST
from pychess.widgets.pydock.PyDockComposite import PyDockComposite


class PyDockCompositeTests(unittest.TestCase):
    def test_children_cannot_shrink_below_their_requisition(self):
        composite = PyDockComposite(EAST, object())
        board = Gtk.Label(label="Board")
        panel = Gtk.Label(label="Panel")

        composite.initChildren(board, panel, preserve_dimensions=True)

        self.assertFalse(composite.paned.child_get_property(board, "shrink"))
        self.assertFalse(composite.paned.child_get_property(panel, "shrink"))

    def test_replaced_child_keeps_minimum_size_constraint(self):
        composite = PyDockComposite(WEST, object())
        board = Gtk.Label(label="Board")
        panel = Gtk.Label(label="Panel")
        replacement = Gtk.Label(label="Replacement")
        composite.initChildren(board, panel, preserve_dimensions=True)

        composite.changeComponent(panel, replacement)

        self.assertFalse(composite.paned.child_get_property(replacement, "shrink"))


if __name__ == "__main__":
    unittest.main()
