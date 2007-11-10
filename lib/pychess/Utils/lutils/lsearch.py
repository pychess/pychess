from time import time

from lmovegen import genAllMoves, genCheckEvasions, genCaptures
from pychess.Utils.const import *
from leval import evaluateComplete
from lsort import getCaptureValue, getMoveValue
from lmove import toSAN
from ldata import MATE_VALUE
from TranspositionTable import TranspositionTable
import ldraw

from heapq import heappush, heappop
TIMECHECK_FREQ = 500

table = TranspositionTable(50000)
searching = False
movesearches = 0
nodes = 0
last = 0
endtime = 0
timecheck_counter = TIMECHECK_FREQ

def alphaBeta (board, depth, alpha=-MATE_VALUE, beta=MATE_VALUE, ply=0):
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
    
    global last, searching, nodes, movesearches, table, endtime, timecheck_counter
    foundPv = False
    hashf = hashfALPHA
    amove = []

    ############################################################################
    # Cheking the time                                                         #
    ############################################################################

    timecheck_counter -= 1
    if timecheck_counter == 0:
        if time() > endtime:
            searching = False
            return [], 0
        timecheck_counter = TIMECHECK_FREQ

    ############################################################################
    # Look up transposition table                                              #
    ############################################################################
    
    table.setHashMove (ply, -1)
    probe = table.probe (board.hash, ply, alpha, beta)
    
    if probe:
        move, score, hashf = probe
        table.setHashMove (ply, move)
        
        if hashf == hashfEXACT:
            return [move], score
        elif hashf == hashfBETA:
            beta = min(score, beta)
        elif hashf == hashfALPHA:
            alpha = score
            
        if alpha >= beta:
            return [move], score
    
    if ldraw.test(board):
        return [], 0
    
    ############################################################################
    # Break itereation if interupted                                           #
    ############################################################################
    
    if not searching:
        last = 1
        return [], evaluateComplete(board, board.color)
    
    ############################################################################
    # Go for quiescent search                                                  #
    ############################################################################
    
    isCheck = board.isChecked()
    
    if depth <= 0:
        if isCheck:
            depth += 1
        else:
            last = 0
            return quiescent(board, alpha, beta, ply)
    
    ############################################################################
    # Find and sort moves                                                      #
    ############################################################################
    
    movesearches += 1
    
    heap = []
    if isCheck:
        for move in genCheckEvasions(board):
            heappush(heap, (-getMoveValue (board, table, ply, move), move))
    else:
        for move in genAllMoves(board):
            heappush(heap, (-getMoveValue (board, table, ply, move), move))
    
    anyMoves = False
    
    ############################################################################
    # Loop moves                                                               #
    ############################################################################
    
    while heap:
        nodes += 1
        
        v, move = heappop(heap)
        
        board.applyMove(move)
        if not isCheck:
            if board.opIsChecked():
                board.popMove()
                continue
        
        anyMoves = True
        
        if foundPv:
            mvs, val = alphaBeta (board, depth-1, -alpha-1, -alpha, ply+1)
            val = -val
            if val > alpha and val < beta:
                mvs, val = alphaBeta (board, depth-1, -beta, -alpha, ply+1)
                val = -val
        else:
            mvs, val = alphaBeta (board, depth-1, -beta, -alpha, ply+1)
            val = -val
        
        board.popMove()
        
        if val > alpha:
            if val >= beta:
                table.record (board.hash, move, beta, hashfBETA, ply)
                # We don't want to use our valuable killer move spaces for
                # captures and promotions, as these are searched early anyways.
                if board.arBoard[move&63] == EMPTY and not move>>12 in \
                        (QUEEN_PROMOTION, ROOK_PROMOTION,
                         BISHOP_PROMOTION, KNIGHT_PROMOTION):
                    table.addKiller (ply, move)
                last = 2
                return [move]+mvs, beta
                
            alpha = val
            amove = [move]+mvs
            hashf = hashfEXACT
            foundPv = True
    
    ############################################################################
    # Return                                                                   #
    ############################################################################
    
    if amove:
        last = 3
        table.record (board, amove[0], alpha, hashf, ply)
        if board.arBoard[amove[0]&63] == EMPTY:
            table.addKiller (ply, amove[0])
        return amove, alpha
        
    if anyMoves:
        last = 4
        return [], alpha

    # If no moves were found, this must be a mate or stalemate
    last = 5
    if isCheck:
        return [], -MATE_VALUE+ply-2
    
    last = 6
    return [], 0

def quiescent (board, alpha, beta, ply):
    
    global nodes
    
    if ldraw.test(board):
        return [], 0
    
    isCheck = board.isChecked()
    
    value = evaluateComplete(board, board.color)
    
    if value >= beta and not isCheck:
        return [], beta
    if value > alpha:
        alpha = value
    
    if isCheck:
        noMove = True
        for move in genCheckEvasions(board):
            noMove = False
            if value >= beta:
                return [], beta
            else:
                break
        if noMove:
            return [], -MATE_VALUE+ply-2
    
    amove = []
    
    heap = []
    for move in genCaptures (board):
        heappush(heap, (-getCaptureValue (board, move), move))
    
    while heap:
        
        nodes += 1
        
        v, move = heappop(heap)
        
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue
        
        mvs, val = quiescent(board, -beta, -alpha, ply+1)
        val = -val
        
        board.popMove()
        
        if val >= beta:
            return [move]+mvs, beta
        
        if val > alpha:
            alpha = val
            amove = [move]+mvs
    
    if amove:
        return amove, alpha
    
    else:
        return [], alpha
