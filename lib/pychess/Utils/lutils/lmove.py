from ldata import *
from LBoard import LBoard
from validator import validateMove

def RANK (cord): return cord >> 3
def FILE (cord): return cord & 7

def TCORD (move): return move & 63
def FCORD (move): return move >> 6 & 63
def FLAG (move): return move >> 12

def PROMOTE_PIECE (flag): return flag -2
def FLAG_PIECE (piece): return piece +2

################################################################################
#   The format of a move is as follows - from left:                            #
#   4 bits:  Descriping the type of the move                                   #
#   6 bits:  cord to move from                                                 #
#   6 bits:  cord to move to                                                   #
################################################################################

shiftedFromCords = []
for i in range(64):
    shiftedFromCords.append(i << 6)

shiftedFlags = []
for i in NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT, \
            KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION:
    shiftedFlags.append(i << 12)

def newMove (fromcord, tocord, flag=NORMAL_MOVE):
    return shiftedFlags[flag] + shiftedFromCords[fromcord] + tocord

class ParsingError (Exception): pass

################################################################################
# parseAny                                                                     #
################################################################################

def parseAny (board, algnot):
    type = determineAlgebraicNotation (algnot)
    if type == SAN:
        return parseSAN (board, algnot)
    if type == AN:
        return parseAN (board, algnot)
    if type == LAN:
        return parseLAN (board, algnot)
    return parseFAN (board, algnot)

def determineAlgebraicNotation (algnot):
    
    upnot = algnot.upper()
    
    if upnot in ("O-O-O", "O-O"):
        return SAN
    
    if "-" in algnot:
        return LAN
    
    if (len(algnot) == 4 or (len(algnot) == 5 and upnot[4] in reprSign)) and \
            algnot[:2] in cordDic and algnot[2:4] in cordDic:
        return AN
    
    if algnot[0] in FAN_PIECES[WHITE] or algnot[0] in FAN_PIECES[BLACK]:
        return FAN
    
    return SAN

################################################################################
# listToSan                                                                    #
################################################################################

def listToSan (board, moves):
    sanmoves = []
    
    board.lock.acquire()
    for move in moves:
        san = toSAN (board, move)
        sanmoves.append(san)
        board.applyMove(move)
        
    for move in moves:
        board.popMove()
    board.lock.release()
    
    return sanmoves

################################################################################
# listToMoves                                                                  #
################################################################################

def listToMoves (board, movstrs, type=None, testvalidate=False):
    moves = []
    
    board.lock.acquire()
    for mstr in movstrs:
        try:
            if type == None:
                move = parseAny (board, mstr)
            elif type == SAN:
                move = parseSAN (board, mstr)
            elif type == AN:
                move = parseAN (board, mstr)
            elif type == LAN:
                move = parseLAN (board, mstr)
        except ParsingError:
            # We expect a ParsingError to be raised when parsing "old" lines
            # from analyzing engines, which haven't yet noticed their new tasks
            break
        
        if testvalidate:
            if not validateMove (board, move):
                break
        
        moves.append(move)
        board.applyMove(move)
        
    for move in moves:
        board.popMove()
    board.lock.release()
    
    return moves

################################################################################
# toSan                                                                        #
################################################################################

