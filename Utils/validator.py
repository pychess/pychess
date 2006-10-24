from Utils.History import WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO
from Utils.History import hisPool
from Utils.Move import Move, movePool
from Utils.Cord import Cord
from System.Log import log
from time import time

range8 = range(8)

#functions = None

def validate (move, history, testCheck=True):
    """Will asume the first cord is an ally piece"""
    
    board = history[-1]
    color = board[move.cord0].color
    
    if move.cord0 == move.cord1:
        return False
    if board[move.cord1] != None and board[move.cord1].color == color:
        return False
    
    method = board[move.cord0].name
    #global functions
    #if not functions: functions = globals()
    if not functions[method](move, color, history, board):
        return False
    
    if testCheck:
        if willCheck(history, move):
            return False
        
    return True
    
def Bishop (move, color, history, board):
    if abs(move.cord0.x - move.cord1.x) != abs(move.cord0.y - move.cord1.y):
        return False
    dx = move.cord1.x > move.cord0.x and 1 or -1
    dy = move.cord1.y > move.cord0.y and 1 or -1
    x = move.cord0.x
    y = move.cord0.y
    for i in range8:
        x += dx; y += dy
        if x == move.cord1.x or y == move.cord0.y:
            break
        if board.data[y][x] != None:
            return False
    return True

def genBishop (cord, history):
    board = history[-1]
    for dx, dy in (1,1),(-1,1),(-1,-1),(1,-1):
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == history.curCol():
                    break
                else:
                    yield x,y
                    break
            yield x,y

def _isclear (board, cols, rows):
    for row in rows:
        for col in cols:
            if board.data[row][col] != None:
                return False
    return True

moveToCastling = {"e1g1": WHITE_OO, "e1c1": WHITE_OOO,
                  "e8g8": BLACK_OO, "e8c8": BLACK_OOO}
def King (move, color, history, board):

    strmove = str(move)
    if strmove in moveToCastling:
        if not history.castling & moveToCastling[strmove]:
            return False
        
        opcolor = color == "white" and "black" or "white"
        rows = color == "black" and (7,) or (0,)
        if move.cord0.x < move.cord1.x:
            cols = [4,5,6]
        else: cols = [2,3,4]
        if not _isclear(board, cols, rows):
            return False
        
        cols.append(4)
        opcolor = history.curCol() == "white" and "black" or "white"
        if genMovesPointingAt (history, cols, rows, opcolor):
            return False
        
        return True

    return abs(move.cord0.x - move.cord1.x) <= 1 and \
           abs(move.cord0.y - move.cord1.y) <= 1

kingPlaces = (1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1),(0,1),(1,1)
def genKing (cord, history):
    board = history[-1]
    for dx, dy in kingPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if not board.data[y][x] or board.data[y][x].color != history.curCol():
            yield x,y
            
    if history.curCol() == "white":
        if history.castling & WHITE_OO:
            if _isclear (board, (0,), (5,6)) and \
               not genMovesPointingAt (history, (4,5,6), (0,), "black"):
                yield 6,0
        if history.castling & WHITE_OOO:
            if _isclear (board, (0,), (1,2,3)) and \
               not genMovesPointingAt (history, (2,3,4), (0,), "black"):
                yield 2,0
    if history.curCol() == "black":
        if history.castling & BLACK_OO:
            if _isclear (board, (7,), (5,6)) and \
               not genMovesPointingAt (history, (4,5,6), (7,), "white"):
                yield 6,7
        if history.castling & BLACK_OOO:
            if _isclear (board, (7,), (1,2,3)) and \
               not genMovesPointingAt (history, (2,3,4), (7,), "white"):
                yield 2,7

def Knight (move, color, history, board):
    return (abs(move.cord0.x - move.cord1.x) == 1 and \
            abs(move.cord0.y - move.cord1.y) == 2) or \
           (abs(move.cord0.x - move.cord1.x) == 2 and \
            abs(move.cord0.y - move.cord1.y) == 1)

knightPlaces = (1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)
def genKnight (cord, history):
    board = history[-1]
    for dx, dy in knightPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if not board.data[y][x] or board.data[y][x].color != history.curCol():
            yield x,y

def Pawn (move, color, history, board):
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

def genPawn (cord, history):
    board = history[-1]

    direction = history.curCol() == "white" and 1 or -1
    x, y = cord.x, cord.y
    if not board.data[y+direction][x]:
        yield x, y+direction
        
    row = history.curCol() == "white" and 1 or 6
    if y == row:
        if not board.data[y+direction*2][x] and \
           not board.data[y+direction][x]:
            yield x, y+direction*2
    
    for side in (1,-1):
        if not 0 <= x+side <= 7:
            continue
        if board.data[y+direction][x+side] and \
           board.data[y+direction][x+side].color != history.curCol():
            yield x+side, y+direction
        elif len(history) >= 2:
            newside = board.data[y][x+side]
            newdown = board.data[y+direction][x+side]
            oldside = history[-2].data[y][x+side]
            olddown = history[-2].data[y+direction][x+side]
            if newside != None and newside.sign == "p" and newside.color != history.curCol() and \
               olddown != None and olddown.sign == "p" and \
               newdown == None and oldside == None:
                yield x+side, y+direction
                
