#!/usr/bin/python

from time import time
import sys, os
import random, math
import subprocess
import email.Utils
import gettext
from urllib import urlopen, urlencode

from pychess.System.prefix import addDataPrefix
gettext.install("pychess", localedir=addDataPrefix("lang"), unicode=1)

from pychess.Utils.const import *
from pychess.Utils.repr import reprResult_long, reprReason_long
from pychess.Utils.book import getOpenings
from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.lmove import *
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils import leval
from pychess.Utils.lutils.validator import validateMove

from pychess.System.GtkWorker import GtkWorker
from pychess.System import glock
from pychess.System.repeat import repeat_sleep
from pychess.System.ThreadPool import pool
from pychess.System.Log import log

from pychess.ic.FICSConnection import FICSConnection

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
        #if len(self.board.history) < 14:
        movestr = self.__getBestOpening()
        if movestr:
            mvs = [parseSAN(self.board, movestr)]
        
        #if len(self.board.history) >= 14 or not movestr:
        if not movestr:
               
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
            glock.acquire()
            self.worker.get()
            glock.release()
            self.worker = None
    
    def __go (self):
        self.worker = GtkWorker(lambda worker: PyChess._PyChess__go(self, worker))
        def process (worker, messages): print "\n".join(messages)
        self.worker.connect("published", process)
        def ondone (worker, result):
            self.board.applyMove(parseSAN(self.board,result))
            print "move %s" % result
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
        if not password:
            self.username = "guest"
        else: self.username = "PyChess"
        self.owner = "Lobais"
        self.password = password
        self.from_address = "The PyChess Bot <%s>" % from_address
        self.to_address = "Thomas Dybdahl Ahle <%s>" % to_address
        
        # Possible start times
        self.minutes = (1,2,3,4,5,6,7,8,9,10)
        self.gains = (0,5,10,15,20)
        # Possible colors. None == random
        self.colors = (WHITE, BLACK, None) 
        # The amount of random challenges, that PyChess sends with each seek
        self.challenges = 10
        self.useegtb = True
        
        self.sudos = set()
        self.ownerOnline = False
        self.waitingForPassword = None
        self.log = []
        self.acceptedTimesettings = []
        
        self.worker = None
        
        repeat_sleep(self.sendChallenges, 60*1)
    
    def __triangular(self, low, high, mode):
        """Triangular distribution.
        Continuous distribution bounded by given lower and upper limits,
        and having a given mode value in-between.
        http://en.wikipedia.org/wiki/Triangular_distribution
        """
        u = random.random()
        c = (mode - low) / (high - low)
        if u > c:
            u = 1 - u
            c = 1 - c
            low, high = high, low
        tri = low + (high - low) * (u * c) ** 0.5
        if tri < mode:
            return int(tri)
        elif tri > mode:
            return int(math.ceil(tri))
        return int(math.round(tri))
    
    def sendChallenges(self):
        if self.connection.bm.isPlaying():
            return True
        
        statsbased = ((0.39197722779282, 3, 0),
                      (0.59341408108783, 5, 0),
                      (0.77320877377846, 1, 0),
                      (0.8246379941394, 10, 0),
                      (0.87388717406441, 2, 12),
                      (0.91443760169489, 15, 0),
                      (0.9286423058163, 4, 0),
                      (0.93891977227793, 2, 0),
                      (0.94674539138335, 20, 0),
                      (0.95321476842423, 2, 2),
                      (0.9594588808257, 5, 2),
                      (0.96564528079889, 3, 2),
                      (0.97173859621034, 7, 0),
                      (0.97774906636184, 3, 1),
                      (0.98357243654425, 5, 12),
                      (0.98881309737017, 5, 5),
                      (0.99319644938247, 6, 0),
                      (0.99675879556023, 3, 12),
                      (1, 5, 3))
        
        #n = random.random()
        #for culminativeChance, minute, gain in statsbased:
        #    if n < culminativeChance:
        #        break
        
        culminativeChance, minute, gain = random.choice(statsbased)
        
        #type = random.choice((TYPE_LIGHTNING, TYPE_BLITZ, TYPE_STANDARD))
        #if type == TYPE_LIGHTNING:
        #    minute = self.__triangular(0,2+1,1)
        #    mingain = not minute and 1 or 0
        #    maxgain = int((3-minute)*3/2)
        #    gain = random.randint(mingain, maxgain)
        #elif type == TYPE_BLITZ:
        #    minute = self.__triangular(0,14+1,5)
        #    mingain = max(int((3-minute)*3/2+1), 0)
        #    maxgain = int((15-minute)*3/2)
        #    gain = random.randint(mingain, maxgain)
        #elif type == TYPE_STANDARD:
        #    minute = self.__triangular(0,20+1,12)
        #    mingain = max(int((15-minute)*3/2+1), 0)
        #    maxgain = int((20-minute)*3/2)
        #    gain = self.__triangular(mingain, maxgain, mingain)
        
        #color = random.choice(self.colors)
        self.extendlog(["Seeking %d %d" % (minute, gain)])
        self.connection.glm.seek(minute, gain, True)
        opps = random.sample(self.connection.glm.getPlayerlist(), self.challenges)
        self.extendlog("Challenging %s" % op for op in opps)
        for player in opps:
            self.connection.om.challenge(player, minute, gain, True)
        
        return True
    
    def makeReady(self):
        PyChess.makeReady(self)
        
        self.connection = FICSConnection("freechess.org",self.ports,
                                         self.username, self.password)
        self.connection.connect("connectingMsg", self.__showConnectLog)
        self.connection._connect()
        
        self.connection.glm.connect("addPlayer", self.__onAddPlayer)
        self.connection.glm.connect("removePlayer", self.__onRemovePlayer)
        self.connection.cm.connect("privateMessage", self.__onTell)
        self.connection.alm.connect("logOut", self.__onLogOut)
        self.connection.bm.connect("playBoardCreated", self.__onPlayBoardCreated)
        self.connection.bm.connect("curGameEnded", self.__onGameEnded)
        self.connection.bm.connect("boardUpdate", self.__onBoardUpdate)
        self.connection.om.connect("onChallengeAdd", self.__onChallengeAdd)
        self.connection.om.connect("onOfferAdd", self.__onOfferAdd)
        self.connection.adm.connect("onAdjournmentsList", self.__onAdjournmentsList)
        self.connection.em.connect("onAmbiguousMove", self.__onAmbiguousMove)
        self.connection.em.connect("onIllegalMove", self.__onAmbiguousMove)
        
        self.connection.adm.queryAdjournments()
        self.connection.lvm.setVariable("autoflag", True)
        
        self.connection.fm.setFingerNote(1,
            "PyChess is the chess engine bundled with the PyChess %s " % VERSION +
            "chess client. This instance is owned by %s, but acts " % self.owner +
            "quite autonomously.")
        
        self.connection.fm.setFingerNote(2,
            "PyChess is 100% Python code and is released under the terms of " +
            "the GPL. The evalution function is largely equal to the one of" +
            "GnuChess, but it plays quite differently.")
        
        self.connection.fm.setFingerNote(3,
            "PyChess runs on an elderly AMD Sempron(tm) Processor 3200+, 512 " +
            "MB DDR2 Ram, but is built to take use of 64bit calculating when " +
            "accessible, through the gpm library.")
        
        self.connection.fm.setFingerNote(4,
            "PyChess uses a small 500 KB openingbook based solely on Kasparov " +
            "games. The engine doesn't have much endgame knowledge, but might " +
            "in some cases access an online endgamedatabase.")
        
        self.connection.fm.setFingerNote(5,
            "PyChess will allow any pause/resume and adjourn wishes, but will " +
            "deny takebacks. Draw, abort and switch offers are accepted, " +
            "if they are found to be an advance. Flag is auto called, but " +
            "PyChess never resigns. We don't want you to forget your basic " +
            "mating skills.")
    
    def run(self):
        self.connection.run()
        self.extendlog([str(self.acceptedTimesettings)])
        self.phoneHome("Session ended\n"+"\n".join(self.log))
        print "Session ended"
    
    #===========================================================================
    # General
    #===========================================================================
    
    def __showConnectLog (self, connection, message):
        print message
    
    def __onLogOut (self, autoLogoutManager):
        self.connection.disconnect()
        #sys.exit()
    
    def __onAddPlayer (self, gameListManager, player):
        if player["name"] in self.sudos:
            self.sudos.remove(player["name"])
        if player["name"] == self.owner:
            self.connection.cm.tellPlayer(self.owner, "Greetings")
            self.ownerOnline = True
    
    def __onRemovePlayer (self, gameListManager, playername):
        if playername == self.owner:
            self.ownerOnline = False
    
    def __onAdjournmentsList (self, adjournManager, adjournments):
        for adjournment in adjournments:
            if adjournment["online"]:
                adjournManager.challenge(adjournment["opponent"])
    
    def __usage (self):
        return "|| PyChess bot help file || " +\
               "# help 'Displays this help file' " +\
               "# sudo <password> <command> 'Lets PyChess execute the given command' "+\
               "# sendlog 'Makes PyChess send you its current log'"
    
    def __onTell (self, chatManager, name, title, isadmin, text):
        
        if self.waitingForPassword:
            if text.strip() == self.password or (not self.password and text == "none"):
                self.sudos.add(name)
                self.tellHome("%s gained sudo access" % name)
                print >> self.connection.client, self.waitingForPassword
            else:
                chatManager.tellPlayer(name, "Wrong password")
                self.tellHome("%s failed sudo access" % name)
            self.waitingForPassword = None
            return
        
        args = text.split()
        
        #if args == ["help"]:
        #    chatManager.tellPlayer(name, self.__usage())
        
        if args[0] == "sudo":
            command = " ".join(args[1:])
            if name in self.sudos or name == self.owner:
                # Notice: This can be used to make nasty loops
                print >> self.connection.client, command
            else:
                print repr(name), self.sudos
                chatManager.tellPlayer(name, "Please send me the password")
                self.waitingForPassword = command
        
        elif args == ["sendlog"]:
            if self.log:
                # TODO: Consider email
                chatManager.tellPlayer(name, "\\n".join(self.log))
            else:
                chatManager.tellPlayer(name, "The log is currently empty")
        
        else:
            if self.ownerOnline:
                self.tellHome("%s told me '%s'" % (name, text))
            else:
                def onlineanswer (message):
                    data = urlopen("http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                                   urlencode({"message":message, "botcust2":"x"})).read()
                    ss = "<b>DMPGirl:</b>"
                    es = "<br>"
                    answer = data[data.find(ss)+len(ss) : data.find(es,data.find(ss))]
                    chatManager.tellPlayer(name, answer)
                pool.start(onlineanswer, text)
            #chatManager.tellPlayer(name, "Sorry, your request was nonsense.\n"+\
            #                           "Please read my help file for more info")
    
    #===========================================================================
    # Challenges and other offers
    #===========================================================================
    
    def __onChallengeAdd (self, offerManager, index, match):
        #match = {"tp": type, "w": fname, "rt": rating, "r": rated, "t": mins, "i": incr}
        offerManager.acceptIndex(index)
    
    def __onOfferAdd (self, offerManager, index, offer):
        if offer.offerType in (PAUSE_OFFER, RESUME_OFFER, ADJOURN_OFFER):
            offerManager.acceptIndex(index)
        elif offer.offerType in (TAKEBACK_OFFER,):
            offerManager.declineIndex(index)
        elif offer.offerType in (DRAW_OFFER, ABORT_OFFER, SWITCH_OFFER):
            if self.scr <= 0:
                offerManager.acceptIndex(index)
            else: offerManager.declineIndex(index)
    
    #===========================================================================
    # Playing
    #===========================================================================
    
    def __onPlayBoardCreated (self, boardManager, board):
        
        self.mytime = int(board["mins"])*60
        self.increment = int(board["incr"])
        self.gameno = board["gameno"]
        self.lastPly = -1
        
        self.acceptedTimesettings.append((self.mytime, self.increment))
        
        self.tellHome("Starting a game (%s, %s) gameno: %s" %
                (board["wname"], board["bname"], board["gameno"]))
        
        if board["bname"].lower() == self.connection.getUsername().lower():
            self.playingAs = BLACK
        else:
            self.playingAs = WHITE
        
        self.board = LBoard(NORMALCHESS)
        # Now we wait until we recieve the board.
    
    def __go (self):
        if self.worker:
            self.worker.cancel()
        self.worker = GtkWorker(lambda worker: PyChess._PyChess__go(self, worker))
        self.worker.connect("published", lambda w, msg: self.extendlog(msg))
        self.worker.connect("done", self.__onMoveCalculated)
        self.worker.execute()
    
    def __onGameEnded (self, boardManager, gameno, wname, bname, result, reason):
        self.tellHome(reprResult_long[result] + " " + reprReason_long[reason])
        lsearch.searching = False
        if self.worker:
            self.worker.cancel()
            self.worker = None
    
    def __onMoveCalculated (self, worker, sanmove):
        if worker.isCancelled() or not sanmove:
            return
        self.board.applyMove(parseSAN(self.board,sanmove))
        self.connection.bm.sendMove(sanmove)
        self.extendlog(["Move sent %s" % sanmove])
    
    def __onBoardUpdate (self, boardManager, gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms):
        self.extendlog(["","I got move %d %s for gameno %s" % (ply, lastmove, gameno)])
        
        if self.gameno != gameno:
            return
        
        self.board.applyFen(fen)
        
        if self.playingAs == WHITE:
            self.mytime = wms/1000.
        else: self.mytime = bms/1000.
        
        if curcol == self.playingAs:
            self.__go()
    
    def __onAmbiguousMove (self, errorManager, move):
        # This is really a fix for fics, but sometimes it is necessary
        if determineAlgebraicNotation(move) == SAN:
            self.board.popMove()
            move_ = parseSAN(self.board, move)
            lanmove = toLAN(self.board, move_)
            self.board.applyMove(move_)
            self.connection.bm.sendMove(lanmove)
        else:
            self.connection.cm.tellOpponent(
                    "I'm sorry, I wanted to move %s, but FICS called " % move +
                    "it 'Ambigious'. I can't find another way to express it, " +
                    "so you can win")
            self.connection.bm.resign()
    
    #===========================================================================
    # Utils
    #===========================================================================
    
    def extendlog(self, messages):
        [log.log(m+"\n") for m in messages]
        self.log.extend(messages)
        del self.log[:-10]
    
    def tellHome(self, message):
        print message
        if self.ownerOnline:
            self.connection.cm.tellPlayer(self.owner, message)
    
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
        
        import signal, gtk
        signal.signal(signal.SIGINT, gtk.main_quit)
        import gettext, gtk.glade
        from pychess.System.prefix import addDataPrefix, getDataPrefix, isInstalled
        if isInstalled():
            gettext.install("pychess", unicode=1)
            gtk.glade.bindtextdomain("pychess")
        else:
            gettext.install("pychess", localedir=addDataPrefix("lang"), unicode=1)
            gtk.glade.bindtextdomain("pychess", addDataPrefix("lang"))
        gtk.glade.textdomain("pychess")
        
        # Start logging
        from pychess.System.Log import log
        log.debug("Started\n")
        from pychess.widgets import LogDialog
        LogDialog.show()
        
    else:
        print "Unknown argument(s):", repr(sys.argv)
        sys.exit(0)
    
    pychess.makeReady()
    
    if len(sys.argv) == 5 and sys.argv[1] == "fics":
        from pychess.System.ThreadPool import pool
        pool.start(pychess.run)
        gtk.gdk.threads_init()
        gtk.main()
    else:
        pychess.run()
