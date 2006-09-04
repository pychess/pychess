#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import gtk

WHITE_OO = 1
WHITE_OOO = 2
BLACK_OO = 4
BLACK_OOO = 8

from Piece import Piece
def c (str):
    color = str[0] == "w" and "white" or "black"
    return Piece (color, str[1])

from Board import Board
startPieces = Board(
[[c("wr"),c("wn"),c("wb"),c("wq"),c("wk"),c("wb"),c("wn"),c("wr")],
[c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp")],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp")],
[c("br"),c("bn"),c("bb"),c("bq"),c("bk"),c("bb"),c("bn"),c("br")]]
)

from Utils.Move import Move

from copy import deepcopy
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

class History (GObject):
    '''Class remembers all moves, and can give you
    a two dimensional array (8x8) of Piece objects'''
    
    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())}
    
    def __init__ (self):
        GObject.__init__(self)
        self.boards = [Board(deepcopy(startPieces))]
        self.moves = []
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
    
    def __getitem__(self, i):
        return self.boards[i]
    
    def __len__(self):
        return len(self.boards)
    
    def add (self, move):
        self.moves += [move]
        self.boards += [self.boards[-1].move(move)]

        if str(move.castling) == "a1":
            self.castling ^= WHITE_OOO
        elif str(move.castling) == "h1":
            self.castling ^= WHITE_OO
        elif str(move.castling) == "h8":
            self.castling ^= BLACK_OO
        elif str(move.castling) == "a8":
            self.castling ^= BLACK_OOO
            
        self.emit("changed")
        return self
    
    def __getslice__(self, i, j):
        i = max(i, 0); j = max(j, 0)
        return self.__class__(self.data[i:j])
    
    def reverse (self):
        del self.boards[-1]
        move = self.moves.pop()
        
        if str(move.castling) == "a1":
            self.castling |= WHITE_OOO
        elif str(move.castling) == "h1":
            self.castling |= WHITE_OO
        elif str(move.castling) == "h8":
            self.castling |= BLACK_OO
        elif str(move.castling) == "a8":
            self.castling |= BLACK_OOO
        
        self.emit("changed")
        return self
    
    def clone (self):
        his = History()
        for move in self.moves:
            his.add(Move(his,move.cords,move.promotion))
        return his
