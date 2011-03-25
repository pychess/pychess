from __future__ import with_statement
import collections
from copy import copy
import Queue
from threading import RLock

from pychess.Utils.Move import *
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.logic import validate, getMoveKillingKing, getStatus, legalMoveCount
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
        
        self.moveLock = RLock()
        # none of the following variables should be changed or used in a
        # condition statement without holding the above self.moveLock
        self.pondermove = None
        self.ignoreNext = False
        self.waitingForMove = False
        self.needBestmove = False
        self.readyForStop = False   # keeps track of whether we already sent a 'stop' command
        self.multipvSetting  = 1    # MultiPV option sent to the engine
        self.multipvExpected = 1    # Number of PVs expected (limited by number of legal moves)
        self.commands = collections.deque()
        
        self.gameBoard = Board(setup=True) # board at the end of all moves played
        self.board = Board(setup=True)     # board to send the engine
        self.uciPosition = "startpos"
        self.uciPositionListsMoves = False
        self.analysis = [ None ]
        
        self.returnQueue = Queue.Queue()
        self.engine.connect("line", self.parseLines)
        self.engine.connect("died", self.__die)
        
        self.connect("readyForOptions", self.__onReadyForOptions_before)
        self.connect_after("readyForOptions", self.__onReadyForOptions)
        self.connect_after("readyForMoves", self.__onReadyForMoves)
    
    def __die (self, subprocess):
        self.returnQueue.put("die")
    
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
        if r == 'die':
            raise PlayerIsDead
        assert r == "ready" or r == 'del'
        #self.emit("readyForOptions")
        #self.emit("readyForMoves")
    
    def __onReadyForOptions_before (self, self_):
        self.readyOptions = True
    
    def __onReadyForOptions (self, self_):
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            if self.hasOption("Ponder"):
                self.setOption('Ponder', False)
        
            self.requestMultiPV(self.multipvSetting)
        
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
            self._searchNow()
    
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
                self.emit("analyze", [])
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    def _moveToUCI (self, board, move):
        cn = CASTLE_KK
        if board.variant == FISCHERRANDOMCHESS:
            cn = CASTLE_KR
        return toAN(board, move, short=True, castleNotation=cn)
    
    def _recordMove (self, board1, move, board2):
        if self.gameBoard == board1:
            return
        if not board2:
            if board1.variant == NORMALCHESS and board1.asFen() == FEN_START:
                self.uciPosition = "startpos"
            else:
                self.uciPosition = "fen " + board1.asFen()
            self.uciPositionListsMoves = False;
        if move:
            if not self.uciPositionListsMoves:
                self.uciPosition += " moves"
                self.uciPositionListsMoves = True
            self.uciPosition += " " + self._moveToUCI(board2, move)
        self.board = self.gameBoard = board1
        if self.mode == INVERSE_ANALYZING:
            self.board = self.gameBoard.switchColor()
    
    def _recordMoveList (self, model):
        self._recordMove(model.boards[0], None, None)
        for board1, move, board2 in zip(model.boards[1:], model.moves, model.boards[:-1]):
            self._recordMove(board1, move, board2)

    def putMove (self, board1, move, board2):
        self._recordMove(board1, move, board2)
        
        if not self.readyMoves: return
        
        self._searchNow()
    
    def makeMove (self, board1, move, board2):
        assert self.readyMoves
        
        with self.moveLock:
            self._recordMove(board1, move, board2)
            self.waitingForMove = True
            ponderhit = False
            
            if board2 and self.pondermove and move == self.pondermove:
                ponderhit = True
            elif board2 and self.pondermove:
                self.ignoreNext = True
                print >> self.engine, "stop"
            
            self._searchNow(ponderhit=ponderhit)
        
        # Parse outputs
        try:
            r = self.returnQueue.get()
            if r == "del":
                raise PlayerIsDead
            if r == "int":
                with self.moveLock:
                    self.pondermove = None
                    self.ignoreNext = True
                    self.needBestmove = True
                    self.hurry()
                    raise TurnInterrupt
            return r
        finally:
            with self.moveLock:
                self.waitingForMove = False
                # empty the queue of any moves received post-undo/TurnInterrupt
                self.returnQueue.queue.clear()
    
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
        if self.mode == INVERSE_ANALYZING:
            self.board = self.gameBoard.switchColor()
    
    def setOptionInitialBoard (self, model):
        self._recordMoveList(model)
    
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
        
        if self.hasOption('UCI_LimitStrength') and strength <= 6:
            self.setOption('UCI_LimitStrength', True)
            if self.hasOption('UCI_Elo'):
                self.setOption('UCI_Elo', 300 * strength + 200)
        
        if not self.hasOption('UCI_Elo') or strength == 7:
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
        
        if self.board.color == self.color or \
                self.mode != NORMAL or self.pondermove:
            self.ignoreNext = True
            print >> self.engine, "stop"
    
    def resume (self):
        self.engine.resume()
        return
        
        if self.mode == NORMAL:
            if self.board.color == self.color:
                self._searchNow()
            elif self.getOption('Ponder') and self.pondermove:
                self._startPonder()
        else:
            self._searchNow()
    
    def hurry (self):
        log.debug("hurry: self.waitingForMove=%s self.readyForStop=%s\n" % \
            (self.waitingForMove, self.readyForStop), self.defname)
        # sending this more than once per move will crash most engines
        # so we need to send only the first one, and then ignore every "hurry" request
        # after that until there is another outstanding "position..go"
        with self.moveLock:
            if self.waitingForMove and self.readyForStop:
                print >> self.engine, "stop"
                self.readyForStop = False
    
    def playerUndoMoves (self, moves, gamemodel):
        self._recordMoveList(gamemodel)
        
        if (gamemodel.curplayer != self and moves % 2 == 1) or \
                (gamemodel.curplayer == self and moves % 2 == 0):
            # Interrupt if we were searching but should no longer do so, or
            # if it is was our move before undo and it is still our move after undo
            # since we need to send the engine the new FEN in makeMove()
            log.debug("playerUndoMoves: putting 'int' into self.returnQueue=%s\n" % \
                self.returnQueue.queue, self.defname)
            self.returnQueue.put("int")
    
    def spectatorUndoMoves (self, moves, gamemodel):
        self._recordMoveList(gamemodel)
        
        if self.readyMoves:
            self._searchNow()
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        if offer.type == DRAW_OFFER:
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
    
    def _searchNow (self, ponderhit=False):
        with self.moveLock:
            commands = []
            
            if ponderhit:
                commands.append("ponderhit")
                
            elif self.mode == NORMAL:
                commands.append("position %s" % self.uciPosition)
                if self.strength <= 3:
                    commands.append("go depth %d" % self.strength)
                else:
                    commands.append("go wtime %d winc %d btime %d binc %d" % \
                                    (self.wtime, self.incr, self.btime, self.incr))
                
            else:
                print >> self.engine, "stop"
                
                if self.mode == INVERSE_ANALYZING:
                    if self.board.board.opIsChecked():
                        # Many engines don't like positions able to take down enemy
                        # king. Therefore we just return the "kill king" move
                        # automaticaly
                        self.emit("analyze", [([getMoveKillingKing(self.board)], MATE_VALUE-1)])
                        return
                    commands.append("position fen %s" % self.board.asFen())
                else:
                    commands.append("position %s" % self.uciPosition)
                commands.append("go infinite")
            
            if self.multipvSetting > 1:
                self.multipvExpected = min(self.multipvSetting, legalMoveCount(self.board))
            else:
                self.multipvExpected = 1
            self.analysis = [None] * self.multipvExpected
            
            if self.needBestmove:
                self.commands.append(commands)
                log.debug("_searchNow: self.needBestmove==True, appended to self.commands=%s\n" % \
                    self.commands, self.defname)
            else:
                for command in commands:
                    print >> self.engine, command
                if getStatus(self.board)[1] != WON_MATE: # XXX This looks fishy.
                    self.needBestmove = True
                    self.readyForStop = True
    
    def _startPonder (self):
        uciPos = self.uciPosition
        if not self.uciPositionListsMoves:
            uciPos += " moves"
        print >> self.engine, "position", uciPos, \
                                self._moveToUCI(self.board, self.pondermove)
        print >> self.engine, "go ponder wtime", self.wtime, \
            "winc", self.incr, "btime", self.btime, "binc", self.incr
    
    #===========================================================================
    #    Parsing from engine
    #===========================================================================
    
    def parseLines (self, engine, lines):
        for line in lines:
            self.__parseLine(line)
    
    def __parseLine (self, line):
        if not self.connected: return
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
            with self.moveLock:
                self.needBestmove = False
                self.__sendQueuedGo()
                
                if self.ignoreNext:
                    log.debug("__parseLine: line='%s' self.ignoreNext==True, returning\n" % \
                        line.strip(), self.defname)
                    self.ignoreNext = False
                    self.readyForStop = True
                    return
                
                if not self.waitingForMove:
                    log.warn("__parseLine: self.waitingForMove==False, ignoring move=%s\n" % \
                        parts[1], self.defname)
                    self.pondermove = None
                    return
                self.waitingForMove = False
                
                move = parseAN(self.board, parts[1])
                
                if not validate(self.board, move):
                    # This is critical. To avoid game stalls, we need to resign on
                    # behalf of the engine.
                    log.error("__parseLine: move=%s didn't validate, putting 'del' in returnQueue. self.board=%s\n" % \
                        (repr(move), self.board), self.defname)
                    self.returnQueue.put('del')
                    return
                
                self._recordMove(self.board.move(move), move, self.board)
                
                if self.getOption('Ponder'):
                    self.pondermove = None
                    # An engine may send an empty ponder line, simply to clear.
                    if len(parts) == 4:
                        # Engines don't always check for everything in their
                        # ponders. Hence we need to validate.
                        # But in some cases, what they send may not even be
                        # correct AN - specially in the case of promotion.
                        try:
                            pondermove = parseAN(self.board, parts[3])
                        except ParsingError:
                            pass
                        else:
                            if validate(self.board, pondermove):
                                self.pondermove = pondermove
                                self._startPonder()
                
                self.returnQueue.put(move)
                log.debug("__parseLine: put move=%s into self.returnQueue=%s\n" % \
                    (move, self.returnQueue.queue), self.defname)
                return
        
        #----------------------------------------------------------- An Analysis
        if self.mode != NORMAL and parts[0] == "info" and "pv" in parts:
            multipv = 1
            if "multipv" in parts:
                multipv = int(parts[parts.index("multipv")+1])
            scoretype = parts[parts.index("score")+1]
            if scoretype in ('lowerbound', 'upperbound'):
                score = None
            else:
                score = int(parts[parts.index("score")+2])
                if scoretype == 'mate':
