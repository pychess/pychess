from gobject import *

from pychess.ic.VerboseTelnet import ConsoleHandler


class ConsoleManager (GObject):
    
    __gsignals__ = {
        'consoleMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        self.connection.client.lines.consolehandler = ConsoleHandler(self.onConsoleMessage)

    def onConsoleMessage (self, lines):
        self.emit("consoleMessage", lines)
