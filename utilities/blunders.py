#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    PyChess blunder finder script.
    This scripts allows you to analyze a played pgn file for blunders, using
    the engine of your choice.
    
    PYTHONPATH=lib/ python blunders.py game.pgn
'''

###############################################################################
# Set up important things
import glib, gobject, __builtin__
__builtin__.__dict__["_"] = lambda x:x
gobject.threads_init()
mainloop = glib.MainLoop()

###############################################################################
# Do the rest of the imports
import sys
import Queue
from pychess.Players.engineNest import discoverer
from pychess.Players.Player import Player, TurnInterrupt, PlayerIsDead
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import *
from pychess.Utils.Move import listToSan, toSAN
from pychess.Savers import pgn

###############################################################################
# Ask the user for details
def queryGameno(path):
    pgnfile = pgn.load(path)
    print "Selected file %s" % path
    if len(pgnfile) == 0:
        print "The file is empty."
        sys.exit()
    print
    
    print "The file contains the following games:"
    for i in xrange(len(pgnfile)):
        name1, name2 = pgnfile.get_player_names(i)
        print "[%d] %s vs. %s" % (i, name1, name2)
    print
    if len(pgnfile) == 1:
        print "Autoselecting game 0."
        gameno = 0
    else:
        gameno = int(raw_input("What engine should be your analyzer? [n] "))
    print
    
    return pgnfile, gameno

def queryAnalyzer(analyzers):
    print "PyChess found the following analyzers on your system:"
    for i, engine in enumerate(analyzers):
        print "[%d] %s" % (i, discoverer.getName(engine))
    print
    n = int(raw_input("What engine should be your analyzer? [n] "))
    print
    return analyzers[n]

def queryTime():
    secs = int(raw_input("Enter how many seconds we should use for each move [n]: "))
    print
    return secs

class DummyPlayer (Player):
    def __init__(self):
        Player.__init__(self)
        self.Q = Queue.Queue()
    def makeMove (self, board1, move, board2):
        r = self.Q.get()
        if r == "del": raise PlayerIsDead
        if r == "int": raise TurnInterrupt
    def undoMoves (self, moves, gamemodel): self.Q.put('int')
    def end (self, status, reason): self.Q.put('del')
    def kill (self, reason): self.Q.put('del')
    def pause (self): pass
    def resume (self):  pass
    def offer (self, offer): self.emit('accept', offer)

def start(discoverer):
    pgnfile, gameno = queryGameno(sys.argv[1])
    analyzer = queryAnalyzer(list(discoverer.getAnalyzers()))
    secs = queryTime()
    name1, name2 = pgnfile.get_player_names(gameno)
    print "%s will now analyze the game between %s and %s with %d seconds per move." % \
            (discoverer.getName(analyzer), name1, name2, secs)
    print
    
    global game, values
    values = {}
    game = GameModel()
    game.setPlayers([DummyPlayer(), DummyPlayer()])
    analyzer = discoverer.initAnalyzerEngine(analyzer, ANALYZING, game.variant)
    analyzer.connect('analyze', onAnalyze)
    game.setSpectactors({0: analyzer})
    game.loadAndStart(sys.argv[1], pgn, gameno, -1)
    
    def cb():
        if game.ply == game.lowply:
            on_finish()
            return False
        check_blund()
        return True
    glib.timeout_add_seconds(secs, cb)

def on_finish():
    print "Finish"
    mainloop.quit()

def check_blund():
    print "Undoing", 
    
    if game.ply+1 in values and game.ply in values:
        color = game.ply%2
        oldmoves, oldscore = values[game.ply]
        moves, score = values[game.ply+1]
        dif = score-oldscore
        print game.ply/2+1, dif, toSAN(game.getBoardAtPly(game.ply-1),game.getMoveAtPly(game.ply-1))
        if dif < -100 and color == WHITE:
            print "White blunder"
            print "Should have done:", listToSan(game.getBoardAtPly(game.ply),oldmoves)
        elif dif > 100 and color == BLACK:
            print "Black blunder"
            print "Should have done:", listToSan(game.getBoardAtPly(game.ply),oldmoves)
    else:
        print
    
    game.undoMoves(1)

def onAnalyze(analyzer, pv, score):
    global values
    sys.stdout.write('.')
    if score != None:
        values[game.ply] = (pv, score*(-1)**game.ply)

###############################################################################
# Push onto the mainloop and start it
discoverer.connect('all_engines_discovered', start)
discoverer.start()
mainloop.run()
