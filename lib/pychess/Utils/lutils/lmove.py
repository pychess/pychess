# -*- coding: UTF-8 -*-

import re

from ldata import *
from validator import validateMove
from pychess.Utils.const import *

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

class ParsingError (Exception):
    """ Please raise this with a 3-tupple: (move, reason, board.asFen())
        The reason should be usable in the context: 'Move was not parseable
        because %s' % reason """
    pass

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
    
    if upnot in ("O-O", "O-O-O", "0-0", "0-0-0"):
        return SAN
    
    # Test for e2-e4
    if "-" in algnot:
        return LAN
    
    # Test for b4xc5
    if "x" in algnot and algnot.split('x')[0] in cordDic:
        return LAN
    
    # Test for e2e4 or a7a8q or a7a8=q
    if algnot[:2] in cordDic and algnot[2:4] in cordDic:
        return AN
    
    if algnot[0] in FAN_PIECES[WHITE] or algnot[0] in FAN_PIECES[BLACK]:
        return FAN
    
    return SAN

################################################################################
# listToSan                                                                    #
################################################################################

def listToSan (board, moves):
    # Work on a copy to ensure we don't break things
    board = board.clone()
    sanmoves = []
    for move in moves:
        san = toSAN (board, move)
        sanmoves.append(san)
        board.applyMove(move)
    return sanmoves

################################################################################
# listToMoves                                                                  #
################################################################################

def listToMoves (board, movstrs, type=None, testvalidate=False):
    # Work on a copy to ensure we don't break things
    board = board.clone()
    moves = []

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
    
    return moves

################################################################################
# toSan                                                                        #
################################################################################

def toSAN (board, move, localRepr=False):
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
        if localRepr:
            part0 += localReprSign[fpiece]
        else:
            part0 += reprSign[fpiece]
    
    part1 = reprCord[tcord]
    
    if not fpiece in (PAWN, KING):
        xs = []
        ys = []
        
        board_clone = board.clone()
        for altmove in genAllMoves(board_clone):
            mfcord = FCORD(altmove)
            if board_clone.arBoard[mfcord] == fpiece and \
                    mfcord != fcord and \
                    TCORD(altmove) == tcord:
                board_clone.applyMove(altmove)
                if not board_clone.opIsChecked():
                    xs.append(FILE(mfcord))
                    ys.append(RANK(mfcord))
                board_clone.popMove()

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
    if flag in PROMOTIONS:
        if localRepr:
            notat += "="+localReprSign[PROMOTE_PIECE(flag)]
        else:
            notat += "="+reprSign[PROMOTE_PIECE(flag)]
    
    board_clone = board.clone()
    board_clone.applyMove(move)
    if board_clone.isChecked():
        for altmove in genAllMoves (board_clone):
            board_clone.applyMove(altmove)
            if board_clone.opIsChecked():
                board_clone.popMove()
                continue
            notat += "+"
            break
        else:
            notat += "#"
    
    return notat

################################################################################
# parseSan                                                                     #
################################################################################

def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    if len(san) < 2:
        if not san:
            raise ParsingError, (san, _("the move is an empty string"), board.asFen())
        raise ParsingError, (san, _("the move is too short"), board.asFen())
    
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
    
    if len(notat) < 2:
        raise ParsingError, (san, _("the move needs a piece and a cord"), board.asFen())
    
    notat = notat.replace("0","O").replace("o","O")
    if notat.startswith("O-O"):
        if color == WHITE:
            fcord = board.ini_kings[0] #E1
            if notat == "O-O":
                flag = KING_CASTLE
                tcord = G1
            else:
                flag = QUEEN_CASTLE
                tcord = C1
        else:
            fcord = board.ini_kings[1] #E8
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
        if not tcord in cordDic:
            raise ParsingError, (
                    san, _("the captured cord (%s) is incorrect") % tcord, board.asFen())
        
        tcord = cordDic[tcord]
        if piece == PAWN:
            # If a pawn is attacking an empty cord, we assue it an enpassant
            if board.arBoard[tcord] == EMPTY:
                flag = ENPASSANT
    else:
        if not notat[-2:] in cordDic:
            raise ParsingError, (
                    san, "the end cord (%s) is incorrect" % notat[-2:], board.asFen())
        
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
    for move in genAllMoves(board):
        if TCORD(move) != tcord:
            continue
        f = FCORD(move)
        if board.arBoard[f] != piece:
            continue
        if frank != None and frank != RANK(f):
            continue
        if ffile != None and ffile != FILE(f):
            continue
        if flag in PROMOTIONS and FLAG(move) != flag:
            continue
        
        board_clone = board.clone()
        board_clone.applyMove(move)
        if board_clone.opIsChecked():
            continue
        
        return move
    
    errstring = "no %s is able to move to %s" % (reprPiece[piece], reprCord[tcord])
    raise ParsingError, (san, errstring, board.asFen())

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
    
    if flag in PROMOTIONS:
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
    if board.variant == FISCHERRANDOMCHESS:
        flag = move >> 12
        if flag == KING_CASTLE:
            return "O-O"
        elif flag == QUEEN_CASTLE:
            return "O-O-O"
    
    if FLAG(move) in PROMOTIONS:
        s += "="+reprSign[PROMOTE_PIECE(FLAG(move))]
    return s

