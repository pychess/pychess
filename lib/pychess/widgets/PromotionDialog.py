import gtk

from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix

from pychess.Utils.Piece import Piece,QUEEN,ROOK,BISHOP,KNIGHT
from pychess.Utils.const import WHITE,BLACK

from PieceWidget import PieceWidget


uistuff.cacheGladefile("promotion.glade")

class PromotionDialog:
    
    def __init__(self):
        self.widgets = uistuff.GladeWidgets("promotion.glade")
        self.dialog = self.widgets["promotionDialog"]
        
        self.color = None
        
        self.widgets["knightDock"].add(PieceWidget(Piece(WHITE, KNIGHT)))
        self.widgets["knightDock"].child.show()
        self.widgets["bishopDock"].add(PieceWidget(Piece(WHITE, BISHOP)))
        self.widgets["bishopDock"].child.show()
        self.widgets["rookDock"].add(PieceWidget(Piece(WHITE, ROOK)))
        self.widgets["rookDock"].child.show()
        self.widgets["queenDock"].add(PieceWidget(Piece(WHITE, QUEEN)))
        self.widgets["queenDock"].child.show()
    
    def setColor(self, color):
        self.widgets["knightDock"].child.getPiece().color = color
        self.widgets["bishopDock"].child.getPiece().color = color
        self.widgets["rookDock"].child.getPiece().color = color
        self.widgets["queenDock"].child.getPiece().color = color
    
    def runAndHide(self, color):
        self.setColor(color)
        res = self.dialog.run()
        self.dialog.hide()
        if res != gtk.RESPONSE_DELETE_EVENT:
            return [QUEEN,ROOK,BISHOP,KNIGHT][int(res)]
        return res
