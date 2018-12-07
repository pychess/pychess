""" This module contains chess logic functins for the pychess client. They are
    based upon the lutils modules, but supports standard object types and is
    therefore not as fast. """

from .lutils import lmovegen
from .lutils.validator import validateMove
from .lutils.lmove import FCORD, TCORD
from .lutils import ldraw
from .Cord import Cord
from .Move import Move
from .const import LOSERSCHESS, WHITE, WHITEWON, BLACKWON, WON_NOMATERIAL, KING, HORDECHESS, \
    SUICIDECHESS, GIVEAWAYCHESS, ATOMICCHESS, WON_KINGEXPLODE, KINGOFTHEHILLCHESS, BLACK, DRAW, \
    CRAZYHOUSECHESS, WON_KINGINCENTER, THREECHECKCHESS, WON_THREECHECK, WON_MATE, DRAW_STALEMATE, \
    DRAW_INSUFFICIENT, DRAW_EQUALMATERIAL, WON_LESSMATERIAL, WON_WIPEOUT, DRAW_REPITITION, \
    WON_KINGINEIGHTROW, RACINGKINGSCHESS, DRAW_50MOVES, DRAW_KINGSINEIGHTROW, RUNNING, ENPASSANT, UNKNOWN_REASON

from .lutils.bitboard import iterBits
from .lutils.attack import getAttacks
from pychess.Variants.suicide import pieceCount
from pychess.Variants.losers import testKingOnly
from pychess.Variants.atomic import kingExplode
from pychess.Variants.kingofthehill import testKingInCenter
from pychess.Variants.threecheck import checkCount
from pychess.Variants.racingkings import testKingInEightRow, test2KingInEightRow


def getDestinationCords(board, cord):
    tcords = []
    for move in lmovegen.genAllMoves(board.board):
        if FCORD(move) == cord.cord:
            if not board.board.willLeaveInCheck(move):
                tcords.append(Cord(TCORD(move)))
    return tcords


def isClaimableDraw(board):
    lboard = board.board
    if lboard.repetitionCount() >= 3:
        return True
    if ldraw.testFifty(lboard):
        return True
    return False


def playerHasMatingMaterial(board, playercolor):
    if board.variant == CRAZYHOUSECHESS:
        return True
    lboard = board.board
    return ldraw.testPlayerMatingMaterial(lboard, playercolor)