def toSAN (board, move):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The board should be prior to the move """
    
    # Has to be importet at calltime, as lmovegen imports lmove
    from lmovegen import genAllMoves
    
    flag = move >> 12
    
    if flag == KING_CASTLE:
        return "O-O"
    elif flag == QUEEN_CASTLE:
        return "O-O-O"
    
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    fpiece = board.arBoard[fcord]
    tpiece = board.arBoard[tcord]
    
    part0 = ""
    part1 = ""
    
    if fpiece != PAWN:
        part0 += reprSign[fpiece]
    
    part1 = reprCord[tcord]
    
    if not fpiece in (PAWN, KING):
        xs = []
        ys = []
        
        board.lock.acquire()
        for altmove in genAllMoves(board):
            mfcord = FCORD(altmove)
            if board.arBoard[mfcord] == fpiece and \
                    mfcord != fcord and \
                    TCORD(altmove) == tcord:
                board.applyMove(altmove)
                if not board.opIsChecked():
                    xs.append(FILE(mfcord))
                    ys.append(RANK(mfcord))
                board.popMove()
        board.lock.release()
        
        x = FILE(fcord)
        y = RANK(fcord)
        
        if ys or xs:
            if y in ys and not x in xs:
                # If we share rank with another piece, but not file
                part0 += reprFile[x]
            elif x in xs and not y in ys:
                # If we share file with another piece, but not rank
                part0 += reprRank[y]
            elif x in xs and y in ys:
                # If we share both file and rank with other pieces
                part0 += reprFile[x] + reprRank[y]
            else:
                # If we doesn't share anything, it is standard to put file
                part0 += reprFile[x]
    
    if tpiece != EMPTY or flag == ENPASSANT:
        part1 = "x" + part1
        if fpiece == PAWN:
            part0 += reprFile[FILE(fcord)]
    
    notat = part0 + part1
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                BISHOP_PROMOTION, KNIGHT_PROMOTION):
        notat += "="+reprSign[PROMOTE_PIECE(flag)]
    
    board.lock.acquire()
    board.applyMove(move)
    if board.isChecked():
        for altmove in genAllMoves (board):
            board.applyMove(altmove)
            if board.opIsChecked():
                board.popMove()
                continue
            board.popMove()
            notat += "+"
            break
        else:
            notat += "#"
    board.popMove()
    board.lock.release()
    
    return notat

################################################################################
# parseSan                                                                     #
################################################################################

def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    
    notat = san
    color = board.color
    
    if notat[-1] in ("+", "#"):
        notat = notat[:-1]
    
    flag = NORMAL_MOVE
    
    # If last char is a piece char, we assue it the promote char
    c = notat[-1].lower()
    if c in chr2Sign:
        flag = chr2Sign[c] + 2
        if notat[-2] == "=":
            notat = notat[:-2]
        else: notat = notat[:-1]
    
    notat = notat.replace("0","O").replace("o","O")
    if notat.startswith("O-O"):
        if color == WHITE:
            fcord = E1
            if notat == "O-O":
                flag = KING_CASTLE
                tcord = G1
            else:
                flag = QUEEN_CASTLE
                tcord = C1
        else:
            fcord = E8
            if notat == "O-O":
                flag = KING_CASTLE
                tcord = G8
            else:
                flag = QUEEN_CASTLE
                tcord = C8
        
        return newMove (fcord, tcord, flag)
    
    if notat[0] in ("Q", "R", "B", "K", "N"):
        piece = chr2Sign[notat[0].lower()]
        notat = notat[1:]
    else:
        piece = PAWN
    
    if "x" in notat:
        notat, tcord = notat.split("x")
        tcord = cordDic[tcord]
        if piece == PAWN:
            # If a pawn is attacking an empty cord, we assue it an enpassant
            if board.arBoard[tcord] == EMPTY:
                flag = ENPASSANT
    else:
        tcord = cordDic[notat[-2:]]
        notat = notat[:-2]
    
    # If there is any extra location info, like in the move Bexd1 or Nh3f4 we
    # want to know
    frank = None
    ffile = None
    if notat and notat[0] in reprRank:
        frank = int(notat[0])-1
        notat = notat[1:]
    if notat and notat[0] and notat in reprFile:
        ffile = ord(notat) - ord("a")
        notat = notat[1:]
    if notat and notat[0] in reprRank:
        frank = int(notat[0])-1
        notat = notat[1:]
    
    # We find all pieces who could have done it. (If san was legal, there should
    # never be more than one)
    from lmovegen import genAllMoves
    moves = [m for m in genAllMoves(board)]
    for move in moves:
        if TCORD(move) != tcord:
            continue
        f = FCORD(move)
        if board.arBoard[f] != piece:
            continue
        if frank != None and frank != RANK(f):
            continue
        if ffile != None and ffile != FILE(f):
            continue
        if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                    BISHOP_PROMOTION, KNIGHT_PROMOTION) and FLAG(move) != flag:
            continue
        
        board.lock.acquire()
        board.applyMove(move)
        if board.opIsChecked():
            board.popMove()
            continue
        board.popMove()
        board.lock.release()
        
        return move
    
    errstring = "Bad SAN move '%s'." % san
    errstring += " No piece is able to move to %s." % reprCord[tcord]
    errstring += " %s %s %s %s " % (ffile, frank, reprPiece[piece], flag)
    
    # Printing the moves seams to sometimes fuck the board up, as it applies a
    # lot of illegal moves. At least we better make a clone.
    board2 = LBoard()
    board2.applyFen (board.asFen())
    
    try:
        errstring += " available moves: %s" % " ".join(listToSan(board2, moves))
    except Exception:
        # If even the error tracing moves can't be parsed, we really can't do
        # any more
        pass
    errstring += board.asFen()
    
    raise ParsingError, errstring
    
################################################################################
# toLan                                                                        #
################################################################################

def toLAN (board, move):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        board should be prior to the move """
    
    fcord = FCORD(move)
    tcord = TCORD(move)
    
    s = ""
    if board.arBoard[fcord] != PAWN:
        s = reprSign[board.arBoard[fcord]]
    s += reprCord[FCORD(move)]
    
    if board.arBoard[tcord] == EMPTY:
        s += "-"
    else: s += "x"
    
    s += reprCord[tcord]
    
    flag = FLAG(move)
    
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                      BISHOP_PROMOTION, KNIGHT_PROMOTION):
        s += "=" + reprSign[PROMOTE_PIECE(flag)]
    
    return s

