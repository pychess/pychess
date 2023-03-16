from time import time

from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.lutils.lmove import toLAN


def do_perft(board, depth, root):
    nodes = 0
    if depth == 0:
        return 1

    for move in genAllMoves(board):
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue

        count = do_perft(board, depth - 1, root - 1)
        nodes += count
        board.popMove()
        if root > 0:
            print("%8s %10d %10d" % (toLAN(board, move), count, nodes))

    return nodes


def perft(board, depth, root):
    for i in range(depth):
        start_time = time()
        nodes = do_perft(board, i + 1, root)
        ttime = time() - start_time
        print(
            "%2d %10d %5.2f %12.2fnps"
            % (i + 1, nodes, ttime, nodes / ttime if ttime > 0 else nodes)
        )
