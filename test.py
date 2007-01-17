from pychess.Utils import LBoard
from pychess.Utils import lmovegen
from pychess.Utils.const import cordRepr
board = LBoard.LBoard()
board.setUpPosition()
for move in lmovegen.genAllMoves(board):
    print "flag", move >> 12, \
          "from", cordRepr[(move >> 6) & 63], \
          "to", cordRepr[move & 63]
