from collections import defaultdict

from gi.repository import Gtk, GObject


POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)
reprPos = ("NORTH", "EAST", "SOUTH", "WEST", "CENTER")


class TabReceiver(Gtk.Alignment):
    __instances = defaultdict(list)

    def __init__(self, perspective):
        GObject.GObject.__init__(self)
        self.__instances[perspective].append(self)

    def _del(self):
        try:
            index = TabReceiver.__instances[self.perspective].index(self)
        except ValueError:
            return
        del TabReceiver.__instances[self.perspective][index]

    def getInstances(self, perspective):
        return iter(self.__instances[perspective])

    def showArrows(self):
        raise NotImplementedError

    def hideArrows(self):
        raise NotImplementedError
