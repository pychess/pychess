signToName = {"b":"Bishop","k":"King","n":"Knight","p":"Pawn","q":"Queen","r":"Rook"}
class Piece:
    def __init__ (self, color, sign):
        self.color = color
        self.sign = sign
        try:
            self.name = signToName[sign]
        except:
            print "SIGN WAS", sign
    
    def __repr__ (self):
        return self.color + " " + self.name

    def __eq__ (self, other):
        return  type(self) == type(other) and \
                self.__class__ == other.__class__ and \
                self.color == other.color and \
                self.sign == other.sign
