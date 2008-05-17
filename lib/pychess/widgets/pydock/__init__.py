import gtk

#===============================================================================
# Composite Constants
#===============================================================================

POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)

#===============================================================================
# Composite Interfaces
#===============================================================================

class DockComponent:
    def dock (self, widget, position, title, id):
        abstract

class TabReceiver (gtk.Layout):
    __instances = []
    
    def __init__ (self):
        gtk.Layout.__init__(self)
        self.__instances.append(self)
    
    def getInstances (self):
        return iter(self.__instances)
    
    def showArrows (self):
        abstract
    
    def hideArrows (self):
        abstract

class DockComposite (DockComponent):
    def changeComponent (self, old, new):
        abstract
    
    def removeComponent (self, component):
        abstract
    
    def getComponents (self):
        abstract

class DockLeaf (DockComponent, TabReceiver):
    def undock (self, widget):
        """ Removes the widget from the leaf, and if it is the only widget, it
            removes the leaf as well.
            Returns (title, id) of the widget """
        abstract
    
    def getPanels (self):
        """ Returns a list of (widget, title, id) tuples """
        abstract

class TopDock (DockComposite, TabReceiver):
    def saveToXML (self, xmlpath):
        """
        <docks>
            <dock id="x">
                <v pos="200">
                    <leaf current="x">
                        <panel id="x" title="Lala" />
                    </leaf>
                    <h pos="200">
                        <leaf current="y">
                            <panel id="y" title="Lala" />
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
    def setId(self, value):
        self.__id = value
    id = property(getId, setId, None, None)
