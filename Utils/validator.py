from Utils.History import WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO
from Utils.Move import Move
from Utils.Cord import Cord
from Utils.Log import log
from time import time

def sort (list):
    list.sort()
    return list

call = 0
def validate (move, history, testCheck=True):
    #global call
    #call += 1
    #print "CALL", call, round(call/float(9*4),2)
    """Will asume the first cord is an ally piece"""
    
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
        if willChess(history, move, color):
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

def tryKing (move, color, history, board):
    #TODO: not allowed to move, if checked
    if color == "white":
        if str(move) == "e1g1" and history.castling & WHITE_OO and \
            _isclear(board, [0], [5,6]): return True
        if str(move) == "e1c1" and history.castling & WHITE_OOO and \
            _isclear(board, [0], [1,2,3]): return True
    elif color == "black":
        if str(move) == "e8g8" and history.castling & BLACK_OO and \
            _isclear(board, [7], [5,6]): return True
        if str(move) == "e8c8" and history.castling & BLACK_OOO and \
            _isclear(board, [7], [1,2,3]): return True

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

def getLegalMoves (history, cord):
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
                if validate (move, history):
                    cords += [cord1]
    return cords

def findMoves (history, color):
    from time import time
    t = time()
    moves = {}
    board = history[-1]
    for row in range(len(board)):
        for col in range(len(board[row])):
            piece = board[row][col]
            if not piece: continue
            if piece.color != color: continue
            cord0 = Cord(col, row)
            for cord1 in getLegalMoves (history, cord0):
                if cord0 in moves:
                    moves[cord0] += [cord1]
                else: moves[cord0] = [cord1]
    log.log("Found %d moves in %.3f seconds" % (sum([len(v) for v in moves.values()]), time()-t))
    return moves

def getPiecesPointingAt (history, cord, color=None, sign=None, r=None, c=None, testCheck=True):
    if sign:
        print "search", cord, color, sign, r, c
        import sys
        sys.stdout.write(str(history[-1]))
    list = []
    board = history[-1]
    for row in range(len(board)):
        for col in range(len(board[row])):
            piece = board[row][col]
            if piece == None: continue
            if color and piece.color != color: continue
            if sign and piece.sign != sign: continue
            if r and row != r: continue
            if c and col != c: continue
            move = Move (history, (board.getCord(piece), cord))
            if validate (move, history, testCheck):
                if sign:
                    print "Found move:", move
                return move

def willChess (history, move, color):
    history = history.clone()
    history.add(move)
    return _isChess(history, color)

def _isChess (history, color):
    opcolor = color == "white" and "black" or "white"
    cord = _findKing(history[-1], color)
    if getPiecesPointingAt(history, cord, opcolor, testCheck=False):
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
def status (history, possibleMoves = None):
    #Should -2 and -4 also be the same?
    if len(history) >= 5 and history[-1] == history[-3] == history[-5]:
        log.log("Game is stale as %s == %s == %s" % (history[-1], history[-3], history[-5]))
        return STALE
    if history.fifty >= 100:
        log.log("Game is stale by the 50 moves rule")
        return STALE
    color = len(history) % 2 == 0 and "black" or "white"
    if not possibleMoves:
        possibleMoves = findMoves (history, color)
    if len(possibleMoves) == 0 and _isChess(history, color):
        return MATE
    elif len(possibleMoves) == 0:
        return STALE
    return FINE
