
from .ldata import BLACK_SQUARES
from pychess.Utils.const import WHITE, BLACK, KNIGHT, BISHOP, ROOK, QUEEN, PAWN


def testFifty(board):
    if board.fifty >= 100:
        return True
    return False


drawSet = set(((0, 0, 0, 0, 0, 0, 0, 0),  # KK
               (0, 1, 0, 0, 0, 0, 0, 0),  # KBK
               (1, 0, 0, 0, 0, 0, 0, 0),  # KNK
               (0, 0, 0, 0, 0, 1, 0, 0),  # KKB
               (0, 0, 0, 0, 1, 0, 0, 0),  # KNK
               (1, 0, 0, 0, 0, 1, 0, 0),  # KNKB
               (0, 1, 0, 0, 1, 0, 0, 0),  # KBKN
               ))

# Contains not 100% sure ones
drawSet2 = set(((2, 0, 0, 0, 0, 0, 0, 0),  # KNNK
                (0, 0, 0, 0, 2, 0, 0, 0),  # KKNN
                (2, 0, 0, 0, 1, 0, 0, 0),  # KNNKN
                (1, 0, 0, 0, 2, 0, 0, 0),  # KNKNN
                (2, 0, 0, 0, 0, 1, 0, 0),  # KNNKB
                (0, 1, 0, 0, 2, 0, 0, 0),  # KBKNN
                (2, 0, 0, 0, 0, 0, 1, 0),  # KNNKR
                (0, 0, 1, 0, 2, 0, 0, 0)   # KRKNN
                ))


def testMaterial(board):
    """ Tests if no players are able to win the game from the current
        position """

    whitePieceCount = board.pieceCount[WHITE]
    blackPieceCount = board.pieceCount[BLACK]

    if whitePieceCount[PAWN] or blackPieceCount[PAWN]:
        return False

    if whitePieceCount[QUEEN] or blackPieceCount[QUEEN]:
        return False

    wn = whitePieceCount[KNIGHT]
    wb = whitePieceCount[BISHOP]
    wr = whitePieceCount[ROOK]
    bn = blackPieceCount[KNIGHT]
    bb = blackPieceCount[BISHOP]
    br = blackPieceCount[ROOK]

    if (wn, wb, wr, 0, bn, bb, br, 0) in drawSet:
        return True

    # Tests KBKB. Draw if bishops are of same color
    if not wn + wr + bn + br and wb == 1 and bb == 1:
        if board.boards[WHITE][BISHOP] & BLACK_SQUARES != \
           board.boards[BLACK][BISHOP] & BLACK_SQUARES:
            return True


def testPlayerMatingMaterial(board, color):
    """ Tests if given color has enough material to mate on board """

    pieceCount = board.pieceCount[color]

    if pieceCount[PAWN] or pieceCount[QUEEN] or pieceCount[ROOK] \
       or (pieceCount[KNIGHT] + pieceCount[BISHOP] > 1):
        return True
    return False

# This could be expanded by the fruit kpk draw function, which can test if a
# certain king verus king and pawn posistion is winable.


def test(board):
    """ Test if the position is drawn. Two-fold repetitions are counted. """
    return board.repetitionCount(draw_threshold=2) > 1 or \
        testFifty(board) or \
        testMaterial(board)
