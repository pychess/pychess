class CordFormatException(Exception): pass

#TODO: In like 6 moves, more than 25000 Cords are inited. Perhaps it should be pooled..
class Cord:
    def __init__ (self, x, y = None):
        if y == None:
            x = x.strip()
            y = int(x[1]) - 1
            x = self.charToInt(x[0])
    
        assert 0 <= y <= 7
        if type(x) == str:
            x = self.charToInt(x)
        assert 0 <= x <= 7
        
        self.x, self.y = int(x), int(y)
    
    def _get_cx (self):
        return self.intToChar(self.x)
    cx = property(_get_cx)
    
    def _get_cy (self):
        return str(self.y+1)
    cy = property(_get_cy)
    
    def intToChar (self, x):
        assert 0 <= x <= 7
        return chr(x + ord('a'))
    
    def charToInt (self, char):
        a = ord(char)
        if ord('A') <= a <= ord('H'):
            a -= ord('A');
        elif ord('a') <= a <= ord('h'):
            a -= ord('a');
        else: raise CordFormatException, "x < 0 || x > 7 (%s, %d)" % (char, a)
        return a
    
    def _set_cords (self, (x, y)):
        self.x, self.y = x, y
    def _get_cords (self):
        return (self.x, self.y)
    cords = property(_get_cords, _set_cords)
    
    def __eq__ (self, other):
        return type(other) == type(self) and (other.x,other.y) == (self.x,self.y)
    
    def __repr__ (self):
        return self.cx + self.cy

    def __hash__ (self):
        return self.x*8+self.y
