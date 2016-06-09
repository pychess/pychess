from __future__ import absolute_import
from __future__ import print_function

from gi.repository import Gtk, GObject

from .__init__ import NORTH, EAST, SOUTH, WEST, CENTER, reprPos


class PyDockComposite(Gtk.Alignment):
    def __init__(self, position):
        GObject.GObject.__init__(self, xscale=1, yscale=1)

        if position == NORTH or position == SOUTH:
            paned = Gtk.VPaned()
        elif position == EAST or position == WEST:
            paned = Gtk.HPaned()
        self.position = position
        self.paned = paned
        self.add(self.paned)
        self.paned.show()

    def _del(self):
        for component in self.getComponents():
            component._del()

    def __repr__(self):
        return "composite %s (%s, %s)" % (reprPos[self.position],
                                          repr(self.paned.get_child1()),
                                          repr(self.paned.get_child2()))

    def dock(self, widget, position, title, id):
        assert position != CENTER, "POSITION_CENTER only makes sense for leaves"
        parent = self.get_parent()
        while not isinstance(parent, PyDockComposite):
            parent = parent.get_parent()
        from .PyDockLeaf import PyDockLeaf
        leaf = PyDockLeaf(widget, title, id)
        new = PyDockComposite(position)
        parent.changeComponent(self, new)
        new.initChildren(self, leaf)
        return leaf

    def changeComponent(self, old, new):
        if old == self.paned.get_child1():
            self.paned.remove(old)
            self.paned.pack1(new, resize=True, shrink=False)
        else:
            self.paned.remove(old)
            self.paned.pack2(new, resize=True, shrink=False)
        new.show()

    def removeComponent(self, component):
        if component == self.paned.get_child1():
            new = self.paned.get_child2()
        else:
            new = self.paned.get_child1()
        self.paned.remove(new)
        parent = self.get_parent()
        while not isinstance(parent, PyDockComposite):
            parent = parent.get_parent()
        parent.changeComponent(self, new)
        component._del()  # TODO: is this necessary?
        new.show()

    def getComponents(self):
        return self.paned.get_children()

    def initChildren(self, old, new, preserve_dimensions=False):
        if self.position == NORTH or self.position == WEST:
            self.paned.pack1(new, resize=True, shrink=False)
            self.paned.pack2(old, resize=True, shrink=False)
        elif self.position == SOUTH or self.position == EAST:
            self.paned.pack1(old, resize=True, shrink=False)
            self.paned.pack2(new, resize=True, shrink=False)
        old.show()
        new.show()

        def cb(widget, allocation):
            if allocation.height != 1:
                if self.position == NORTH:
                    pos = 0.381966011 * allocation.height
                elif self.position == SOUTH:
                    pos = 0.618033989 * allocation.height
                elif self.position == WEST:
                    pos = 0.381966011 * allocation.width
                elif self.position == EAST:
                    pos = 0.618033989 * allocation.width
                widget.set_position(int(pos + .5))
                widget.disconnect(conid)

        if not preserve_dimensions:
            conid = self.paned.connect("size-allocate", cb)

    def getPosition(self):
        """ Returns NORTH or SOUTH if the children are packed vertically.
            Returns WEST or EAST if the children are packed horizontally.
            Returns CENTER if there is only one child """
        return self.position
