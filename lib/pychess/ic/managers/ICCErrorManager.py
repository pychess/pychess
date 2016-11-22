from gi.repository import GObject

from pychess.ic.icc import DG_ILLEGAL_MOVE
from pychess.ic.managers.ErrorManager import ErrorManager


class ICCErrorManager(ErrorManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_ILLEGAL_MOVE, self.on_icc_illegal_move)

        self.connection.client.run_command("set-2 %s 1" % DG_ILLEGAL_MOVE)

    def on_icc_illegal_move(self, data):
        # gamenumber movestring reason
        gameid, move, reason = data.split(" ", 2)
        self.emit("onIllegalMove", move)
