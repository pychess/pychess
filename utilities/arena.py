#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    PyChess arena tournament script.
    This script executes a tournament between the engines installed on your
    system. The script is executed from a terminal with the usual environment.
'''

import os
import sys

###############################################################################
# Set up important things
from gi.repository import GLib
from gi.repository import GObject

GObject.threads_init()
mainloop = GLib.MainLoop()

from pychess.Utils.const import *

###############################################################################
# Fix environment
if "PYTHONPATH" in os.environ:
    os.environ["PYTHONPATH"] = os.pathsep.join(
        os.path.abspath(p) for p in os.environ["PYTHONPATH"].split(os.pathsep))

###############################################################################
from pychess.System import Log
Log.DEBUG = False

###############################################################################
# Do the rest of the imports
from pychess.Players.engineNest import discoverer
from pychess.Savers.pgn import save
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Variants import variants

###############################################################################
# Look up engines
def prepare():
    print("Discovering engines", end=' ')
    discoverer.connect('discovering_started', cb_started)
    discoverer.connect('engine_discovered', cb_gotone)
    discoverer.connect('all_engines_discovered', start)
    discoverer.discover()

def cb_started(discoverer, binnames):
    print("Wait a moment while we discover %d engines" % len(binnames))

def cb_gotone (discoverer, binname, engine):
    sys.stdout.write(".")

###############################################################################
# Ask the user for details
engines = []
results = []
minutes = 0
current = [0,0]

def start(discoverer):
    global engines, results, minutes
    engines = discoverer.getEngines()
    n = len(engines)
    for i in range(n):
        results.append([None]*n)

    print()
    print("Your installed engines are:")
    for i, engine in enumerate(engines):
        name = discoverer.getName(engine)
        print("[%s] %s" % (name[:3], name))
    print("The total amount of fights will be %d" % (n*(n-1)))
    print()
    minutes = int(input("Please enter the clock minutes for each game [n]: "))
    print("The games will last up to %d minutes." % (2*n*(n-1)*minutes))
    print("You will be informed of the progress as the games finish.")
    print()

    runGame()

###############################################################################
# Run games
def runGame():
    a, b = findMatch()
    if a == None:
        print("All games have now been played. Here are the final scores:")
        printResults()
        mainloop.quit()
        return
    current[0] = a
    current[1] = b

    game = GameModel(TimeModel(minutes*60,0))
    game.connect('game_started', cb_gamestarted)
    game.connect('game_ended', cb_gameended)
    p0 = discoverer.initPlayerEngine(engines[a], WHITE, 8, variants[NORMALCHESS], secs=minutes*60, incr=0, forcePonderOff=True)
    p1 = discoverer.initPlayerEngine(engines[b], BLACK, 8, variants[NORMALCHESS], secs=minutes*60, incr=0, forcePonderOff=True)
    game.setPlayers([p0,p1])
    game.start()

def cb_gamestarted(game):
    print("Starting the game between %s and %s" % tuple(game.players))

def cb_gameended(game, reason):
    print("The game between %s and %s ended %s" % (tuple(game.players)+(reprResult[game.status],)))
    if game.status not in (DRAW, WHITEWON, BLACKWON):
        print("Something must have gone wrong. But we'll just try to continue!")
    else:
        i, j = current
        results[i][j] = game.status
        print("The current scores are:")
    printScoreboard()
    print()

    with open("arena.pgn", "a+") as fh:
        save(fh, game)

    runGame()

###############################################################################
# A few helpers
def printScoreboard():
    names = [discoverer.getName(e)[:3] for e in engines]
    print(r"W\B", " ".join(names))
    for i, nameA in enumerate(names):
        print(nameA, end=' ')
        for j, nameB in enumerate(names):
            if i == j: print(" # ", end=' ')
            elif results[i][j] == DRAW: print("½-½", end=' ')
            elif results[i][j] == WHITEWON: print("1-0", end=' ')
            elif results[i][j] == BLACKWON: print("0-1", end=' ')
            else: print(" . ", end=' ')
        print()

def printResults():
    scores = []
    for i in range(len(engines)):
        points = sum(2 for j in range(len(engines)) if results[i][j] == WHITEWON) \
               + sum(1 for j in range(len(engines)) if results[i][j] == DRAW) \
               + sum(2 for j in range(len(engines)) if results[j][i] == BLACKWON) \
               + sum(1 for j in range(len(engines)) if results[j][i] == DRAW)
        scores.append((points, i))
    scores.sort(reverse=True)
    for points, i in scores:
        print(discoverer.getName(engines[i]), ":", points/2, "½"*(points%2))

#def findMatch():
#    for i, engineA in enumerate(engines):
#        for j, engineB in enumerate(engines):
#            if i != j and results[i][j] == None:
#                return i, j
#    return None, None

import random
def findMatch():
    pos = [(i,j) for i in range(len(engines))
                 for j in range(len(engines))
                 if i != j and results[i][j] == None]
    #pos = [(i,j) for i,j in pos if
    #       "pychess" in discoverer.getName(engines[i]).lower() or
    #       "pychess" in discoverer.getName(engines[j]).lower()]
    if not pos:
        return None, None
    return random.choice(pos)

###############################################################################
# Push onto the mainloop and start it
#glib.idle_add(prepare)
prepare()
def do(discoverer):
    game = GameModel(TimeModel(60,0))
    #game.connect('game_started', cb_gamestarted2)
    game.connect('game_ended', lambda *a: mainloop.quit())
    p0 = discoverer.initPlayerEngine(discoverer.getEngines()['rybka'], WHITE, 7, variants[NORMALCHESS], 60)
    p1 = discoverer.initPlayerEngine(discoverer.getEngines()['gnuchess'], BLACK, 7, variants[NORMALCHESS], 60)
    game.setPlayers([p0,p1])
    game.start()
#discoverer.connect('all_engines_discovered', do)
#discoverer.start()
mainloop.run()
