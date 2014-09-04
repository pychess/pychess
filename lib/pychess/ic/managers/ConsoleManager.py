#from gobject import *
from gi.repository import GObject

from pychess.ic.VerboseTelnet import ConsoleHandler


class ConsoleManager (GObject.GObject):
    
    __gsignals__ = {
        'consoleMessage' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.connection.client.lines.consolehandler = ConsoleHandler(self.onConsoleMessage)

    def onConsoleMessage (self, lines):
        self.emit("consoleMessage", lines)
