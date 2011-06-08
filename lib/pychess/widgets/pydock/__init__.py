import gtk

#===============================================================================
# Composite Constants
#===============================================================================

POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)

#===============================================================================
# Composite Interfaces
#===============================================================================

class DockComponent (object):
    def dock (self, widget, position, title, id):
        abstract

class TabReceiver (gtk.Alignment):
    __instances = []
    
    def __init__ (self):
        gtk.Alignment.__init__(self,1,1,1,1)
        self.__instances.append(self)
    
    def __del__ (self):
        try:
            index = TabReceiver.__instances.index(self)
        except ValueError:
            return
        del TabReceiver.__instances[index]
    
    def getInstances (self):
        return iter(self.__instances)
    
    def showArrows (self):
        abstract
    
    def hideArrows (self):
        abstract

class DockComposite (DockComponent):
    def __del__ (self):
        for component in self.getComponents():
            component.__del__()
    
    def changeComponent (self, old, new):
        abstract
    
    def removeComponent (self, component):
        abstract
    
    def getComponents (self):
        abstract
    
    def getPosition (self):
        """ Returns NORTH or SOUTH if the children are packed vertically.
            Returns WEST or EAST if the children are packed horizontally.
            Returns CENTER if there is only one child """
        abstract

class DockLeaf (DockComponent, TabReceiver):
    def __del__ (self):
        TabReceiver.__del__(self)
    
    def undock (self, widget):
        """ Removes the widget from the leaf, and if it is the only widget, it
            removes the leaf as well.
            Returns (title, id) of the widget """
        abstract
    
    def getPanels (self):
        """ Returns a list of (widget, title, id) tuples """
        abstract
    
    def getCurrentPanel (self):
        """ Returns the panel id currently shown """
        abstract
    
    def setCurrentPanel (self, id):
        abstract
    
    def setDockable (self, dockable):
        """ If the leaf is not dockable it won't be moveable and won't accept
            new panels """
        abstract
    
    def isDockable (self):
        abstract

class TopDock (DockComposite, TabReceiver):
    def __init__ (self, id):
        TabReceiver.__init__(self)
        self.__id = id
    
    def __del__ (self):
        TabReceiver.__del__(self)
        DockComposite.__del__(self)
    
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
        abstract
    
    def loadFromXML (self, xmlpath, idToWidget):
        """ idTowidget is a dictionary {id: (widget,title)}
            asserts that self.id is in the xmlfile """
        abstract
    
    def getId(self):
        return self.__id
    
    id = property(getId, None, None, None)
