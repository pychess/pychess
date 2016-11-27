from gi.repository import GObject

from pychess.ic.managers.OfferManager import OfferManager


class ICCOfferManager(OfferManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
