import sys, os, time, thread
from threading import Condition, Lock

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from Engine import Engine, EngineDead, EngineConnection
from Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from Utils.History import History
from Utils.Cord import Cord
from System.Log import log

def isdigits (strings):
    for s in strings:
        if s.startswith("-"):
            if not s[1:].isdigit():
                return False
        else:
            if not s.isdigit():
                return False
    return True

class CECPEngine (Engine):

    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }

    def __init__ (self, args, color):
        GObject.__init__(self)
        self.proto = CECProtocol (args[0], color)
        
        self.readycon = Condition()
        self.readylist = []
        
        self.movecond = Condition()
        self.move = None
        self.analyzeMoves = []
        self.proto.connect("draw_offer", lambda w:self.emit("draw_offer"))
        self.proto.connect("resign", lambda w:self.emit("resign"))
        self.proto.connect("move", self.onMove)
        self.proto.connect("analyze", self.onAnalyze)
        def dead (engine):
            self.movecond.acquire()
            self.move = None
            self.movecond.notifyAll()
            self.movecond.release()
            self.emit("dead")
        self.proto.connect("dead", dead)
        
        self.proto.connect("ready", self.onReady)
        
    def setStrength (self, strength):
        def todo():
            if strength == 0:
                self.proto.setPonder (False)
                self.proto.setDepth (1)
            elif strength == 1:
                self.proto.setPonder (False)
                self.proto.setDepth (4)
            elif strength == 2:
                self.proto.setPonder (True)
                self.proto.setDepth (9)
        self.runWhenReady(todo)
    
    def runWhenReady (self, method, *args):
        self.readycon.acquire()
        if self.proto.ready:
            method(*args)
        else:
            self.readylist.append((method,args))
        self.readycon.release()
    
    def onReady (self, proto):
        self.readycon.acquire()
        if self.readylist:
            for method, args in self.readylist:
                method(*args)
        self.readycon.notifyAll()
        self.readycon.release()
    
    def setTime (self, secs, gain):
        self.runWhenReady(self.proto.setTimeControls, secs, gain)
    
    def setBoard (self, fen):
        self.runWhenReady(self.proto.setBoard, fen)
    
    def hurry (self):
        self.runWhenReady(self.proto.moveNow)
    
    def offerDraw (self):
        self.runWhenReady(self.proto.offerDraw)
    
    def makeMove (self, history):
        self.movecond.acquire()
        self.runWhenReady(self.proto.move, history)
        
        if self.proto.forced:
            del self.analyzeMoves[:]
            self.movecond.release()
            return
        
        while not self.move:
            self.movecond.wait()
        if not self.move:
            self.movecond.release()
            raise EngineDead
        move = self.move
        self.move = None
        self.movecond.release()
        return move
    
    def onMove (self, proto, move):
        self.movecond.acquire()
        self.move = move
        self.movecond.notifyAll()
        self.movecond.release()
        
    def _wait (self):
        if self.proto.ready:
            return
        self.readycon.acquire()
        while not self.proto.ready and self.proto.connected:
            self.readycon.wait()
        self.readycon.release()
        if not self.proto.connected:
            return False
        return True
    
    def onAnalyze (self, proto, moves):
        self.analyzeMoves = moves
        self.emit ("analyze", moves)
    
    def canAnalyze (self):
        return False
        self._wait()
        assert self.proto.ready
        return self.proto.features["analyze"]
    
    def analyze (self):
        self.runWhenReady(self.proto.analyze)
    
    def __repr__ (self):
        self._wait()
        return self.proto.features["myname"]
    
    def __del__ (self):
        self.proto.__del__()
    
import re, gobject, select
d_plus_dot_expr = re.compile(r"\d+\.")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})\s")
multiWs = re.compile(r"\s+")

from Savers import epd
from cStringIO import StringIO

