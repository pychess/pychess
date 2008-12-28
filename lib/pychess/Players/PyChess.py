#!/usr/bin/python

from time import time
import sys, os
import random
import subprocess
import email.Utils
import gettext

from pychess.System.prefix import addDataPrefix
gettext.install("pychess", localedir=addDataPrefix("lang"), unicode=1)

from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.lmove import toSAN, parseAny, parseSAN, FLAG, listToSan
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils import leval
from pychess.Utils.lutils.validator import validateMove

from pychess.System.GtkWorker import GtkWorker

from pychess.ic.FICSConnection import FICSConnection

from Engine import Engine

class PyChess:
    
    def __init__ (self):
        self.sd = 10
        self.skipPruneChance = 0
        self.useegtb = False
        
        self.increment = None
        self.mytime = None
        #self.optime = None
        
        self.scr = 0 # The current predicted score. Used when accepting draw offers
        self.playingAs = WHITE
    
    def makeReady(self):
        try:
            import psyco
            psyco.bind(alphaBeta)
        except ImportError:
            pass
    
    #===========================================================================
    # Play related
    #===========================================================================
    
    def __remainingMovesA (self):
        # Based on regression of a 180k games pgn
        x = len(self.board.history)
        return -1.71086e-12*x**6 \
               +1.69103e-9*x**5 \
               -6.00801e-7*x**4 \
               +8.17741e-5*x**3 \
               +2.91858e-4*x**2 \
               -0.94497*x \
               +78.8979
    
    def __remainingMovesB (self):
        # We bet a game will be around 80 moves
        x = len(self.board.history)
        return max(80-x,4)
    
    def __getBestOpening (self):
        score = 0
        move = None
        for m, w, d, l in getOpenings(self.board):
            s = (w+d/3.0)*random.random()
            if not move or s > score:
                move = m
                score = s
        return move
    
    def __go (self, worker):
        """ Finds and prints the best move from the current position """
        
        # TODO: Length info should be put in the book.
        # Btw. 10 is not enough. Try 20
        if len(self.board.history) < 14:
            movestr = self.__getBestOpening()
            if movestr:
                mvs = [parseSAN(self.board, movestr)]
        
        if len(self.board.history) >= 14 or not movestr:
            
            lsearch.skipPruneChance = self.skipPruneChance
            lsearch.useegtb = self.useegtb
            lsearch.searching = True
            
            if self.mytime == None:
                lsearch.endtime = sys.maxint
                worker.publish("Searching to depth %d without timelimit" % self.sd)
                mvs, self.scr = alphaBeta (self.board, self.sd)
            
            else:
                usetime = self.mytime / self.__remainingMovesA()
                if self.mytime < 6*60+self.increment*40:
                    # If game is blitz, we assume 40 moves rather than 80
                    usetime *= 2
                # The increment is a constant. We'll use this allways
                usetime += self.increment
                if usetime < 0.5:
                    # We don't wan't to search for e.g. 0 secs
                    usetime = 0.5
                
                starttime = time()
                lsearch.endtime = starttime + usetime
                prevtime = 0
                worker.publish("Time left: %3.2f seconds; Planing to thinking for %3.2f seconds" % (self.mytime, usetime))
                for depth in range(1, self.sd+1):
                    # Heuristic time saving
                    # Don't waste time, if the estimated isn't enough to complete next depth
                    if usetime > prevtime*4 or usetime <= 1:
                        lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
                        search_result = alphaBeta(self.board, depth)
                        if lsearch.searching:
                            mvs, self.scr = search_result
                            if time() > lsearch.endtime:
                                # Endtime occured after depth
                                worker.publish("Endtime occured after depth")
                                break
                            worker.publish("got moves %s from depth %d" % (" ".join(listToSan(self.board, mvs)), depth))
                        else:
                            # We were interrupted
                            worker.publish("I was interrupted (%d) while searching depth %d" % (lsearch.last, depth))
                            if depth == 1:
                                worker.publish("I've got to have some move, so I use what we got")
                                mvs, self.scr = search_result
                            break
                        prevtime = time()-starttime - prevtime
                    else:
                        worker.publish("I don't have enough time to go into depth %d" % depth)
                        # Not enough time for depth
                        break
                else:
                    worker.publish("I searched through depths [1, %d]" % (self.sd+1))
                
                self.mytime -= time() - starttime
                self.mytime += self.increment
            
            if not mvs:
                if not lsearch.searching:
                    # We were interupted
                    lsearch.movesearches = 0
                    lsearch.nodes = 0
                    searchLock.release()
                    return
                
                # This should only happen in terminal mode
                
                #if lsearch.last == 4:
                #    print "resign"
                #else:
                if self.scr == 0:
                    worker.publish("result %s" % reprResult[DRAW])
                elif self.scr < 0:
                    if self.board.color == WHITE:
                        worker.publish("result %s" % reprResult[BLACKWON])
                    else: worker.publish("result %s" % reprResult[WHITEWON])
                else:
                    if self.board.color == WHITE:
                        worker.publish("result %s" % reprResult[WHITEWON])
                    else: worker.publish("result %s" % reprResult[BLACKWON])
                worker.publish("last: %d %d" % (lsearch.last, self.scr))
                return
            
            worker.publish("moves were: %s %d" % (" ".join(listToSan(self.board, mvs)), self.scr))
            
            lsearch.movesearches = 0
            lsearch.nodes = 0
            lsearch.searching = False
        
        move = mvs[0]
        sanmove = toSAN(self.board, move) 
        self.board.applyMove(move)
        return sanmove
    
    def __analyze (self, worker):
        """ Searches, and prints info from, the position as stated in the cecp
            protocol """
        
        start = time()
        lsearch.endtime = sys.maxint
        lsearch.searching = True
        
        for depth in xrange (1, 10):
            if not lsearch.searching:
                break
            t = time()
            
            mvs, scr = alphaBeta (self.board, depth)
            
            # Analyze strings are given in the following format:
            # depth in plies, evaluation, time used, nodes searched, p/v
            
            movstrs = " ".join(listToSan(self.board, mvs))
            worker.publish("\t".join(("%d","%d","%0.2f","%d","%s")) %
                           (depth, scr, time()-start, lsearch.nodes, movstrs))
            
            if lsearch.movesearches:
                mvs_pos = lsearch.nodes/float(lsearch.movesearches)
                mvs_tim = lsearch.nodes/(time()-t)
                worker.publish("%0.1f moves/position; %0.1f n/s" % (mvs_pos, mvs_tim))
            
            lsearch.nodes = 0
            lsearch.movesearches = 0
    
    def __analyze2 ():
        import profile
        profile.runctx("self.__analyze2()", locals(), globals(), "/tmp/pychessprofile")
        from pstats import Stats
        s = Stats("/tmp/pychessprofile")
        s.sort_stats('cumulative')
        s.print_stats()

