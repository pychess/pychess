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
startPieces = \
[[c("wr"),c("wn"),c("wb"),c("wq"),c("wk"),c("wb"),c("wn"),c("wr")],
[c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp")],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp")],
[c("br"),c("bn"),c("bb"),c("bq"),c("bk"),c("bb"),c("bn"),c("br")]]

from Utils.Move import Move
from Utils.Log import log
import validator

from copy import copy
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

def getStartPieces ():
    l = []
    for row in startPieces:
        l += [[]]
        for piece in row:
            l[-1] += [piece]
    return l

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

class History (GObject):
    '''Class remembers all moves, and can give you
    a two dimensional array (8x8) of Piece objects'''
    
    __gsignals__ = {'changed': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
                    'stall':   (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
                    'mate':    (SIGNAL_RUN_FIRST, TYPE_NONE, ())}
    
    def __init__ (self):
        GObject.__init__(self)
        self.boards = [Board(getStartPieces())]
        self.fifty = 0
        self.moves = []
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
    
    def __getitem__(self, i):
        return self.boards[i]
    
    def __len__(self):
        return len(self.boards)
    
    def add (self, move):
        capture = self.boards[-1][move.cord1] != None
        
        if move.castling:
            c = str(move.castling[0])
            if c == 'a1': self.castling = rm(self.castling, WHITE_OOO)
            elif c == 'h1': self.castling = rm(self.castling, WHITE_OO)
            elif c == 'a8': self.castling = rm(self.castling, BLACK_OOO)
            elif c == 'h8': self.castling = rm(self.castling, BLACK_OO)

        p = self.boards[-1][move.cord0]

        if p.sign == "k":
            if p.color == "black":
                self.castling = rm(self.castling, BLACK_OO)
                self.castling = rm(self.castling, BLACK_OOO)
            elif p.color == "white":
                self.castling = rm(self.castling, WHITE_OO)
                self.castling = rm(self.castling, WHITE_OOO)
        
        elif p.sign == "r":
            c = str(move.cord0)
            if c == 'a1': self.castling = rm(self.castling, WHITE_OOO)
            elif c == 'h1': self.castling = rm(self.castling, WHITE_OO)
            elif c == 'a8': self.castling = rm(self.castling, BLACK_OOO)
            elif c == 'h8': self.castling = rm(self.castling, BLACK_OO)
        
        self.moves += [move]
        self.boards += [self.boards[-1].move(move)]

        if capture or self.boards[-1][move.cord1].sign != "p":
            self.fifty += 1
        else: self.fifty = 0
        
        self.emit("changed")
        return self
    
    def __getslice__(self, i, j):
        i = max(i, 0); j = max(j, 0)
        return self.__class__(self.data[i:j])
    
    def reverse (self):
        log.warn("Using buggy Move.reverse method!")
        
        del self.boards[-1]
        move = self.moves.pop()
        
        #FIXME: This doesn't work at ALL!!!!
        #Not fixing as the new validator system hopefully will make it irrelevant
        
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
        his.castling = self.castling
        his.fifty = self.fifty
        his.moves = copy(self.moves)
        his.boards = copy(self.boards)
        return his
