# -*- coding: UTF-8 -*-

from ldata import *
from bitboard import bitLength, firstBit
from validator import validateMove
from pychess.Utils.const import *
from pychess.Utils.repr import reprPiece, localReprSign
from pychess.Utils.lutils.lmovegen import genAllMoves, genPieceMoves, newMove

def RANK (cord): return cord >> 3
def FILE (cord): return cord & 7

def TCORD (move): return move & 63
def FCORD (move): return move >> 6 & 63
def FLAG (move): return move >> 12

def PROMOTE_PIECE (flag): return flag -2
def FLAG_PIECE (piece): return piece +2


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

def listToMoves (board, movstrs, type=None, testvalidate=False, ignoreErrors=False):
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
            if ignoreErrors:
                break
            raise
        
        if testvalidate:
            if not validateMove (board, move):
                if not ignoreErrors:
                    raise ParsingError, (mstr, 'Validation', board.asFen())
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
    #from lmovegen import genAllMoves

    def check_or_mate():
        board_clone = board.clone()
        board_clone.applyMove(move)
        sign = ""
        if board_clone.isChecked():
            for altmove in genAllMoves (board_clone):
                board_clone.applyMove(altmove)
                if board_clone.opIsChecked():
                    board_clone.popMove()
                    continue
                sign = "+"
                break
            else:
                sign = "#"
        return sign
    
    flag = move >> 12
    
    if flag == NULL_MOVE:
        return "--"
    
    if flag == KING_CASTLE:
        return "O-O%s" % check_or_mate()
    elif flag == QUEEN_CASTLE:
        return "O-O-O%s" % check_or_mate()
    
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
    
    return "%s%s" % (notat, check_or_mate())

################################################################################
# parseSan                                                                     #
################################################################################

def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    if not san:
        raise ParsingError, (san, _("the move is an empty string"), board.asFen())
    elif len(san) < 2:
        raise ParsingError, (san, _("the move is too short"), board.asFen())
    notat = san
    
    if notat == "--":
        if board.color == WHITE:
            return newMove(board.kings[WHITE], board.kings[WHITE], NULL_MOVE)
        else:
            return newMove(board.kings[BLACK], board.kings[BLACK], NULL_MOVE)

    if notat[-1] in ("+", "#"):
        notat = notat[:-1]
        # If '++' was used in place of #
        if notat[-1] == "+":
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
        if board.color == WHITE:
            fcord = board.ini_kings[0] #E1
            if notat == "O-O":
                flag = KING_CASTLE
                if board.variant == FISCHERRANDOMCHESS:
                    tcord = board.ini_rooks[0][1]
                else:
                    tcord = G1
            else:
                flag = QUEEN_CASTLE
                if board.variant == FISCHERRANDOMCHESS:
                    tcord = board.ini_rooks[0][0]
                else:
                    tcord = C1
        else:
            fcord = board.ini_kings[1] #E8
            if notat == "O-O":
                flag = KING_CASTLE
                if board.variant == FISCHERRANDOMCHESS:
                    tcord = board.ini_rooks[1][1]
                else:
                    tcord = G8
            else:
                flag = QUEEN_CASTLE
                if board.variant == FISCHERRANDOMCHESS:
                    tcord = board.ini_rooks[1][0]
                else:
                    tcord = C8
        
        return newMove (fcord, tcord, flag)

    # LAN is not allowed in pgn spec, but sometimes it occures
    if "-" in notat:
        notat = notat.replace("-", "")

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

    if piece == KING:
        if board.color == WHITE:
            return newMove(board.kings[WHITE], tcord, flag)
        else:
            return newMove(board.kings[BLACK], tcord, flag)

    # If there is any extra location info, like in the move Bexd1 or Nh3f4 we
    # want to know
    frank = None
    ffile = None
    if notat and notat[0] in reprRank:
        frank = int(notat[0])-1
        notat = notat[1:]
    if notat and notat[0] in reprFile:
        ffile = ord(notat[0]) - ord("a")
        notat = notat[1:]
    if notat and notat[0] in reprRank:
        frank = int(notat[0])-1
        notat = notat[1:]
        # we know all we want
        return newMove(frank*8+ffile, tcord, flag)

    if piece == PAWN:
        pawns = board.boards[WHITE][PAWN] if board.color == WHITE else board.boards[BLACK][PAWN]

        if (ffile is not None) and ffile != FILE(tcord):
            # capture
            if board.color == WHITE:
                fcord = tcord-7 if ffile > FILE(tcord) else tcord-9
            else:
                fcord = tcord+7 if ffile < FILE(tcord) else tcord+9
        else:
            if board.color == WHITE:
                fcord = tcord-16 if RANK(tcord)==3 and not (pawns & fileBits[FILE(tcord)] & rankBits[2]) else tcord-8
            else:
                fcord = tcord+16 if RANK(tcord)==4 and not (pawns & fileBits[FILE(tcord)] & rankBits[5]) else tcord+8
        return newMove(fcord, tcord, flag)
    else:
        if bitLength(board.boards[board.color][piece]) == 1:
            # we have only one from this kind if piece, so:
            fcord = firstBit(board.boards[board.color][piece])
            return newMove(fcord, tcord, flag)

        # We find all pieces who could have done it. (If san was legal, there should
        # never be more than one)
        for move in genPieceMoves(board, piece, tcord):
            f = FCORD(move)
            if frank != None and frank != RANK(f):
                continue
            if ffile != None and ffile != FILE(f):
                continue
            
            board_clone = board.clone()
            board_clone.applyMove(move)
            if board_clone.opIsChecked():
                continue
            return move

    # If the piece letter was omitted (not  a canonical SAN)
    for piece in (KNIGHT, BISHOP, ROOK, QUEEN):
        for move in genPieceMoves(board, piece, tcord):
            f = FCORD(move)
            if frank != None and frank != RANK(f):
                continue
            if ffile != None and ffile != FILE(f):
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

