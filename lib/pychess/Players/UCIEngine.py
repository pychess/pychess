from pychess.Players.Player import PlayerIsDead
from pychess.Players.ProtocolEngine import ProtocolEngine
from pychess.Utils.Move import *
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.GameModel import GameModel
from pychess.Utils.logic import validate, getMoveKillingKing
from pychess.Utils.const import *
from pychess.System.Log import log
from pychess.System.SubProcess import TimeOutError, SubProcessError
from pychess.System.ThreadPool import pool
from pychess.Variants.fischerandom import FischerRandomChess

TYPEDIC = {"check":lambda x:x=="true", "spin":int}
OPTKEYS = ("type", "min", "max", "default", "var")

# FIXME: isready system is not very good. In many methods where we ought to wait
#        for readyok, we don't.
#        Perhaps we could block on a classglobal write method?

class UCIEngine (ProtocolEngine):
    
    def __init__ (self, subprocess, color, protover):
        ProtocolEngine.__init__(self, subprocess, color, protover)
        
        self.ids = {}
        self.options = {}
        self.wtime = 60000
        self.btime = 60000
        self.incr = 0
        
        self.readyok = False
        self.pondermove = None
        self.ignoreNext = False
        self.board = None
        self.uciok = False
    
    ############################################################################
    #   Move                                                                   #
    ############################################################################
    
    def start (self, block):
        print >> self.engine, "uci"
        
        if block:
            while not self.ready:
                try:
                    line = self.engine.readline()
                except SubProcessError, e:
                    # We catch this later in getMove
                    print "FUCK", e.args
                    self.emit("ready")
                    break
                self.parseLine(line)
    
    def autoAnalyze (self, inverse=False):
        self.start(block=True)
        
        if not inverse:
            self.mode = ANALYZING
        else: self.mode = INVERSE_ANALYZING
        self.setOptions({'Ponder': False})
        
        self.makeMove(GameModel())
        
        def autorun ():
            while self.connected:
                try:
                    self.parseLine(self.engine.readline())
                except PlayerIsDead:
                    if self.connected:
                        log.warn("Analyzer died\n", self.defname)
                        self.connected = False
                except SubProcessError, e:
                    if self.connected:
                        log.warn("Analyzer raised: %s\n" % e, self.defname)
                        self.connected = False
        pool.start(autorun)
    
    def makeMove (self, gamemodel):
        
        if not self.board:
            self.isready()
            self.newGame()
        
        self.board = gamemodel.boards[-1]
        
        ponderhit = False
        
        if self.mode == NORMAL:
            if gamemodel.ply > gamemodel.lowply+1 and self.pondermove:
                if self.pondermove and gamemodel.moves[-1] == self.pondermove:
                    print >> self.engine, "ponderhit"
                    ponderhit = True
                else:
                    self.ignoreNext = True
                    print >> self.engine, "stop"
        
        elif self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()
        
        if not ponderhit:
            self._searchNow()
        
        # We don't block when analyzing. Instead the readline call is placed in
        # a thread created by autoAnalyze
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            return
        
        # Parse outputs
        while True:
            try:
                line = self.engine.readline()
            except SubProcessError, e:
                raise PlayerIsDead, e
            
            move = self.parseLine(line)
            if move:
                return move
    
    ############################################################################
    #   Internal                                                               #
    ############################################################################
    
    def _searchNow (self):
        if self.mode == NORMAL:
            print >> self.engine, "position fen", self.board.asFen()
            
            if self.getOption('UCI_LimitStrength') or self.strength == EXPERT:
                print >> self.engine, "go wtime", self.wtime, "btime", self.btime, \
                                         "winc", self.incr, "binc", self.incr
            
            elif self.strength == INTERMEDIATE:
                print >> self.engine, "go depth 4"
                
            elif self.strength == EASY:
                print >> self.engine, "go depth 1"
        
        else:
            print >> self.engine, "stop"
            if self.mode == INVERSE_ANALYZING:
                if self.board.board.opIsChecked():
                    # Many engines don't like positions able to take down enemy
                    # king. Therefore we just return the "kill king" move
                    # automaticaly
                    self.emit("analyze", [getMoveKillingKing(self.board)])
                    return
            print >> self.engine, "position fen", self.board.asFen()
            print >> self.engine, "go infinite"
    
    def _startPonder (self):
        print >> self.engine, "position fen", self.board.asFen(), \
                                "moves", self.pondermove
        print >> self.engine, "go ponder wtime", self.wtime, \
            "btime", self.btime, "winc", self.incr, "binc", self.incr
    
    ############################################################################
    #   From Engine                                                            #
    ############################################################################
    
    def parseLine (self, line):
        parts = line.split()
        if not parts: return
        
        if parts[0] == "id":
            self.ids[parts[1]] = " ".join(parts[2:])
            return
        
        if parts[0] == "option":
            dic = {}
            last = 1
            varlist = []
            for i in xrange (2, len(parts)+1):
                if i == len(parts) or parts[i] in OPTKEYS:
                    key = parts[last]
                    value = " ".join(parts[last+1:i])
                    if "type" in dic and dic["type"] in TYPEDIC:
                        value = TYPEDIC[dic["type"]](value)
                        
                    if key == "var":
                        varlist.append(value)
                    else:
                        dic[key] = value
                        
                    last = i
            if varlist:
                dic["vars"] = varlist
            
            name = dic["name"]
            del dic["name"]
            self.options[name] = dic
            return
        
        if parts[0] == "uciok":
            self.uciok = True
            # We need to run isready before any searching. However setOptions
            # will run it, so we only need to do it here for engines we don't
            # set options for
            if "OwnBook" in self.options:
                self.setOptions({"OwnBook": True})
            self.emit("ready")
            return
        
        if parts[0] == "readyok":
            return "ready"
        
        # A Move
        if self.mode == NORMAL and parts[0] == "bestmove":
            
            if self.ignoreNext:
                self.ignoreNext = False
                return
            
            move = parseAN(self.board, parts[1])
            self.board = self.board.move(move)
            
            if self.getOption('Ponder'):
                if len(parts) == 4 and self.board:
                    self.pondermove = parseAN(self.board, parts[3])
                    self._startPonder()
                else: self.pondermove = None
            
            return move
        
        if self.mode != NORMAL and parts[0] == "info" and "pv" in parts:
            movstrs = parts[parts.index("pv")+1:]
            moves = listToMoves (self.board, movstrs, AN, validate=True)
            self.emit("analyze", moves)
            return
    
    ############################################################################
    #   To Engine                                                              #
    ############################################################################
    
    def setOptions (self, dic):
        #assert self.uciok
        for option, value in dic.iteritems():
            if self.options[option]["default"] != value:
                self.options[option]["default"] = value
                if type(value) == bool: value = str(value).lower()
                print >> self.engine, "setoption name", option, "value", str(value)
    
    def getOption (self, option):
        if option in self.options:
            return self.options[option]["default"]
        return None
    
    def isready (self):
        print >> self.engine, "isready"
        while True:
            try:
                line = self.engine.readline()
            except SubProcessError, e:
                raise PlayerIsDead, e
            
            ready = self.parseLine(line)
            if ready == "ready":
                break
    
    def updateTime (self, secs, opsecs):
        if self.color == WHITE:
            self.wtime = int(secs*1000)
            self.btime = int(opsecs*1000)
        else:
            self.btime = int(secs*1000)
            self.wtime = int(opsecs*1000)
    
    def newGame (self):
        print >> self.engine, "ucinewgame"
    
    def setBoard (self, model):
        # UCI always sets the position when searching for a new game, so we
        # don't actually have to do anything here. However when the new board
        # is from an entirely different game than the current, there is no need
        # that the engine still stores the old transposition table
        self.board = None

        if model.boards[0].asFen() != FEN_START:
            if "UCI_Chess960" in self.options and \
                    model.variant == FischerRandomChess:
                self.setOptions({"UCI_Chess960": True})
    
        ########################################################################
        #   Offer Stuff                                                        #
        ########################################################################
    
    def offer (self, offer):
        if offer.offerType == DRAW_OFFER:
            self.emit("decline", offer)
        else:
            self.emit("accept", offer)
    
    def hurry (self):
        print >> self.engine, "stop"
    
    def pause (self):
        if self.ready:
            if self.board and self.board.color == self.color or \
                    self.mode != NORMAL or self.pondermove:
                self.ignoreNext = True
                print >> self.engine, "stop"
        else:
            self.runWhenReady(self.pause)
    
    def resume (self):
        if self.ready:
            if self.mode == NORMAL:
                if self.board and self.board.color == self.color:
                    self._searchNow()
                elif self.getOption('Ponder') and self.pondermove:
                    self._startPonder()
            else:
                self._searchNow()
        else:
            self.runWhenReady(self.resume)
    
    def undoMoves (self, moves, gamemodel):
        # Not nessesary in UCI
        pass
    
        ########################################################################
        #   Start / Stop                                                       #
        ########################################################################
    
    def setStrength (self, strength):
        if self.ready:
            self.strength = strength
            options = {}
            
            if 'UCI_LimitStrength' in self.options and 'UCI_Elo' in self.options:
                options['UCI_LimitStrength'] = True
                if strength == EASY:
                    options['UCI_Elo'] = 1000
                elif strength == INTERMEDIATE:
                    options['UCI_Elo'] = 1500
            
            if 'Ponder' in self.options:
                options['Ponder'] = strength==EXPERT
            
            self.setOptions(options)
        else:
            self.runWhenReady(self.setStrength, strength)
    
    def setTime (self, secs, gain):
        self.wtime = max(secs*1000, 1)
        self.btime = max(secs*1000, 1)
        self.incr = max(gain*1000, 1)
    
    def end (self, status, reason):
        if self.connected:
            # UCI doens't care about reason, so we just kill
            self.kill(reason)
    
    def kill (self, reason):
        """ Kills the engine, starting with the 'stop' and 'quit' commands, then
            trying sigterm and eventually sigkill.
            Returns the exitcode, or if engine have already been killed, the
            method returns None """
        if self.connected:
            self.connected = False
            try:
                try:
                    print >> self.engine, "stop"
                    print >> self.engine, "quit"
                    return self.engine.gentleKill()
                
                except OSError, e:
                    # No need to raise on a hang up error, as the engine is dead
                    # anyways
                    if e.errno == 32:
                        log.warn("Hung up Error", self.defname)
                        return e.errno
                    else: raise
            
            finally:
                # Clear the analyzed data, if any
                self.emit("analyze", [])
    
    ############################################################################
    #   Info                                                                   #
    ############################################################################
    
    def canAnalyze (self):
        return True
    
    def __repr__ (self):
        if self.name:
            return self.name
        if "name" in self.ids:
            return self.ids["name"]
        return self.defname