# Chess Engine Communication Protocol
class CECProtocol (GObject):
    
    __gsignals__ = {
        'move': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'ready': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    def __init__ (self, executable, color):
        GObject.__init__(self)
        
        defname = os.path.split(executable)[1]
        defname = defname[:1].upper() + defname[1:].lower()
    
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
            "myname":    defname,
            "colors":    1,
            "ics":       0,
            "name":      0,
            "pause":     0
        }
        
        self.color = color
        self.executable = executable
        
        self.history = History()
        self.forced = False
        self.gonext = False
        self.sd = True
        self.st = True
        
        self.readycon = Condition()
        self.lock = Lock()
        self.ready = False
        self.engine = EngineConnection (self.executable)
        self.connected = True
        
        log.debug(color+"\n", defname)
        
        def callback (engine):
            if self.connected:
                self.__del__()
                if not self.ready:
                    self.ready = True
                    self.emit("ready")
                self.emit('dead')
        self.engine.connect("hungup", callback)
        
        thread.start_new(self.run,())
        
    def run (self):

        print >> self.engine, "xboard"
        print >> self.engine, "protover 2"
        self.nopost() # Mostly a service to the "Faile" engine
        
        self.timeout = 2
        self.start = time.time()
        
        while self.connected:
            now = time.time()
            if now >= self.start+self.timeout:
                break
            line = self.engine.readline(self.start+self.timeout-now)
            if not line:
                break # We've probably met the select timeout
            self.parseLine(line)
            if line.find("done=1") >= 0:
                break
            elif line.find("done=0") >= 0:
                # This'll buy you 10 more minutes
                self.timeout = 60*10

        self.ready = True
        self.emit("ready")
            
        while self.connected:
            line = self.engine.readline()
            if line:
                self.parseLine(line)
            
    ########################
    
    def parseMove (self, movestr, history=None):
        if not history: history=self.history
        if self.features["san"]:
            return parseSAN(history, movestr)
        else:
            try: return parseAN(history, movestr)
            except:
                try: return parseLAN(history, movestr)
                except: return parseSAN(history, movestr)
    
    def parseLine (self, line):
        #self.lock.acquire()
    
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
        if self.history:
            if parts[0] == "move":
                movestr = parts[1]
            # Old Variation
            elif d_plus_dot_expr.match(parts[0]) and parts[1] == "...":
                movestr = parts[2]
            else:
                movestr = False
            
            if movestr:
                move = self.parseMove(movestr)
                self.history = None
                self.emit("move", move)
                return
        
        # Analyzing
        if len(parts) >= 5 and self.forced and isdigits(parts[1:4]):
            if parts[:4] == ["0","0","0","0"]:
                # Crafty don't analyze untill it is out of book
                print >> self.engine, "book off"
                return
            his2 = self.history.clone()
            moves = []
            for m in movre.findall(" ".join(parts[4:])+" "):
                try:
                    moves.append(self.parseMove(m, his2))
                except Exception, e:
                    continue
                if moves:
                    his2.add(moves[-1], mvlist=False)
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
            print "Tell User Error", repr(" ".join(parts[1:]))
            return
            
        # Tell Somebody
        if parts[0][:4] == "tell" and \
                parts[0][4:] in ("others", "all", "ics", "icsnoalias"):
            return
            #print "Tell", parts[0][4:], repr(" ".join(parts[1:]))
        
        # Error
        if parts[0].lower() in ("illegal", "error"):
            self.__del__()
            self.emit('dead')
            return
            
        # Features
        if parts[0] == "feature":
            for i, pair in enumerate(parts[1:]):
                if pair.find("=") < 0: continue
                key, value = pair.split("=")
                if value.startswith("\"") and value.endswith("\""):
                    value = value[1:-1]
                elif value.startswith("\"") and not value.endswith("\""):
                    rest = value[1:]+" "+" ".join(parts[2+i:])
                    i = rest.find("\"")
                    if i >= 0:
                        value = rest[:i]
                    else: value[1:]
                else: value = int(value)
                
                self.features[key] = value
            return
        #self.lock.release()
        
    ########################
    
    def newGame (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "new"
        print >> self.engine, "random"
    
    def __del__ (self):
        if self.connected:
            self.connected = False
            print >> self.engine, "quit"
        else:
            if self.features["sigterm"]:
                self.engine.sigterm()
            else: self.engine.sigkill()
        self.engine.wait4exit()
    
    def moveNow (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "?"
    
    def move (self, history):
        assert self.ready, "Still waiting for done=1"
        
        self.history = history
        
        if not history.moves or self.gonext:
            self.go()
            self.gonext = False
            return
        
        if self.features["usermove"]:
            self.write("usermove ")
        
        move = history.moves[-1]
        if self.features["san"]:
            print >> self.engine, toSAN(history)
        else: print >> self.engine, toAN(history)
        
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
    
    def time (self, whitetime, blacktime):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["time"]:
            if self.color == "white":
                print >> self.engine, "time", whitetime
                print >> self.engine, "otim", blacktime
            else:
                print >> self.engine, "time", blacktime
                print >> self.engine, "otim", whitetime
    
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
    
    def setBoard (self, history):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["setboard"]:
            io = StringIO()
            epd.save(io, history)
            fen = io.getvalue()
            print >> self.engine, "force"
            print >> self.engine, "setboard", fen
        else:
            # Kludge to set black to move, avoiding the troublesome and now
            # deprecated "black" command. - Equal to the one xboard uses
            print >> self.engine, "force"
            if history.curCol() == "black":
                print >> self.engine, "a2a3"
            print >> self.engine, "edit"
            print >> self.engine, "#"
            for color in "white", "black":
                for y, row in enumerate(history[-1].data):
                    for x, piece in enumerate(row):
                        if not piece or piece.color != color:
                            continue
                        sign = piece.sign.upper()
                        cord = repr(Cord(x,y))
                        print >> self.engine, sign+cord
                print >> self.engine, "c"
            print >> self.engine, "."
        
        if history.curCol() == self.color and not self.forced:
            self.gonext = True
        
        self.history = history
    
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
    
    def analyze (self):
        if self.features["analyze"]:
            self.force()
            self.post()
            print >> self.engine, "analyze"
