from gi.repository import GObject

sanmove = "([a-hx@OoPKQRBN0-8+#=-]{2,7})"


class ErrorManager(GObject.GObject):

    __gsignals__ = {
        'onCommandNotFound': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'onAmbiguousMove': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'onIllegalMove': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        connection.expect_line(self.onError, "(.*?): Command not found\.")
        connection.expect_line(self.onAmbiguousMove,
                               "Ambiguous move \((%s)\)\." % sanmove)
        connection.expect_line(self.onIllegalMove, "Illegal move \((%s)\)\." %
                               sanmove)

    def onError(self, match):
        command = match.groups()[0]
        self.emit("onCommandNotFound", command)

    def onAmbiguousMove(self, match):
        move = match.groups()[0]
        self.emit("onAmbiguousMove", move)

    def onIllegalMove(self, match):
        move = match.groups()[0]
        self.emit("onIllegalMove", move)
