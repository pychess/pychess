from const import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from const import reprSign, reprColor, reprPiece

pieceName = ["King", "Queen", "Rook", "Bishop", "Knight", "Pawn"]

class Piece:
    def __init__ (self, color, sign):
        self.color = color
        self.sign = sign
    	
    	self.opacity = 1.0
    	self.x = None
    	self.y = None
    
    def __repr__ (self):
        represen = "<%s %s" % (reprColor[self.color], pieceName[self.sign])
        if self.opacity != 1.0:
            represen += " Op:%0.1f" % self.opacity
        if self.x != None:
            represen += " X:%0.1f" % self.x
        if self.y != None:
            represen += " Y:%0.1f" % self.y
        represen += ">"
        return represen
