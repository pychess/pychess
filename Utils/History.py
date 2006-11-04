#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from copy import copy
from threading import Lock

class HistoryPool:
    def __init__ (self):
        self.objects = []
        self.lock = Lock()
        
    def pop (self, clear=True):
        self.lock.acquire()
        
        if len(self.objects) <= 0:
            self.objects.append(History())
        his = self.objects.pop()
        his.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        
        self.lock.release()
        return his
        
    def add (self, history):
        #Todo: deconnect signals
        self.objects.append(history)
hisPool = HistoryPool()

from Piece import Piece
from Board import Board
from Utils.const import *
startBoard = Board(
[[Piece(WHITE, ROOK), Piece(WHITE, KNIGHT), Piece(WHITE, BISHOP), Piece(WHITE, QUEEN), Piece(WHITE, KING), Piece(WHITE, BISHOP), Piece(WHITE, KNIGHT), Piece(WHITE, ROOK)],
[Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN), Piece(WHITE, PAWN)],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[None,None,None,None,None,None,None,None],
[Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN), Piece(BLACK, PAWN)],
[Piece(BLACK, ROOK), Piece(BLACK, KNIGHT), Piece(BLACK, BISHOP), Piece(BLACK, QUEEN), Piece(BLACK, KING), Piece(BLACK, BISHOP), Piece(BLACK, KNIGHT), Piece(BLACK, ROOK)]])

from System.Log import log
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject
from Utils import validator

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

class History (GObject):
    '''Class remembers all moves, and can give you
    a two dimensional array (8x8) of Piece objects'''
    
    __gsignals__ = {
        'changed': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'added': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'cleared': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int))
    }
    
    def __init__ (self, mvlist=False):
        GObject.__init__(self)
        self.reset(mvlist)
    
    def reset (self, mvlist=False):
        GObject.__init__(self)
        
        self.boards = [startBoard.clone()]
        self.moves = []
        self.curColModi = 0
        if mvlist:
            self.boards[-1].movelist = validator.findMoves(self.boards[-1])
        
        self.emit("cleared")
    
    def __getitem__(self, i):
        return self.boards[i]
    
    def __len__(self):
        return len(self.boards)
    
    def curCol (self):
        return (len(self)+self.curColModi) % 2 == 0 and BLACK or WHITE
    
    def setStartingColor (self, color):
        if color == BLACK:
            self.curColModi = 1
        else: self.curColModi = 0
    
    def add (self, move, mvlist=False):
        
        self.moves.append(move)
        board = self.boards[-1].move(move, mvlist)
        self.boards.append(board)
        self.emit("changed")
        
        if mvlist:
            status, comment = validator.status(self)
            if status != RUNNING:
                board.status = status
                board.comment = comment
                self.emit("game_ended", board.status, board.comment)
                return False
            
        return self
    
    def __eq__ (self, other):
        """ Warning: Not complete equals test.
            Only most important stuff is tested """
        
        if not isinstance(other, History):
            return False
        
        if len(self) != len(other) or \
                self.curColModi != other.curColModi:
            return False
        
        if self.boards[-1].__eq__(other.boards[-1]):
            return True
        return False

    def clone (self):
        his = hisPool.pop()
        his.moves = copy(self.moves)
        his.boards = copy(self.boards)
        return his
