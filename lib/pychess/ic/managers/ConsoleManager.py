from gobject import *


class ConsoleManager (GObject):
    
    __gsignals__ = {
        'consoleMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_nothing(self.onConsoleMessage)

    def onConsoleMessage (self, line, prediction_name):
        self.emit("consoleMessage", line, prediction_name)
