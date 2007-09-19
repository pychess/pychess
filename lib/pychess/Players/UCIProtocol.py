
from Protocol import Protocol
from pychess.System.SubProcess import SubProcessError, TimeOutError
from pychess.System.ThreadPool import pool
from pychess.Utils.Move import parseAN, listToMoves
from pychess.Utils.Board import Board
from pychess.Utils.const import *
from pychess.Utils.GameModel import GameModel
from pychess.Utils.logic import getMoveKillingKing

# Chess Engine Communication Protocol
class UCIProtocol (Protocol):
    
    def __init__ (self, executable, color, protover):
        Protocol.__init__(self, executable, color, protover)
        self.ids = {}
        self.options = {}
        self.wtime = 60000
        self.btime = 60000
        self.incr = 0
        
        self.pondermove = None
        self.ignoreNext = False
        self.started = False
        self.board = None
        
        pool.start(self.run)
    
    def run (self):
        print >> self.engine, "uci"
        
        while self.connected:
            try:
                line = self.engine.readline(5000)
            except TimeOutError:
                break
            except SubProcessError:
                break
            self.parseLine(line)
            if line.find("uciok") >= 0:
                break
        
        self.ready = True
        self.emit("ready")
    
    def startGame (self):
        if "OwnBook" in self.options:
            self._setOption("OwnBook", True)
        
        print >> self.engine, "isready"
        
        while self.connected:
            try:
                line = self.engine.readline()
            except SubProcessError:
                self.emit("dead")
                return
            if line:
                self.parseLine(line)
            if line.find("readyok") >= 0:
                break
        
        self.started = True
        print >> self.engine, "ucinewgame"
        
        def loop():
            while self.connected:
                try:
                    line = self.engine.readline()
                except SubProcessError:
                    self.emit("dead")
                    return
                self.parseLine(line)
        pool.start(loop)
    
    ######################## FROM ENGINE ########################
    
    def parseLine (self, line):
        
        parts = line.split()
        if not parts:
            return
        
        if parts[0] == "id":
            self.ids[parts[1]] = " ".join(parts[2:])
            return
        
        if parts[0] == "option":
            
            typedic = {"check":lambda x:x=="true", "spin":int}
            
            keys = ("type", "min", "max", "default", "var")
            
            dic = {}
            last = 1
            varlist = []
            for i in xrange (2, len(parts)+1):
                if i == len(parts) or parts[i] in keys:
                    key = parts[last]
                    value = " ".join(parts[last+1:i])
                    if "type" in dic and dic["type"] in typedic:
                        value = typedic[dic["type"]](value)
                        
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
        
        # A Move
        
        if parts[0] == "bestmove" and self.mode == NORMAL:
            
            if self.ignoreNext:
                self.ignoreNext = False
                return
            
            move = parseAN(self.board, parts[1])
            self.emit("move", move)
            
            self.board = self.board.move(move)
            if self._getOption('Ponder'):
                if len(parts) == 4 and self.board:
                    self.pondermove = parseAN(self.board, parts[3])
                    self._startPonder()
                else: self.pondermove = None
            
            return
        
        if "pv" in parts and self.mode != NORMAL:
            movstrs = parts[parts.index("pv")+1:]
            moves = listToMoves (self.board, movstrs, AN, validate=True)
            self.emit("analyze", moves)
    
    def _startPonder (self):
        print >> self.engine, "position fen", self.board.asFen(), \
                              "moves", self.pondermove
        print >> self.engine, "go ponder wtime", self.wtime, \
            "btime", self.btime, "winc", self.incr, "binc", self.incr
    
    ######################## TO ENGINE ########################
    
    def end (self, status, reason):
        if self.connected:
            # UCI seems not to care about reason
            self.kill(reason)
    
    def kill (self, reason):
        if self.connected:
            self.connected = False
            print >> self.engine, "stop"
            print >> self.engine, "quit"
            self.emit("analyze", [])
    
    def moveNow (self):
        print >> self.engine, "stop"
    
    def move (self, gamemodel):
        if not self.started:
            self.startGame()
        
        self.board = gamemodel.boards[-1]
        
        if self.mode != NORMAL:
            print >> self.engine, "stop"
            if self.mode == INVERSE_ANALYZING:
                self.board = self.board.switchColor()
                if self.board.board.opIsChecked():
                    # Many engines don't like positions able to take down enemy
                    # king. Therefore we just return the "kill king" move
                    # automaticaly
                    self.emit("analyze", [getMoveKillingKing(self.board)])
                    return
            print >> self.engine, "position fen", self.board.asFen()
            print >> self.engine, "go infinite"
            return
        
        if gamemodel.ply > gamemodel.lowply+1 and self._getOption('Ponder'):
            if self.pondermove and gamemodel.moves and \
                    gamemodel.moves[-1] == self.pondermove:
                print >> self.engine, "ponderhit"
                return
            else:
                self.ignoreNext = True
                print >> self.engine, "stop"
        
        self._searchNow()
        
    def _searchNow (self):
        print >> self.engine, "position fen", self.board.asFen()
        
        if self._getOption('UCI_LimitStrength') or self.strength == EXPERT:
            print >> self.engine, "go wtime", self.wtime, "btime", self.btime, \
                                     "winc", self.incr, "binc", self.incr
        
        elif self.strength == INTERMEDIATE:
            print >> self.engine, "go depth 4"
            
        elif self.strength == EASY:
            print >> self.engine, "go depth 1"
    
    def time (self, engine, opponent):
        if self.color == WHITE:
            self.wtime = int(engine*1000)
            self.btime = int(opponent*1000)
        else:
            self.btime = int(engine*1000)
            self.wtime = int(opponent*1000)
    
    def setTimeControls (self, secs, increment = 0, moves = 0):
        self.wtime = max(secs*1000, 1)
        self.btime = max(secs*1000, 1)
        self.incr = max(increment*1000, 1)
    
    def setStrength (self, strength):
        assert not self.started, "Can't set strength after game's started"
        
        if 'UCI_LimitStrength' in self.options and 'UCI_Elo' in self.options:
            if strength == EASY:
                self._setOption('UCI_LimitStrength', True)
                self._setOption('UCI_Elo', 1000)
            elif strength == INTERMEDIATE:
                self._setOption('UCI_LimitStrength', True)
                self._setOption('UCI_Elo', 1500)
        
        if 'Ponder' in self.options:
            self._setOption('Ponder', strength == EXPERT)
        
        self.strength = strength
    
    def _setOption (self, option, value):
        if option in self.options and self.options[option]["default"] != value:
            print "setting option",option,"from value",self.options[option]["default"],"to value",value
            print >> self.engine, "setoption name", option, "value", str(value).lower()
            self.options[option]["default"] = value
    
    def _getOption (self, option):
        if option in self.options:
            return self.options[option]["default"]
        return None
    
    def setBoard (self, gamemodel):
        # UCI always sets the position when searching for a new game, so we
        # don't actually have to do anything here. However when the new board
        # is from an entirely different game than the current, there is no need
        # that the engine still stores the old transposition table
        print >> self.engine, "ucinewgame"
    
    def analyze (self, inverse=False):
        if not inverse:
            self.mode = ANALYZING
        else: self.mode = INVERSE_ANALYZING
        self._setOption('Ponder', False)
        self.move(GameModel())
    
    def pause (self):
        if self.board and self.board.color == self.color or \
                self._getOption('Ponder'):
            self.ignoreNext = True
            print >> self.engine, "stop"
    
    def resume (self):
        if self.board and self.board.color == self.color:
            self._searchNow()
        elif self._getOption('Ponder') and self.pondermove:
            self._startPonder()
    
    def undoMoves (self, moves, gamemodel):
        pass
    
    def canAnalyze (self):
        return True
        
    def isAnalyzing (self):
    	return self.mode in (ANALYZING, INVERSE_ANALYZING)
    	
    def __repr__ (self):
        if "name" in self.ids:
            return self.ids["name"]
        return self.defname