################################################################################
# parseLan                                                                     #
################################################################################

def parseLAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    # To parse LAN pawn moves like "e2-e4" as SAN moves, we have to remove a few
    # fields
    if len(lan) == 5:
        if "x" in lan:
            # e4xd5 -> exd5
            return parseSAN (board, lan[0]+lan[3:])
        else:
            # e2-e4 -> e4
            return parseSAN (board, lan[3:])
    
    # We want to use the SAN parser for LAN moves like "Nb1-c3" or "Rd3xd7"
    # The san parser should be able to handle most stuff, as long as we remove
    # the slash
    if not lan.upper().startswith("O-O"):
        lan = lan.replace("-","")
    return parseSAN (board, lan)

################################################################################
# toAN                                                                         #
################################################################################

def toAN (board, move):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move """
    
    s = reprCord[FCORD(move)] + reprCord[TCORD(move)]
    if FLAG(move) in (QUEEN_PROMOTION, ROOK_PROMOTION,
                      BISHOP_PROMOTION, KNIGHT_PROMOTION):
        s += reprSign[PROMOTE_PIECE(FLAG(move))]
    return s

################################################################################
# parseAN                                                                      #
################################################################################

def parseAN (board, an):
    """ Parse an Algebraic Notation string """
    if not 4 <= len(an) <= 5:
        raise ParsingError, "Bad an move, %s. Wrong size" % an
    
    try:
        fcord = cordDic[an[:2]]
        tcord = cordDic[an[2:4]]
    except KeyError:
        raise ParsingError, "Bad an move, %s" % an
    
    if len(an) == 5:
        flag = chr2Sign[an[4].lower()] + 2
    elif board.arBoard[fcord] == KING and fcord - tcord == 2:
        flag = QUEEN_CASTLE
    elif board.arBoard[fcord] == KING and fcord - tcord == -2:
        flag = KING_CASTLE
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT
    else: flag = NORMAL_MOVE
    
    return newMove (fcord, tcord, flag)

################################################################################
# toFAN                                                                        #
################################################################################

def toFAN (board, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    
    fans = FAN_PIECES[board.color]
    san = toSAN (board, san)
    
    lan = san
    if "K" in lan or "Q" in lan or "R" in lan or "B" in lan or "N" in lan:
        lan = lan.replace("K", fans[KING])
        lan = lan.replace("Q", fans[QUEEN])
        lan = lan.replace("R", fans[ROOK])
        lan = lan.replace("B", fans[BISHOP])
        lan = lan.replace("N", fans[KNIGHT])
    else:
        lan = fans[PAWN] + lan
    
    return lan

################################################################################
# parseFAN                                                                     #
################################################################################

def parseFAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    fans = FAN_PIECES[board.color]
    
    san = lan
    san = san.replace(fans[KING], "K")
    san = san.replace(fans[QUEEN], "Q")
    san = san.replace(fans[ROOK], "R")
    san = san.replace(fans[BISHOP], "B")
    san = san.replace(fans[KNIGHT], "N")
    san = san.replace(fans[PAWN])
    
    return parseSAN (board, san)