def Rook (move, color, history, board):
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
    
    for i in range8:
        x += dx; y += dy
        if x == move.cord1.x and y == move.cord1.y:
            break
        if board.data[y][x] != None:
            return False
    return True

def genRook (cord, history):
    board = history[-1]
    for dx, dy in (1,0),(0,-1),(-1,0),(0,1):
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == history.curCol():
                    break
                else:
                    yield x,y
                    break
            yield x,y

def Queen (move, color, history, board):
    return Rook (move, color, history, board) or \
           Bishop (move, color, history, board)

def genQueen (cord, history):
    for move in genRook (cord,history):
        yield move
    for move in genBishop (cord,history):
        yield move

functions = {"Bishop":Bishop,"King":King,"Queen":Queen,"Rook":Rook,"Pawn":Pawn,"Knight":Knight}

sign2gen = {"k":genKing, "q":genQueen, "r":genRook, "b":genBishop, "n":genKnight, "p":genPawn}
def findMoves2 (history, testCheck=True):
    for y, row in enumerate(history[-1].data):
        for x, piece in enumerate(row):
            if not piece: continue
            if piece.color != history.curCol(): continue
            cord0 = Cord(x,y)
            for xy in sign2gen[piece.sign](cord0,history):
                move = movePool.pop(history, cord0, Cord(*xy))
                if not testCheck or not willCheck(history, move):
                    yield move
                else: movePool.add(move)

def _getLegalMoves (history, cord, testCheck):
    cords = []
    for row in range8:
        for col in range8:
            if row == cord.y and col == cord.x: continue
            if abs(row - cord.y) <= 2 or abs(col - cord.x) <= 2 or \
                    cord.y == row or cord.x == col or \
                    abs(cord.y - row) == abs(cord.x - col):
                cord1 = Cord(col, row)
                move = movePool.pop(history, cord, cord1)
                if validate (move, history, testCheck):
                    cords.append(cord1)
                movePool.add(move)
    return cords

def findMoves (history):
    #t = time()
    
    moves = {}
    for move in findMoves2(history, True):
        c0, c1 = move.cords
        if c0 in moves:
            moves[c0].append(c1)
        else: moves[c0] = [c1]
    
    #board = history[-1]
    #color = history.curCol()
    #for y, row in enumerate(board.data):
    #    for x, piece in enumerate(row):
    #        if not piece: continue
    #        if piece.color != color: continue
    #        cord0 = Cord(x, y)
    #        for cord1 in _getLegalMoves (history, cord0, True):
    #            if cord0 in moves:
    #                moves[cord0].append(cord1)
    #            else: moves[cord0] = [cord1]
                
    #mvcount = sum([len(v) for v in moves.values()])
    #log.log("Found %d moves in %.3f seconds\n" % (mvcount, time()-t))
    #log.debug(str(moves))
    
    return moves

def getMovePointingAt (history, cord, color=None, sign=None, r=None, c=None):
    #if sign:
    #    print "search", cord, color, sign, r, c
    #    print "movelist", history.movelist
    #    import sys
    #    sys.stdout.write(str(history[-1]))
    board = history[-1]
    
    if history.movelist[-1] != None:
    
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
    
    else:
        cords = []
        for y, row in enumerate(board.data):
            for x, piece in enumerate(row):
                if piece == None: continue
                if color and piece.color != color: continue
                if sign and piece.sign != sign: continue
                if r and y != r: continue
                if c and x != c: continue
                cord1 = Cord(x,y)
                moves = _getLegalMoves(history,cord1,False)
                if cord in moves:
                    cords.append(cord1)
        
        if len(cords) == 1:
            return cords[0]
        
        elif len(cords) > 1:
            for cord1 in cords:
                moves = _getLegalMoves(history,cord1,True)
                if cord in moves:
                    return cord1
            
        else: return None

def genMovesPointingAt (history, cols, rows, color, testCheck=False):
    board = history[-1]
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if piece == None: continue
            if piece.color != color: continue
            cord0 = Cord(x,y)
            for r in rows:
                for c in cols:
                    move = movePool.pop(history, cord0, Cord(c,r))
                    if validate (move, history, testCheck):
                        return move
                    else: movePool.add(move)

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
    for x in range8:
        for y in range8:
            piece = board.data[y][x]
            if piece and piece.sign == "k" and piece.color == color:
                return Cord(x,y)

FINE, DRAW, WHITEWON, BLACKWON = range(4)
DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, WON_RESIGN, WON_CALLFLAG, WON_MATE = range(7)

def status (history):

    if len(history) >= 9 and history[-1] == history[-5] == history[-9]:
        return DRAW, DRAW_REPITITION
        
    if history.fifty >= 100:
        return DRAW, DRAW_50MOVES
        
    if len(history.movelist[-1]) == 0:
    
        if isCheck(history, history.curCol()):
            if history.curCol() == "white":
                return BLACKWON, WON_MATE
            else: return WHITEWON, WON_MATE
            
        return DRAW, DRAW_STALEMATE
        
    return FINE, None
