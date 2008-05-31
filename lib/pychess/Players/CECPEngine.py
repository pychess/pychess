
import re
from threading import RLock

from pychess.Players.Player import PlayerIsDead
from pychess.Players.ProtocolEngine import ProtocolEngine
from pychess.Utils.Move import *
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.logic import validate, getMoveKillingKing
from pychess.Utils.const import *
from pychess.System.Log import log
from pychess.System.SubProcess import TimeOutError, SubProcessError
from pychess.System.ThreadPool import pool
from pychess.Variants.fischerandom import FischerRandomChess


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

d_plus_dot_expr = re.compile(r"\d+\.")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})[?!]*\s")
whitespaces = re.compile(r"\s+")

class CECPEngine (ProtocolEngine):
    
    def __init__ (self, subprocess, color, protover):
        ProtocolEngine.__init__(self, subprocess, color, protover)
        
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
        
        self.board = None
        self.forced = False
        self.gonext = False
        self.sd = True
        self.st = True
        
        self.lastping = 0
        self.lastpong = 0
        self.timeout = None
        
        self.changeLock = RLock()
    
    ############################################################################
    #   From Engine                                                            #
    ############################################################################
    
    def start (self, block):
        print >> self.engine, "xboard"
        
        if self.protover == 2:
            print >> self.engine, "protover 2"
            
            if block:
                # XBoard will only give 2 secconds, but as we are quite sure that
                # the engines support the protocol, we can add more.
                # We can't add infinit time, both for the sake of bugs, but also
                # to make sure old versions of the engines, which perhaps doens't
                # support protover 2, don't hang us.
                self.timeout = 10*1000
                
                while not self.ready:
                    try:
                        line = self.engine.readline(self.timeout)
                    except TimeOutError:
                        self._beforeReady()
                        break
                    except SubProcessError:
                        self._beforeReady()
                        break
                    self.parseLine(line)
        else:
            self._beforeReady()
    
    def _beforeReady (self):
        # Some engines has the 'post' option enabled by default, and posts a lot
        # of debug information. Generelly this only help to increase the log
        # file size, and we don't really need it.
        print >> self.engine, "nopost" 
        # We don't want a timeout while playing
        self.timeout = None
        self.emit("ready")
    
    def _blockTillMove (self):
        self.movecon.acquire()
        self.movecon.wait()
        self.movecon.release()
    
    def autoAnalyze (self, inverse=False):
        self.start(block=True)
        self.analyze(inverse)
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
        self.changeLock.acquire()
        try:
            # Make the move
            self.board = gamemodel.boards[-1]
            
            if self.isAnalyzing():
                del self.analyzeMoves[:]
            
            if gamemodel.ply == 0 or self.gonext and \
                    not self.mode in (ANALYZING, INVERSE_ANALYZING):
                self.go()
                self.gonext = False
            else:
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
        finally:
            self.changeLock.release()
        
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
    
    def parseLine (self, line):
        self.changeLock.acquire()
        try:
            parts = whitespaces.split(line.strip())
            
            if parts[0] == "pong":
                self.lastpong = int(parts[1])
                return
            
            # Illegal Move
            if parts[0].lower().find("illegal") >= 0:
                if parts[-2] == "sd" and parts[-1].isdigit():
                    self.sd = False
                    self.setDepth (int(parts[-1]))
                return
            
            # A Move (Perhaps)
            if self.board:
                if parts[0] == "move":
                    movestr = parts[1]
                # Old Variation
                elif d_plus_dot_expr.match(parts[0]) and parts[1] == "...":
                    movestr = parts[2]
                else:
                    movestr = False
                
                if movestr:
                    try:
                        if self.forced:
                            # If engine was set in pause just before the engine sent its
                            # move, we ignore it. However the engine has to know that we
                            # ignored it, and therefor we step it one back
                            print >> self.engine, "undo"
                        else:
                            try:
                                move = parseAny(self.board, movestr)
                            except ParsingError, e:
                                raise PlayerIsDead, e
                            if validate(self.board, move):
                                self.board = None
                                return move
                            raise PlayerIsDead, "Board didn't validate after move"
                    finally:
                        self.movecon.acquire()
                        self.movecon.notifyAll()
                        self.movecon.release()
            
            # Analyzing
            if len(parts) >= 5 and self.forced and isdigits(parts[1:4]):
                if parts[:4] == ["0","0","0","0"]:
                    # Crafty doesn't analyze untill it is out of book
                    print >> self.engine, "book off"
                    return
                
                mvstrs = movre.findall(" ".join(parts[4:])+" ")
                
                moves = listToMoves (self.board, mvstrs, type=None, validate=True)
                
                # Don't emit if we weren't able to parse moves, or if we have a move
                # to kill the opponent king - as it confuses many engines
                if moves and not self.board.board.opIsChecked():
                    self.analyzeMoves = moves
                    self.emit("analyze", moves)
                
                return
            
            # Offers draw
            if parts[0:2] == ["offer", "draw"]:
                self.emit("accept", Offer(DRAW_OFFER))
                return
            
            # Resigns
            if "resign" in parts:
                self.emit("offer", Offer(RESIGNATION))
                return
            
            #if parts[0].lower() == "error":
            #    return
            
            #Tell User Error
            if parts[0] == "tellusererror":
                #print "Tell User Error", repr(" ".join(parts[1:]))
                return
            
            # Tell Somebody
            if parts[0][:4] == "tell" and \
                    parts[0][4:] in ("others", "all", "ics", "icsnoalias"):
                #print "Tell", parts[0][4:], repr(" ".join(parts[1:]))
                return
            
            if "feature" in parts:
                # We skip parts before 'feature', as some engines give us lines like
                # White (1) : feature setboard=1 analyze...e="GNU Chess 5.07" done=1
                parts = parts[parts.index("feature"):]
                for i, pair in enumerate(parts[1:]):
                    
                    # As "parts" is split with no thoughs on quotes or double quotes
                    # we need to do some extra handling.
                    
                    if pair.find("=") < 0: continue
                    key, value = pair.split("=",1)
                    
                    if value[0] in ('"',"'") and value[-1] in ('"',"'"):
                        value = value[1:-1]
                    
                    # If our pair was unfinished, like myname="GNU, we search the
                    # rest of the pairs for a quotating mark.
                    elif value[0] in ('"',"'"):
                        rest = value[1:] + " " + " ".join(parts[2+i:])
                        i = rest.find('"')
                        j = rest.find("'")
                        if i + j == -2:
                            log.warn("Missing endquotation in %s feature", repr(self))
                            value = rest
                        elif min(i, j) != -1:
                            value = rest[:min(i, j)]
                        else:
                            l = max(i, j)
                            value = rest[:l]
                    
                    else:
                        # All nonquoted values are ints
                        value = int(value)
                    
                    if key == "done":
                        if value:
                            self._beforeReady()
                        else:
                            log.warn("Adds 10 minutes timeout", repr(self))
                            # This'll buy you 10 more minutes
                            self.timeout = 60*10*1000
                        return
                    
                    self.features[key] = value
        finally:
            self.changeLock.release()
    
    ############################################################################
    #   To Engine                                                              #
    ############################################################################
    
        ########################################################################
        #   Commands                                                           #
        ########################################################################
    
    def hint (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "hint"
    
    def ping (self):
        if self.ready:
            self.lastping += 1
            print >> self.engine, "ping", self.lastping
        else:
            self.runWhenReady(self.ping)
    
    def force (self):
        print >> self.engine, "force"
        self.forced = True
    
    def go (self):
        print >> self.engine, "go"
        self.forced = False
    
    def post (self):
        print >> self.engine, "post"
    
    def analyze (self, inverse=False):
        if self.ready:
            self.force()
            self.post()
            if inverse:
                self.board = self.board.setColor(1-self.color)
                self.printColor()
                self.mode = INVERSE_ANALYZING
            else:
                self.mode = ANALYZING
            
            print >> self.engine, "analyze"
        else:
            self.runWhenReady(self.analyze, inverse)
    
    def printColor (self):
        #if self.features["colors"]:
        if self.board.color == WHITE:
            print >> self.engine, "white"
        else: print >> self.engine, "black"
        if self.forced: print >> self.engine, "force"
        #elif self.features["playother"]:
        #    print >> self.engine, "playother"
    
    def updateTime (self, secs, opsecs):
        if self.ready:
            print >> self.engine, "time", int(secs)
            print >> self.engine, "otim", int(opsecs)
        else:
            self.runWhenReady(self.updateTime, secs, opsecs)
    
    def _setBoard (self, board):
        if self.features["setboard"]:
            self.force()
            print >> self.engine, "setboard", board.asFen()
        else:
            # Kludge to set black to move, avoiding the troublesome and now
            # deprecated "black" command. - Equal to the one xboard uses
            self.force()
            if board.color == BLACK:
                print >> self.engine, "a2a3"
            print >> self.engine, "edit"
            print >> self.engine, "#"
            for color in WHITE, BLACK:
                for y, row in enumerate(board.data):
                    for x, piece in enumerate(row):
                        if not piece or piece.color != color:
                            continue
                        sign = reprSign[piece.sign]
                        cord = repr(Cord(x,y))
                        print >> self.engine, sign+cord
                print >> self.engine, "c"
            print >> self.engine, "."
    
    def setBoard (self, gamemodel):
        # Notice: If this method is to be called while playing, the engine will
        # need 'new' and an arrangement simmilar to that of 'pause' to avoid
        # the current thought move to appear
        
        self.changeLock.acquire()
        try:
            if self.ready:
                self.force()
                if gamemodel.boards[0].asFen() != FEN_START:
                    if "fischerandom" in self.features["variants"] and \
                            gamemodel.variant == FischerRandomChess:
                        print >> self.engine, "variant", "fischerandom"
                    self._setBoard(gamemodel.boards[0])
                
                for board, move in zip(gamemodel.boards[:-1], gamemodel.moves):
                    if self.features["usermove"]:
                        self.engine.write("usermove ")
                    
                    if self.features["san"]:
                        print >> self.engine, toSAN(board, move)
                    else: print >> self.engine, toAN(board, move)
                
                if self.mode in (ANALYZING, INVERSE_ANALYZING) or \
                        gamemodel.boards[-1].color == self.color:
                    self.board = gamemodel.boards[-1]
                    if self.mode == ANALYZING:
                        self.analyze()
                    elif self.mode == INVERSE_ANALYZING:
                        self.analyze(inverse=True)
                    else:
                        self.gonext = True
            else:
                self.runWhenReady(self.setBoard, gamemodel)
        finally:
            self.changeLock.release()
    
    
        ########################################################################
        #   Offer Stuff                                                        #
        ########################################################################
    
    def hurry (self):
        if self.ready:
            print >> self.engine, "?"
        else:
            self.runWhenReady(self.hurry)
    
    def pause (self):
        """ Pauses engine using the "pause" command if available. Otherwise put
            engine in force mode. By the specs the engine shouldn't ponder in
            force mode, but some of them do so anyways. """
        
        if self.ready:
            if self.mode in (ANALYZING, INVERSE_ANALYZING):
                return
            if self.features["pause"]:
                print >> self.engine, "pause"
            elif self.board:
                self.force()
                self._blockTillMove()
        else:
            self.runWhenReady(self.pause)
    
    def resume (self):
        if self.ready:
            if self.mode not in (ANALYZING, INVERSE_ANALYZING):
                if self.features["pause"]:
                    print "features resume"
                    print >> self.engine, "resume"
                elif self.board:
                    print "go resume"
                    self.go()
        else:
            self.runWhenReady(self.resume)
    
    def undoMoves (self, moves, gamemodel):
        if self.ready:
            if self.mode not in (ANALYZING, INVERSE_ANALYZING):
                if self.board:
                    print 1
                    self.movecon.acquire()
                    print 2
                    try:
                        self.hurry()
                        self.force()
                        self.movecon.wait()
                    finally:
                        self.movecon.release()
                else:
                    self.force()
            
            self.changeLock.acquire()
            try:
                
                for i in xrange(moves):
                    print >> self.engine, "undo"
                
                if self.mode not in (ANALYZING, INVERSE_ANALYZING):
                    if gamemodel.curplayer.color == self.color:
                        self.board = gamemodel.boards[-1]
                        self.go()
                    else:
                        self.board = None
                else:
                    self.board = gamemodel.boards[-1]
            finally:
                self.changeLock.release()
        else:
            self.runWhenReady(self.undoMoves, moves, gamemodel)
    
    def offer (self, offer):
        if offer.offerType == DRAW_OFFER:
            if self.features["draw"]:
                print >> self.engine, "draw"
        else:
            self.emit("accept", offer)
    
    def offerError (self, offer, error):
        if self.features["draw"]:
            # We don't keep track if engine draws are offers or accepts. We just
            # Always assume they are accepts, and if they are not, we get this
            # error and emit offer instead
            if offer.offerType == DRAW_OFFER and \
                    error == ACTION_ERROR_NONE_TO_ACCEPT:
                self.emit("offer", Offer(DRAW_OFFER))
    
        ########################################################################
        #   Start / Stop                                                       #
        ########################################################################
    
    def newGame (self):
        if self.ready:
            print >> self.engine, "new"
            print >> self.engine, "random"
        else:
            self.runWhenReady(self.newGame)
    
    def setStrength (self, strength):
        if self.ready:
            if strength == 0:
                self.setPonder (False)
                self.setDepth (1)
            elif strength == 1:
                self.setPonder (False)
                self.setDepth (4)
            elif strength == 2:
                self.setPonder (True)
                self.setDepth (9)
        else:
            self.runWhenReady(self.setStrength, strength)
    
    def setDepth (self, depth):
        if self.ready:
            if self.sd:
                print >> self.engine, "sd", depth
            else:
                print >> self.engine, "depth %d" % depth
        else:
            self.runWhenReady(self.setDepth, ponder)
    
    def setPonder (self, ponder):
        if self.ready:
            if ponder:
                print >> self.engine, "hard"
            else:
                print >> self.engine, "hard"
                print >> self.engine, "easy"
        else:
            self.runWhenReady(self.setPonder, ponder)
    
    def setTime (self, secs, gain):
        if self.ready:
            minutes = int(secs / 60)
            secs = int(secs % 60)
            s = str(minutes)
            if secs:
                s += ":" + str(secs)
            print >> self.engine, "level 0 %s %d" % (s, gain)
        else:
            self.runWhenReady(self.setTime, secs, gain)
    
    def end (self, status, reason):
        if self.connected:
            # We currently can't fillout the comment "field" as the repr strings
            # for reasons and statuses lies in Main.py
            # Creating Status and Reason class would solve this
            if status == DRAW:
                print >> self.engine, "result 1/2-1/2 {?}"
            elif status == WHITEWON:
                print >> self.engine, "result 1-0 {?}"
            elif status == BLACKWON:
                print >> self.engine, "result 0-1 {?}"
            else:
                print >> self.engine, "result * {?}"
            
            # Make sure the engine exits and do some cleaning
            self.kill(reason)
    
    def kill (self, reason):
        """ Kills the engine, starting with the 'quit' command, then sigterm and
            eventually sigkill.
            Returns the exitcode, or if engine have already been killed, returns
            None """
        if self.connected:
            self.connected = False
            try:
                try:
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
    
    def setName (self, name):
        self.name = name
    
    def canAnalyze (self):
        assert self.ready, "Still waiting for done=1"
        return self.features["analyze"]
    
    def isAnalyzing (self):
        return self.mode in (ANALYZING, INVERSE_ANALYZING)
    
    def __repr__ (self):
        if self.name:
            return self.name
        return self.features["myname"]
