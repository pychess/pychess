# -*- coding: UTF-8 -*-
from __future__ import print_function

from threading import Thread

from gi.repository import GObject

from pychess.compat import Queue
from pychess.Utils.const import *
from pychess.Variants.setupposition import SetupBoard
from pychess.System import conf, fident


class SetupMove:
    def __init__ (self, move):
        self.cord0 = move[0]
        self.cord1 = move[1]
        self.flag = 0
    
    def is_capture(self, board):
        return False


class SetupPlayer:
    __type__ = LOCAL

    def __init__ (self, board_control):
        self.queue = Queue()
        self.board_control = board_control
        self.board_control.connect("action", lambda bc, action, param: self.queue.put((action, param)))
        self.board_control.connect("piece_moved", self.piece_moved)

    def make_move (self):
        item = self.queue.get(block=True)
        return item

    def piece_moved (self, board, move, color):
        self.queue.put((SetupMove(move), color))


class SetupModel (GObject.GObject, Thread):
    __gsignals__ = {
        "game_started":  (GObject.SignalFlags.RUN_FIRST, None, ()),
        "game_changed":  (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "moves_undoing": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "game_loading":  (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "game_loaded":   (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "game_ended":    (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        }

    def __init__ (self):
        GObject.GObject.__init__(self)
        Thread.__init__(self, name=fident(self.run))
        self.daemon = True
        self.stop = False
        self.lowply = 0
        self.status = RUNNING
        self.players = []
        self.moves = []
        self.variant = SetupBoard
        self.boards = [self.variant()]
        self.variations = [self.boards]

    def _get_ply (self):
        return self.boards[-1].ply
    ply = property(_get_ply)

    def getBoardAtPly (self, ply, variation=0):
        return self.boards[ply]

    def getMoveAtPly (self, ply, variation=0):
        return self.moves[ply]

    def isPlayingICSGame(self):
        # prevent hovering over fields
        return True
        
    def run (self):
        self.emit("game_started")
        while True:
            p0, p1 = self.curplayer.make_move()
            if isinstance(p0, SetupMove):
                #print(p0.cord0, p0.cord1, p1)
                new_board = self.boards[-1].move(p0, p1)
                self.moves.append(p0)
                self.boards.append(new_board)
                self.emit("game_changed", self.ply)
            elif p0 == "SETUP":
                #print("SETUP", p0, p1)
                self.emit("game_ended", 0)
                self.boards = [self.variant(setup=p1)]
                self.variations = [self.boards]
                self.emit("game_loaded", 0)
                self.emit("game_started")
                self.emit("game_changed", 0)
            elif p0 == "CLOSE":
                #print("CLOSE")
                break
