import os, thread
import datetime
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, idle_add

from pychess.Utils.History import History
import pychess.Utils.Move
from pychess.Utils.eval import evaluateComplete
#from pychess.Utils.book import getBestOpening, getOpenings

from pychess.Players.Engine import EngineDead
from pychess.Utils.const import *
from pychess.System.protoopen import protoopen

profile = True
profile = False

class Game (GObject):
    
    def __init__(   self, gmwidg, history, analyzers,
                    p1, p2, cc = None, seconds = 0, plus = 0):
        
        GObject.__init__(self)
        
        self.gmwidg = gmwidg
        
        self.player1 = p1
        self.player2 = p2
        self.chessclock = cc
        self.history = history
        self.history.reset(mvlist=True)
        self.history.connect("game_ended", lambda h,s,c: self.gameEnded(s,c))
        self.analyzers = analyzers
        
        # FIXME: Draw offers should be unset after perhaps 2 moves
        self.drawState = None
        
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
        
        def callback (player, action):
            idle_add(lambda: self._action(player, action))
        
        self.player1.connect("action", callback)
        self.player2.connect("action", callback)
    
    def load (self, uri, gameno, position, loader):
        ending = uri[uri.rfind(".")+1:]
        chessfile = loader.load(protoopen(uri))
        
        self.gmwidg.widgets["board"].view.autoUpdateShown = False
        chessfile.loadToHistory(gameno, position, self.history)
        self.gmwidg.widgets["board"].view.autoUpdateShown = True
        self.gmwidg.widgets["board"].view.shown = len(self.history)-1
        
        self.lastSave = (self.history.clone(), uri)
        
        self.event = chessfile.get_event(gameno)
        self.site = chessfile.get_site(gameno)
        self.round = chessfile.get_round(gameno)
        self.year, self.month, self.day = chessfile.get_date(gameno)
        
        if self.history[-1].status == RUNNING:
            for player in self.players:
                if hasattr(player, "setBoard"):
                    player.setBoard(self.history)
            
            for analyzer in self.analyzers:
                analyzer.setBoard(self.history)
            
            self.run()
            
        else:
            self.kill()
    
    def save (self, path, saver):
        fileobj = open(path, "w")
        saver.save(fileobj, self)
        lastSave = (self.history.clone(), path)
        fileobj.close()
        
    def isChanged (self):
    	if not os.path.isfile(self.lastSave[1][7:]): return True
        if len(self.history) <= 1: return False
        if self.lastSave[0] == self.history: return False
        return True
    
    def run (self):
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
        self.running = True
        while self.running:
            player, no = { WHITE: (self.player1, 0),
                           BLACK: (self.player2, 1)} [self.history.curCol()]
            
            if self.chessclock:
                self.chessclock.player = no
            
            if player.__type__ == LOCAL:
                self.gmwidg.setTabReady(True)
            else: self.gmwidg.setTabReady(False)
            
            if self.chessclock:
                if no == WHITE:
                    player.updateTime (self.chessclock.p0time/10.,
                                       self.chessclock.p1time/10.)
                else: player.updateTime (self.chessclock.p1time/10.,
                                         self.chessclock.p0time/10.)
            
            try:
                move = player.makeMove(self.history)
            except EngineDead:
                break
            
            if not self.running:
                break
            
            if not self.history.add(move,True):
                break
            
            for analyzer in self.analyzers:
                analyzer.makeMove(self.history)
                
    def kill (self):
        self.gmwidg.setTabReady(False)
        self.running = False
        self.player1.__del__()
        self.player2.__del__()
        for analyzer in self.analyzers:
            analyzer.__del__()
        if self.chessclock: self.chessclock.stop()
    
    def gameEnded (self, stat, comment):
        self.kill()
        m1 = {
            DRAW: _("The game ended in a draw"),
            WHITEWON: _("White player won the game"),
            BLACKWON: _("Black player won the game")
        }[stat]
        m2 = {
            DRAW_INSUFFICIENT: _("caused by insufficient material"),
            DRAW_REPITITION: _("as the same position was repeated three times in a row"),
            DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
            DRAW_STALEMATE: _("because of stalemate"),
            DRAW_AGREE: _("as the players agreed to"),
            WON_RESIGN: _("as opponent resigned"),
            WON_CALLFLAG: _("as opponent ran out of time"),
            WON_MATE: _("on a mate")
        }[comment]
        self.gmwidg.status("%s %s." % (m1,m2), idle_add=True)
        
    def _action (self, player, action):
        
        if action == RESIGNATION:
            p = player == self.player1 and BLACKWON or WHITEWON
            self.gameEnded(p, WON_RESIGN)
            
        elif action == DRAW_OFFER:
            otherPlayer = player == self.player1 and self.player2 or self.player1
            if self.drawState == otherPlayer:
                self.gameEnded(DRAW, DRAW_AGREE)
            else:
                self.gmwidg.status(_("Draw offer has been sent"), True)
                self.drawState = player
                otherPlayer.offerDraw()
            
        elif action == FLAG_CALL:
            if not self.chessclock:
                self.gmwidg.status(_("Couldn't call flag in game with no timecontrols"), True)
                return
            p = player == self.player2 and BLACKWON or WHITEWON
            p_other = player == self.player1 and 1 or 0
            if self.chessclock._get_playerTime(p_other) <= 0:
                self.gameEnded(p, WON_CALLFLAG)
            else:
                self.gmwidg.status(_("Couldn't call flag on player not out of time"), True)
                
    def _get_active_player (self):
        return self.history.curCol() == WHITE and self.player1 or self.player2
    activePlayer = property(_get_active_player)

    def _get_players (self):
        return self.player1, self.player2
    players = property(_get_players)
