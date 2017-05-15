
from pychess.Utils.lutils.lmovegen import genAllMoves

################################################################################
#   Validate move                                                              #
################################################################################


def validateMove(board, move):
    return move in genAllMoves(board)
