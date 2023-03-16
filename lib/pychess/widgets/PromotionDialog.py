from gi.repository import Gtk

from pychess.Utils.Piece import Piece
from pychess.Utils.const import (
    SUICIDECHESS,
    GIVEAWAYCHESS,
    SITTUYINCHESS,
    SCHESS,
    WHITE,
    KING,
    QUEEN,
    ROOK,
    BISHOP,
    KNIGHT,
    HAWK,
    ELEPHANT,
)

from .PieceWidget import PieceWidget


class PromotionDialog:
    """:Description: A popup dialog that allows you to select form a set of pieces the exchange
    for a pawn through the promotion rule
    """

    def __init__(self, variant):
        from .gamewidget import getWidgets

        self.widgets = getWidgets()
        self.dialog = self.widgets["promotionDialog"]

        self.color = None

        if self.widgets["queenDock"].get_child() is None:
            self.widgets["queenDock"].add(PieceWidget(Piece(WHITE, QUEEN), variant))
            self.widgets["queenDock"].get_child().show()
            self.widgets["rookDock"].add(PieceWidget(Piece(WHITE, ROOK), variant))
            self.widgets["rookDock"].get_child().show()
            self.widgets["bishopDock"].add(PieceWidget(Piece(WHITE, BISHOP), variant))
            self.widgets["bishopDock"].get_child().show()
            self.widgets["knightDock"].add(PieceWidget(Piece(WHITE, KNIGHT), variant))
            self.widgets["knightDock"].get_child().show()
            self.widgets["kingDock"].add(PieceWidget(Piece(WHITE, KING), variant))
            self.widgets["kingDock"].get_child().show()
            if variant == SCHESS:
                self.widgets["hawkDock"].add(PieceWidget(Piece(WHITE, HAWK), variant))
                self.widgets["hawkDock"].get_child().show()
                self.widgets["elephantDock"].add(
                    PieceWidget(Piece(WHITE, ELEPHANT), variant)
                )
                self.widgets["elephantDock"].get_child().show()

    def setColor(self, color, variant):
        self.widgets["knightDock"].get_child().getPiece().color = color
        self.widgets["bishopDock"].get_child().getPiece().color = color
        self.widgets["rookDock"].get_child().getPiece().color = color
        self.widgets["queenDock"].get_child().getPiece().color = color
        self.widgets["kingDock"].get_child().getPiece().color = color
        if variant == SCHESS:
            self.widgets["hawkDock"].get_child().getPiece().color = color
            self.widgets["elephantDock"].get_child().getPiece().color = color

    def runAndHide(self, color, variant):
        self.setColor(color, variant)
        if variant != SUICIDECHESS and variant != GIVEAWAYCHESS:
            self.widgets["button5"].hide()

        if variant != SCHESS:
            self.widgets["button6"].hide()
            self.widgets["button7"].hide()

        if variant == SITTUYINCHESS:
            self.widgets["button4"].hide()
            self.widgets["button3"].hide()
            self.widgets["button2"].hide()

        res = self.dialog.run()
        self.dialog.hide()
        if res != Gtk.ResponseType.DELETE_EVENT:
            return [QUEEN, ROOK, BISHOP, KNIGHT, KING, HAWK, ELEPHANT][int(res)]
        return None