class PyChessCECP(PyChess):
    
    def __init__ (self):
        PyChess.__init__(self)
        self.board = LBoard(NORMALCHESS)
        self.board.applyFen(FEN_START)
        
        self.forced = False
        self.analyzing = False
        self.worker = None
        
        self.features = {
            "setboard": 1,
            "analyze": 1,
            "usermove": 1,
            "reuse": 0,
            "draw": 1,
            "sigterm": 1,
            "variants": "normal,nocastle,fischerandom",
            "myname": "PyChess %s" % VERSION
        }
    
    def makeReady(self):
        print "feature done=0"
        PyChess.makeReady(self)
    
    def run (self):
        while True:
            line = raw_input()
            if not line.strip(): continue
            lines = line.split()
            
            if lines[0] == "protover":
                stringPairs = ["=".join([k,repr(v)]) for k,v in self.features.iteritems()]
                print "feature %s done=1" % " ".join(stringPairs)
            
            elif lines[0] == "usermove":
                
                self.__stopSearching()
                
                move = parseAny (self.board, lines[1])
                
                if not validateMove(self.board, move):
                    print "Illegal move", lines[1]
                    continue
                
                self.board.applyMove(move)
                
                self.playingAs = self.board.color
                
                if not self.forced and not self.analyzing:
                    self.__go()
                
                if self.analyzing:
                    self.__analyze()
            
            elif lines[0] == "sd":
                self.sd = int(lines[1])
                self.skipPruneChance = max(0, (5-self.sd)*0.02)
                if self.sd >= 5:
                    print "If the game has no timesettings, you probably don't want\n"+\
                          "to set a search depth much greater than 4"
            
            elif lines[0] == "egtb":
                # This is a crafty command interpreted a bit loose
                self.useegtb = True
            
            elif lines[0] == "level":
                moves = int(lines[1])
                self.increment = int(lines[3])
                minutes = lines[2].split(":")
                self.mytime = int(minutes[0])*60
                if len(minutes) > 1:
                    self.mytime += int(minutes[1])
                print "Playing %d moves in %d seconds + %d increment" % \
                        (moves, self.mytime, self.increment)
            
            elif lines[0] == "time":
                self.mytime = int(lines[1])/100.
            
            #elif lines[0] == "otim":
            #   self.optime = int(lines[1])
            
            elif lines[0] == "quit":
                sys.exit()
            
            elif lines[0] == "result":
                # We don't really care what the result is at the moment.
                sys.exit()
            
            elif lines[0] == "force":
                if not self.forced and not self.analyzing:
                    self.forced = True
                    self.__stopSearching()
            
            elif lines[0] == "go":
                self.playingAs = self.board.color
                self.forced = False
                self.__go()
            
            elif lines[0] == "undo":
                self.__stopSearching()
                self.board.popMove()
                if self.analyzing:
                    self.__analyze()
            
            elif lines[0] == "?":
                self.__stopSearching()
            
            elif lines[0] in ("black", "white"):
                newColor = lines[0] == "black" and BLACK or WHITE
                if self.playingAs != newColor:
                    self.__stopSearching()
                    self.playingAs = newColor
                    # It is dangerous to use the same table, when we change color
                    #lsearch.table.clear()
                    self.board.setColor(newColor)
                    # Concider the case:
                    # * White moves a pawn and creates a enpassant cord
                    # * Spy analyzer is not set back to white to analyze the
                    #   position. An attackable enpassant cord now no longer makes
                    #   sense.
                    # * Notice though, that when the color is shifted back to black
                    #   to make the actual move - and it is an enpassant move - the
                    #   cord won't be set in the lboard.
                    self.board.setEnpassant(None)
                    if self.analyzing:
                        self.__analyze()
            
            elif lines[0] == "analyze":
                self.playingAs = self.board.color
                self.analyzing = True
                self.__analyze()
                
            elif lines[0] == "draw":
                if self.scr <= 0:
                    print "offer draw"
                
            elif lines[0] == "random":
                leval.random = True
            
            elif lines[0] == "variant":
                if lines[1] == "fischerandom":
                    self.board.variant = FISCHERRANDOMCHESS
                
            elif lines[0] == "setboard":
                self.__stopSearching()
                self.board.applyFen(" ".join(lines[1:]))
                if self.analyzing:
                    self.__analyze()
            
            elif lines[0] in ("xboard", "otim", "hard", "easy", "nopost", "post"):
                pass
            
            else: print "Warning (unknown command):", line
    
    def __stopSearching(self):
        lsearch.searching = False
        if self.worker:
            self.worker.cancel()
            self.worker.get()
            self.worker = None
    
    def __go (self):
        self.worker = GtkWorker(lambda worker: PyChess._PyChess__go(self, worker))
        def process (worker, messages): print "\n".join(messages)
        self.worker.connect("published", process)
        def ondone (worker, result): print "move %s" % result
        self.worker.connect("done", ondone)
        self.worker.execute()
    
    def __analyze (self):
        self.worker = GtkWorker(lambda worker: PyChess._PyChess__analyze(self, worker))
        def process (worker, messages): print "\n".join(messages)
        self.worker.connect("published", process)
        self.worker.execute()

