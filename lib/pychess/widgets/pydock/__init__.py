from gi.repository import Gtk, GObject


POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)
reprPos = ("NORTH", "EAST", "SOUTH", "WEST", "CENTER")


class TabReceiver(Gtk.Alignment):
    __instances = []

    def __init__(self):
        GObject.GObject.__init__(self)
        self.__instances.append(self)

    def _del(self):
        try:
            index = TabReceiver.__instances.index(self)
        except ValueError:
            return
        del TabReceiver.__instances[index]

    def getInstances(self):
        return iter(self.__instances)

    def showArrows(self):
        raise NotImplementedError

    def hideArrows(self):
        raise NotImplementedError
