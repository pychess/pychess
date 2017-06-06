from time import time
from random import random
from heapq import heappush, heappop

from .lmovegen import genAllMoves, genCheckEvasions, genCaptures
from .egtb_gaviota import EgtbGaviota
from pychess.Utils.const import ATOMICCHESS, KINGOFTHEHILLCHESS, THREECHECKCHESS,\
    LOSERSCHESS, SUICIDECHESS, EMPTY, PROMOTIONS, DROP, KING,\
    hashfALPHA, hashfBETA, hashfEXACT, hashfBAD, DRAW, WHITE, WHITEWON
from .leval import evaluateComplete
from .lsort import getCaptureValue, getMoveValue
from .ldata import MATE_VALUE, VALUE_AT_PLY
from .TranspositionTable import TranspositionTable
from pychess.Variants.atomic import kingExplode
from pychess.Variants.kingofthehill import testKingInCenter
from pychess.Variants.threecheck import checkCount
from . import ldraw

TIMECHECK_FREQ = 500

table = TranspositionTable(32 * 1024 * 1024)
skipPruneChance = 0
searching = False
nodes = 0
endtime = 0
timecheck_counter = TIMECHECK_FREQ
egtb = None


def alphaBeta(board, depth, alpha=-MATE_VALUE, beta=MATE_VALUE, ply=0):
    """ This is a alphabeta/negamax/quiescent/iterativedeepend search algorithm
        Based on moves found by the validator.py findmoves2 function and
        evaluated by eval.py.
        The function recalls itself "depth" times. If the last move in range
        depth was a capture, it will continue calling itself, only searching for
        captures.
        It returns a tuple of
        *   a list of the path it found through the search tree (last item being
            the deepest)
        *   a score of your standing the the last possition. """

    global searching, nodes, table, endtime, timecheck_counter
    foundPv = False
    hashf = hashfALPHA
    amove = []

    ############################################################################
    # Mate distance pruning
    ############################################################################

    MATED = -MATE_VALUE + ply
    MATE_IN_1 = MATE_VALUE - ply - 1

    if beta <= MATED:
        return [], MATED
    if beta >= MATE_IN_1:
        beta = MATE_IN_1
        if alpha >= beta:
            return [], MATE_IN_1

    if board.variant == ATOMICCHESS:
        if bin(board.boards[board.color][KING]).count("1") == 0:
            return [], MATED
    elif board.variant == KINGOFTHEHILLCHESS:
        if testKingInCenter(board):
            return [], MATED
    elif board.variant == THREECHECKCHESS:
        if checkCount(board) == 3:
            return [], MATED

    ############################################################################
    # Look in the end game table
    ############################################################################

    global egtb
    if egtb:
        tbhits = egtb.scoreAllMoves(board)
        if tbhits:
            move, state, steps = tbhits[0]

            if state == DRAW:
                score = 0
            elif board.color == WHITE:
                if state == WHITEWON:
                    score = MATE_VALUE - steps
                else:
                    score = -MATE_VALUE + steps
            else:
                if state == WHITEWON:
                    score = -MATE_VALUE + steps
                else:
                    score = MATE_VALUE - steps
            return [move], score

    ###########################################################################
    # We don't save repetition in the table, so we need to test draw before   #
    # table.                                                                  #
    ###########################################################################

    # We don't adjudicate draws. Clients may have different rules for that.
    if ply > 0:
        if ldraw.test(board):
            return [], 0

    ############################################################################
    # Look up transposition table                                              #
    ############################################################################
    if ply == 0:
        table.newSearch()

    table.setHashMove(depth, -1)
    probe = table.probe(board, depth, alpha, beta)
    if probe:
        move, score, hashf = probe
        score = VALUE_AT_PLY(score, ply)
        table.setHashMove(depth, move)

        if hashf == hashfEXACT:
            return [move], score
        elif hashf == hashfBETA:
            beta = min(score, beta)
        elif hashf == hashfALPHA:
            alpha = score

        if hashf != hashfBAD and alpha >= beta:
            return [move], score

    ############################################################################
    # Cheking the time                                                         #
    ############################################################################

    timecheck_counter -= 1
    if timecheck_counter == 0:
        if time() > endtime:
            searching = False
        timecheck_counter = TIMECHECK_FREQ

    ############################################################################
    # Break itereation if interupted or if times up                            #
    ############################################################################

    if not searching:
        return [], -evaluateComplete(board, 1 - board.color)

    ############################################################################
    # Go for quiescent search                                                  #
    ############################################################################

    isCheck = board.isChecked()

    if depth <= 0:
        if isCheck:
            # Being in check is that serious, that we want to take a deeper look
            depth += 1
        elif board.variant in (LOSERSCHESS, SUICIDECHESS, ATOMICCHESS):
            return [], evaluateComplete(board, board.color)
        else:
            mvs, val = quiescent(board, alpha, beta, ply)
            return mvs, val

    ############################################################################
    # Find and sort moves                                                      #
    ############################################################################

    # Generate all possible captures
    mlist = [m for m in genCaptures(board)]
    if isCheck:
        # If isCheck, first priority is to evade check.
        moves = [(-getMoveValue(board, table, depth, m), m)
                 for m in genCheckEvasions(board)]
    elif mlist:
        # If capture is possible and not checked, force player to choose
        # best capture. 
        moves = [(-getMoveValue(board, table, depth, m), m) for m in mlist]
    else:
        # If no captures available, just generate all possible moves.
        moves = [(-getMoveValue(board, table, depth, m), m)
                 for m in genAllMoves(board)]

    # A capture should not lead to a check
    checks = 0
    if not isCheck and mlist:
        # Determines if next move leads to a check. If so, increment
        # checks and reverts move.
        for _, move in moves:
            board.applyMove(move)
            if board.opIsChecked():
                checks += 1
            board.popMove()

        # If all captures lead to check, generate all possible moves.
        if len(moves) == checks:
            moves = [(-getMoveValue(board, table, depth, m), m)
             for m in genAllMoves(board)]


    moves.sort()

    # This is needed on checkmate
    catchFailLow = None

    ############################################################################
    # Loop moves                                                               #
    ############################################################################

    for moveValue, move in moves:

        nodes += 1

        board.applyMove(move)
        if not isCheck:
            if board.opIsChecked():
                board.popMove()
                continue

        catchFailLow = move

        if foundPv:
            mvs, val = alphaBeta(board, depth - 1, -alpha - 1, -alpha, ply + 1)
            val = -val
            if val > alpha and val < beta:
                mvs, val = alphaBeta(board, depth - 1, -beta, -alpha, ply + 1)
                val = -val
        else:
            mvs, val = alphaBeta(board, depth - 1, -beta, -alpha, ply + 1)
            val = -val

        board.popMove()

        if val > alpha:
            if val >= beta:
                if searching and move >> 12 != DROP:
                    table.record(board, move, VALUE_AT_PLY(beta, -ply),
                                 hashfBETA, depth)
                    # We don't want to use our valuable killer move spaces for
                    # captures and promotions, as these are searched early anyways.
                    if board.arBoard[move & 63] == EMPTY and \
                            not move >> 12 in PROMOTIONS:
                        table.addKiller(depth, move)
                        table.addButterfly(move, depth)
                return [move] + mvs, beta

            alpha = val
            amove = [move] + mvs
            hashf = hashfEXACT
            foundPv = True

    ############################################################################
    # Return                                                                   #
    ############################################################################

    if amove:
        if searching:
            table.record(board, amove[0], VALUE_AT_PLY(alpha, -ply), hashf,
                         depth)
            if board.arBoard[amove[0] & 63] == EMPTY:
                table.addKiller(depth, amove[0])
        return amove, alpha

    if catchFailLow:
        if searching:
            table.record(board, catchFailLow, VALUE_AT_PLY(alpha, -ply), hashf,
                         depth)
        return [catchFailLow], alpha

    # If no moves were found, this must be a mate or stalemate
    if isCheck:
        return [], MATED

    return [], 0