def toAN (board, move, short=False, castleNotation=CASTLE_SAN):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move
        
        short -- returns the short variant, e.g. f7f8q rather than f7f8=Q
    """
    fcord = FCORD(move)
    tcord = TCORD(move)
    
    if FLAG(move) in (KING_CASTLE, QUEEN_CASTLE):
        if castleNotation == CASTLE_SAN:
            return FLAG(move) == KING_CASTLE and "O-O" or "O-O-O"
        elif castleNotation == CASTLE_KR:
            rooks = board.ini_rooks[board.color]
            tcord = rooks[FLAG(move) == KING_CASTLE and 1 or 0]
        # No treatment needed for CASTLE_KK
    
    s = reprCord[fcord] + reprCord[tcord]
    
    if FLAG(move) in PROMOTIONS:
        if short:
            s += reprSign[PROMOTE_PIECE(FLAG(move))].lower()
        else:
            s += "=" + reprSign[PROMOTE_PIECE(FLAG(move))]
    return s

################################################################################
# parseAN                                                                      #
################################################################################

def parseAN (board, an):
    """ Parse an Algebraic Notation string """

    if not 4 <= len(an) <= 6:
        raise ParsingError, (an, "the move must be 4 or 6 chars long", board.asFen())
    
    try:
        fcord = cordDic[an[:2]]
        tcord = cordDic[an[2:4]]
    except KeyError, e:
        raise ParsingError, (an, "the cord (%s) is incorrect" % e.args[0], board.asFen())
    
    flag = NORMAL_MOVE
    if len(an) == 5:
        #The a7a8q variant
        flag = chr2Sign[an[4].lower()] + 2
    elif len(an) == 6:
        #The a7a8=q variant
        flag = chr2Sign[an[5].lower()] + 2
    elif board.arBoard[fcord] == KING:
        if board.variant == FISCHERRANDOMCHESS and board.arBoard[tcord] == ROOK:
            color = board.color
            friends = board.friends[color]
            if bitPosArray[tcord] & friends:
                if board.ini_rooks[color][0] == tcord:
                    flag = QUEEN_CASTLE
                else:
                    flag = KING_CASTLE
                
        elif fcord - tcord == 2:
            flag = QUEEN_CASTLE
        elif fcord - tcord == -2:
            flag = KING_CASTLE
        else:
            flag = NORMAL_MOVE
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT

    return newMove (fcord, tcord, flag)

################################################################################
# toFAN                                                                        #
################################################################################

san2WhiteFanDic = {
    ord(u"K"): FAN_PIECES[WHITE][KING],
    ord(u"Q"): FAN_PIECES[WHITE][QUEEN],
    ord(u"R"): FAN_PIECES[WHITE][ROOK],
    ord(u"B"): FAN_PIECES[WHITE][BISHOP],
    ord(u"N"): FAN_PIECES[WHITE][KNIGHT],
    ord(u"+"): u"†",
    ord(u"#"): u"‡"
}

san2BlackFanDic = {
    ord(u"K"): FAN_PIECES[BLACK][KING],
    ord(u"Q"): FAN_PIECES[BLACK][QUEEN],
    ord(u"R"): FAN_PIECES[BLACK][ROOK],
    ord(u"B"): FAN_PIECES[BLACK][BISHOP],
    ord(u"N"): FAN_PIECES[BLACK][KNIGHT],
    ord(u"+"): u"†",
    ord(u"#"): u"‡"
}

def toFAN (board, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    
    san = unicode(toSAN (board, move))
    if board.color == WHITE:
        return san.translate(san2WhiteFanDic)
    else:
        return san.translate(san2BlackFanDic)

################################################################################
# parseFAN                                                                     #
################################################################################

fan2SanDic = {}
for k, v in san2WhiteFanDic.iteritems():
    fan2SanDic[ord(v)] = unichr(k)
for k, v in san2BlackFanDic.iteritems():
    fan2SanDic[ord(v)] = unichr(k)

def parseFAN (board, fan):
    """ Parse a Figurine Algebraic Notation string """

    san = fan.translate(fan2SanDic)
    return parseSAN (board, san)

################################################################################
# toPolyglot                                                                   #
################################################################################

def toPolyglot (board, move):
    """ Returns a 16-bit Polyglot-format move 
        board should be prior to the move
    """
    pg = move & 4095
    if FLAG(move) in PROMOTIONS:
        pg |= ( PROMOTE_PIECE(FLAG(move)) - 1 ) << 12
    elif FLAG(move) == QUEEN_CASTLE:
        pg = (pg & 4032) | board.ini_rooks[board.color][0]
    elif FLAG(move) == KING_CASTLE:
        pg = (pg & 4032) | board.ini_rooks[board.color][1]
    
    return pg

################################################################################
# parsePolyglot                                                                #
################################################################################

def parsePolyglot (board, pg):
    """ Parse a 16-bit Polyglot-format move """
    
    tcord = TCORD(pg)
    fcord = FCORD(pg)
    flag = NORMAL_MOVE
    if pg >> 12:
        flag = FLAG_PIECE( (pg >> 12) + 1 )
    elif board.arBoard[fcord] == KING:
        if board.arBoard[tcord] == ROOK:
            color = board.color
            friends = board.friends[color]
            if bitPosArray[tcord] & friends:
                if board.ini_rooks[color][0] == tcord:
                    flag = QUEEN_CASTLE
                    if board.variant == NORMALCHESS: # Want e1c1/e8c8
                        tcord += 2
                else:
                    flag = KING_CASTLE
                    if board.variant == NORMALCHESS: # Want e1g1/e8g8
                        tcord -= 1
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT

    return newMove (fcord, tcord, flag)
