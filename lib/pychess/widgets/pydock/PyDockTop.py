import os
from xml.dom import minidom

import gtk
import gobject

from pychess.System.prefix import addDataPrefix

from PyDockLeaf import PyDockLeaf
from PyDockComposite import PyDockComposite
from ArrowButton import ArrowButton
from HighlightArea import HighlightArea
from __init__ import TopDock, DockLeaf, DockComponent, DockComposite
from __init__ import NORTH, EAST, SOUTH, WEST, CENTER

class PyDockTop (TopDock):
    def __init__ (self, id):
        TopDock.__init__(self, id)
        self.set_no_show_all(True)
        
        self.__sock = gtk.Alignment(xscale=1, yscale=1)
        self.put(self.__sock, 0, 0)
        self.connect("size-allocate", lambda self, alloc: \
                     self.__sock.set_size_request(alloc.width, alloc.height))
        self.__sock.show()
        
        self.highlightArea = HighlightArea()
        self.put(self.highlightArea, 0, 0)
        
        self.buttons = (ArrowButton(addDataPrefix("glade/dock_top.svg"), NORTH),
                        ArrowButton(addDataPrefix("glade/dock_right.svg"), EAST),
                        ArrowButton(addDataPrefix("glade/dock_bottom.svg"), SOUTH),
                        ArrowButton(addDataPrefix("glade/dock_left.svg"), WEST))
        for button in self.buttons:
            self.put(button, 0, 0)
            button.connect("dropped", self.__onDrop)
            button.connect("hovered", self.__onHover)
            button.connect("left", self.__onLeave)
    
    #===========================================================================
    #    Component stuff
    #===========================================================================
    
    def addComponent (self, widget):
        self.__sock.add(widget)
        widget.show()
    
    def changeComponent (self, old, new):
        self.removeComponent(old)
        self.addComponent(new)
    
    def removeComponent (self, widget):
        self.__sock.remove(widget)
    
    def getComponents (self):
        return [child for child in self.__sock.get_children() if \
                isinstance(child, DockComponent)]
    
    def dock (self, widget, position, title, id):
        if not self.getComponents():
            leaf = PyDockLeaf(widget, title, id)
            self.addComponent(leaf)
            return leaf
        else:
            return self.__sock.get_child().dock(widget, position, title, id)
    
    def clear (self):
        self.__sock.remove(self.__sock.child)
    
    #===========================================================================
    #    Signals
    #===========================================================================
    
    def showArrows (self):
        for button in self.buttons:
            button.show()
    
    def hideArrows (self):
        for button in self.buttons:
            button.hide()
        self.highlightArea.hide()
    
    def __onDrop (self, arrowButton, sender):
        self.highlightArea.hide()
        child = sender.get_nth_page(sender.get_current_page())
        title, id = sender.get_parent().undock(child)
        self.dock(child, arrowButton.position, title, id)
    
    def __onHover (self, arrowButton, widget):
        self.highlightArea.showAt(arrowButton.position)
    
    def __onLeave (self, arrowButton):
        self.highlightArea.hide()
    
    #===========================================================================
    #    XML
    #===========================================================================
    
    def saveToXML (self, xmlpath):
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
            doc = minidom.getDOMImplementation().createDocument(None, "docks", None)
            dockElem = doc.createElement("dock")
            dockElem.setAttribute("id", self.id)
            doc.documentElement.appendChild(dockElem)
        
        if self.__sock.child:
            self.__addToXML(self.__sock.child, dockElem, doc)
        f = file(xmlpath, "w")
        doc.writexml(f)
        f.close()
        doc.unlink()
    
    def __addToXML (self, component, parentElement, document):
        if isinstance(component, DockComposite):
            if component.getPosition() in (NORTH, SOUTH):
                childElement = document.createElement("v")
            else: childElement = document.createElement("h")
            childElement.setAttribute("pos", str(component.paned.get_position()))
            self.__addToXML(component.getComponents()[0], childElement, document)
            self.__addToXML(component.getComponents()[1], childElement, document)
        
        elif isinstance(component, DockLeaf):
            childElement = document.createElement("leaf")
            childElement.setAttribute("current", component.getCurrentPanel())
            childElement.setAttribute("dockable", str(component.isDockable()))
            for panel, title, id in component.getPanels():
                e = document.createElement("panel")
                e.setAttribute("id", id)
                childElement.appendChild(e)
        
        parentElement.appendChild(childElement)
    
    def loadFromXML (self, xmlpath, idToWidget):
        doc = minidom.parse(xmlpath)
        for elem in doc.getElementsByTagName("dock"):
            if elem.getAttribute("id") == self.id:
                break
        else:
            raise AttributeError, \
                  "XML file contains no <dock> elements with id '%s'" % self.id
        
        child = [n for n in elem.childNodes if isinstance(n, minidom.Element)]
        if child:
            self.addComponent(self.__createWidgetFromXML(child[0], idToWidget)) 
    
    def __createWidgetFromXML (self, parentElement, idToWidget):
        children = [n for n in parentElement.childNodes
                      if isinstance(n, minidom.Element)]
        
        if parentElement.tagName in ("h", "v"):
            child1, child2 = children
            if parentElement.tagName == "h":
                new = PyDockComposite(EAST)
            else: new = PyDockComposite(SOUTH)
            new.initChildren(self.__createWidgetFromXML(child1, idToWidget),
                             self.__createWidgetFromXML(child2, idToWidget))
            def cb (widget, allocation, pos):
                widget.set_position(pos)
                if allocation.width >= pos:
                    widget.disconnect(conid)
            conid = new.paned.connect_after("size-allocate", cb,
                                            int(parentElement.getAttribute("pos")))
            return new
        
        elif parentElement.tagName == "leaf":
            id = children[0].getAttribute("id")
            title, widget = idToWidget[id]
            leaf = PyDockLeaf(widget, title, id)
            for panelElement in children[1:]:
                id = panelElement.getAttribute("id")
                title, widget = idToWidget[id]
                leaf.dock(widget, CENTER, title, id)
            leaf.setCurrentPanel(parentElement.getAttribute("current"))
            if parentElement.getAttribute("dockable").lower() == "false":
                leaf.setDockable(False)
            return leaf
