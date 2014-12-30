from __future__ import print_function

from pychess.compat import raw_input
from pychess.Players.PyChess import PyChess
from pychess.System import conf, fident
from pychess.Utils.book import getOpenings
from pychess.Utils.const import *
from pychess.Utils.lutils.Benchmark import benchmark
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.ldata import MAXPLY
from pychess.Utils.lutils import lsearch, leval
from pychess.Utils.lutils.lmove import parseSAN, parseAny, toSAN, ParsingError
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.validator import validateMove
import pychess
import re
import signal
import sys
from threading import Thread

class PyChessCECP(PyChess):
    
    def __init__ (self):
        PyChess.__init__(self)
        self.board = LBoard(NORMALCHESS)
        self.board.applyFen(FEN_START)
        
        self.forced = False
        self.analyzing = False
        self.thread = None

        self.basetime = 0
        
        self.features = {
            "ping": 1,
            "setboard": 1,
            "playother": 1,
            "san": 1,
            "usermove": 1,
            "time": 1,
            "draw": 1,
            "sigint": 0,
            "sigterm": 0,
            "reuse": 1,
            "analyze": 1,
            "myname": "PyChess %s" % pychess.VERSION,
            "variants": "normal,wildcastle,nocastle,fischerandom,crazyhouse,losers,suicide,atomic,king-of-the-hill",
            "colors": 0,
            "ics": 0,
            "name": 0,
            "pause": 0, # Unimplemented
            "nps": 0, # Unimplemented
            "debug": 1,
            "memory": 0, # Unimplemented
            "smp": 0, # Unimplemented
            "egt": "gaviota",
            "option": "skipPruneChance -slider 0 0 100"
        }
    
    def handle_sigterm(self, *args):
        self.__stopSearching()
        sys.exit(0)
    
    def makeReady(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, self.handle_sigterm)
    
    def run (self):
        while True:
            try:
                line = raw_input()
            except EOFError:
                line = "quit"
            lines = line.split()
            if 1:
            #try:
                if not lines:
                    continue
     
                ########## CECP commands ##########
                # See http://www.gnu.org/software/xboard/engine-intf.html#8
                
                elif lines[0] == "xboard":
                    pass
     
                elif lines[0] == "protover":
                    stringPairs = ["=".join([k, '"%s"' % v if type(v) is str else str(v)]) for k,v in self.features.items()]
                    print("feature %s" % " ".join(stringPairs))
                    print("feature done=1")
                
                elif lines[0] in ("accepted", "rejected"):
                    # We only really care about one case:
                    if tuple(lines) == ("rejected", "debug"):
                        self.debug = False
     
                elif lines[0] == "new":
                    self.__stopSearching()
                    self.board = LBoard(NORMALCHESS)
                    self.board.applyFen(FEN_START)
                    self.forced = False
                    self.playingAs = BLACK
                    self.clock[:] = self.basetime, self.basetime
                    self.searchtime = 0
                    self.sd = MAXPLY
                    if self.analyzing:
                        self.__analyze()
                
                elif lines[0] == "variant":
                    if len(lines) > 1:
                        if lines[1] == "fischerandom":
                            self.board.variant = FISCHERRANDOMCHESS
                        elif lines[1] == "crazyhouse":
                            self.board.variant = CRAZYHOUSECHESS
                            self.board.iniHouse()
                        elif lines[1] == "wildcastle":
                            self.board.variant = WILDCASTLESHUFFLECHESS
                        elif lines[1] == "losers":
                            self.board.variant = LOSERSCHESS
                        elif lines[1] == "suicide":
                            self.board.variant = SUICIDECHESS
                        elif lines[1] == "atomic":
                            self.board.variant = ATOMICCHESS
                            self.board.iniAtomic()
                        elif lines[1] == "king-of-the-hill":
                            self.board.variant = KINGOFTHEHILLCHESS
                
                elif lines[0] == "quit":
                    self.forced = True
                    self.__stopSearching()
                    sys.exit(0)
                    
                elif lines[0] == "random":
                    leval.random = True
     
                elif lines[0] == "force":
                    if not self.forced and not self.analyzing:
                        self.forced = True
                        self.__stopSearching()
                
                elif lines[0] == "go":
                    self.playingAs = self.board.color
                    self.forced = False
                    self.__go()
                
                elif lines[0] == "playother":
                    self.playingAs = 1-self.board.color
                    self.forced = False
                    # TODO: start pondering, if possible
                
                elif lines[0] in ("black", "white"):
                    newColor = lines[0] == "black" and BLACK or WHITE
                    self.__stopSearching()
                    self.playingAs = 1-newColor
                    if self.board.color != newColor:
                        self.board.setColor(newColor)
                        self.board.setEnpassant(None)
                    if self.analyzing:
                        self.__analyze()
                
                elif lines[0] == "level":
                    self.movestogo = int(lines[1])
                    inc = int(lines[3])
                    minutes = lines[2].split(":")
                    # Per protocol spec, strip off any non-numeric suffixes.
                    for i in range(len(minutes)):
                        minutes[i] = re.match(r'\d*', minutes[i]).group()
                    self.basetime = int(minutes[0])*60
                    if len(minutes) > 1 and minutes[1]:
                        self.basetime += int(minutes[1])
                    self.clock[:] = self.basetime, self.basetime
                    self.increment = inc, inc
                
                elif lines[0] == "st":
                    self.searchtime = float(lines[1])
     
                elif lines[0] == "sd":
                    self.sd = int(lines[1])
                
                # Unimplemented: nps
                
                elif lines[0] == "time":
                    self.clock[self.playingAs] = float(lines[1])/100.
                
                elif lines[0] == "otim":
                    self.clock[1-self.playingAs] = float(lines[1])/100.
                
                elif lines[0] == "usermove":
                    self.__stopSearching()
                    try:
                        move = parseAny (self.board, lines[1])
                    except ParsingError as e:
                        print("Error (unknown command):", lines[1])
                        print(self.board)
                        continue
                    if not validateMove(self.board, move):
                        print("Illegal move", lines[1])
                        print(self.board)
                        continue
                    self.board.applyMove(move)
                    self.playingAs = self.board.color
                    if not self.forced and not self.analyzing:
                        self.__go()
                    if self.analyzing:
                        self.__analyze()
                
                elif lines[0] == "?":
                    if not self.forced and not self.analyzing:
                        self.__stopSearching()
                
                elif lines[0] == "ping":
                    print("pong", lines[1])
                    
                elif lines[0] == "draw":
                    if self.__willingToDraw():
                        print("offer draw")
                
                elif lines[0] == "result":
                    # We don't really care what the result is at the moment.
                    pass
                    
                elif lines[0] == "setboard":
                    self.__stopSearching()
                    try:
                        self.board = LBoard(self.board.variant)
                        fen = " ".join(lines[1:])
                        self.board.applyFen(fen.replace("[", "/").replace("]", ""))
                    except SyntaxError as e:
                        print("tellusererror Illegal position:", str(e))
                
                # "edit" is unimplemented. See docs. Exiting edit mode returns to analyze mode.
     
                elif lines[0] == "hint":
                    pass # TODO: Respond "Hint: MOVE" if we have an expected reply
                
                elif lines[0] == "bk":
                    entries = getOpenings(self.board)
                    if entries:
                        totalWeight = sum(entry[1] for entry in entries)
                        for entry in entries:
                            print("\t%s\t%02.2f%%" % (toSAN(self.board, entry[0]), entry[1] * 100.0 / totalWeight))
                
                elif lines[0] == "undo":
                    self.__stopSearching()
                    self.board.popMove()
                    if self.analyzing:
                        self.__analyze()
     
                elif lines[0] == "remove":
                    self.__stopSearching()
                    self.board.popMove()
                    self.board.popMove()
                    if self.analyzing:
                        self.__analyze()
                
                elif lines[0] in ("hard", "easy"):
                    self.ponder = (lines[0] == "hard")
                
                elif lines[0] in ("post", "nopost"):
                    self.post = (lines[0] == "post")
                
                elif lines[0] == "analyze":
                    self.analyzing = True
                    self.__analyze()
     
                elif lines[0] in ("name", "rating", "ics", "computer"):
                    pass # We don't care.
     
                # Unimplemented: pause, resume
     
                elif lines[0] == "memory":
                    # FIXME: this is supposed to control the *total* memory use.
                    if lsearch.searching:
                        print("Error (already searching):", line)
                    else:
                        limit = int(lines[1])
                        if limit < 1:
                            print("Error (limit too low):", line)
                        else:
                            pass
                            # TODO implement
                            #lsearch.setHashSize(limit)
     
                elif lines[0] == "cores":
                    pass # We aren't SMP-capable.
     
                elif lines[0] == "egtpath":
                    if len(lines) >= 3 and lines[1] == "gaviota":
                        conf.set("egtb_path", conf.get("egtb_path", lines[2]))
                        from pychess.Utils.lutils.lsearch import enableEGTB
                        enableEGTB()
     
                elif lines[0] == "option" and len(lines) > 1:
                    name, eq, value = lines[1].partition("=")
                    if value: value = int(value) # CECP spec says option values are *always* numeric
                    if name == "skipPruneChance":
                        if 0 <= value <= 100:
                            self.skipPruneChance = value / 100.0
                        else:
                            print("Error (argument must be an integer 0..100):", line)
     
                ########## CECP analyze mode commands ##########
                # See http://www.gnu.org/software/xboard/engine-intf.html#11
     
                elif lines[0] == "exit":
                    if self.analyzing:
                        self.__stopSearching()
                        self.analyzing = False
     
                # Periodic updates (".") are not implemented.
     
                ########## Custom commands ##########
     
                elif lines[0] == "benchmark":
                    benchmark()
                
                elif lines[0] == "profile":
                    if len(lines) > 1:
                        import cProfile
                        cProfile.runctx("benchmark()", locals(), globals(), lines[1])
                    else:
                        print("Usage: profile outputfilename")
                
                elif len(lines) == 1:
                    # A GUI without usermove support might try to send a move.
                    try:
                        move = parseAny (self.board, line)
                    except:
                        print("Error (unknown command):", line)
                        continue
                    if not validateMove(self.board, move):
                        print("Illegal move", lines[0])
                        print(self.board)
                        continue
                    self.__stopSearching()
                    self.board.applyMove(move)
                    self.playingAs = self.board.color
                    if not self.forced and not self.analyzing:
                        self.__go()
                    if self.analyzing:
                        self.__analyze()

                else:
                    print("Error (unknown command):", line)
            #except SystemExit:
                #sys.exit(0)
            #except:
                #print "Error (missing or invalid argument)", line
    
    def __stopSearching(self):
        lsearch.searching = False
        if self.thread:
            self.thread.join()
    
    def __go (self):
        def ondone (result):
            if not self.forced:
                self.board.applyMove(parseSAN(self.board,result))
                print("move %s" % result)
            # TODO: start pondering, if enabled
        self.thread = Thread(target=PyChess._PyChess__go,
                             name=fident(PyChess._PyChess__go),
                             args=(self,ondone))
        self.thread.daemon = True
        self.thread.start()
    
    def __analyze (self):
        self.thread = Thread(target=PyChess._PyChess__analyze,
                             name=fident(PyChess._PyChess__analyze),
                             args=(self,))
        self.thread.daemon = True
        self.thread.start()

    def __willingToDraw (self):
        return self.scr <= 0 # FIXME: this misbehaves in all but the simplest use cases
