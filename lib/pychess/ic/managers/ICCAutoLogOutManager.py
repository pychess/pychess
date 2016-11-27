from gi.repository import GObject

from pychess.ic.managers.AutoLogOutManager import AutoLogOutManager


class ICCAutoLogOutManager(AutoLogOutManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
