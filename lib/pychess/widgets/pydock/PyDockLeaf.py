from __future__ import absolute_import
from __future__ import print_function

from gi.repository import Gtk, GObject

from pychess.System.prefix import addDataPrefix

from .__init__ import CENTER, TabReceiver

from .PyDockComposite import PyDockComposite
from .StarArrowButton import StarArrowButton
from .HighlightArea import HighlightArea


class PyDockLeaf(TabReceiver):
    def __init__(self, widget, title, id):
        TabReceiver.__init__(self)
        self.set_no_show_all(True)

        def customGetTabLabelText(child):
            try:
                name = self.book.get_tab_label(child).get_text()
            except:
                name = child.get_name()
            return name

        self.book = Gtk.Notebook()
        self.book.set_name(id)
        #self.book.get_tab_label_text = customGetTabLabelText
        self.book_cids = [
            self.book.connect("drag-begin", self.__onDragBegin),
            self.book.connect("drag-end", self.__onDragEnd),
            self.book.connect_after("switch-page", self.__onPageSwitched),
        ]
        self.add(self.book)
        self.book.show()
        # self.book.props.tab_vborder = 0
        # self.book.props.tab_hborder = 1

        self.highlightArea = HighlightArea(self)
        # self.put(self.highlightArea, 0, 0)

        self.button_cids = []

        self.starButton = StarArrowButton(
            self, addDataPrefix("glade/dock_top.svg"),
            addDataPrefix("glade/dock_right.svg"),
            addDataPrefix("glade/dock_bottom.svg"),
            addDataPrefix("glade/dock_left.svg"),
            addDataPrefix("glade/dock_center.svg"),
            addDataPrefix("glade/dock_star.svg"))
        # self.put(self.starButton, 0, 0)
        self.button_cids += [
            self.starButton.connect("dropped", self.__onDrop),
            self.starButton.connect("hovered", self.__onHover),
            self.starButton.connect("left", self.__onLeave),
        ]
        self.dockable = True
        self.panels = []

        self.zoomPointer = Gtk.Label()
        self.realtop = None
        self.zoomed = False

        # assert isinstance(widget, Gtk.Notebook)

        self.__add(widget, title, id)

    def _del(self):
        self.highlightArea.disconnect(self.highlightArea.cid)

        for cid in self.button_cids:
            self.starButton.disconnect(cid)
        self.button_cids = []

        for cid in self.book_cids:
            self.book.disconnect(cid)

        self.starButton.myparent = None
        self.highlightArea.myparent = None
        #self.starButton = None
        #self.highlightArea = None

        TabReceiver._del(self)

    def __repr__(self):
        s = "leaf"  # PyDockLeaf.__repr__(self)
        panels = []
        for widget, title, id in self.getPanels():
            panels.append(id)
        return s + " (" + ", ".join(panels) + ")"

    def __add(self, widget, title, id):
        # widget = BorderBox(widget, top=True)
        self.panels.append((widget, title, id))
        self.book.append_page(widget, title)
        # self.book.set_tab_label_packing(widget, True, True, Gtk.PACK_START)
        self.book.set_tab_detachable(widget, True)
        self.book.set_tab_reorderable(widget, True)
        widget.show_all()

    def dock(self, widget, position, title, id):
        """ if position == CENTER: Add a new widget to the leaf-notebook
            if position != CENTER: Fork this leaf into two """

        if position == CENTER:
            self.__add(widget, title, id)
            return self
        else:
            parent = self.get_parent()
            while not isinstance(parent, PyDockComposite):
                parent = parent.get_parent()

            leaf = PyDockLeaf(widget, title, id)
            new = PyDockComposite(position)
            parent.changeComponent(self, new)
            new.initChildren(self, leaf)
            new.show_all()
            return leaf

    def undock(self, widget):
        """ remove the widget from the leaf-notebook
            if this was the only widget, remove this leaf from its owner """

        for i, (widget_, title, id) in enumerate(self.panels):
            if widget_ == widget:
                break
        else:
            raise KeyError("No %s in %s" % (widget, self))
        del self.panels[i]

        self.book.remove_page(self.book.page_num(widget))
        if self.book.get_n_pages() == 0:

            def cb():
                parent = self.get_parent()
                while not isinstance(parent, PyDockComposite):
                    parent = parent.get_parent()
                parent.removeComponent(self)
                self._del()
            # We need to idle_add this, as the widget won't emit drag-ended, if
            # it is removed to early
            GObject.idle_add(cb)

        return title, id

    def zoomUp(self):
        if self.zoomed:
            return

        from .PyDockTop import PyDockTop
        parent = self.get_parent()
        if not isinstance(parent, PyDockTop):
            while not isinstance(parent, PyDockComposite):
                parent = parent.get_parent()

            parent.changeComponent(self, self.zoomPointer)

            while not isinstance(parent, PyDockTop):
                parent = parent.get_parent()

            self.realtop = parent.getComponents()[0]
            parent.changeComponent(self.realtop, self)

        self.zoomed = True
        self.book.set_show_border(False)

    def zoomDown(self):
        if not self.zoomed:
            return

        if self.zoomPointer.get_parent():
            top_parent = self.get_parent()
            old_parent = self.zoomPointer.get_parent()

            while not isinstance(old_parent, PyDockComposite):
                old_parent = old_parent.get_parent()

            top_parent.changeComponent(self, self.realtop)
            old_parent.changeComponent(self.zoomPointer, self)

        self.realtop = None
        self.zoomed = False
        self.book.set_show_border(True)

    def getPanels(self):
        """ Returns a list of (widget, title, id) tuples """
        return self.panels

    def getCurrentPanel(self):
        for i, (widget, title, id) in enumerate(self.panels):
            if i == self.book.get_current_page():
                return id

    def setCurrentPanel(self, id):
        """ Returns the panel id currently shown """
        for i, (widget, title, id_) in enumerate(self.panels):
            if id == id_:
                self.book.set_current_page(i)
                break

    def isDockable(self):
        return self.dockable

    def setDockable(self, dockable):
        """ If the leaf is not dockable it won't be moveable and won't accept
            new panels """
        self.book.set_show_tabs(dockable)
        # self.book.set_show_border(dockable)
        self.dockable = dockable

    def showArrows(self):
        if self.dockable:
            self.starButton._calcSize()
            self.starButton.show()

    def hideArrows(self):
        self.starButton.hide()
        self.highlightArea.hide()

    def __onDragBegin(self, widget, context):
        for instance in self.getInstances():
            instance.showArrows()

    def __onDragEnd(self, widget, context):
        for instance in self.getInstances():
            instance.hideArrows()

    def __onDrop(self, starButton, position, sender):
        self.highlightArea.hide()

        # if the undocked leaf was alone, __onDragEnd may not triggered
        # because leaf was removed
        for instance in self.getInstances():
            instance.hideArrows()

        if self.dockable:
            if sender.get_parent() == self and self.book.get_n_pages() == 1:
                return
            # cp = sender.get_current_page()
            child = sender.get_nth_page(sender.get_current_page())
            title, id = sender.get_parent().undock(child)
            self.dock(child, position, title, id)

    def __onHover(self, starButton, position, widget):
        if self.dockable:
            self.highlightArea.showAt(position)
            starButton.get_window().raise_()

    def __onLeave(self, starButton):
        self.highlightArea.hide()

    def __onPageSwitched(self, book, page, page_num):
        # When a tab is dragged over another tab, the page is temporally
        # switched, and the notebook child is hovered. Thus we need to reraise
        # our star
        if self.starButton.get_window():
            self.starButton.get_window().raise_()