class PyChessFICS(PyChess):
    def __init__ (self, password, from_address, to_address):
        PyChess.__init__(self)
        
        self.ports = (23, 5000)
        self.username = "PyChess"
        self.owner = "Lobais"
        self.password = password
        self.from_address = "The PyChess Bot <%s>" % from_address
        self.to_address = "Thomas Dybdahl Ahle <%s>" % to_address
        
        self.sudos = set()
        self.waitingForPassword = None
        self.log = []
    
    def makeReady(self):
        PyChess.makeReady(self)
        
        self.connection = FICSConnection("freechess.org",self.ports,
                                         self.username, self.password)
        self.connection.connect("connectingMsg", self.__showConnectLog)
        self.connection._connect()
        
        self.connection.glm.connect("addPlayer", self.__onAddPlayer)
        self.connection.cm.connect("privateMessage", self.__onTell)
        self.connection.alm.connect("logOut", self.__onLogOut)
        self.connection.bm.connect("playBoardCreated", self.__onPlayBoardCreated)
        self.connection.bm.connect("clockUpdatedMs", self.__onClockUpdatedMs)
        self.connection.bm.connect("boardRecieved", self.__onBoardRecieved)
        self.connection.bm.connect("moveRecieved", self.__onMoveRecieved)
        self.connection.om.connect("onChallengeAdd", self.__onChallengeAdd)
    
    def run(self):
        self.connection.run()
        self.phoneHome("Session ended")
        print "Session ended"
    
    #===========================================================================
    # General
    #===========================================================================
    
    def __showConnectLog (self, connection, message):
        print message
    
    def __onLogOut (self, autoLogoutManager):
        self.connection.disconnect()
    
    def __onAddPlayer (self, gameListManager, player):
        if player["name"] in self.sudos:
            self.sudos.remove(player["name"])
        if player["name"] == self.owner:
            self.connection.cm.tellPlayer(self.owner, "Greetings")
    
    def __usage (self):
        return "|| PyChess bot help file || " +\
               "# help 'Displays this help file' " +\
               "# sudo <password> <command> 'Lets PyChess execute the given command' "+\
               "# sendlog 'Makes PyChess send you its current log'"
    
    def __onTell (self, chatManager, name, title, isadmin, text):
        
        if self.waitingForPassword:
            if text.strip() == self.password:
                self.sudos.add(name)
                print >> self.connection.client, self.waitingForPassword
            else:
                chatManager.tellPlayer(name, "Wrong password")
            self.waitingForPassword = None
            return
        
        args = text.split()
        
        if args == ["help"]:
            chatManager.tellPlayer(name, self.__usage())
        
        elif args[0] == "sudo":
            command = " ".join(args[1:])
            if name in self.sudos or name == self.owner:
                # Notice: This can be used to make nasty loops
                print >> self.connection.client, command
            else:
                print repr(name), self.sudos
                chatManager.tellPlayer(name, "Please send me the password")
                self.waitingForPassword = command
        
        elif args == ["sendlog"]:
            log2 = self.log[:]
            del self.log[:]
            # TODO: Consider email
            chatManager.tellPlayer(name, "\\n".join(log2))
        
        else:
            chatManager.tellPlayer(name, "Sorry, your request was nonsense.\n"+\
                                       "Please read my help file for more info")
    
    #===========================================================================
    # Challenges and other offers
    #===========================================================================
    
    def __onChallengeAdd (self, offerManager, index, match):
        #match = {"tp": type, "w": fname, "rt": rating, "r": rated, "t": mins, "i": incr}
        offerManager.acceptIndex(index)
    
    #===========================================================================
    # Playing
    #===========================================================================
    
    def __onClockUpdatedMs (self, boardManager, gameno, msecs, color):
        if self.gameno == gameno and self.playingAs == color:
            self.mytime = msecs/1000.
    
    def __onPlayBoardCreated (self, boardManager, board):
        self.mytime = int(board["mins"])*60
        self.increment = int(board["incr"])
        self.gameno = board["gameno"]
        self.lastPly = -1
        
        self.board = LBoard(NORMALCHESS)
        self.board.applyFen(FEN_START)
        # TODO: Support board.variant = FISCHERRANDOMCHESS
        
        if board["bname"].lower() == self.connection.getUsername().lower():
            self.playingAs = BLACK
        else:
            self.playingAs = WHITE
            self.__go()
    
    def __go (self):
        worker = GtkWorker(lambda worker: PyChess._PyChess__go(self, worker))
        worker.connect("published", lambda w, msg: self.log.extend(messages))
        worker.connect("done", lambda w, res: self.connection.bm.sendMove(res))
        worker.execute()
    
    def __onMoveRecieved (self, boardManager, moveply, sanmove, gameno, movecol):
        if self.gameno == gameno:
            # We want the current ply rather than the moveply, so we add one
            curply = int(moveply) +1
            # In some cases (like lost on time) the last move is resent
            if curply <= self.lastPly:
                return
            self.lastPly = curply
            if self.playingAs != movecol:
                move = parseSAN (self.board, sanmove)
                self.board.applyMove(move)
                self.__go()
    
    def __onBoardRecieved (self, boardManager, gameno, ply, fen, wsecs, bsecs):
        # Take back
        self.board.applyFen(fen)
        if self.gameno == gameno:
            if self.playingAs == WHITE:
                self.mytime = wsecs
            else: self.mytime = bsecs
    
    #===========================================================================
    # Utils
    #===========================================================================
    
    def phoneHome(self, message):
        
        SENDMAIL = '/usr/sbin/sendmail'
        SUBJECT = "Besked fra botten"
        
        p = subprocess.Popen([SENDMAIL, '-f',
                              email.Utils.parseaddr(self.from_address)[1],
                              email.Utils.parseaddr(self.to_address)[1]],
                              stdin=subprocess.PIPE)
        
        print >> p.stdin, "MIME-Version: 1.0"
        print >> p.stdin, "Content-Type: text/plain; charset=UTF-8"
        print >> p.stdin, "Content-Disposition: inline"
        print >> p.stdin, "From: %s" % self.from_address
        print >> p.stdin, "To: %s" % self.to_address
        print >> p.stdin, "Subject: %s" % SUBJECT
        print >> p.stdin
        print >> p.stdin, message
        print >> p.stdin, "Cheers"
        
        p.stdin.close()
        p.wait()

################################################################################
# main                                                                         #
################################################################################

if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1:] == ["xboard"]:
        pychess = PyChessCECP()
    elif len(sys.argv) == 5 and sys.argv[1] == "fics":
        pychess = PyChessFICS(*sys.argv[2:])
    else:
        print "Unknown argument(s):", repr(sys.argv)
        sys.exit(0)
    
    pychess.makeReady()
    pychess.run()
