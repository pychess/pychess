from Utils.History import History

def game (board, player1, player2, chessclock = None, seconds = 0, plus = 0):
    board.history = History()
    if chessclock:
        chessclock.setTime(seconds*10)
        chessclock.setGain(plus*10)
    while True:
        for player in player1, player2:
            print "make move"
            answer = player.makeMove(board.history)
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
