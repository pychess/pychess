from Utils.History import History
def game (board, player1, player2, chessclock = None, seconds = 0, plus = 0):
    board.history = History()
    if chessclock:
        chessclock.setTime(seconds*10)
        chessclock.setGain(plus*10)
    while True:
        for player in player1, player2:
            answer = player.makeMove(board.history)
            if type(answer) in (list, tuple):
                move, animate = answer
            else: move, animate = answer, True
            board.move(move, animate)
            if chessclock:
                chessclock.switch()
