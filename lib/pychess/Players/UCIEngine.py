from copy import copy
import Queue

from pychess.Utils.Move import *
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.GameModel import GameModel
from pychess.Utils.logic import validate, getMoveKillingKing
from pychess.Utils.const import *
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.System.Log import log
from pychess.System.SubProcess import TimeOutError, SubProcessError
from pychess.System.ThreadPool import pool
from pychess.Variants.fischerandom import FischerRandomChess

from ProtocolEngine import ProtocolEngine
from Player import Player, PlayerIsDead, TurnInterrupt

TYPEDIC = {"check":lambda x:x=="true", "spin":int}
OPTKEYS = ("type", "min", "max", "default", "var")

class UCIEngine (ProtocolEngine):
    
    def __init__ (self, subprocess, color, protover):
        ProtocolEngine.__init__(self, subprocess, color, protover)
        
        self.ids = {}
        self.options = {}
        self.optionsToBeSent = {}
        
        self.wtime = 60000
        self.btime = 60000
        self.incr = 0
        self.timeHandicap = 1 
        
        self.pondermove = None
        self.ignoreNext = False
        self.board = None
        self.uciok = False
        
        self.returnQueue = Queue.Queue()
        self.engine.connect("line", self.parseLines)
        self.engine.connect("died", lambda e: self.returnQueue.put("del"))
        
        self.connect("readyForOptions", self.__onReadyForOptions_before)
        self.connect_after("readyForOptions", self.__onReadyForOptions)
        self.connect_after("readyForMoves", self.__onReadyForMoves)
    
    #===========================================================================
    #    Starting the game
    #===========================================================================
    
    def prestart (self):
        print >> self.engine, "uci"
    
    def start (self):
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            pool.start(self.__startBlocking)
        else:
            self.__startBlocking()
    
    def __startBlocking (self):
        r = self.returnQueue.get()
        assert r == "ready"
        #self.emit("readyForOptions")
        #self.emit("readyForMoves")
    
    def __onReadyForOptions_before (self, self_):
        self.readyOptions = True
    
    def __onReadyForOptions (self, self_):
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            if self.hasOption("Ponder"):
                self.setOption('Ponder', False)
        
        for option, value in self.optionsToBeSent.iteritems():
            if self.options[option]["default"] != value:
                self.options[option]["default"] = value
                if type(value) == bool: value = str(value).lower()
                print >> self.engine, "setoption name", option, "value", str(value)
        
        print >> self.engine, "isready"
    
    def __onReadyForMoves (self, self_):
        self.returnQueue.put("ready")
        self.readyMoves = True
        self._newGame()
        
        # If we are an analyzer, this signal was already called in a different
        # thread, so we can safely block it.
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            if not self.board:
                self.board = Board(setup=True)
            self.putMove(self.board, None, None)
    
    #===========================================================================
    #    Ending the game
    #===========================================================================
    
    def end (self, status, reason):
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
                    self.returnQueue.put("del")
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
                self.emit("analyze", [], None)
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    def putMove (self, board1, move, board2):
        if not self.readyMoves:
            return
        
        self.board = board1
        
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()
        
        self._searchNow()
    
    def makeMove (self, board1, move, board2):
        
        assert self.readyMoves
        
        self.board = board1
        
        ponderhit = False
        
        if board2 and self.pondermove:
            if self.pondermove and move == self.pondermove:
                print >> self.engine, "ponderhit"
                ponderhit = True
            else:
                self.ignoreNext = True
                print >> self.engine, "stop"
        
        if not ponderhit:
            self._searchNow()
        
        # Parse outputs
        r = self.returnQueue.get()
        if r == "del":
            raise PlayerIsDead
        if r == "int":
            raise TurnInterrupt
        return r
    
    def updateTime (self, secs, opsecs):
        if self.color == WHITE:
            self.wtime = int(secs*1000*self.timeHandicap)
            self.btime = int(opsecs*1000)
        else:
            self.btime = int(secs*1000*self.timeHandicap)
            self.wtime = int(opsecs*1000)
    
    #===========================================================================
    #    Standard options
    #===========================================================================
    
    def setOptionAnalyzing (self, mode):
        self.mode = mode
    
    def setOptionInitialBoard (self, model):
        # UCI always sets the position when searching for a new game, but for
        # getting analyzers ready to analyze at first ply, it is good to have.
        self.board = model.getBoardAtPly(model.ply)
        pass
    
    def setOptionVariant (self, variant):
        if variant == FischerRandomChess:
            assert self.hasOption("UCI_Chess960")
            self.setOption("UCI_Chess960", True)
    
    def setOptionTime (self, secs, gain):
        self.wtime = int(max(secs*1000*self.timeHandicap, 1))
        self.btime = int(max(secs*1000*self.timeHandicap, 1))
        self.incr = int(gain*1000*self.timeHandicap)
    
    def setOptionStrength (self, strength):
        self.strength = strength
        
        if self.hasOption('UCI_LimitStrength') and self.hasOption('UCI_Elo'):
            self.setOption('UCI_LimitStrength', True)
            if strength <= 6:
                self.setOption('UCI_Elo', 300 * strength + 200)
        else:
            self.timeHandicap = th = 0.01 * 10**(strength/4.)
            self.wtime = int(max(self.wtime*th, 1))
            self.btime = int(max(self.btime*th, 1))
            self.incr = int(self.incr*th)
        
        if self.hasOption('Ponder'):
            self.setOption('Ponder', strength >= 7)
    
    #===========================================================================
    #    Interacting with the player
    #===========================================================================
    
    def pause (self):
        self.engine.pause()
        return
        
        if self.board and self.board.color == self.color or \
                self.mode != NORMAL or self.pondermove:
            self.ignoreNext = True
            print >> self.engine, "stop"
    
    def resume (self):
        self.engine.resume()
        return
        
        if self.mode == NORMAL:
            if self.board and self.board.color == self.color:
                self._searchNow()
            elif self.getOption('Ponder') and self.pondermove:
                self._startPonder()
        else:
            self._searchNow()
    
    def hurry (self):
        print >> self.engine, "stop"
    
    def undoMoves (self, moves, gamemodel):
        # Not really necessary in UCI, but for the analyzer, it needs to keep up
        # with the latest trends
        
        if self.mode not in (ANALYZING, INVERSE_ANALYZING):
            if gamemodel.curplayer != self and moves % 2 == 1:
                # Interrupt if we were searching, but should no longer do so
                self.returnQueue.put("int")
        else:
            self.putMove(gamemodel.getBoardAtPly(gamemodel.ply), None, None)
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        if offer.offerType == DRAW_OFFER:
            self.emit("decline", offer)
        else:
            self.emit("accept", offer)
    
    #===========================================================================
    #    Option handling
    #===========================================================================
    
    def setOption (self, key, value):
        """ Set an option, which will be sent to the engine, after the
            'readyForOptions' signal has passed.
            If you want to know the possible options, you should go to
            engineDiscoverer or use the getOption, getOptions and hasOption
            methods, while you are in your 'readyForOptions' signal handler """ 
        if self.readyMoves:
            log.warn("Options set after 'readyok' are not sent to the engine", self.defname)
        self.optionsToBeSent[key] = value
    
    def getOption (self, option):
        assert self.readyOptions
        if option in self.options:
            return self.options[option]["default"]
        return None
    
    def getOptions (self):
        assert self.readyOptions
        return copy(self.options)
    
    def hasOption (self, key):
        assert self.readyOptions
        return key in self.options
    
    #===========================================================================
    #    Internal
    #===========================================================================
    
    def _newGame (self):
        print >> self.engine, "ucinewgame"
    
    def _searchNow (self):
        if self.mode == NORMAL:
            print >> self.engine, "position fen", self.board.asFen()
            
            if self.strength <= 3:
                print >> self.engine, "go depth %d" % self.strength
            else:
                print >> self.engine, "go wtime", self.wtime, "btime", self.btime, \
                                      "winc", self.incr, "binc", self.incr
        
        else:
            print >> self.engine, "stop"
            if self.mode == INVERSE_ANALYZING:
                if self.board.board.opIsChecked():
                    # Many engines don't like positions able to take down enemy
                    # king. Therefore we just return the "kill king" move
                    # automaticaly
                    self.emit("analyze", [getMoveKillingKing(self.board)], MATE_VALUE-1)
                    return
            print >> self.engine, "position fen", self.board.asFen()
            print >> self.engine, "go infinite"
    
    def _startPonder (self):
        print >> self.engine, "position fen", self.board.asFen(), \
                                "moves", self.pondermove
        print >> self.engine, "go ponder wtime", self.wtime, \
            "btime", self.btime, "winc", self.incr, "binc", self.incr
    
    #===========================================================================
    #    Parsing from engine
    #===========================================================================
    
    def parseLines (self, engine, lines):
        for line in lines:
            self.__parseLine(line)
    
    def __parseLine (self, line):
        if not self.connected:
            return
        
        parts = line.split()
        if not parts: return
        
        #---------------------------------------------------------- Initializing
        if parts[0] == "id":
            self.ids[parts[1]] = " ".join(parts[2:])
            return
        
        if parts[0] == "uciok":
            self.emit("readyForOptions")
            return
        
        if parts[0] == "readyok":
            self.emit("readyForMoves")
            return
        
        #------------------------------------------------------- Options parsing
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
        
        #---------------------------------------------------------------- A Move
        if self.mode == NORMAL and parts[0] == "bestmove":
            
            if self.ignoreNext:
                self.ignoreNext = False
                return
            
            move = parseAN(self.board, parts[1])
            
            if not validate(self.board, move):
                # This is critical. To avoid game stalls, we need to resign on
                # behalf of the engine.
                self.returnQueue.put('del')
                return
            
            self.board = self.board.move(move)
            
            if self.getOption('Ponder'):
                if len(parts) == 4 and self.board:
                    self.pondermove = parseAN(self.board, parts[3])
                    # Engines don't always check for everything in their ponders
                    if validate(self.board, self.pondermove):
                        self._startPonder()
                    else: self.pondermove = None
                else: self.pondermove = None
            
            self.returnQueue.put(move)
        
        #----------------------------------------------------------- An Analysis
        if self.mode != NORMAL and parts[0] == "info" and "pv" in parts:
            scoretype = parts[parts.index("score")+1]
            if scoretype in ('lowerbound', 'upperbound'):
                score = None
            else:
                score = int(parts[parts.index("score")+2])
                if scoretype == 'mate':
                    score = MATE_VALUE-abs(score)
                    score *= score/abs(score) # sign
            
            movstrs = parts[parts.index("pv")+1:]
            try:
                moves = listToMoves (self.board, movstrs, AN, validate=True, ignoreErrors=False)
            except ParsingError, e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("Ignored (%s) from analyzer: ParsingError%s\n" %
                          (' '.join(movstrs),e), self.defname)
                return
            
            self.emit("analyze", moves, score)
            return
    
        #* score
        #* cp <x>
        #    the score from the engine's point of view in centipawns.
        #* mate <y>
        #    mate in y moves, not plies.
        #    If the engine is getting mated use negative values for y.
        #* lowerbound
        #  the score is just a lower bound.
        #* upperbound
        #   the score is just an upper bound.
    
    #===========================================================================
    #    Info
    #===========================================================================
    
    def canAnalyze (self):
        # All UCIEngines can analyze
        return True
    
    def __repr__ (self):
        if self.name:
            return self.name
        if "name" in self.ids:
            return self.ids["name"]
        return ', '.join(self.defname)
