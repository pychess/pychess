from Utils.History import WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO
from Utils.Move import Move
from Utils.Cord import Cord
from Utils.Log import log

def sort (list):
    list.sort()
    return list

def validate (move, history):
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
    
    if willChess(history, move, color):
        log.debug("v chess")
        return False
        
    return True
    
def tryBishop (move, color, history, board):
    if abs(move.cord0.x - move.cord1.x) != abs(move.cord0.y - move.cord1.y):
        log.debug("v b 1" + str((move.cord0.x, move.cord1.x)))
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
            log.debug("v b 2" + str(Cord(x,y)))
            return False
    return True
    
def tryKing (move, color, history, board):
    row = color == "black" and 7 or 0
    if move.cord0.y == row and move.cord1.y == row:
        if move.cord0.x - move.cord1.x == 2:
            if color == "black" and history.castling & BLACK_OOO:
                return True
            elif color == "white" and history.castling & WHITE_OOO:
                return True
        elif move.cord0.x - move.cord1.x == -2:
            if color == "black" and history.castling & BLACK_OO:
                return True
            elif color == "white" and history.castling & WHITE_OO:
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
        board[Cord(move.cord0.x, move.cord0.y+dr)] == None and \
        move.cord0.x == move.cord1.x:
        return True
    return False

def tryRook (move, color, history, board):
    if move.cord0.x != move.cord1.x and move.cord0.y != move.cord1.y:
        log.debug("v r 1 " + str((move.cord0.x, move.cord1.x)))
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
            log.debug("v r 2" + str(Cord(x,y)))
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

def getPiecesPointingAt (history, cord, color=None, sign=None, r=None, c=None):
    if sign:
        print "search", cord, color, sign, r, c
        import sys
        sys.stdout.write(str(history[-1]))
    list = []
    board = history[-1]
    for row in range(len(board)):
        for col in range(len(board[row])):
            piece = board[row][col]
            if piece == None:
                log.debug("f 1 %d %d" % (row, col))
                continue
            if color and piece.color != color:
                log.debug("f 2 %d %d" % (row, col))
                continue
            if sign and piece.sign != sign:
                log.debug("f 3 %d %d" % (row, col))
                continue
            if r and row != r:
                log.debug("f 4 %d %d" % (row, col))
                continue
            if c and col != c:
                log.debug("f 5 %d %d" % (row, col))
                continue
            move = Move (history, (board.getCord(piece), cord))
            if validate (move, history):
                list += [move]
    if sign:
        print list
    return list

def willChess (history, move, color):
    afterhis = history.clone().add(move)
    opcolor = color == "white" and "black" or "white"
    cord = _findKing(afterhis[-1], color)
    if getPiecesPointingAt(afterhis, cord, opcolor):
        return True
    return False

def _findKing (board, color):
    for row in range(len(board)):
        for col in range(len(board[row])):
            cord = Cord (col, row)
            piece = board[cord]
            if piece != None and piece.sign == "k" and piece.color == color:
                return cord

def test():
    from History import History
    history = History()
    print validate(Move(history, ("g2", "g4")), history)
