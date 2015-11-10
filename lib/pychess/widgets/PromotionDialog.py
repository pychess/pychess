from __future__ import absolute_import
from gi.repository import Gtk

from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix

from pychess.Utils.Piece import Piece, KING, QUEEN, ROOK, BISHOP, KNIGHT
from pychess.Utils.const import *

from .PieceWidget import PieceWidget


class PromotionDialog:
    
    def __init__(self, variant):
        self.widgets = uistuff.GladeWidgets("promotion.glade")
        self.dialog = self.widgets["promotionDialog"]
        
        self.color = None
        
        self.widgets["knightDock"].add(PieceWidget(Piece(WHITE, KNIGHT), variant))
        self.widgets["knightDock"].get_child().show()
        self.widgets["bishopDock"].add(PieceWidget(Piece(WHITE, BISHOP), variant))
        self.widgets["bishopDock"].get_child().show()
        self.widgets["rookDock"].add(PieceWidget(Piece(WHITE, ROOK), variant))
        self.widgets["rookDock"].get_child().show()
        self.widgets["queenDock"].add(PieceWidget(Piece(WHITE, QUEEN), variant))
        self.widgets["queenDock"].get_child().show()
        self.widgets["kingDock"].add(PieceWidget(Piece(WHITE, KING), variant))
        self.widgets["kingDock"].get_child().show()
    
    def setColor(self, color):
        self.widgets["knightDock"].get_child().getPiece().color = color
        self.widgets["bishopDock"].get_child().getPiece().color = color
        self.widgets["rookDock"].get_child().getPiece().color = color
        self.widgets["queenDock"].get_child().getPiece().color = color
        self.widgets["kingDock"].get_child().getPiece().color = color
    
    def runAndHide(self, color, variant):
        self.setColor(color)
        if variant != SUICIDECHESS:
            self.widgets["button5"].hide()
        
        if variant == SITTUYINCHESS:
            self.widgets["button4"].hide()
            self.widgets["button3"].hide()
            self.widgets["button2"].hide()
            
        res = self.dialog.run()
        self.dialog.hide()
        if res != Gtk.ResponseType.DELETE_EVENT:
            return [QUEEN, ROOK, BISHOP, KNIGHT, KING][int(res)]
        return None
