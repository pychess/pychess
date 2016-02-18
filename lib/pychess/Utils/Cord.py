from __future__ import absolute_import

from .lutils.lmove import FILE, RANK
from pychess.compat import cmp


class CordFormatException(Exception):
    pass


class Cord:
    def __init__(self, var1, var2=None):
        """ Inits a new highlevel cord object.
            The cord B3 can be inited in the folowing ways:
            Cord(17), Cord("b3"), Cord(1,2), Cord("b",3)
        """

        if var2 is None:
            if isinstance(var1, int):
                # We assume the format Cord(17)
                self.x = FILE(var1)
                self.y = RANK(var1)
            else:
                # We assume the format Cord("b3")
                self.x = self.charToInt(var1[0])
                self.y = int(var1[1]) - 1
        else:
            if isinstance(var1, str):
                # We assume the format Cord("b",3)
                self.x = self.charToInt(var1)
                self.y = var2 - 1
            else:
                # We assume the format Cord(1,2)
                self.x = var1
                self.y = var2

    def _get_cord(self):
        return self.y * 8 + self.x

    cord = property(_get_cord)

    def _get_cx(self):
        return self.intToChar(self.x)

    cx = property(_get_cx)

    def _get_cy(self):
        return str(self.y + 1)

    cy = property(_get_cy)

    def intToChar(self, x):
        # assert 0 <= x <= 7
        return chr(x + ord('a'))

    def charToInt(self, char):
        ord_char = ord(char)
        if ord('A') <= ord_char <= ord('H'):
            ord_char -= ord('A')
        elif ord('a') <= ord_char <= ord('h'):
            ord_char -= ord('a')
        else:
            raise CordFormatException("x < 0 || x > 7 (%s, %d)" % (char, ord_char))
        return ord_char

    def _set_cords(self, x_y):
        self.x, self.y = x_y

    def _get_cords(self):
        return (self.x, self.y)

    cords = property(_get_cords, _set_cords)

    def __cmp__(self, other):
        if other is None:
            return 1
        if cmp(self.x, other.x):
            return cmp(self.x, other.x)
        if cmp(self.y, other.y):
            return cmp(self.y, other.y)
        return 0

    def __eq__(self, other):
        return other is not None and other.x == self.x and other.y == self.y

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.cx + self.cy

    def __hash__(self):
        return self.x * 8 + self.y