################################################################################
# parseAN                                                                      #
################################################################################

def parseAN (board, an):
    """ Parse an Algebraic Notation string """

    if board.variant == FISCHERRANDOMCHESS:
        color = board.color
        notat = an
        notat = notat.replace("0","O").replace("o","O")
        if notat.startswith("O-O"):
            if color == WHITE:
                fcord = board.ini_kings[0] #E1
                if notat == "O-O":
                    flag = KING_CASTLE
                    tcord = G1
                else:
                    flag = QUEEN_CASTLE
                    tcord = C1
            else:
                fcord = board.ini_kings[1] #E8
                if notat == "O-O":
                    flag = KING_CASTLE
                    tcord = G8
                else:
                    flag = QUEEN_CASTLE
                    tcord = C8
            return newMove (fcord, tcord, flag)

    if not 4 <= len(an) <= 5:
        raise ParsingError, (an, "the move must be 4 or 5 chars long", board.asFen())
    
    try:
        fcord = cordDic[an[:2]]
        tcord = cordDic[an[2:4]]
    except KeyError, e:
        raise ParsingError, (an, "the cord (%s) is incorrect" % e.args[0], board.asFen())
    
    if len(an) == 5:
        #The a7a8q variant
        flag = chr2Sign[an[4].lower()] + 2
    elif len(an) == 6:
        #The a7a8=q variant
        flag = chr2Sign[an[5].lower()] + 2
    elif board.arBoard[fcord] == KING:
        if fcord - tcord == 2:
            flag = QUEEN_CASTLE
        elif fcord - tcord == -2:
            flag = KING_CASTLE
        else:
            flag = NORMAL_MOVE
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT
    else: flag = NORMAL_MOVE

    return newMove (fcord, tcord, flag)

################################################################################
# toFAN                                                                        #
################################################################################

san2WhiteFanDic = {
    "K": FAN_PIECES[WHITE][KING],
    "Q": FAN_PIECES[WHITE][QUEEN],
    "R": FAN_PIECES[WHITE][ROOK],
    "B": FAN_PIECES[WHITE][BISHOP],
    "N": FAN_PIECES[WHITE][KNIGHT],
    "+": "†",
    "#": "‡"
}
san2WhiteFanRegex = re.compile(
    "(%s)" % "|".join(re.escape(k) for k in san2WhiteFanDic.keys()) )
san2WhiteFanFunc = lambda match: san2WhiteFanDic[match.group()]

san2BlackFanDic = {
    "K": FAN_PIECES[BLACK][KING],
    "Q": FAN_PIECES[BLACK][QUEEN],
    "R": FAN_PIECES[BLACK][ROOK],
    "B": FAN_PIECES[BLACK][BISHOP],
    "N": FAN_PIECES[BLACK][KNIGHT],
    "+": "†",
    "#": "‡"
}
san2BlackFanRegex = re.compile(
    "(%s)" % "|".join(re.escape(k) for k in san2BlackFanDic.keys()) )
san2BlackFanFunc = lambda match: san2BlackFanDic[match.group()]

def toFAN (board, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    
    lan = toSAN (board, move)
    
    if board.color == WHITE:
        lan = san2WhiteFanRegex.sub(san2WhiteFanFunc, lan)
    else:
        lan = san2BlackFanRegex.sub(san2BlackFanFunc, lan)
    
    return lan

################################################################################
# parseFAN                                                                     #
################################################################################

fan2SanDic = {}
for k, v in san2WhiteFanDic.iteritems():
    fan2SanDic[v] = k
for k, v in san2BlackFanDic.iteritems():
    fan2SanDic[v] = k

fan2SanRegex = re.compile(
    "(%s)" % "|".join(re.escape(k) for k in fan2SanDic.keys()) )
fan2SanFunc = lambda match: fan2SanDic[match.group()]

def parseFAN (board, fan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    san = fan2SanRegex.sub(fan2SanFunc, fan)
    
    pawnFan = FAN_PIECES[board.color][PAWN]
    if san[0] == pawnFan:
        san = san.replace(pawnFan, "")
        # If the pawn file has been omitted from a capture fan notation, it
        # means that there was only one pawn able to move to the end cord. We
        # just need to find it.
        if san[0] == "x":
            # We need to find the endcord ourselves. Can't wait for parseSAN
            i = san.find("=")
            if i >= 0:
                tocord = san[1:i]
            else: tocord = san[1:]
            tcord = cordDic[tocord]
            
            from lmovegen import genAllMoves
            board_clone = board.clone()
            for altmove in genAllMoves(board_clone):
                if board_clone.arBoard[FCORD(altmove)] == PAWN and \
                        TCORD(altmove) == tcord:
                    board_clone.applyMove(altmove)
                    if not board_clone.opIsChecked():
                        san = reprFile(mfcord) + san
                    board_clone.popMove()
                    # We know there is only one pawn which can move to tcord, so
                    # we stop work here
                    break
    
    return parseSAN (board, san)
