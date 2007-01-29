"""
    This module is written to do basic chess computing.
    This module can validate a Move or generate a list of possible moves
    It can also be used to find moves for SAN parsing
    and to detect the status of the game
"""

from pychess.Utils.Move import Move, movePool
from pychess.Utils.Cord import Cord
from pychess.System.Log import log
from pychess.Utils.const import *
from time import time

# this ordering cut down alphabeta search time, by searching from the center
range8 = (3, 4, 2, 5, 1, 6, 0, 7)

def validate (move, board, testCheck=True, cancapture=False):
    """ Tests if "move" is a legal move on board "board"
        Will asume the first cord of move is an ally piece
        @param cancapture: Only test if the piece can capture cord1. """
    
    piece = board[move.cord0]
    
    if piece.sign == PAWN:
        if not valiPawn(move, board, cancapture):
            return False
    elif piece.sign == KNIGHT:
        if not valiKnight(move, board, cancapture):
           return False
    elif piece.sign == BISHOP:
        if not valiBishop(move, board, cancapture):
            return False
    elif piece.sign == ROOK:
        if not valiRook(move, board, cancapture):
            return False
    elif piece.sign == QUEEN:
        if not valiQueen(move, board, cancapture):
            return False
    else:
        if not valiKing(move, board, cancapture):
            return False
    
    if testCheck:
        if willCheck(board, move):
            return False
    
    return True

def valiBishop (move, board, cancapture=False):
    """ Validate bishop move """
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

bishopDirections = (1,1),(-1,1),(-1,-1),(1,-1)
def genBishop (cord, board, pureCaptures=False):
    """ Generate bishop moves. Bishop is located at cord """
    for dx, dy in bishopDirections:
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == board.color:
                    break
                else:
                    yield x,y
                    break
            if not pureCaptures:
                yield x,y

def _isclear (board, cols, rows):
    """ Test if cords in cols and rows are empty """
    for row in rows:
        for col in cols:
            if board.data[row][col] != None:
                return False
    return True

moveToCastling = {"e1g1": WHITE_OO, "e1c1": WHITE_OOO,
                  "e8g8": BLACK_OO, "e8c8": BLACK_OOO}
def valiKing (move, board, cancapture=False):
    """ Validate king move """
    
    if not cancapture:
        strmove = str(move)
        if strmove in moveToCastling:
            if not board.castling & moveToCastling[strmove]:
                return False
            
            rows = board.color == BLACK and (7,) or (0,)
            if move.cord0.x < move.cord1.x:
                colsIsClear = [5,6]
                colsPointingAt = [4,5]
                rookx = 7
            else:
                colsIsClear = [1,2,3]
                colsPointingAt = [3,4]
                rookx = 0
        
            if board.data[rows[0]][rookx] == None:
                return False
            
            if not _isclear(board, colsIsClear, rows):
                return False
            
            opcolor = 1 - board.color
            if genMovesPointingAt (board, colsPointingAt, rows, opcolor):
                return False
            
            return True
    
    return abs(move.cord0.x - move.cord1.x) <= 1 and \
           abs(move.cord0.y - move.cord1.y) <= 1

kingPlaces = (1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1),(0,1),(1,1)
def genKing (cord, board, pureCaptures=False):
    """ Generate king moves. King is located at cord """
    for dx, dy in kingPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if board.data[y][x]:
            if board.data[y][x].color != board.color:
                yield x,y
        elif not pureCaptures:
            yield x,y
    
    if pureCaptures: return
    
    if board.color == WHITE:
        if board.castling & WHITE_OO and board.data[0][7] != None:
            if _isclear (board, (5,6), (0,)) and \
               not genMovesPointingAt (board, (4,5), (0,), BLACK):
                yield 6,0
        if board.castling & WHITE_OOO and board.data[0][0] != None:
            if _isclear (board, (1,2,3), (0,)) and \
               not genMovesPointingAt (board, (3,4), (0,), BLACK):
                yield 2,0
    if board.color == BLACK:
        if board.castling & BLACK_OO and board.data[7][7] != None:
            if _isclear (board, (5,6), (7,)) and \
               not genMovesPointingAt (board, (4,5), (7,), WHITE):
                yield 6,7
        if board.castling & BLACK_OOO and board.data[7][0] != None:
            if _isclear (board, (1,2,3), (7,)) and \
               not genMovesPointingAt (board, (3,4), (7,), WHITE):
                yield 2,7

def valiKnight (move, board, cancapture=False):
    """ Validate knight move """
    return (abs(move.cord0.x - move.cord1.x) == 1 and \
            abs(move.cord0.y - move.cord1.y) == 2) or \
           (abs(move.cord0.x - move.cord1.x) == 2 and \
            abs(move.cord0.y - move.cord1.y) == 1)

knightPlaces = (1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2)
def genKnight (cord, board, pureCaptures=False):
    """ Generate knight moves. Knight is located at cord """
    for dx, dy in knightPlaces:
        x, y = cord.x+dx, cord.y+dy
        if not (0 <= x <= 7 and 0 <= y <= 7):
            continue
        if board.data[y][x]:
            if board.data[y][x].color != board.color:
                yield x,y
        elif not pureCaptures:
            yield x,y

