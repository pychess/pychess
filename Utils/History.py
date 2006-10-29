#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from time import time

import pygtk
pygtk.require("2.0")
import gtk

WHITE_OO = 1
WHITE_OOO = 2
BLACK_OO = 4
BLACK_OOO = 8
WHITE_CASTLED = 16
BLACK_CASTLED = 32

class HistoryPool:
    def __init__ (self):
        self.objects = []
    def pop (self, clear=True):
        if len(self.objects) <= 0:
            self.objects.append(History())
        his = self.objects.pop()
        his.status = validator.FINE
        his.castling = WHITE_OO | WHITE_OOO | WHITE_CASTLED \
                     | BLACK_OO | BLACK_OOO | BLACK_CASTLED
        return his
    def add (self, history):
        #Todo: deconnect signals
        self.objects.append(history)
hisPool = HistoryPool()

from Piece import Piece
def c (str):
    color = str[0] == "w" and "white" or "black"
    return Piece (color, str[1])

from Board import Board
startBoard = Board(
[[c("wr"),c("wn"),c("wb"),c("wq"),c("wk"),c("wb"),c("wn"),c("wr")],
[c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp"),c("wp")],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp"),c("bp")],
[c("br"),c("bn"),c("bb"),c("bq"),c("bk"),c("bb"),c("bn"),c("br")]])

from System.Log import log
import validator

from copy import copy
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

def cloneStartPieces ():
    l = []
    for row in startPieces:
        l.append([])
        for piece in row:
            l[-1].append(piece)
    return l

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

from Utils.Cord import Cord
a1 = Cord('a1')
h1 = Cord('h1')
a8 = Cord('a8')
h8 = Cord('h8')

class History (GObject):
    '''Class remembers all moves, and can give you
    a two dimensional array (8x8) of Piece objects'''
    
    __gsignals__ = {
        'changed': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'cleared': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int))
    }
    
    def __init__ (self, mvlist=False):
        GObject.__init__(self)
        self.reset(mvlist)
    
    def reset (self, mvlist=False):
        GObject.__init__(self)
        
        self.boards = [startBoard.clone()]
        self.curColModi = 0
        self.fifty = 0
        self.moves = []
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        self.status = validator.FINE
        self.movelist = []
        if mvlist:
            self.movelist.append(validator.findMoves(self))
        else: self.movelist.append(None)
        
        self.emit("cleared")
    
    def __getitem__(self, i):
        return self.boards[i]
    
    def __len__(self):
        return len(self.boards)
    
    def curCol (self):
        return (len(self)+self.curColModi) % 2 == 1 and "white" or "black"
    
    def setStartingColor (self, color):
        if color == "black":
            self.curColModi = 1
        else: self.curColModi = 0
    
    def add (self, move, mvlist=False):
        
        capture = self.boards[-1][move.cord1] != None
        
        if move.castling:
            c = move.castling[0]
            if c == a1: self.castling |= WHITE_CASTLED
            elif c == h1: self.castling |= WHITE_CASTLED
            elif c == a8: self.castling |= BLACK_CASTLED
            elif c == h8: self.castling |= BLACK_CASTLED

        p = self.boards[-1][move.cord0]

        if p.sign == "k":
            if p.color == "black":
                self.castling = rm(self.castling, BLACK_OO)
                self.castling = rm(self.castling, BLACK_OOO)
            elif p.color == "white":
                self.castling = rm(self.castling, WHITE_OO)
                self.castling = rm(self.castling, WHITE_OOO)
        
        elif p.sign == "r":
            c = move.cord0
            if c == a1: self.castling = rm(self.castling, WHITE_OOO)
            elif c == h1: self.castling = rm(self.castling, WHITE_OO)
            elif c == a8: self.castling = rm(self.castling, BLACK_OOO)
            elif c == h8: self.castling = rm(self.castling, BLACK_OO)
        
        self.moves.append(move)
        self.boards.append(self.boards[-1].move(move))

        if capture or self.boards[-1][move.cord1].sign != "p":
            self.fifty += 1
        else: self.fifty = 0
        
        if mvlist:
            self.movelist.append(validator.findMoves(self))
        else: self.movelist.append(None)
        
        if mvlist:
            status, comment = validator.status(self)
            if status != validator.FINE:
                self.status = status
                self.emit("changed")
                self.emit("game_ended", status, comment)
                return False
        
        self.emit("changed")
        
        return self
    
    def __eq__ (self, other):
    	""" Warning: Not complete equals test.
    		Only most important stuff is tested """
    	
    	if not isinstance(other, History):
    		return False
    	
    	if len(self) != len(other) or \
	    		self.curColModi != other.curColModi or \
    			self.status != other.status or \
    			self.castling != other.castling:
    		return False
    	
    	if self.boards[-1].__eq__(other.boards[-1]):
    		return True
    	return False

    def clone (self):
        his = hisPool.pop()
        his.castling = self.castling
        his.fifty = self.fifty
        his.moves = copy(self.moves)
        his.boards = copy(self.boards)
        his.movelist = copy(self.movelist)
        his.status = self.status
        return his
