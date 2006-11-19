import os, thread
import datetime
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.Utils.History import History
import pychess.Utils.Move
from pychess.Utils.eval import evaluateComplete
#from pychess.Utils.book import getBestOpening, getOpenings

from pychess.Players.Engine import EngineDead
from pychess.Utils.const import *
from pychess.Utils.protoopen import protoopen

from pychess.widgets import gamewidget

profile = True
profile = False

class Game (GObject):

    __gsignals__ = {
        'game_ended' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int))
    }

    def __init__(self, widgid, analyzer, p1, p2, cc = None, seconds = 0, plus = 0):
        GObject.__init__(self)
        
        self.widgid = widgid
        
        self.player1 = p1
        self.player2 = p2
        self.chessclock = cc
        self.history = gamewidget.getWidgets(widgid)[0].view.history
        self.history.reset(mvlist=True)
        self.analyzer = analyzer
        
        self.lastSave = (None, "")
        
        #Event: the name of the tournament or match event.
        self.event = _("Local Event")
        #Site: the location of the event.
        self.site = _("Local site")
        self.round = 1
        today = datetime.date.today()
        self.year = today.year
        self.month = today.month
        self.day = today.day
        
        if self.chessclock:
            self.chessclock.reset()
            self.chessclock.setTime(seconds*10)
            self.chessclock.setGain(plus*10)
        
        self.history.connect("game_ended", self._gameEnded)
        
        self.player1.connect("action", self._action)
        self.player2.connect("action", self._action)
    
    def load (self, uri, loader):
        self.lastSave = (self.history.clone(), uri)
        ending = uri[uri.rfind(".")+1:]
        tags = loader.load(protoopen(uri), self.history)
        for player in self.players:
            if hasattr(player, "setBoard"):
                player.setBoard(self.history)
        self.analyzer.setBoard(self.history)
        
        if "Event" in tags:
            self.event = tags["Event"]
        if "Site" in tags:
            self.site = tags["Site"]
        if "Round" in tags:
            if tags["Round"].isdigit():
                self.round = int(tags["Round"])
        if "Date" in tags:
             date = tags["Date"].split(".")
             self.year, self.month, self.day = map(int, date)
    
    def save (self, path, saver):
        saver.save(open(path,"w"), self)
        lastSave = (self.history.clone(), path)
    
    def isChanged (self):
        return not self.lastSave[1] or self.lastSave[0] != self.history
    
    def run (self):
        self.connect_after("game_ended", lambda g,stat,comm: self.kill())
        if not profile:
            thread.start_new(self._run, ())
        else:
            def do():
                from profile import runctx
                loc = locals()
                loc["self"] = self
                runctx ("self._run()", loc, globals(), "/tmp/pychessprofile")
                from pstats import Stats
                s = Stats("/tmp/pychessprofile")
                s.sort_stats("time")
                s.print_stats()
            thread.start_new(do,())
    
    def _run (self):
        self.run = True
        while self.run:
            player, no = { WHITE: (self.player1, 0),
                           BLACK: (self.player2, 1)} [self.history.curCol()]
            
            if self.chessclock:
                self.chessclock.player = no
            
            try:
                move = player.makeMove(self.history)
            
            except pychess.Utils.Move.ParsingError:
                #Mostly debugging really
                import traceback
                print traceback.format_exc()
                print "Player 1 board:"
                self.player1.showBoard()
                print "Player 2 board:"
                self.player2.showBoard()
                raise
                
            except EngineDead:
                self.kill()
                break
            
            if not self.run:
                self.kill()
                break
            
            if not self.history.add(move,True):
                self.kill()
                break

            self.analyzer.makeMove(self.history)
                
    def kill (self):
        self.run = False
        if self.player1: self.player1.__del__()
        if self.player2: self.player2.__del__()
        if self.analyzer: self.analyzer.__del__()
        if self.chessclock: self.chessclock.stop()
    
    def _gameEnded (self, history, stat, comment):
        self.emit("game_ended", stat, comment)
        m1 = {
            DRAW: _("The game ended in a draw"),
            WHITEWON: _("White player won the game"),
            BLACKWON: _("Black player won the game")
        }[stat]
        m2 = {
            DRAW_REPITITION: _("as the same position was repeated three times in a row"),
            DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
            DRAW_STALEMATE: _("because of stalemate"),
            DRAW_AGREE: _("as the players agreed to"),
            WON_RESIGN: _("as opponent resigned"),
            WON_CALLFLAG: _("as opponent ran out of time"),
            WON_MATE: _("on a mate")
        }[comment]
        gamewidget.status(self.widgid, "%s %s." % (m1,m2), idle_add=True)
        
    def _action (self, player, action):

        if action == player.RESIGNATION:
            p = player == self.player1 and BLACKWON or WHITEWON
            self.emit("game_ended", p, WON_RESIGN)
            
        elif action == player.DRAW_OFFER:
            status(_("Draw offer has been sent"), True)
            otherPlayer = player == self.player1 and self.player2 or self.player1
            otherPlayer.offerDraw()
            
        elif action == player.DRAW_ACCEPTION:
            #FIXME: Test if draw is (still) valid
            self.emit("game_ended", DRAW, DRAW_AGREE)
            
        elif action == player.FLAG_CALL:
            if not self.chessclock:
                status(_("Couldn't call flag in game with no timecontrols"), True)
                return
            p = player == self.player2 and BLACKWON or WHITEWON
            p_other = player == self.player1 and 1 or 0
            if self.chessclock._get_playerTime(p_other) <= 0:
                self.emit("game_ended", p, WON_CALLFLAG)
            else:
                status(_("Couldn't call flag on player not out of time"), True)
                
    def _get_active_player (self):
        return self.history.curCol() == WHITE and self.player1 or self.player2
    activePlayer = property(_get_active_player)

    def _get_players (self):
        return self.player1, self.player2
    players = property(_get_players)
