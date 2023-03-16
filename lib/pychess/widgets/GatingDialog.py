from gi.repository import Gtk

from pychess.Utils.Piece import Piece
from pychess.Utils.const import (
    WHITE,
    HAWK,
    ELEPHANT,
    HAWK_GATE,
    ELEPHANT_GATE,
    HAWK_GATE_AT_ROOK,
    ELEPHANT_GATE_AT_ROOK,
)
from pychess.System import uistuff
from pychess.widgets import mainwindow

from .PieceWidget import PieceWidget


class GatingDialog:
    def __init__(self, variant):
        self.widgets = uistuff.GladeWidgets("gating.glade")
        self.widgets["gatingDialog"].set_transient_for(mainwindow())
        self.dialog = self.widgets["gatingDialog"]

        self.color = None

        if self.widgets["hawkDock"].get_child() is None:
            self.widgets["hawkDock"].add(PieceWidget(Piece(WHITE, HAWK), variant))
            self.widgets["hawkDock"].get_child().show()
            self.widgets["elephantDock"].add(
                PieceWidget(Piece(WHITE, ELEPHANT), variant)
            )
            self.widgets["elephantDock"].get_child().show()

            self.widgets["hawkAtRookDock"].add(PieceWidget(Piece(WHITE, HAWK), variant))
            self.widgets["hawkAtRookDock"].get_child().show()
            self.widgets["elephantAtRookDock"].add(
                PieceWidget(Piece(WHITE, ELEPHANT), variant)
            )
            self.widgets["elephantAtRookDock"].get_child().show()

    def setColor(self, color):
        self.widgets["hawkDock"].get_child().getPiece().color = color
        self.widgets["elephantDock"].get_child().getPiece().color = color

        self.widgets["hawkAtRookDock"].get_child().getPiece().color = color
        self.widgets["elephantAtRookDock"].get_child().getPiece().color = color

    def runAndHide(self, color, castling, hawk, elephant):
        self.setColor(color)

        self.widgets["button1"].show()
        self.widgets["button2"].show()
        self.widgets["button3"].show()
        self.widgets["button4"].show()

        if not castling:
            self.widgets["button3"].hide()
            self.widgets["button4"].hide()

        if not hawk:
            self.widgets["button1"].hide()
            self.widgets["button3"].hide()

        if not elephant:
            self.widgets["button2"].hide()
            self.widgets["button4"].hide()

        res = self.dialog.run()
        self.dialog.hide()
        if res != Gtk.ResponseType.DELETE_EVENT:
            return [HAWK_GATE, ELEPHANT_GATE, HAWK_GATE_AT_ROOK, ELEPHANT_GATE_AT_ROOK][
                int(res)
            ]
        return None
