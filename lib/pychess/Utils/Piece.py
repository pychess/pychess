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
    	
    def __eq__ (self, other):
        return  other != None and \
                self.color == other.color and \
                self.sign == other.sign
    
    def __repr__ (self):
        return "<%s %s>" % (reprColor[self.color], pieceName[self.sign])
