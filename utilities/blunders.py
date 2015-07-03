#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    PyChess blunder finder script.
    This scripts allows you to analyze a played pgn file for blunders, using
    the engine of your choice.
    
    PYTHONPATH=lib/ python blunders.py game.pgn
'''
from __future__ import print_function

###############################################################################
# Set up important things
from gi.repository import GLib
from gi.repository import GObject
GObject.threads_init()
mainloop = GLib.MainLoop()

###############################################################################
# Do the rest of the imports
import atexit
import sys
from pychess.compat import Queue, raw_input, PY2
from pychess.Players.engineNest import discoverer
from pychess.Players.Player import Player, TurnInterrupt, PlayerIsDead
from pychess.System.protoopen import protoopen
from pychess.System import SubProcess
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import *
from pychess.Utils.Move import listToSan, toSAN
from pychess.Savers import pgn

if PY2:
    # This hack fixes some UnicodDecode Errors caused pygi not making
    # magic hidden automatic unicode conversion pygtk did
    reload(sys)
    sys.setdefaultencoding("utf-8")

###############################################################################
# Ask the user for details
def queryGameno(path):
    pgnfile = pgn.load(protoopen(path))
    print("Selected file %s" % path)
    if len(pgnfile) == 0:
        print("The file is empty.")
        sys.exit()
    print()
    
    print("The file contains the following games:")
    for i in range(len(pgnfile)):
        name1, name2 = pgnfile.get_player_names(i)
        print("[%d] %s vs. %s" % (i, name1, name2))
    print()
    if len(pgnfile) == 1:
        print("Autoselecting game 0.")
        gameno = 0
    else:
        gameno = int(raw_input("Select game number to be analyzed. [n]: "))
    print()
    
    return pgnfile, gameno

def queryAnalyzer(analyzers):
    print("PyChess found the following analyzers on your system:")
    for i, engine in enumerate(analyzers):
        print("[%d] %s" % (i, discoverer.getName(engine)))
    print()
    n = int(raw_input("What engine should be your analyzer? [n] "))
    print()
    return analyzers[n]

def queryTime():
    secs = int(raw_input("Enter how many seconds we should use for each move [n]: "))
    print()
    return secs

class DummyPlayer (Player):
    def __init__(self):
        Player.__init__(self)
        self.Q = Queue()
        self.__type__ = LOCAL
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
    atexit.register(SubProcess.finishAllSubprocesses)
    pgnfile, gameno = queryGameno(sys.argv[1])
    analyzer = queryAnalyzer(discoverer.getAnalyzers())
    secs = queryTime()
    name1, name2 = pgnfile.get_player_names(gameno)
    print("%s will now analyze the game between %s and %s with %d seconds per move." % \
            (discoverer.getName(analyzer), name1, name2, secs))
    print()
    
    global game, values
    values = {}
    game = GameModel()
    game.setPlayers([DummyPlayer(), DummyPlayer()])
    analyzer = discoverer.initAnalyzerEngine(analyzer, ANALYZING, game.variant)
    analyzer.connect('analyze', onAnalyze)
    game.spectators[HINT] = analyzer
    game.loadAndStart(sys.argv[1], pgn, gameno, -1)
    
    def cb():
        if game.ply == game.lowply:
            on_finish()
            return False
        check_blund()
        return True
    GLib.timeout_add_seconds(secs, cb)

def on_finish():
    print("Finish")
    mainloop.quit()

def check_blund():
    print()
    
    if game.ply+1 in values and game.ply in values:
        color = game.ply % 2
        oldmoves, oldscore = values[game.ply]
        moves, score = values[game.ply+1]
        dif = score-oldscore
        if dif < -100 and color == WHITE:
            print("White blunder", dif)
            print("Should have done:", ", ".join(listToSan(game.getBoardAtPly(game.ply),oldmoves)))
            print()
        elif dif > 100 and color == BLACK:
            print("Black blunder", dif)
            print("Should have done:", ", ".join(listToSan(game.getBoardAtPly(game.ply),oldmoves)))
            print()
    
    movename = toSAN(game.getBoardAtPly(game.ply-1),game.getMoveAtPly(game.ply-1))
    if game.ply % 2 == 1:
        move_suffix = ""
    else:
        move_suffix = "..."
    print("Considering %d%s %s " % ((game.ply+1)//2, move_suffix, movename,), end=' ')
    game.undoMoves(1)

def onAnalyze(analyzer, analysis):
    global values
    if analysis:
        pv, score, depth = analysis[0]
        sys.stdout.write('.')
        sys.stdout.flush()
        if score != None:
            values[game.ply] = (pv, score*(-1)**game.ply)

###############################################################################
# Slightly validate arguments 

if len(sys.argv) != 2 or sys.argv[1] == "--help":
    print("Usage: python blunders.py FILENAME   Analyze the specified pgn file")
    print("       python blunders.py --help     Display this help and exit")
    print("Note: You'll probably need to run the scripts with your PYTHONPATH set")
    print(" like 'PYTHONPATH=../lib/ python blunders...'")
    sys.exit()

###############################################################################
# Push onto the mainloop and start it
discoverer.connect('all_engines_discovered', start)
discoverer.discover()
mainloop.run()
