""" This module handles CECP/XBoard protocol engines
    It should be used together with the ProtocolEngine class, which extends
    Engine """

import time, thread

from Protocol import Protocol
from pychess.Utils.Move import Move, parseAny, toSAN, toAN, ParsingError, listToMoves
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.const import *
from pychess.Utils.logic import validate, getMoveKillingKing

def isdigits (strings):
    for s in strings:
        s = s.replace(".","")
        if s.startswith("-"):
            if not s[1:].isdigit():
                return False
        else:
            if not s.isdigit():
                return False
    return True

import re, gobject, select
d_plus_dot_expr = re.compile(r"\d+\.")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})[?!]*\s")
multiWs = re.compile(r"\s+")

# Chess Engine Communication Protocol
class CECPProtocol (Protocol):
    
    def __init__ (self, executable, color):
        Protocol.__init__(self, executable, color)
        
        self.features = {
            "ping":      0,
            "setboard":  0,
            "playother": 0,
            "san":       0,
            "usermove":  0,
            "time":      1,
            "draw":      1,
            "sigint":    0,
            "sigterm":   1,
            "reuse":     1,
            "analyze":   0,
            "myname":    self.defname,
            "colors":    1,
            "ics":       0,
            "name":      0,
            "pause":     0
        }
        
        self.board = Board(setup=True)
        self.forced = False
        self.gonext = False
        self.sd = True
        self.st = True
        
        thread.start_new(self.run,())
        
    def run (self):

        print >> self.engine, "xboard"
        print >> self.engine, "protover 2"
        self.nopost() # Mostly a service to the "Faile" engine
        
        # The XBoard/CECP doc says 2 seconds, but it is acually quite a long time.
        # Perhaps we could measure how long it normaly takes,
        # and then scale it down for later calls.
        # 
        # Engine could take an argument with lines to write just when it started.
        # Then engines.py and later an xml document could make "features done=1"
        # Be called on non protover 2 engines.
        self.timeout = 2
        self.start = time.time()
        
        while self.connected:
            line = self.engine.readline(self.start+self.timeout)
            if line == None:
                break # We've probably met the select timeout
            self.parseLine(line)
            if line.find("done=1") >= 0:
                break
            elif line.find("done=0") >= 0:
                print "WARNING: Giving 10 minutes for loading engine", repr(self)
                # This'll buy you 10 more minutes
                self.timeout = 60*10

        self.ready = True
        self.emit("ready")
            
        while self.connected:
            line = self.engine.readline()
            if line:
                self.parseLine(line)
                
    ############################################################################
    #   FROM ENGINE                                                            #
    ############################################################################
    
    def parseLine (self, line):
    
        parts = multiWs.split(line.strip())
        if self.features["sigint"]:
            self.engine.sigint()
        
        # Illegal Move
        if parts[0].lower().find("illegal") >= 0:
            if parts[-2] == "sd" and parts[-1].isdigit():
                self.sd = False
                self.setDepth (int(parts[-1]))
            return
        
        # A Move
        if self.board:
            if parts[0] == "move":
                movestr = parts[1]
            # Old Variation
            elif d_plus_dot_expr.match(parts[0]) and parts[1] == "...":
                movestr = parts[2]
            else:
                movestr = False
            
            if movestr:
                move = parseAny(self.board, movestr)
                self.board = None
                self.emit("move", move)
                return
        
        # Analyzing
        if len(parts) >= 5 and self.forced and isdigits(parts[1:4]):
            if parts[:4] == ["0","0","0","0"]:
                # Crafty doesn't analyze untill it is out of book
                print >> self.engine, "book off"
                return
            
            board = self.board
            mvstrs = movre.findall(" ".join(parts[4:])+" ")
            
            moves = listToMoves (self.board, mvstrs, type=None, validate=True)
            
            if moves:
                self.emit("analyze", moves)
            
            return
            
        # Offers draw
        if parts[0] == "offer" and parts[1] == "draw":
            self.emit("draw_offer")
            return
            
        # Resigns
        if line.find("resign") >= 0:
            self.emit("resign")
            return
            
        #Tell User Error
        if parts[0] in ("tellusererror", "Error"):
            #print "Tell User Error", repr(" ".join(parts[1:]))
            return
            
        # Tell Somebody
        if parts[0][:4] == "tell" and \
                parts[0][4:] in ("others", "all", "ics", "icsnoalias"):
            return
            #print "Tell", parts[0][4:], repr(" ".join(parts[1:]))
        
        # Features
        if "feature" in parts:
            # Little hack needed en cases of engines responding like this:
            # White (1) : feature setboard=1 analyze...e="GNU Chess 5.07" done=1
            parts = parts[parts.index("feature"):]
            for i, pair in enumerate(parts[1:]):
                if pair.find("=") < 0: continue
                key, value = pair.split("=")
                if value[0] in ('"',"'") and value[-1] in ('"',"'"):
                    value = value[1:-1]
                elif value[0] in ('"',"'") and not value[-1] in ('"',"'"):
                    rest = value[1:]+" "+" ".join(parts[2+i:])
                    i = rest.find('"')
                    if i < 0:
                        i = rest.find("'")
                    if i >= 0:
                        value = rest[:i]
                    else: value[1:]
                else: value = int(value)
                
                self.features[key] = value
            return
        
    ############################################################################
    #   TO ENGINE                                                              #
    ############################################################################
    
    def newGame (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "new"
        print >> self.engine, "random"
    
    def kill (self, status, reason):
        if self.connected:
            self.connected = False
            print >> self.engine, "quit"
            self.emit("analyze", [])
        else:
            pass
            # Suporting sigterm seams (ironicaly) to cause engine killing to hang
            #if self.features["sigterm"]:
            #    self.engine.sigterm()
        #thread.start_new(self.engine.wait4exit,())
    
    def setStrength (self, strength):
        assert self.ready, "Still waiting for done=1"
        
        if strength == 0:
            self.setPonder (False)
            self.setDepth (1)
        elif strength == 1:
            self.setPonder (False)
            self.setDepth (4)
        elif strength == 2:
            self.setPonder (True)
            self.setDepth (9)
    
    def moveNow (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "?"
    
    def move (self, gamemodel):
        assert self.ready, "Still waiting for done=1"
        
        self.board = gamemodel.boards[-1]
        
        if gamemodel.ply == 0 or self.gonext and \
        		not self.mode in (ANALYZING, INVERSE_ANALYZING):
            self.go()
            self.gonext = False
            return
        
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.setColor(1-self.board.color)
            self.printColor()
        
        if self.features["usermove"]:
            self.engine.write("usermove ")
        
        move = gamemodel.moves[-1]
        if self.features["san"]:
            print >> self.engine, toSAN(gamemodel.boards[-2], move)
        else: print >> self.engine, toAN(gamemodel.boards[-2], move)
        
        if self.mode == INVERSE_ANALYZING:
            if self.board.board.opIsChecked():
                # Many engines don't like positions able to take down enemy
                # king. Therefore we just return the "kill king" move
                # automaticaly
                self.emit("analyze", [getMoveKillingKing(self.board)])
                return
            self.printColor()
        
        if self.forced and not self.mode in (ANALYZING, INVERSE_ANALYZING):
            self.go()
        
    def pause (self):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["pause"]:
            print >> self.engine, "pause"
        else:
            self.force()
    
    def resume (self):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["pause"]:
            print >> self.engine, "resume"
        else:
            self.go()
    
    def force (self):
        print >> self.engine, "force"
        self.forced = True
    
    def go (self):
        print >> self.engine, "go"
        self.forced = False
    
    def post (self):
        print >> self.engine, "post"
    
    def nopost (self):
        print >> self.engine, "nopost"
    
    def resultWhite (self, comment="White Mates"):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "result 1-0 {%s}" % comment
    
    def resultBlack (self, comment="Black Mates"):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "result 0-1 {%s}" % comment
    
    def resultDraw (self, comment="Draw Game"):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "result 1/2-1/2 {%s}" % comment
    
    def time (self, engine, opponent):
        assert self.ready, "Still waiting for done=1"
        
        print >> self.engine, "time", int(engine)
        print >> self.engine, "otim", int(opponent)
    
    def offerDraw (self):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["draw"]:
            print >> self.engine, "draw"
    
    def setPonder (self, b):
        assert self.ready, "Still waiting for done=1"
        
        if b: print >> self.engine, "hard"
        else:
            print >> self.engine, "hard"
            print >> self.engine, "easy"
    
    def hint (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "hint"
    
    def printColor (self):
        #if self.features["colors"]:
        if self.board.color == WHITE:
            print >> self.engine, "white"
        else: print >> self.engine, "black"
        if self.forced: print >> self.engine, "force"
        #elif self.features["playother"]:
        #    print >> self.engine, "playother"
    
    def setBoard (self, gamemodel):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["setboard"]:
            self.force()
            print >> self.engine, "setboard", gamemodel.boards[-1].asFen()
        else:
            # Kludge to set black to move, avoiding the troublesome and now
            # deprecated "black" command. - Equal to the one xboard uses
            self.force()
            if gamemodel.boards[-1].color == BLACK:
                print >> self.engine, "a2a3"
            print >> self.engine, "edit"
            print >> self.engine, "#"
            for color in WHITE, BLACK:
                for y, row in enumerate(gamemodel.boards[-1].data):
                    for x, piece in enumerate(row):
                        if not piece or piece.color != color:
                            continue
                        sign = reprSign[piece.sign]
                        cord = repr(Cord(x,y))
                        print >> self.engine, sign+cord
                print >> self.engine, "c"
            print >> self.engine, "."
        
        self.board = gamemodel.boards[-1]
        
        if self.mode == ANALYZING:
            self.analyze()
            
        elif self.mode == INVERSE_ANALYZING:
        	self.analyze(inverse=True)
        	
        elif self.board.color == self.color:
            self.gonext = True
    
    def setDepth (self, depth):
        assert self.ready, "Still waiting for done=1"
        
        if self.sd:
            print >> self.engine, "sd", depth
        else:
            print >> self.engine, "depth %d" % depth
    
    def setTimeControls (self, secs, increment = 0, moves = 0):
        assert self.ready, "Still waiting for done=1"
        
        minutes = int(secs / 60)
        secs = int(secs % 60)
        
        s = str(minutes)
        if secs:
            s += ":" + str(secs)
        
        print >> self.engine, "level %d %s %d" % (moves, s, increment)
    
    def analyze (self, inverse=False):
        self.force()
        self.post()
        if inverse:
            self.board = self.board.setColor(1-self.color)
            self.printColor()
            self.mode = INVERSE_ANALYZING
        else:
            self.mode = ANALYZING
        
        print >> self.engine, "analyze"
    
    ############################################################################
    #   DIRECT METHODS                                                         #
    ############################################################################
    
    def canAnalyze (self):
        return self.features["analyze"]
    
    def isAnalyzing (self):
    	return self.mode in (ANALYZING, INVERSE_ANALYZING)
    
    def __repr__ (self):
        return self.features["myname"]
