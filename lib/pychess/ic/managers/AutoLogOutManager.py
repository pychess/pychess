from gobject import *
class AutoLogOutManager (GObject):
    __gsignals__ = {
        'logOut': (SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        self.connection.expect_line (self.onLogOut,
           "**** Auto-logout because you were idle more than \d+ minutes. ****")
        #FIXME: **** Lobais has arrived - you can't both be logged in. ****
        # (Logout screen by Alefith)
        # Thank you for using the Free Internet Chess server (http://www.freechess.org).
    def onLogOut (self, match):
        self.emit("logOut")