#                    print >> self.engine, "stop"
                    sign = score/abs(score)
                    score = sign * (MATE_VALUE-abs(score))
            
            movstrs = parts[parts.index("pv")+1:]
            try:
                moves = listToMoves (self.board, movstrs, AN, validate=True, ignoreErrors=False)
            except ParsingError, e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s\n" % \
                    (' '.join(movstrs),e), self.defname)
                return
            
            self.analysis[multipv - 1] = (moves, score)
            if multipv == self.multipvExpected:
                self.emit("analyze", self.analysis)
            return
        
        #-----------------------------------------------  An Analyzer bestmove
        if self.mode != NORMAL and parts[0] == "bestmove":
            with self.moveLock:
                log.debug("__parseLine: processing analyzer bestmove='%s'\n" % \
                    line.strip(), self.defname)
                self.needBestmove = False
                self.__sendQueuedGo(sendlast=True)
                return
        
        #  Stockfish complaining it received a 'stop' without a corresponding 'position..go'
        if line.strip() == "Unknown command: stop":
            with self.moveLock:
                log.debug("__parseLine: processing '%s'\n" % line.strip(), self.defname)
                self.ignoreNext = False
                self.needBestmove = False
                self.readyForStop = False
                self.__sendQueuedGo()
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
    
    def __sendQueuedGo (self, sendlast=False):
        """ Sends the next position...go or ponderhit command set which was queued (if any).
        
        sendlast -- If True, send the last position-go queued rather than the first,
        and discard the others (intended for analyzers)
        """
        with self.moveLock:
            if len(self.commands) > 0:
                if sendlast:
                    commands = self.commands.pop()
                    self.commands.clear()
                else:
                    commands = self.commands.popleft()
                
                for command in commands:
                    print >> self.engine, command
                self.needBestmove = True
                self.readyForStop = True
                log.debug("__sendQueuedGo: sent queued go=%s\n" % commands, self.defname)

    #===========================================================================
    #    Info
    #===========================================================================
    
    def maxAnalysisLines (self):
        try:
            return int(self.options["MultiPV"]["max"])
        except (KeyError, ValueError):
            return 1 # Engine does not support the MultiPV option
        
    def requestMultiPV (self, n):
        multipvMax = self.maxAnalysisLines()
        n = min(n, multipvMax)
        
        if n != self.multipvSetting:
            with self.moveLock:
                self.multipvSetting  = n
                print >> self.engine, "stop"
                print >> self.engine, "setoption name MultiPV value", n
                self._searchNow()
        
        return n
    
    def __repr__ (self):
        if self.name:
            return self.name
        if "name" in self.ids:
            return self.ids["name"]
        return ', '.join(self.defname)
