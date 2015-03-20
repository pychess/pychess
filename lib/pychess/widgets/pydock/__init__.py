from gi.repository import Gtk
from gi.repository import GObject

#===============================================================================
# Composite Constants
#===============================================================================

POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)
reprPos = ("NORTH", "EAST", "SOUTH", "WEST", "CENTER")

#===============================================================================
# Composite Interfaces
#===============================================================================

class DockComponent (object):
    def dock (self, widget, position, title, id):
        raise NotImplementedError

class TabReceiver (Gtk.Alignment):
    __instances = []
    
    def __init__ (self):
        #GObject.GObject.__init__(self,1,1,1,1)
        GObject.GObject.__init__(self)
        self.__instances.append(self)
    
    def _del (self):
        try:
            index = TabReceiver.__instances.index(self)
        except ValueError:
            return
        del TabReceiver.__instances[index]
    
    def getInstances (self):
        return iter(self.__instances)
    
    def showArrows (self):
        raise NotImplementedError
    
    def hideArrows (self):
        raise NotImplementedError

class DockComposite (DockComponent):
    def _del (self):
        for component in self.getComponents():
            component._del()
    
    def changeComponent (self, old, new):
        raise NotImplementedError
    
    def removeComponent (self, component):
        raise NotImplementedError
    
    def getComponents (self):
        raise NotImplementedError
    
    def getPosition (self):
        """ Returns NORTH or SOUTH if the children are packed vertically.
            Returns WEST or EAST if the children are packed horizontally.
            Returns CENTER if there is only one child """
        raise NotImplementedError

class DockLeaf (DockComponent, TabReceiver):
    def _del (self):
        TabReceiver._del(self)
    
    def undock (self, widget):
        """ Removes the widget from the leaf, and if it is the only widget, it
            removes the leaf as well.
            Returns (title, id) of the widget """
        raise NotImplementedError
    
    def getPanels (self):
        """ Returns a list of (widget, title, id) tuples """
        raise NotImplementedError
    
    def getCurrentPanel (self):
        """ Returns the panel id currently shown """
        raise NotImplementedError
    
    def setCurrentPanel (self, id):
        raise NotImplementedError
    
    def setDockable (self, dockable):
        """ If the leaf is not dockable it won't be moveable and won't accept
            new panels """
        raise NotImplementedError
    
    def isDockable (self):
        raise NotImplementedError

class TopDock (DockComposite, TabReceiver):
    def __init__ (self, id):
        TabReceiver.__init__(self)
        self.__id = id
    
    def _del (self):
        TabReceiver._del(self)
        DockComposite._del(self)
    
    def getPosition (self):
        return CENTER
    
    def saveToXML (self, xmlpath):
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
        raise NotImplementedError
    
    def loadFromXML (self, xmlpath, idToWidget):
        """ idTowidget is a dictionary {id: (widget,title)}
            asserts that self.id is in the xmlfile """
        raise NotImplementedError
    
    def getId(self):
        return self.__id
    
    id = property(getId, None, None, None)
