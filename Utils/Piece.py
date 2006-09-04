signToName = {"b":"Bishop","k":"King","n":"Knight","p":"Pawn","q":"Queen","r":"Rook"}
class Piece:
    def __init__ (self, color, sign):
        self.color = color
        self.sign = sign
        self.name = signToName[sign]
    
    def __repr__ (self):
        return self.color + " " + self.name
