from Utils.History import History

def game (board, player1, player2, chessclock = None, seconds = 0, plus = 0):
    board.history = History(True)
    if chessclock:
        chessclock.setTime(seconds*10)
        chessclock.setGain(plus*10)
    while True:
        for player in player1, player2:
            try:
                answer = player.makeMove(board.history)
            except:
                import traceback
                print traceback.format_exc()
                print "Player 1 board:"
                player1.showBoard()
                print "Player 2 board:"
                player2.showBoard()
                import sys
                sys.exit()
                
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
