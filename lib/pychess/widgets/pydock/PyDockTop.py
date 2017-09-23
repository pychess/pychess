
import os
from xml.dom import minidom
from collections import defaultdict


from pychess.System.prefix import addDataPrefix

from .PyDockLeaf import PyDockLeaf
from .PyDockComposite import PyDockComposite
from .ArrowButton import ArrowButton
from .HighlightArea import HighlightArea
from .__init__ import TabReceiver
from .__init__ import NORTH, EAST, SOUTH, WEST, CENTER


class PyDockTop(PyDockComposite, TabReceiver):
    def __init__(self, id, perspective):
        TabReceiver.__init__(self, perspective)
        self.id = id
        self.perspective = perspective
        self.set_no_show_all(True)
        self.highlightArea = HighlightArea(self)

        self.button_cids = defaultdict(list)

        self.buttons = (
            ArrowButton(self, addDataPrefix("glade/dock_top.svg"), NORTH),
            ArrowButton(self, addDataPrefix("glade/dock_right.svg"), EAST),
            ArrowButton(self, addDataPrefix("glade/dock_bottom.svg"), SOUTH),
            ArrowButton(self, addDataPrefix("glade/dock_left.svg"), WEST))

        for button in self.buttons:
            self.button_cids[button] += [
                button.connect("dropped", self.__onDrop),
                button.connect("hovered", self.__onHover),
                button.connect("left", self.__onLeave),
            ]

    def _del(self):
        if self.highlightArea.handler_is_connected(self.highlightArea.cid):
            self.highlightArea.disconnect(self.highlightArea.cid)

        for button in self.buttons:
            for cid in self.button_cids[button]:
                if button.handler_is_connected(cid):
                    button.disconnect(cid)
            button.myparent = None

        self.button_cids = {}
        self.highlightArea.myparent = None

        TabReceiver._del(self)
        PyDockComposite._del(self)

    def getPosition(self):
        return CENTER

    def __repr__(self):
        return "top (%s)" % self.id

    # ===========================================================================
    #    Component stuff
    # ===========================================================================

    def addComponent(self, widget):
        self.add(widget)
        widget.show()

    def changeComponent(self, old, new):
        self.removeComponent(old)
        self.addComponent(new)

    def removeComponent(self, widget):
        self.remove(widget)

    def getComponents(self):
        child = self.get_child()
        if isinstance(child, PyDockComposite) or isinstance(child, PyDockLeaf):
            return [child]
        return []

    def dock(self, widget, position, title, id):
        if not self.getComponents():
            leaf = PyDockLeaf(widget, title, id, self.perspective)
            self.addComponent(leaf)
            return leaf
        else:
            return self.get_child().dock(widget, position, title, id)

    def clear(self):
        self.remove(self.get_child())

    # ===========================================================================
    #    Signals
    # ===========================================================================

    def showArrows(self):
        for button in self.buttons:
            button._calcSize()
            button.show()

    def hideArrows(self):
        for button in self.buttons:
            button.hide()
        self.highlightArea.hide()

    def __onDrop(self, arrowButton, sender):
        self.highlightArea.hide()
        child = sender.get_nth_page(sender.get_current_page())

        for instance in sender.get_parent().getInstances(self.perspective):
            instance.hideArrows()

        title, id = sender.get_parent().undock(child)
        self.dock(child, arrowButton.myposition, title, id)

    def __onHover(self, arrowButton, widget):
        self.highlightArea.showAt(arrowButton.myposition)
        arrowButton.get_window().raise_()

    def __onLeave(self, arrowButton):
        self.highlightArea.hide()

    # ===========================================================================
    #    XML
    # ===========================================================================

    def saveToXML(self, xmlpath):
        """
        <docks>
            <dock id="x">
                <v pos="200">
                    <leaf current="x" dockable="False">
                        <panel id="x" />
                    </leaf>
                    <h pos="200">
                        <leaf current="y" dockable="True">
                            <panel id="y" />
                            <panel id="z" />
                        </leaf>
                        <leaf current="y" dockable="True">
                            <panel id="y" />
                        </leaf>
                    </h>
                </v>
            </dock>
        </docks>
        """
        dockElem = None

        if os.path.isfile(xmlpath):
            doc = minidom.parse(xmlpath)
            for elem in doc.getElementsByTagName("dock"):
                if elem.getAttribute("id") == self.id:
                    for node in elem.childNodes:
                        elem.removeChild(node)
                    dockElem = elem
                    break

        if not dockElem:
            doc = minidom.getDOMImplementation().createDocument(None, "docks",
                                                                None)
            dockElem = doc.createElement("dock")
            dockElem.setAttribute("id", self.id)
            doc.documentElement.appendChild(dockElem)

        if self.get_child():
            self.__addToXML(self.get_child(), dockElem, doc)
        f_handle = open(xmlpath, "w")
        doc.writexml(f_handle)
        f_handle.close()
        doc.unlink()

    def __addToXML(self, component, parentElement, document):
        if isinstance(component, PyDockComposite):
            pos = component.paned.get_position()
            if component.getPosition() in (NORTH, SOUTH):
                childElement = document.createElement("v")
                size = float(component.get_allocation().height)
            else:
                childElement = document.createElement("h")
                size = float(component.get_allocation().width)