def quiescent(board, alpha, beta, ply):

    if skipPruneChance and random() < skipPruneChance:
        return [], (alpha + beta) // 2

    global nodes

    if ldraw.test(board):
        return [], 0

    isCheck = board.isChecked()

    # no stand-pat when in check
    if not isCheck:
        value = evaluateComplete(board, board.color)
        if value >= beta:
            return [], beta
        if value > alpha:
            alpha = value

    amove = []

    heap = []

    if isCheck:
        someMove = False
        for move in genCheckEvasions(board):
            someMove = True
            # Heap.append is fine, as we don't really do sorting on the few moves
            heap.append((0, move))
        if not someMove:
            return [], -MATE_VALUE + ply
    else:
        for move in genCaptures(board):
            heappush(heap, (-getCaptureValue(board, move), move))

    while heap:

        nodes += 1

        v, move = heappop(heap)

        board.applyMove(move)
        if not isCheck:
            if board.opIsChecked():
                board.popMove()
                continue

        mvs, val = quiescent(board, -beta, -alpha, ply + 1)
        val = -val

        board.popMove()

        if val >= beta:
            return [move] + mvs, beta

        if val > alpha:
            alpha = val
            amove = [move] + mvs

    if amove:
        return amove, alpha

    else:
        return [], alpha


class EndgameTable():
    def __init__(self):
        self.provider = EgtbGaviota()

    def _pieceCounts(self, board):
        return sorted([bin(board.friends[i]).count("1") for i in range(2)])

    def scoreAllMoves(self, lBoard):
        """ Return each move's result and depth to mate.
            lBoard: A low-level board structure
            Return value: a list, with best moves first, of:
            move: A high-level move structure
            game_result: Either WHITEWON, DRAW, BLACKWON
            depth: Depth to mate
        """

        pc = self._pieceCounts(lBoard)
        if self.provider.supports(pc):
            return self.provider.scoreAllMoves(lBoard)
        return []


def enableEGTB():
    global egtb
    egtb = EndgameTable()