def valiPawn (move, board, cancapture=False):
    """ Validate pawn move """
    dr = board.data[move.cord0.y][move.cord0.x].color == WHITE and 1 or -1
    
    #Leaves only 1 and 2 cords difference - ahead
    if not 0 < (move.cord1.y - move.cord0.y)*dr <= 2:
        return False
    
    #Can capture
    if cancapture:
        if move.cord0.y+dr == move.cord1.y and \
                abs(move.cord0.x - move.cord1.x) == 1:
            return True
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
           board[move.cord1].color != board.color:
            return True
            
        #En passant
        if board.enpassant == move.cord1:
            return True
            
    #Handles double move
    row = board.color == WHITE and 1 or 6
    if (move.cord1.y - move.cord0.y)*dr == 2 and \
        move.cord0.y == row and \
        board[move.cord1] == None and \
        board[Cord(move.cord0.x, move.cord0.y+dr)] == None and \
        move.cord0.x == move.cord1.x:
        return True
        
    return False

def genPawn (cord, board, pureCaptures=False):
    """ Generate pawn moves. Pawn is located at cord """
    
    direction = board.color == WHITE and 1 or -1
    x, y = cord.x, cord.y
    
    for side in (1,-1):
        if not 0 <= x+side <= 7: continue
        if board.data[y+direction][x+side] and \
           board.data[y+direction][x+side].color != board.color:
            yield x+side, y+direction
    
    if pureCaptures: return
    
    if not board.data[y+direction][x]:
        yield x, y+direction
        
    row = board.color == WHITE and 1 or 6
    if y == row:
        if not board.data[y+direction*2][x] and \
           not board.data[y+direction][x]:
            yield x, y+direction*2
    
    if board.enpassant and abs(board.enpassant.x - cord.x) == 1:
        if (board.enpassant.y == 5 and board.color == WHITE and cord.y == 4) or \
           (board.enpassant.y == 2 and board.color == BLACK and cord.y == 3) :
            yield board.enpassant.x, board.enpassant.y
     
def valiRook (move, board, cancapture=False):
    """ Validate rook move """
    
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

rookDirections = (1,0),(0,-1),(-1,0),(0,1)
def genRook (cord, board, pureCaptures=False):
    """ Generate rook moves. Rook is located at cord """
    
    for dx, dy in rookDirections:
        x, y = cord.x, cord.y
        while True:
            x += dx
            y += dy
            if not (0 <= x <= 7 and 0 <= y <= 7):
                break
            if board.data[y][x]:
                if board.data[y][x].color == board.color:
                    break
                else:
                    yield x,y
                    break
            if not pureCaptures:
                yield x,y

def valiQueen (move, board, cancapture=False):
    """ Validate queen move """
    
    return valiRook (move, board, cancapture) or \
           valiBishop (move, board, cancapture)

def genQueen (cord, board, pureCaptures=False):
    """ Generate queen moves. Queen is located at cord """
    
    for move in genRook (cord, board, pureCaptures):
        yield move
    for move in genBishop (cord, board, pureCaptures):
        yield move

def findMoves2 (board, testCheck=True, pureCaptures=False):
    """ Generate all possible moves for current player (board.color) """
    
    for y in range8:
        for x in range8:
            piece = board.data[y][x]
            if not piece: continue
            if piece.color != board.color: continue
            cord0 = Cord(x,y)
            
            for move in genLegalMoves(board,cord0,testCheck):
                yield move

def genLegalMoves (board, cord, testCheck):
    """ Generate all legal moves for piece at cord """
    
    piece = board[cord]
    if piece.sign == PAWN:
        generator = genPawn
    elif piece.sign == KNIGHT:
        generator = genKnight
    elif piece.sign == BISHOP:
        generator = genBishop
    elif piece.sign == ROOK:
        generator = genRook
    elif piece.sign == QUEEN:
        generator = genQueen
    else:
        generator = genKing
    
    for xy in generator (cord,board):
        move = movePool.pop(cord, Cord(*xy))
        try:
            if not testCheck or not willCheck(board, move):
                yield move
            else: movePool.add(move)
        except Exception:
            print piece, cord, "\n", board
            raise

def _getLegalMoves (board, cord, testCheck):
    """ Find all legal moves for piece at cord
        returns a list of possible destination cords """
    return [move.cord1 for move in genLegalMoves(board, cord, testCheck)]

def findMoves (board, testCheck=True):
    """ Creates a dict of all legal moves for current player (baord.color)
        Returns a dict of {fromcord:[tocord,tocord...],...} """
    
    moves = {}
    for move in findMoves2(board, testCheck):
        c0, c1 = move.cords
        if c0 in moves:
            moves[c0].append(c1)
        else: moves[c0] = [c1]
    
    return moves

