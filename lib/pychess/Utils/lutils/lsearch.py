
from lmovegen import genAllMoves, genCheckEvasions, genCaptures
from pychess.Utils.const import *
from leval import evaluateComplete
from lsort import sortCaptures, sortMoves
from lmove import toSAN
from TranspositionTable import TranspositionTable

from sys import maxint

table = TranspositionTable(5000)
searching = True
movesearches = 0
nodes = 0
last = 0

def alphaBeta (board, depth, alpha=-maxint, beta=maxint, ply=0):
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
    
    global last, searching, nodes, movesearches, table
    foundPv = False
    hashf = hashfALPHA
    amove = []
    
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
    
    ############################################################################
    # Go for quiescent search                                                  #
    ############################################################################
    
    if depth <= 0:
        last = 0
        return quiescent(board, alpha, beta)
    
    ############################################################################
    # Break itereation if interupted                                           #
    ############################################################################
    
    if not searching:
        last = 1
        return [], evaluateComplete(board, board.color)
    
    ############################################################################
    # Find and sort moves                                                      #
    ############################################################################
    
    movesearches += 1
    
    if board.isChecked():
        moves = [m for m in genCheckEvasions(board)]
    else: moves = sortMoves(board, table, ply, [m for m in genAllMoves(board)])
    
    ############################################################################
    # Loop moves                                                               #
    ############################################################################
    
    for move in moves:
        nodes += 1
        
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue
        
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
                table.record (board.hash, move, beta, hashfBETA)
                if board.arBoard[move&63] == EMPTY:
                    table.addKiller (ply, move)
                last = 3
                return [move]+mvs, beta
                
            alpha = val
            amove = [move]+mvs
            hashf = hashfEXACT
            foundPv = True
    
    ############################################################################
    # Return                                                                   #
    ############################################################################
    
    if amove:
        last = 4
        table.record (board, amove[0], alpha, hashf)
        if board.arBoard[amove[0]&63] == EMPTY:
            table.addKiller (ply, amove[0])
        return amove, alpha
        
    elif moves:
        last = 6
        return [], alpha

    # If no moves were found, this must be a mate or stalemate
    last = 5
    if board.isChecked():
        return [], -maxint
    
    return [], 0

def quiescent (board, alpha, beta):
    
    value = evaluateComplete(board, board.color)
    
    if value >= beta:
        return [], beta
    if value > alpha:
        alpha = value
    
    amove = []
    
    captures = sortCaptures(board, [cap for cap in genCaptures (board)])
    
    for move in captures:
        
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue
        
        mvs, val = quiescent(board, -beta, -alpha)
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
