#!/usr/bin/python

import threading
from pychess.System.prefix import addDataPrefix
from pychess.Utils.book import getOpenings
from pychess.Utils.const import *
from pychess.Utils.lutils import leval, lsearch
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseSAN, listToSan, toSAN, parseAny
from pychess.Utils.lutils.lsearch import alphaBeta, enableEGTB
from pychess.Utils.lutils.validator import validateMove
from time import time
import gettext
import pychess
import random
import signal
import sys

print "feature done=0"

gettext.install("pychess", localedir=addDataPrefix("lang"), unicode=1)


class PyChess:
    
    def __init__ (self):
        self.sd = 10
        self.skipPruneChance = 0
        
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
        totalWeight = 0
        choice = None
        for move, weight, histGames, histScore in getOpenings(self.board):
            totalWeight += weight
            if totalWeight == 0:
                break
            if not move or random.randrange(totalWeight) < weight:
                choice = move
        return choice
    
    def __go (self, ondone=None):
        """ Finds and prints the best move from the current position """
        
        mv = self.__getBestOpening()
        if mv:
            mvs = [mv]
        
        if not mv:
               
            lsearch.skipPruneChance = self.skipPruneChance
            lsearch.searching = True
            
            if self.mytime == None:
                lsearch.endtime = sys.maxint
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
                print "Time left: %3.2f seconds; Planing to thinking for %3.2f seconds" % (self.mytime, usetime)
                for depth in range(1, self.sd+1):
                    # Heuristic time saving
                    # Don't waste time, if the estimated isn't enough to complete next depth
                    if usetime <= prevtime*4 and usetime > 1:
                        break
                    lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
                    search_result = alphaBeta(self.board, depth)
                    if lsearch.searching:
                        mvs, self.scr = search_result
                        if time() > lsearch.endtime:
                            break
                        if self.post:
                            movstrs = " ".join(listToSan(self.board, mvs))
                            print "\t".join(("%d","%d","%0.2f","%d","%s")) % \
                                           (depth, self.scr, time()-starttime, lsearch.nodes, movstrs)
                    else:
                        # We were interrupted
                        if depth == 1:
                            mvs, self.scr = search_result
                        break
                    prevtime = time()-starttime - prevtime
                
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
                    print "result %s" % reprResult[DRAW]
                elif self.scr < 0:
                    if self.board.color == WHITE:
                        print "result %s" % reprResult[BLACKWON]
                    else: print "result %s" % reprResult[WHITEWON]
                else:
                    if self.board.color == WHITE:
                        print "result %s" % reprResult[WHITEWON]
                    else: print "result %s" % reprResult[BLACKWON]
                print "last: %d %d" % (lsearch.last, self.scr)
                return
            
            lsearch.movesearches = 0
            lsearch.nodes = 0
            lsearch.searching = False
        
        move = mvs[0]
        sanmove = toSAN(self.board, move)
        if ondone: ondone(sanmove)
        return sanmove
    
    def __analyze (self):
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
            print "\t".join(("%d","%d","%0.2f","%d","%s")) % \
                           (depth, scr, time()-start, lsearch.nodes, movstrs)
            
            if lsearch.movesearches:
                mvs_pos = lsearch.nodes/float(lsearch.movesearches)
                mvs_tim = lsearch.nodes/(time()-t)
                print "%0.1f moves/position; %0.1f n/s" % (mvs_pos, mvs_tim)
            
            lsearch.nodes = 0
            lsearch.movesearches = 0
    
    def __analyze2 (self):
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
        self.thread = None
        
        self.features = {
            "setboard": 1,
            "analyze": 1,
            "san": 1,
            "usermove": 1,
            "reuse": 0,
            "draw": 1,
            "sigterm": 1,
            "colors": 1,
            "variants": "normal,nocastle,fischerandom",
            "myname": "PyChess %s" % pychess.VERSION
        }
    
    def makeReady(self):
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
                #self.skipPruneChance = max(0, (5-self.sd)*0.02)
                if self.sd >= 5:
                    print "If the game has no timesettings, you probably don't want\n"+\
                          "to set a search depth much greater than 4"
            
            elif lines[0] == "egtb":
                # This is a crafty command interpreted a bit loose
                enableEGTB()
            
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
            
            elif lines[0] == "post":
                self.post = True
            
            elif lines[0] == "nopost":
                self.post = False
            
            elif lines[0] in ("xboard", "otim", "hard", "easy", "accepted", "rejected"):
                pass
            
            else: print "Warning (unknown command):", line
    
    def __stopSearching(self):
        lsearch.searching = False
        if self.thread:
            self.thread.join()
    
    def __go (self):
        def ondone (result):
            self.board.applyMove(parseSAN(self.board,result))
            print "move %s" % result
        self.thread = threading.Thread(target=PyChess._PyChess__go, args=(self,ondone))
        self.thread.start()
    
    def __analyze (self):
        self.thread = threading.Thread(target=PyChess._PyChess__analyze, args=(self,))
        self.thread.start()

################################################################################
# main                                                                         #
################################################################################

if __name__ == "__main__":
    
    if len(sys.argv) == 1 or sys.argv[1:] == ["xboard"]:
        pychess = PyChessCECP()
    
    elif len(sys.argv) == 5 and sys.argv[1] == "fics":
        from pychess.Players import PyChessFICS
        pychess = PyChessFICS(*sys.argv[2:])
        
    else:
        print "Unknown argument(s):", repr(sys.argv)
        sys.exit(0)
    
    pychess.makeReady()
    pychess.run()
