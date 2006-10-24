import sys, os, time, thread
from threading import Condition

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from Engine import Engine, EngineDead, EngineConnection
from Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from System.Log import log

knownCECPEngines = ("gnuchess", "crafty")
def findKnownEngines ():
    for engine in knownCECPEngines:
        for path in os.environ["PATH"].split(":"):
            executable = os.path.join(path, engine)
            if os.path.isfile(executable):
                yield executable

class CECPEngine (Engine):

    __gsignals__ = {
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }

    def __init__ (self, args, color):
        GObject.__init__(self)
        self.proto = CECProtocol (args[0], color)
        self.readycond = self.proto.cond
        
        self.movecond = Condition()
        self.move = None
        self.proto.connect("move", self.onMove)
        def dead (engine):
            self.movecond.acquire()
            self.move = None
            self.movecond.notifyAll()
            self.movecond.release()
            self.emit("dead")
        self.proto.connect("dead", dead)
        
    def setStrength (self, strength):
        if strength == 0:
            self.proto.setPonder (False)
            self.proto.setDepth (1)
        elif strength == 1:
            self.proto.setPonder (False)
            self.proto.setDepth (4)
        elif strength == 2:
            self.proto.setPonder (True)
            self.proto.setDepth (9)
    
    def setTime (self, secs, gain):
        self.proto.setTimeControls(secs, gain)
    
    def setBoard (self, fen):
        self.proto.setBoard(fen)
    
    def makeMove (self, history):
        self.movecond.acquire()
        self.proto.move(history)
        while not self.move:
            self.movecond.wait()
        if not self.move:
            raise EngineDead
        move = self.move
        self.move = None
        return move
    
    def onMove (self, proto, move):
        self.movecond.acquire()
        self.move = move
        self.movecond.notifyAll()
        self.movecond.release()
        
    def wait (self):
        if self.proto.ready:
            return
        self.readycond.acquire()
        while not self.proto.ready and self.proto.connected:
            self.readycond.wait()
        self.readycond.release()
        if not self.proto.connected:
            return False
        return True
        
    def __repr__ (self):
        return self.proto.features["myname"]
    
    def __del__ (self):
        self.proto.__del__()
    
import re, gobject, select
d_plus_dot_expr = re.compile(r"\d+\.")

from Savers import epd
from cStringIO import StringIO

# Chess Engine Communication Protocol
class CECProtocol (GObject):
    
    __gsignals__ = {
        'move': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
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
        
        self.history = None
        self.forced = False
        self.gonext = False
        self.sd = True
        self.st = True
        
        self.cond = Condition()
        self.ready = False
        self.engine = EngineConnection (self.executable)
        self.connected = True
        
        log.debug(color+"\n", defname)
        
        self.engine.connect("readline", lambda e, l: self.parseLine(l))
        def callback (engine):
            if self.connected:
                self.cond.acquire()
                self.__del__()
                self.cond.notifyAll()
                self.cond.release()
                self.emit('dead')
                
        self.engine.connect("hungup", callback)
        
        thread.start_new(self.run,())
        
    def run (self):

        print >> self.engine, "xboard"
        print >> self.engine, "protover 2"
        print >> self.engine, "nopost" # Mostly a service to the "Faile" engine
        
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
        
        self.cond.acquire()
        self.ready = True
        self.cond.notifyAll()
        self.cond.release()
        
        #print self.features
            
        while self.connected:
            line = self.engine.readline()
            if line:
                self.parseLine(line)
            
    ########################
    
    def parseLine (self, line):
        parts = line.split()
        if self.features["sigint"]:
            self.engine.sigint()
    
        # Illegal Move
        if parts[0].lower().find("illegal") >= 0:
            if parts[-2] == "sd" and parts[-1].isdigit():
                self.sd = False
                self.setDepth (int(parts[-1]))
        
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
                if self.features["san"]:
                    move = parseSAN(self.history, movestr)
                else:
                    try:
                        move = parseAN(self.history, movestr)
                    except:
                        move = parseLAN(self.history, movestr)
                
                self.history = None
                self.emit("move", move)
        
        # A Hint
        if parts[0] == "Hint:":
            print "Hint", parts[1]
        
        # Offers draw
        if parts[0] == "offer" and parts[1] == "draw":
            print "Offer Draw"
        
        #Tell User Error
        if parts[0] in ("tellusererror", "Error"):
            print "Tell User Error", repr(" ".join(parts[1:]))
        
        # Tell Somebody
        if parts[0][:4] == "tell" and \
                parts[0][4:] in ("others", "all", "ics", "icsnoalias"):
            print "Tell", parts[0][4:], repr(" ".join(parts[1:]))
        
        # Resigns
        if line.find("resign") >= 0:
            print "Resigns"
        
        # Features
        try: j = parts.index("feature")
        except ValueError: j = -1
        if j >= 0:
            for i, pair in enumerate(parts[j+1:]):
                if pair.find("=") < 0: continue
                key, value = pair.split("=")
                if value.startswith("\"") and value.endswith("\""):
                    value = value[1:-1]
                elif value.startswith("\"") and not value.endswith("\""):
                    rest = value[1:]+" "+" ".join(parts[2+i+j:])
                    i = rest.find("\"")
                    if i >= 0:
                        value = rest[:i]
                    else: value[1:]
                else: value = int(value)
                
                self.features[key] = value
    
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
    
    def moveNow (self):
        assert self.ready, "Still waiting for done=1"
        print >> self.engine, "?"
    
    def move (self, history):
        assert self.ready, "Still waiting for done=1"
        
        self.history = history
        
        if not history.moves or self.gonext:
            print >> self.engine, "go"
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
            print >> self.engine, "force"
            self.forced = True
    
    def resume (self):
        assert self.ready, "Still waiting for done=1"
        
        if self.features["pause"]:
            print >> self.engine, "resume"
        else:
            print >> self.engine, "go"
    
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
        
        #if self.features["setboard"]:
        io = StringIO()
        epd.save(io, history)
        fen = io.getvalue()
        if history.curCol() == self.color:
            self.gonext = True
        print >> self.engine, "setboard", fen
        #FIXME: Convert fen to edit commands
    
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
    
    def getBook (self):
        pass #TODO: "bk" og self.bookRequested
    
    def getScore (self):
        pass #TODO
    
    def analyze (self):
        if self.features["analyze"]:
            print >> self.engine, "post\nanalyze"
            # Some engines don't support analyze (e.g. faile) and gives no response what so ever..
