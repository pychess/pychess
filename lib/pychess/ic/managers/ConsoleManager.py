from gobject import *

from pychess.ic.VerboseTelnet import ConsoleHandler


class ConsoleManager (GObject):
    
    __gsignals__ = {
        'consoleMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        self.connection.client.consolehandler = ConsoleHandler(self.onConsoleMessage)

    def onConsoleMessage (self, line, block_code):
        self.emit("consoleMessage", line, block_code)