#             if component.getPosition() in (NORTH, SOUTH):
#                 print "saving v position as %s out of %s (%s)" % (str(pos), str(size), str(pos/max(size,pos)))
            childElement.setAttribute("pos", str(pos / max(size, pos)))
            self.__addToXML(component.getComponents()[0], childElement,
                            document)
            self.__addToXML(component.getComponents()[1], childElement,
                            document)

        elif isinstance(component, PyDockLeaf):
            childElement = document.createElement("leaf")
            childElement.setAttribute("current", component.getCurrentPanel())
            childElement.setAttribute("dockable", str(component.isDockable()))
            for panel, title, id in component.getPanels():
                element = document.createElement("panel")
                element.setAttribute("id", id)
                element.setAttribute("visible", str(panel.get_visible()))
                childElement.appendChild(element)

        parentElement.appendChild(childElement)

    def loadFromXML(self, xmlpath, idToWidget):
        """ idTowidget is a dictionary {id: (widget,title)}
            asserts that self.id is in the xmlfile """
        doc = minidom.parse(xmlpath)
        for elem in doc.getElementsByTagName("dock"):
            if elem.getAttribute("id") == self.id:
                break
        else:
            raise AttributeError(
                "XML file contains no <dock> elements with id '%s'" % self.id)

        child = [n for n in elem.childNodes if isinstance(n, minidom.Element)]
        if child:
            self.addComponent(self.__createWidgetFromXML(child[0], idToWidget))

    def __createWidgetFromXML(self, parentElement, idToWidget):
        children = [n
                    for n in parentElement.childNodes
                    if isinstance(n, minidom.Element)]

        if parentElement.tagName in ("h", "v"):
            child1, child2 = children
            if parentElement.tagName == "h":
                new = PyDockComposite(EAST, self.perspective)
            else:
                new = PyDockComposite(SOUTH, self.perspective)
            new.initChildren(
                self.__createWidgetFromXML(child1, idToWidget),
                self.__createWidgetFromXML(child2, idToWidget),
                preserve_dimensions=True)

            def cb(widget, event, pos):
                allocation = widget.get_allocation()
                if parentElement.tagName == "h":
                    widget.set_position(int(allocation.width * pos))
                else:
                    # print "loading v position as %s out of %s (%s)" % \
                    # (int(allocation.height * pos), str(allocation.height), str(pos))
                    widget.set_position(int(allocation.height * pos))
                widget.disconnect(conid)

            conid = new.paned.connect("size-allocate", cb, float(parentElement.getAttribute("pos")))
            return new

        elif parentElement.tagName == "leaf":
            id = children[0].getAttribute("id")
            try:
                title, widget, menu_item = idToWidget[id]
            except KeyError:
                id = self.old2new(id)
                title, widget, menu_item = idToWidget[id]

            leaf = PyDockLeaf(widget, title, id, self.perspective)
            visible = children[0].getAttribute("visible")
            visible = visible == "" or visible == "True"
            widget.set_visible(visible)
            if menu_item is not None:
                menu_item.set_active(visible)

            for panelElement in children[1:]:
                id = panelElement.getAttribute("id")
                try:
                    title, widget, menu_item = idToWidget[id]
                except KeyError:
                    id = self.old2new(id)
                    title, widget, menu_item = idToWidget[id]

                visible = panelElement.getAttribute("visible")
                visible = visible == "" or visible == "True"
                leaf.dock(widget, CENTER, title, id)
                widget.set_visible(visible)
                if menu_item is not None:
                    menu_item.set_active(visible)

            leaf.setCurrentPanel(self.old2new(parentElement.getAttribute("current")))
            if parentElement.getAttribute("dockable").lower() == "false":
                leaf.setDockable(False)
            return leaf

    def old2new(self, name):
        """ After 0.99.0 database perspective panel names changed """
        x = {"switcher": "SwitcherPanel",
             "openingtree": "OpeningTreePanel",
             "filter": "FilterPanel",
             "preview": "PreviewPanel",
             "chat": "ChatPanel",
             "console": "ConsolePanel",
             "news": "NewsPanel",
             "seeklist": "SeekListPanel",
             "seekgraph": "SeekGraphPanel",
             "playerlist": "PlayerListPanel",
             "gamelist": "GameListPanel",
             "archivelist": "ArchiveListPanel",
             }
        return x[name] if name in x else name
