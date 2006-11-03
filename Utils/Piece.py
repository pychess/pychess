from const import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from const import reprSign, reprColor

pieceName = ["King", "Queen", "Rook", "Bishop", "Knight", "Pawn"]

class Piece:
    def __init__ (self, color, sign):
        self.color = color
        self.sign = sign
    
    def __repr__ (self):
        return "<%s %s>" % (reprColor[self.color], pieceName[self.name])

    def __eq__ (self, other):
        return  isinstance(other, Piece) and \
                self.color == other.color and \
                self.sign == other.sign
