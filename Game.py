from Utils.History import History
import Utils.Move
import os
from Players.Engine import EngineDead

player1 = None
player2 = None
chessclock = None
run = False

def game (history, oracle, p1, p2, cc = None, seconds = 0, plus = 0):
    global player1, player2, chessclock, run
    player1, player2, chessclock = p1, p2, cc
    run = True
    
    history.reset(True)
    if chessclock:
        chessclock.setTime(seconds*10)
        chessclock.setGain(plus*10)
    i = 0
    while run:
        for player in player1, player2:
            i += 1
            print "LOOP", i, "STARTED"
            try:
                print "------------- W", 1
                answer = player.makeMove(history)
                
            except Utils.Move.ParsingError:
                #Mostly debugging really
                import traceback
                print traceback.format_exc()
                print "Player 1 board:"
                player1.showBoard()
                print "Player 2 board:"
                player2.showBoard()
                import sys
                sys.exit()
                
            except EngineDead:
                run = False
                print "LOOP", i, "ENDED EngineDead"
                break
            
            print "------------- W", 2
            if type(answer) in (list, tuple):
                move, animate = answer
            else: move, animate = answer, True
            
            if not run:
                break
            
            print "------------- W", 3
            if not history.add(move,True):
                run = False
                print "LOOP", i, "ENDED, history.add"
                break
            
            print "------------- W", 4
            if chessclock:
                chessclock.switch()
            print "LOOP", i, "ENDED"
    
    player1.__del__()
    player2.__del__()
    if chessclock:
        chessclock.stop()
    oracle.game_ended()

#def game (history, oracle, p1, p2, cc = None, seconds = 0, plus = 0):
#    import profile
#    print "GOING IN"
#    profile.runctx('game2(history, oracle, p1, p2, cc, seconds, plus)', locals(), globals())
#    print "EXIT"

def kill ():
    global player1, player2, chessclock, run
    run = False
    if player1: player1.__del__()
    if player2: player2.__del__()
    if chessclock: chessclock.stop()
