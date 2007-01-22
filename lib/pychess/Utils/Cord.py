class CordFormatException(Exception): pass

class Cord:
    def __init__ (self, var1, var2 = None):
        """ Inits a new highlevel cord object.
            The cord B3 can be inited in the folowing ways:
                Cord(17), Cord("b3"), Cord(2,3), Cord("b",3) """
                
        if y == None:
            if type(var1) == int:
                x = FILE(var1)
                y = RANK(var1)
            else:
                x = self.charToInt(var[0])
                y = int(var[1]) - 1
        else:
            if type(x) == str:
                x = self.charToInt(x)
        
        self.x = x
        self.y = y
    
    def _get_cord (self):
        return (7-y)*8+x
    cord = property(_get_cord)
    
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
    
    def __cmp__ (self, other):
        if other == None:
            return 1
        if cmp (self.x, other.x):
            return cmp (self.x, other.x)
        if cmp (self.y, other.y):
            return cmp (self.y, other.y)
        return 0
    
    def __eq__ (self, other):
        return other != None and other.x == self.x and other.y == self.y
    
    def __ne__ (self, other):
        return not self.__eq__(other)
    
    def __repr__ (self):
        return self.cx + self.cy

    def __hash__ (self):
        return self.x*8+self.y
