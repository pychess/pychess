from Utils.History import History
import Utils.Move
import os
from Players.Engine import EngineDead

player1 = None
player2 = None
chessclock = None
run = False

def game (board, oracle, p1, p2, cc = None, seconds = 0, plus = 0):
    global player1, player2, chessclock, run
    player1, player2, chessclock = p1, p2, cc
    run = True
    
    board.history.reset(True)
    if chessclock:
        chessclock.setTime(seconds*10)
        chessclock.setGain(plus*10)
    while run:
        for player in player1, player2:
            try:
                answer = player.makeMove(board.history)
                
            except Utils.Move.ParsingError:
                import traceback
                print traceback.format_exc()
                print "Player 1 board:"
                player1.showBoard()
                print "Player 2 board:"
                player2.showBoard()
                import sys
                sys.exit()
                
            except EngineDead:
                return
            
            if type(answer) in (list, tuple):
                move, animate = answer
            else: move, animate = answer, True
            again = board.move(move, animate)
            
            if not again:
                player1.__del__()
                player2.__del__()
                if chessclock:
                    chessclock.stop()
                return
                
            if chessclock:
                chessclock.switch()

def kill ():
    global player1, player2, chessclock, run
    run = False
    if player1: player1.__del__()
    if player2: player2.__del__()
    if chessclock: chessclock.stop()
