from Utils.History import WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO
from Utils.History import hisPool
from Utils.Move import Move, movePool
from Utils.Cord import Cord
from System.Log import log
from time import time


call0 = 0
call1 = 0
def validate (move, history, testCheck=True):
    """Will asume the first cord is an ally piece"""
    
    #global call0, call1
    #if testCheck:
    #    call0 += 1
    #else: call1 += 1
    #print "CALL", call0, call1
    
    board = history[-1]
    color = board[move.cord0].color
    
    if move.cord0 == move.cord1:
        return False
    if board[move.cord1] != None and board[move.cord1].color == color:
        return False
    
    method = "try" + board[move.cord0].name
    if not globals()[method](move, color, history, board):
        return False
    
    if testCheck:
        if willCheck(history, move):
            return False
        
    return True
    
def tryBishop (move, color, history, board):
    if abs(move.cord0.x - move.cord1.x) != abs(move.cord0.y - move.cord1.y):
        return False
    dx = move.cord1.x > move.cord0.x and 1 or -1
    dy = move.cord1.y > move.cord0.y and 1 or -1
    x = move.cord0.x
    y = move.cord0.y
    for i in range(8):
        x += dx; y += dy
        if x == move.cord1.x or y == move.cord0.y:
            break
        if board[Cord(x,y)] != None:
            return False
    return True

def _isclear (board, rows, cols):
    for row in rows:
        for col in cols:
            if board[row][col] != None:
                return False
    return True

moveToCastling = {"e1g1": WHITE_OO, "e1c1": WHITE_OOO,
                  "e8g8": BLACK_OO, "e8c8": BLACK_OOO}
def tryKing (move, color, history, board):

    strmove = str(move)
    if strmove in moveToCastling:
        if not history.castling & moveToCastling[strmove]:
            return False
        
        opcolor = color == "white" and "black" or "white"
        rows = color == "black" and (7,) or (0,)
        if move.cord0.x < move.cord1.x:
            cols = [5,6]
        else: cols = [1,2,3]
        if not _isclear(board, rows, cols):
            return False
        
        cols.append(4)
        opcolor = history.curCol() == "white" and "black" or "white"
        if genMovesPointingAt (history, cols, rows, opcolor):
            return False
        
        return True

    return abs(move.cord0.x - move.cord1.x) <= 1 and \
           abs(move.cord0.y - move.cord1.y) <= 1

def tryKnight (move, color, history, board):
    return (abs(move.cord0.x - move.cord1.x) == 1 and \
            abs(move.cord0.y - move.cord1.y) == 2) or \
           (abs(move.cord0.x - move.cord1.x) == 2 and \
            abs(move.cord0.y - move.cord1.y) == 1)

def tryPawn (move, color, history, board):
    dr = color == "white" and 1 or -1
    #Leaves only 1 and 2 cords difference - ahead
    if not 0 < (move.cord1.y - move.cord0.y)*dr <= 2:
        return False
    #Handles normal move
    if (move.cord1.y - move.cord0.y)*dr == 1 and \
        move.cord0.x == move.cord1.x and \
        board[move.cord1] == None:
        return True
    #Handles capturing
    if (move.cord1.y - move.cord0.y)*dr == 1 and \
        abs(move.cord0.x - move.cord1.x) == 1:
        #Normal
        if board[move.cord1] != None and \
           board[move.cord1].color != color:
            return True
        #En passant
        if len(history) < 2 or move.cord1.y in [0,7]:
            return False
        newside = board[Cord(move.cord1.x, move.cord0.y)]
        newdown = board[Cord(move.cord1.x, move.cord1.y+dr)]
        oldside = history[-2][Cord(move.cord1.x, move.cord0.y)]
        olddown = history[-2][Cord(move.cord1.x, move.cord1.y+dr)]
        if newside != None and newside.sign == "p" and newside.color != color and \
           olddown != None and olddown.sign == "p" and \
           newdown == None and oldside == None:
            return True
    #Handles double move
    row = color == "white" and 1 or 6
    if (move.cord1.y - move.cord0.y)*dr == 2 and \
        move.cord0.y == row and \
        board[move.cord1] == None and \
        board[Cord(move.cord0.x, move.cord0.y+dr)] == None and \
        move.cord0.x == move.cord1.x:
        return True
    return False

