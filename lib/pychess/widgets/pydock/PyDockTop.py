import gtk

from pychess.System.prefix import addDataPrefix

from PyDockLeaf import PyDockLeaf
from PyDockComposite import PyDockComposite
from ArrowButton import ArrowButton
from HighlightArea import HighlightArea
from __init__ import TopDock, DockLeaf, DockComponent
from __init__ import NORTH, EAST, SOUTH, WEST, CENTER

class PyDockTop (TopDock):
    def __init__ (self, id):
        TopDock.__init__(self)
        self.set_no_show_all(True)
        
        self.__sock = gtk.Alignment(xscale=1, yscale=1)
        self.put(self.__sock, 0, 0)
        #self.__recursiveOnAdd(self, self.__sock)
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
    
    #===========================================================================
    #    Signals
    #===========================================================================
    
    def __recursiveOnAdd (self, parrent, child):
        if isinstance(child, PyDockLeaf):
            child.book.connect("drag-end", self.__onDragEnd)
            child.book.connect("drag-begin", self.__onDragBegin)
        
        elif isinstance(child, PyDockComposite):
            child.paned.connect("add", self.__recursiveOnAdd)
        
        elif isinstance(child, gtk.Container):
            child.connect("add", self.__recursiveOnAdd)
    
    def showArrows (self):
        for button in self.buttons:
            button.show()
    
    def hideArrows (self):
        for button in self.buttons:
            button.hide()
        self.highlightArea.hide()
    
    #def __onDragBegin (self, widget, context):
    #    for button in self.buttons:
    #        button.show()
    
    #def __onDragEnd (self, widget, context):
    #    for button in self.buttons:
    #        button.hide()
    #    self.highlightArea.hide()
    
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
        
        self._addChildsToXML(self, dockElem, doc)
        f = file(xmlpath, "w")
        doc.writexml(f)
        f.close()
        doc.unlink()
    
    def _addChildsToXML (self, container, parentElement, document):
        for widget in container.get_children():
            if isinstance(widget, DockComposite):
                if isinstance(widget, VDockComposite):
                    childElement = document.createElement("v")
                else: childElement = document.createElement("h")
                childElement.setAttribute("pos", str(widget.get_position()))
                self._addChildsToXML(widget, childElement, document)
            
            elif isinstance(widget, DockLeaf):
                childElement = document.createElement("leaf")
                for panel, title, id in widget.getPanels():
                    if widget.get_nth_page(widget.get_current_page()) == panel:
                        childElement.setAttribute("current", id)
                    e = document.createElement("panel")
                    e.setAttribute("id", id)
                    childElement.appendChild(e)
            parentElement.appendChild(childElement)
    
    def loadFromXML (self, xmlpath, idToWidget):
        doc = minidom.parse(xmlpath)
        for elem in doc.getElementsByTagName("dock"):
            if elem.getAttribute("id") == self.id:
                dockElem = elem
                break
        else:
            raise AttributeError, \
                  "XML file contains no <dock> elements with id '%s'" % self.id
        
        e = [n for n in dockElem.childNodes if not isinstance(n, minidom.Text)][0]
        self.add(self._createWidgetFromXML(e, idToWidget)) 
    
    def _createWidgetFromXML (self, parentElement, idToWidget):
        children = [n for n in parentElement.childNodes
                      if not isinstance(n, minidom.Text)]
        if parentElement.tagName in ("h", "v"):
            child1, child2 = children
            if parentElement.tagName == "h":
                new = PyDockComposite(POSITION_RIGHT)
            else: new = PyDockComposite(POSITION_BOTTOM)
            new._initChildren(self._createWidgetFromXML(child1, idToWidget),
                              self._createWidgetFromXML(child2, idToWidget))
            return new
        
        elif parentElement.tagName == "leaf":
            id = children[0].getAttribute("id")
            widget, title = idToWidget[id]
            leaf = PyDockLeaf(widget, title, id)
            for panelElement in children[1:]:
                id = panelElement.getAttribute("id")
                widget, title = idToWidget[id]
                leaf.dock(widget, POSITION_CENTER, title, id)
            return leaf
