import os, thread
import datetime
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from Utils.History import History
import Utils.Move

from Players.Engine import EngineDead

from Utils.validator import FINE, DRAW, WHITEWON, BLACKWON
from Utils.validator import DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, WON_RESIGN, WON_CALLFLAG, WON_MATE

class Game (GObject):

    __gsignals__ = {
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int))
    }

    def __init__(self, his, oracle, p1, p2, cc = None, seconds = 0, plus = 0):
        GObject.__init__(self)
    
        self.player1 = p1
        self.player2 = p2
        self.chessclock = cc
        self.history = his
        self.event = 'Local Event'
        self.site = 'Local site'
        self.round = '1'
        today = datetime.date.today()
        self.year = str(today.year)
        self.month = str(today.month)
        if len(self.month) == 1:
            self.month = "0" + self.month
        self.day = str(today.day)
        if len(self.day) == 1:
            self.day = "0" + self.day
        
        self.history.reset(True)
        if self.chessclock:
            self.chessclock.setTime(seconds*10)
            self.chessclock.setGain(plus*10)
        
        self.history.connect("game_ended", lambda h,stat,comm: self.emit("game_ended", stat, comm))
        
        self.player1.connect("action", self._action)
        self.player2.connect("action", self._action)
    
    def run (self):
        self.connect_after("game_ended", lambda g,stat,comm: self.kill())
        thread.start_new(self._run, ())
    
    def _run (self):
        self.run = True
        while self.run:
            for player in self.player1, self.player2:

                try:
                    answer = player.makeMove(self.history)
                    
                except Utils.Move.ParsingError:
                    #Mostly debugging really
                    import traceback
                    print traceback.format_exc()
                    print "Player 1 board:"
                    self.player1.showBoard()
                    print "Player 2 board:"
                    self.player2.showBoard()
                    import sys
                    sys.exit()
                    
                except EngineDead:
                    self.run = False
                    break
                
                if type(answer) in (list, tuple):
                    move, animate = answer
                else: move, animate = answer, True
                
                if not self.run:
                    log.warn("The 'line' in Game.py was used :O")
                    break
                
                if not self.history.add(move,True):
                    self.kill()
                    break
                
                if self.chessclock:
                    self.chessclock.switch()

    def kill (self):
        self.run = False
        if self.player1: self.player1.__del__()
        if self.player2: self.player2.__del__()
        if self.chessclock: self.chessclock.stop()
    
    def _action (self, player, action):
        p = player == self.player2 and BLACKWON or WHITEWON
        
        if action == player.RESIGNATION:
            self.emit("game_ended", p, WON_RESIGN)
            
        elif action == player.DRAW_OFFER:
            otherPlayer = player == self.player1 and self.player2 or self.player1
            otherPlayer.offerDraw()
            
        elif action == player.DRAW_ACCEPTION:
            #FIXME: Test if draw is (still) valid
            self.emit("game_ended", DRAW, DRAW_AGREE)
            
        elif action == FLAG_CALL:
            if not self.chessclock: return
            if self.chessclock._get_playerTime(1-p) <= 0:
                self.emit("game_ended", self.p, WON_CALLFLAG)
                