def getMovePointingAt (board, cord, color=None, sign=None, r=None, c=None):
    
    """ Returns a cord containing a piece that can attack the specified cord
        If color, sign, r, or c is not = None, only cords with that
        color / sign / row / column will be returned """
    
    if board.movelist != None:
        for cord0, cord1s in board.movelist.iteritems():
            piece = board[cord0]
            if color != None and piece.color != color: continue
            if sign != None and piece.sign != sign: continue
            if r != None and cord0.y != r: continue
            if c != None and cord0.x != c: continue
            for cord1 in cord1s:
                if cord1 == cord:
                    return cord0
    
    else:
        cords = []
        for y in range8:
            for x in range8:
                if r != None and y != r: continue
                if c != None and x != c: continue
                piece = board.data[y][x]
                if piece == None: continue
                if color != None and piece.color != color: continue
                if sign != None and piece.sign != sign: continue
                
                for move in genLegalMoves(board, Cord(x,y), False):
                    if move.cord1 == cord:
                        cords.append(move.cord0)
        
        if len(cords) == 1:
            return cords[0]
        
        # If there are more than one piece that can be moved to the cord,
        # We have to test if one of them moving will cause check.
        elif len(cords) > 1:
            for cord0 in cords:
                move = movePool.pop(cord0, cord)
                if not willCheck(board,move):
                    return cord0
                else: movePool.add(move)
            
        else: return None

def genMovesPointingAt (board, cols, rows, color, testCheck=False):
    
    """ Returns a move that legaly attack a cord with the specified color
        in one of the specified columns or rows """
    
    for y in range8:
        for x in range8:
            piece = board.data[y][x]
            if piece == None: continue
            if piece.color != color: continue
            cord0 = Cord(x,y)
            for r in rows:
                for c in cols:
                    move = movePool.pop(cord0, Cord(c,r))
                    if validate (move, board, testCheck, cancapture=True):
                        return move
                    movePool.add(move)

def willCheck (board, move):
    """ Returns True if the move will cause the player
        making the move to be in check """
    board2 = board.move(move)
    return isCheck(board2, board.color)

from pychess.System.LimitedDict import LimitedDict
checkDic = LimitedDict(5000)

def isCheck (board, who):  
    """ Returns True if "who" is in check in the specified possition """
    
    # TODO: Does this make a difference? I Guess not.
    #if board in checkDic:
    #    r = checkDic[board][who]
    #    if r != None:
    #        return r
    
    cord = _findKing(board, who)
    if genMovesPointingAt(board, (cord.x,), (cord.y,), 1-who):
        r = True
    else: r = False
    
    #if not board in checkDic:
    #    checkDic[board] = [None,None]
    #checkDic[board][who] = r
    
    return r

def _findKing (board, color):
    """ Returns the cord of the king of the specified color """
    for x in range8:
        for y in range8:
            piece = board.data[y][x]
            if piece and piece.sign == KING and piece.color == color:
                return Cord(x,y)
    raise Exception, "Could not find %s king on board ?!\n%s" % \
            (reprColor[color], repr(board))

def status (history):
    """ Returns a tuple of (the current status of the game, a comment of the reason)
        Status can be one of RUNNING, DRAW, WHITEWON or BLACKWON.
        Comment can be any from pychess.Utils.const or None, if status is RUNNING """
    
    board = history[-1]
    pieceCount = {}
    for x in range8:
        for y in range8:
            piece = board.data[y][x]
            if piece:
                if not piece.sign in pieceCount:
                    pieceCount[piece.sign] = [x % 2 + y % 2 == 1]
                else: pieceCount[piece.sign].append(x % 2 + y % 2 == 1)
    copieces = sum([len(v) for v in pieceCount.values()])
    
    if copieces == 2:
        # 1. king versus king
        return DRAW, DRAW_INSUFFICIENT
    elif copieces == 3 and BISHOP in pieceCount and len(pieceCount[BISHOP]) == 1:
        # 2. king and bishop versus king
        return DRAW, DRAW_INSUFFICIENT
    elif copieces == 3 and KNIGHT in pieceCount and len(pieceCount[KNIGHT]) == 1:
        # 3. king and knight against king
        return DRAW, DRAW_INSUFFICIENT
    elif copieces == 4 and BISHOP in pieceCount and len(pieceCount[BISHOP]) == 2 and \
            pieceCount[BISHOP][0] and pieceCount[BISHOP][1]:
        # 4. king and bishop versus king and bishop with the bishops on the same color.
        return DRAW, DRAW_INSUFFICIENT
    
    if len(history) >= 9 and history[-1] == history[-5] == history[-9]:
        return DRAW, DRAW_REPITITION
    
    board = history[-1]
    
    if board.fifty >= 100:
        return DRAW, DRAW_50MOVES
    
    if len(board.movelist) == 0:
        if isCheck(board, board.color):
            if board.color == WHITE:
                return BLACKWON, WON_MATE
            else: return WHITEWON, WON_MATE
            
        return DRAW, DRAW_STALEMATE
        
    return RUNNING, None