def getStatus(board):
    lboard = board.board

    if board.variant == LOSERSCHESS:
        if testKingOnly(lboard):
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_NOMATERIAL
    elif board.variant == SUICIDECHESS or board.variant == GIVEAWAYCHESS:
        if pieceCount(lboard, lboard.color) == 0:
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_NOMATERIAL
    elif board.variant == HORDECHESS:
        if pieceCount(lboard, lboard.color) == 0 and board.color == WHITE:
            status = BLACKWON
            return status, WON_WIPEOUT
    elif board.variant == ATOMICCHESS:
        if lboard.boards[board.color][KING] == 0:
            if board.color == WHITE:
                status = BLACKWON
            else:
                status = WHITEWON
            return status, WON_KINGEXPLODE
    elif board.variant == KINGOFTHEHILLCHESS:
        if testKingInCenter(lboard):
            if board.color == BLACK:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_KINGINCENTER
    elif board.variant == THREECHECKCHESS:
        if checkCount(lboard, lboard.color) == 3:
            if board.color == BLACK:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_THREECHECK
    elif board.variant == RACINGKINGSCHESS:
        if test2KingInEightRow(lboard):
            return DRAW, DRAW_KINGSINEIGHTROW
        elif testKingInEightRow(lboard):
            can_save = False
            for move in lmovegen.genAllMoves(lboard):
                if lboard.willGiveCheck(move) or lboard.willLeaveInCheck(move):
                    continue

                lboard.applyMove(move)
                if testKingInEightRow(lboard):
                    can_save = True
                    lboard.popMove()
                    break
                lboard.popMove()
            if not can_save:
                if board.color == BLACK:
                    status = WHITEWON
                else:
                    status = BLACKWON
                return status, WON_KINGINEIGHTROW
    else:
        if ldraw.testMaterial(lboard):
            return DRAW, DRAW_INSUFFICIENT

    hasMove = False
    for move in lmovegen.genAllMoves(lboard):
        if board.variant == ATOMICCHESS:
            if kingExplode(lboard, move, 1 - board.color) and not kingExplode(
                    lboard, move, board.color):
                hasMove = True
                break
            elif kingExplode(lboard, move, board.color):
                continue
        lboard.applyMove(move)
        if lboard.opIsChecked():
            lboard.popMove()
            continue
        hasMove = True
        lboard.popMove()
        break

    if not hasMove:
        if lboard.isChecked():
            if board.variant == LOSERSCHESS:
                if board.color == WHITE:
                    status = WHITEWON
                else:
                    status = BLACKWON
            else:
                if board.color == WHITE:
                    status = BLACKWON
                else:
                    status = WHITEWON
            return status, WON_MATE
        else:
            if board.variant == LOSERSCHESS or board.variant == GIVEAWAYCHESS:
                if board.color == WHITE:
                    status = WHITEWON
                else:
                    status = BLACKWON
                return status, DRAW_STALEMATE
            elif board.variant == SUICIDECHESS:
                if pieceCount(lboard, WHITE) == pieceCount(lboard, BLACK):
                    return status, DRAW_EQUALMATERIAL
                else:
                    if board.color == WHITE and pieceCount(
                            lboard, WHITE) < pieceCount(lboard, BLACK):
                        status = WHITEWON
                    else:
                        status = BLACKWON
                    return status, WON_LESSMATERIAL
            else:
                return DRAW, DRAW_STALEMATE

    if lboard.repetitionCount() >= 3:
        return DRAW, DRAW_REPITITION

    if ldraw.testFifty(lboard):
        return DRAW, DRAW_50MOVES

    return RUNNING, UNKNOWN_REASON


def standard_validate(board, move):
    return validateMove(board.board, move.move) and \
        not board.board.willLeaveInCheck(move.move)


def validate(board, move):
    if board.variant == LOSERSCHESS:
        capture = move.flag == ENPASSANT or board[move.cord1] is not None
        if capture:
            return standard_validate(board, move)
        else:
            can_capture = False
            can_escape_with_capture = False
            ischecked = board.board.isChecked()
            for c in lmovegen.genCaptures(board.board):
                if board.board.willLeaveInCheck(c):
                    continue
                else:
                    can_capture = True
                    if ischecked:
                        can_escape_with_capture = True
                    break
            if can_capture:
                if ischecked and not can_escape_with_capture:
                    return standard_validate(board, move)
                else:
                    return False
            else:
                return standard_validate(board, move)
    elif board.variant == SUICIDECHESS:
        capture = move.flag == ENPASSANT or board[move.cord1] is not None
        if capture:
            return standard_validate(board, move)
        else:
            can_capture = False
            for c in lmovegen.genCaptures(board.board):
                can_capture = True
            if can_capture:
                return False
            else:
                return standard_validate(board, move)
    elif board.variant == ATOMICCHESS:
        # Moves exploding our king are not allowed
        if kingExplode(board.board, move.move, board.color):
            return False
        # Exploding oppont king takes precedence over mate
        elif kingExplode(board.board, move.move, 1 -
                         board.color) and validateMove(board.board, move.move):
            return True
        else:
            return standard_validate(board, move)
    elif board.variant == RACINGKINGSCHESS:
        # Giving check is forbidden
        if board.board.willGiveCheck(move.move):
            return False
        else:
            return standard_validate(board, move)
    else:
        return standard_validate(board, move)


def getMoveKillingKing(board):
    """ Returns a move from the current color, able to capture the opponent
        king """

    lboard = board.board
    color = lboard.color
    opking = lboard.kings[1 - color]

    for cord in iterBits(getAttacks(lboard, opking, color)):
        return Move(Cord(cord), Cord(opking), board)


def genCastles(board):
    for move in lmovegen.genCastles(board.board):
        yield Move(move)


def legalMoveCount(board):
    moves = 0
    for move in lmovegen.genAllMoves(board.board):
        if not board.board.willLeaveInCheck(move):
            moves += 1
    return moves