def tryRook (move, color, history, board):
    if move.cord0.x != move.cord1.x and move.cord0.y != move.cord1.y:
        return False
    
    if move.cord1.x > move.cord0.x:
        dx = 1; dy = 0
    elif move.cord1.x < move.cord0.x:
        dx = -1; dy = 0
    elif move.cord1.y > move.cord0.y:
        dx = 0; dy = 1
    elif move.cord1.y < move.cord0.y:
        dx = 0; dy = -1
    x = move.cord0.x
    y = move.cord0.y
    
    for i in range(8):
        x += dx; y += dy
        if x == move.cord1.x and y == move.cord1.y:
            break
        if board[Cord(x,y)] != None:
            return False
    return True

def tryQueen (move, color, history, board):
    return tryRook (move, color, history, board) or \
           tryBishop (move, color, history, board)

def _getLegalMoves (history, cord, testCheck):
    cords = []
    board = history[-1]
    for row in range(len(board)):
        for col in range(len(board[row])):
            if row == cord.y and col == cord.x: continue
            if abs(row - cord.y) <= 2 or abs(col - cord.x) <= 2 or \
                    cord.y == row or cord.x == col or \
                    abs(cord.y - row) == abs(cord.x - col):
                cord1 = Cord(col, row)
                move = Move(history, (cord, cord1))
                if validate (move, history, testCheck):
                    cords.append(cord1)
    return cords

def findMoves (history):
    t = time()
    moves = {}
    board = history[-1]
    color = history.curCol()
    for row in range(len(board)):
        for col in range(len(board[row])):
            piece = board[row][col]
            if not piece: continue
            if piece.color != color: continue
            cord0 = Cord(col, row)
            for cord1 in _getLegalMoves (history, cord0, True):
                if cord0 in moves:
                    moves[cord0].append(cord1)
                else: moves[cord0] = [cord1]
    log.log("Found %d moves in %.3f seconds" % (sum([len(v) for v in moves.values()]), time()-t))
    #log.debug(str(moves))
    return moves

def getMovePointingAt (history, cord, color=None, sign=None, r=None, c=None):
    #if sign:
    #    print "search", cord, color, sign, r, c
    #    print "movelist", history.movelist[-1]
    #    import sys
    #    sys.stdout.write(str(history[-1]))
    board = history[-1]
    
    for cord0, cord1s in history.movelist[-1].iteritems():
        piece = board[cord0]
        if color and piece.color != color: continue
        if sign and piece.sign != sign: continue
        if r and cord0.y != r: continue
        if c and cord0.x != c: continue
        for cord1 in cord1s:
            if cord1 == cord:
                #if sign:
                #    print "Found move:", cord0, cord1
                return cord0

def genMovesPointingAt (history, cols, rows, color, testCheck=False):
    board = history[-1]
    
    for row in range(len(board)):
        for col in range(len(board[row])):
            piece = board[row][col]
            if piece == None: continue
            if piece.color != color: continue
            cord0 = Cord(col,row)
            for r in rows:
                for c in cols:
                    move = Move (history, (cord0, Cord(c,r)))
                    if validate (move, history, testCheck):
                        return move

def willCheck (history, move):
    history = history.clone()
    history.add(move, mvlist=False)
    check = isCheck(history, history.curCol() == "white" and "black" or "white")
    hisPool.add(history)
    return check

def isCheck (history, color):
    opcolor = color == "white" and "black" or "white"
    cord = _findKing(history[-1], color)
    if genMovesPointingAt(history, (cord.x,), (cord.y,), opcolor):
        return True
    return False

def _findKing (board, color):
    for row in range(len(board)):
        for col in range(len(board[row])):
            cord = Cord (col, row)
            piece = board[cord]
            if piece != None and piece.sign == "k" and piece.color == color:
                return cord

FINE, STALE, MATE = range(3)
def status (history):
    if len(history) >= 9 and history[-1] == history[-5] == history[-9]:
        log.log("Game is stale as %s == %s == %s" % (history[-1], history[-5], history[-9]))
        return STALE
    if history.fifty >= 100:
        log.log("Game is stale by the 50 moves rule")
        return STALE
    if len(history.movelist[-1]) == 0:
        if isCheck(history, history.curCol()):
            return MATE
        return STALE
    return FINE
