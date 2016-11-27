from gi.repository import GObject

from pychess.ic.managers.NewsManager import NewsManager


class ICCNewsManager(NewsManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
