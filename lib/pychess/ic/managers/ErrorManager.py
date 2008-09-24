
from gobject import *

class ErrorManager (GObject):
    
    __gsignals__ = {
        'onCommandNotFound' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        connection.expect_line (self.onError, "(.*?): Command not found.")
    
    def onError (self, match):
        command = match.groups()[0]
        self.emit("onCommandNotFound", command)
