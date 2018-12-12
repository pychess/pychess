# -*- coding: UTF-8 -*-

from .ldata import bitPosArray, fileBits, rankBits, moveArray
from .bitboard import firstBit, iterBits
from .validator import validateMove

from pychess.Utils.const import SAN, AN, LAN, ENPASSANT, EMPTY, PAWN, KING_CASTLE, QUEEN_CASTLE,\
    reprFile, reprRank, chr2Sign, cordDic, reprSign, reprCord, reprSignSittuyin, reprSignMakruk,\
    QUEEN, KNIGHT, BISHOP, ROOK, KING, NORMALCHESS, NORMAL_MOVE, PROMOTIONS, WHITE, BLACK, DROP,\
    FAN_PIECES, SITTUYINCHESS, FISCHERRANDOMCHESS, SUICIDECHESS, MAKRUKCHESS, CAMBODIANCHESS,\
    GIVEAWAYCHESS, ATOMICCHESS, WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, HORDECHESS,\
    chrU2Sign, CASTLE_KR, CASTLE_SAN, QUEEN_PROMOTION, NULL_MOVE, FAN, ASEAN_QUEEN
from pychess.Utils.repr import reprPiece, localReprSign
from pychess.Utils.lutils.lmovegen import genAllMoves, genPieceMoves, newMove


def RANK(cord):
    return cord >> 3


def FILE(cord):
    return cord & 7


def TCORD(move):
    return move & 63


def FCORD(move):
    return move >> 6 & 63


def FLAG(move):
    return move >> 12


def PROMOTE_PIECE(flag):
    return flag - 2


def FLAG_PIECE(piece):
    return piece + 2


class ParsingError(Exception):
    """ Please raise this with a 3-tupple: (move, reason, board.asFen())
        The reason should be usable in the context: 'Move was not parseable
        because %s' % reason """
    pass


def sittuyin_promotion_fcord(board, tcord):
    from pychess.Variants import variants
    queenMoves = moveArray[ASEAN_QUEEN]
    promotion_zone = variants[SITTUYINCHESS].PROMOTION_ZONE[board.color]
    for fcord in iterBits(queenMoves[tcord]):
        if fcord in promotion_zone:
            return fcord

################################################################################
# parseAny                                                                     #
################################################################################


def parseAny(board, algnot):
    type = determineAlgebraicNotation(algnot)
    if type == SAN:
        return parseSAN(board, algnot)
    if type == AN:
        return parseAN(board, algnot)
    if type == LAN:
        return parseLAN(board, algnot)
    return parseFAN(board, algnot)


def determineAlgebraicNotation(algnot):
    upnot = algnot.upper()
    if upnot in ("O-O", "O-O-O", "0-0", "0-0-0", "OO", "OOO", "00", "000"):
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


def listToSan(board, moves):
    # Work on a copy to ensure we don't break things
    board = board.clone()
    sanmoves = []
    for move in moves:
        san = toSAN(board, move)
        sanmoves.append(san)
        board.applyMove(move)
    return sanmoves

################################################################################
# listToMoves                                                                  #
################################################################################


def listToMoves(board,
                movstrs,
                type=None,
                testvalidate=False,
                ignoreErrors=False):
    # Work on a copy to ensure we don't break things
    board = board.clone()
    moves = []

    for mstr in movstrs:
        try:
            if type is None:
                move = parseAny(board, mstr)
            elif type == SAN:
                move = parseSAN(board, mstr)
            elif type == AN:
                move = parseAN(board, mstr)
            elif type == LAN:
                move = parseLAN(board, mstr)
        except ParsingError:
            if ignoreErrors:
                break
            raise

        if testvalidate and mstr != "--":
            if not validateMove(board, move):
                if not ignoreErrors:
                    raise ParsingError(mstr, 'Validation', board.asFen())
                break

        moves.append(move)
        board.applyMove(move)

    return moves

################################################################################
# toSan                                                                        #
################################################################################


def toSAN(board, move, localRepr=False):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move
        The board should be prior to the move """

    def check_or_mate():
        board_clone = board.clone()
        board_clone.applyMove(move)
        sign = ""
        if board_clone.isChecked():
            for altmove in genAllMoves(board_clone):
                if board.variant == ATOMICCHESS:
                    from pychess.Variants.atomic import kingExplode
                    if kingExplode(board_clone, altmove, 1 - board_clone.color) and \
                            not kingExplode(board_clone, altmove, board_clone.color):
                        sign = "+"
                        break
                    elif kingExplode(board_clone, altmove, board_clone.color):
                        continue
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

    fcord = (move >> 6) & 63
    if flag == KING_CASTLE:
        return "O-O%s" % check_or_mate()
    elif flag == QUEEN_CASTLE:
        return "O-O-O%s" % check_or_mate()

    tcord = move & 63

    fpiece = fcord if flag == DROP else board.arBoard[fcord]
    tpiece = board.arBoard[tcord]

    part0 = ""
    part1 = ""

    if fpiece != PAWN or flag == DROP:
        if board.variant in (CAMBODIANCHESS, MAKRUKCHESS):
            part0 += reprSignMakruk[fpiece]
        elif board.variant == SITTUYINCHESS:
            part0 += reprSignSittuyin[fpiece]
        elif localRepr:
            part0 += localReprSign[fpiece]
        else:
            part0 += reprSign[fpiece]

    part1 = reprCord[tcord]

    if flag == DROP:
        return "%s@%s%s" % (part0, part1, check_or_mate())

    if fpiece != PAWN:
        xs = []
        ys = []

        board_clone = board.clone()
        for altmove in genAllMoves(board_clone, drops=False):
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
            if y in ys and x not in xs:
                # If we share rank with another piece, but not file
                part0 += reprFile[x]
            elif x in xs and y not in ys:
                # If we share file with another piece, but not rank
                part0 += reprRank[y]
            elif x in xs and y in ys:
                # If we share both file and rank with other pieces
                part0 += reprFile[x] + reprRank[y]
            else:
                # If we doesn't share anything, it is standard to put file
                part0 += reprFile[x]

    if tpiece != EMPTY or flag == ENPASSANT:
        if not (board.variant == SITTUYINCHESS and fcord == tcord):
            part1 = "x" + part1
            if fpiece == PAWN:
                part0 += reprFile[FILE(fcord)]

    if board.variant == SITTUYINCHESS and flag in PROMOTIONS:
        part0 = reprCord[fcord]

    notat = part0 + part1
    if flag in PROMOTIONS:
        if board.variant in (CAMBODIANCHESS, MAKRUKCHESS):
            notat += "=" + reprSignMakruk[PROMOTE_PIECE(flag)]
        elif board.variant == SITTUYINCHESS:
            notat += "=" + reprSignSittuyin[PROMOTE_PIECE(flag)]
        elif localRepr:
            notat += "=" + localReprSign[PROMOTE_PIECE(flag)]
        else:
            notat += "=" + reprSign[PROMOTE_PIECE(flag)]

    return "%s%s" % (notat, check_or_mate())

################################################################################
# parseSan                                                                     #
################################################################################


def parseSAN(board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    notat = san

    color = board.color

    if notat == "--":
        return newMove(board.kings[color], board.kings[color], NULL_MOVE)

    if notat[-1] in "+#":
        notat = notat[:-1]
        # If '++' was used in place of #
        if notat[-1] == "+":
            notat = notat[:-1]

    flag = NORMAL_MOVE

    # If last char is a piece char, we assue it the promote char
    c = notat[-1]
    if c in "KQRBNSMFkqrbnsmf.":
        c = c.lower()
        if c == "k" and board.variant != SUICIDECHESS and board.variant != GIVEAWAYCHESS:
            raise ParsingError(san, _("invalid promoted piece"), board.asFen())
        elif c == ".":
            if board.variant in (CAMBODIANCHESS, MAKRUKCHESS, SITTUYINCHESS):
                # temporary hack for xboard bug
                flag = QUEEN_PROMOTION
            else:
                raise ParsingError(san, "invalid san", board.asFen())
        else:
            flag = chr2Sign[c] + 2

        if notat[-2] == "=":
            notat = notat[:-2]
        else:
            notat = notat[:-1]

    if len(notat) < 2:
        raise ParsingError(san, _("the move needs a piece and a cord"),
                           board.asFen())

    if notat[0] in "O0o":
        fcord = board.ini_kings[color]
        flag = KING_CASTLE if notat in ("O-O", "0-0", "o-o", "OO", "00", "oo") else QUEEN_CASTLE
        side = flag - QUEEN_CASTLE
        if FILE(fcord) == 3 and board.variant in (WILDCASTLECHESS,
                                                  WILDCASTLESHUFFLECHESS):
            side = 0 if side == 1 else 1
        if board.variant == FISCHERRANDOMCHESS:
            tcord = board.ini_rooks[color][side]
        else:
            tcord = board.fin_kings[color][side]
        return newMove(fcord, tcord, flag)

    # LAN is not allowed in pgn spec, but sometimes it occures
    if "-" in notat:
        notat = notat.replace("-", "")

    if "@" in notat:
        tcord = cordDic[notat[-2:]]
        if notat[0].islower():
            # Sjeng-ism
            piece = chr2Sign[notat[0]]
        else:
            piece = chrU2Sign[notat[0]]
        return newMove(piece, tcord, DROP)

    # standard piece letters
    if notat[0] in "QRBKNSMF":
        piece = chrU2Sign[notat[0]]
        notat = notat[1:]
    # unambigious lowercase piece letters
    elif notat[0] in "qrknsm":
        piece = chr2Sign[notat[0]]
        notat = notat[1:]
    # a lowercase bishop letter or a pawn capture
    elif notat[0] == "b" and len(notat) > 2 and board.variant == NORMALCHESS:
        tcord = cordDic[notat[-2:]]
        trank = int(notat[-1])
        # if from and to lines are not neighbours -> Bishop
        if abs(ord(notat[0]) - ord(notat[-2])) > 1:
            piece = chr2Sign[notat[0]]
            notat = notat[1:]
        # if from and to lines are neighbours (or the same) but to is an empty square
        # which can't be en-passant square target -> Bishop
        elif board.arBoard[tcord] == EMPTY and ((color == BLACK and trank != 3) or (color == WHITE and trank != 6)):
            piece = chr2Sign[notat[0]]
            notat = notat[1:]
        # elif "ba3", "bc3" ,"ba6", "bc6"
        # these can be Bishop or Pawn moves, but we don't try to introspect them (sorry)
        else:
            piece = PAWN
    else:
        piece = PAWN
        if notat[-1] in "18" and flag == NORMAL_MOVE and board.variant != SITTUYINCHESS:
            flag = QUEEN_PROMOTION

    if "x" in notat:
        notat, tcord = notat.split("x")
        if tcord not in cordDic:
            raise ParsingError(san, _("the captured cord (%s) is incorrect") %
                               tcord, board.asFen())

        tcord = cordDic[tcord]

        if piece == PAWN:
            # If a pawn is attacking an empty cord, we assue it an enpassant
            if board.arBoard[tcord] == EMPTY:
                if (color == BLACK and 2 * 8 <= tcord < 3 * 8) or (color == WHITE and 5 * 8 <= tcord < 6 * 8):
                    flag = ENPASSANT
                else:
                    raise ParsingError(
                        san, _("pawn capture without target piece is invalid"),
                        board.asFen())
    else:
        if not notat[-2:] in cordDic:
            raise ParsingError(san, _("the end cord (%s) is incorrect") %
                               notat[-2:], board.asFen())

        tcord = cordDic[notat[-2:]]
        notat = notat[:-2]

    # In suicide promoting to king is valid, so
    # more than 1 king per side can exist !
    if board.variant != SUICIDECHESS and board.variant != GIVEAWAYCHESS and piece == KING:
        return newMove(board.kings[color], tcord, flag)

    # If there is any extra location info, like in the move Bexd1 or Nh3f4 we
    # want to know
    frank = None
    ffile = None
    if notat and notat[0] in reprRank:
        frank = int(notat[0]) - 1
        notat = notat[1:]
    if notat and notat[0] in reprFile:
        ffile = ord(notat[0]) - ord("a")
        notat = notat[1:]
    if notat and notat[0] in reprRank:
        frank = int(notat[0]) - 1
        notat = notat[1:]
        # we know all we want
        return newMove(frank * 8 + ffile, tcord, flag)

    if piece == PAWN:
        if (ffile is not None) and ffile != FILE(tcord):
            # capture
            if color == WHITE:
                fcord = tcord - 7 if ffile > FILE(tcord) else tcord - 9
            else:
                fcord = tcord + 7 if ffile < FILE(tcord) else tcord + 9
        else:
            if color == WHITE:
                pawns = board.boards[WHITE][PAWN]
                # In horde white pawns on first rank may move two squares also
                if board.variant == HORDECHESS and RANK(tcord) == 2 and not (
                        pawns & fileBits[FILE(tcord)] & rankBits[1]):
                    fcord = tcord - 16
                else:
                    fcord = tcord - 16 if RANK(tcord) == 3 and not (
                        pawns & fileBits[FILE(tcord)] & rankBits[2]) else tcord - 8
            else:
                pawns = board.boards[BLACK][PAWN]
                fcord = tcord + 16 if RANK(tcord) == 4 and not (
                    pawns & fileBits[FILE(tcord)] & rankBits[5]) else tcord + 8

            if board.variant == SITTUYINCHESS and flag == QUEEN_PROMOTION:
                if pawns & fileBits[FILE(tcord)] & rankBits[RANK(tcord)]:
                    # in place promotion
                    return newMove(tcord, tcord, flag)
                else:
                    # queen move promotion (fcord have to be the closest cord of promotion zone)
                    fcord = sittuyin_promotion_fcord(board, tcord)
                    return newMove(fcord, tcord, flag)
        return newMove(fcord, tcord, flag)
    else:
        if board.pieceCount[color][piece] == 1:
            # we have only one from this kind if piece, so:
            fcord = firstBit(board.boards[color][piece])
            return newMove(fcord, tcord, flag)
        else:
            # We find all pieces who could have done it. (If san was legal, there should
            # never be more than one)
            moves = genPieceMoves(board, piece, tcord)
            if len(moves) == 1:
                return moves.pop()
            else:
                for move in moves:
                    f = FCORD(move)
                    if frank is not None and frank != RANK(f):
                        continue
                    if ffile is not None and ffile != FILE(f):
                        continue
                    board_clone = board.clone()
                    board_clone.applyMove(move)
                    if board_clone.opIsChecked():
                        continue
                    return move

    errstring = "no %s is able to move to %s" % (reprPiece[piece],
                                                 reprCord[tcord])
    raise ParsingError(san, errstring, board.asFen())

################################################################################
# toLan                                                                        #
################################################################################


def toLAN(board, move, localRepr=False):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        board should be prior to the move """

    fcord = FCORD(move)
    tcord = TCORD(move)
    flag = FLAG(move)
    fpiece = fcord if flag == DROP else board.arBoard[fcord]

    s = ""
    if fpiece != PAWN or flag == DROP:
        if board.variant in (CAMBODIANCHESS, MAKRUKCHESS):
            s = reprSignMakruk[fpiece]
        elif board.variant == SITTUYINCHESS:
            s = reprSignSittuyin[fpiece]
        elif localRepr:
            s = localReprSign[fpiece]
        else:
            s = reprSign[fpiece]

    if flag == DROP:
        s += "@"
    else:
        s += reprCord[FCORD(move)]
        if board.arBoard[tcord] == EMPTY:
            s += "-"
        else:
            s += "x"

    s += reprCord[tcord]

    if flag in PROMOTIONS:
        s += "=" + reprSign[PROMOTE_PIECE(flag)]

    return s

################################################################################
# parseLan                                                                     #
################################################################################


def parseLAN(board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """

    # To parse LAN pawn moves like "e2-e4" as SAN moves, we have to remove a few
    # fields
    if len(lan) == 5:
        if "x" in lan:
            # e4xd5 -> exd5
            return parseSAN(board, lan[0] + lan[3:])
        else:
            # e2-e4 -> e4
            return parseSAN(board, lan[3:])

    # We want to use the SAN parser for LAN moves like "Nb1-c3" or "Rd3xd7"
    # The san parser should be able to handle most stuff, as long as we remove
    # the slash
    if not lan.upper().startswith("O-O") and not lan.startswith("--"):
        lan = lan.replace("-", "")
    return parseSAN(board, lan)

################################################################################
# toAN                                                                         #
################################################################################


def toAN(board, move, short=False, castleNotation=CASTLE_SAN):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move
        short -- returns the short variant, e.g. f7f8q rather than f7f8=Q
    """

    fcord = (move >> 6) & 63
    tcord = move & 63
    flag = move >> 12

    if flag in (KING_CASTLE, QUEEN_CASTLE):
        if castleNotation == CASTLE_SAN:
            return flag == KING_CASTLE and "O-O" or "O-O-O"
        elif castleNotation == CASTLE_KR:
            rooks = board.ini_rooks[board.color]
            tcord = rooks[flag == KING_CASTLE and 1 or 0]
        # No treatment needed for CASTLE_KK

    if flag == DROP:
        if board.variant == SITTUYINCHESS:
            s = "%s@%s" % (reprSignSittuyin[fcord], reprCord[tcord])
        else:
            s = "%s@%s" % (reprSign[fcord], reprCord[tcord])
    else:
        s = reprCord[fcord] + reprCord[tcord]

    if flag in PROMOTIONS:
        if short:
            if board.variant in (CAMBODIANCHESS, MAKRUKCHESS):
                s += reprSignMakruk[PROMOTE_PIECE(flag)].lower()
            elif board.variant == SITTUYINCHESS:
                s += reprSignSittuyin[PROMOTE_PIECE(flag)].lower()
            else:
                s += reprSign[PROMOTE_PIECE(flag)].lower()
        else:
            if board.variant in (CAMBODIANCHESS, MAKRUKCHESS):
                s += "=" + reprSignMakruk[PROMOTE_PIECE(flag)]
            elif board.variant == SITTUYINCHESS:
                s += "=" + reprSignSittuyin[PROMOTE_PIECE(flag)]
            else:
                s += "=" + reprSign[PROMOTE_PIECE(flag)]
    return s

################################################################################
# parseAN                                                                      #
################################################################################


def parseAN(board, an):
    """ Parse an Algebraic Notation string """

    if not 4 <= len(an) <= 6:
        raise ParsingError(an, "the move must be 4 or 6 chars long",
                           board.asFen())

    if "@" in an:
        tcord = cordDic[an[-2:]]
        if an[0].islower():
            # Sjeng-ism
            piece = chr2Sign[an[0]]
        else:
            piece = chrU2Sign[an[0]]
        return newMove(piece, tcord, DROP)

    try:
        fcord = cordDic[an[:2]]
        tcord = cordDic[an[2:4]]
    except KeyError as e:
        raise ParsingError(an, "the cord (%s) is incorrect" % e.args[0],
                           board.asFen())

    flag = NORMAL_MOVE

    if len(an) > 4 and not an[-1] in "QRBNMSFqrbnmsf":
        if (board.variant != SUICIDECHESS and board.variant != GIVEAWAYCHESS) or \
            (board.variant == SUICIDECHESS or board.variant == GIVEAWAYCHESS) and not an[
                -1] in "Kk":
            raise ParsingError(an, "invalid promoted piece", board.asFen())

    if len(an) == 5:
        # The a7a8q variant
        flag = chr2Sign[an[4].lower()] + 2
    elif len(an) == 6:
        # The a7a8=q variant
        flag = chr2Sign[an[5].lower()] + 2
    elif board.arBoard[fcord] == KING:
        if fcord - tcord == 2:
            flag = QUEEN_CASTLE
            if board.variant == FISCHERRANDOMCHESS:
                tcord = board.ini_rooks[board.color][0]
        elif fcord - tcord == -2:
            flag = KING_CASTLE
            if board.variant == FISCHERRANDOMCHESS:
                tcord = board.ini_rooks[board.color][1]
        elif board.arBoard[
                tcord] == ROOK:
            color = board.color
            friends = board.friends[color]
            if bitPosArray[tcord] & friends:
                if board.ini_rooks[color][0] == tcord:
                    flag = QUEEN_CASTLE
                else:
                    flag = KING_CASTLE
        else:
            flag = NORMAL_MOVE
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT
    elif board.arBoard[fcord] == PAWN:
        if an[3] in "18" and board.variant != SITTUYINCHESS:
            flag = QUEEN_PROMOTION

    return newMove(fcord, tcord, flag)


################################################################################
# toFAN                                                                        #
################################################################################

san2WhiteFanDic = {
    ord("K"): FAN_PIECES[WHITE][KING],
    ord("Q"): FAN_PIECES[WHITE][QUEEN],
    ord("M"): FAN_PIECES[WHITE][QUEEN],
    ord("F"): FAN_PIECES[WHITE][QUEEN],
    ord("R"): FAN_PIECES[WHITE][ROOK],
    ord("B"): FAN_PIECES[WHITE][BISHOP],
    ord("S"): FAN_PIECES[WHITE][BISHOP],
    ord("N"): FAN_PIECES[WHITE][KNIGHT],
    ord("P"): FAN_PIECES[WHITE][PAWN],
    ord("+"): "†",
    ord("#"): "‡"
}

san2BlackFanDic = {
    ord("K"): FAN_PIECES[BLACK][KING],
    ord("Q"): FAN_PIECES[BLACK][QUEEN],
    ord("M"): FAN_PIECES[BLACK][QUEEN],
    ord("F"): FAN_PIECES[BLACK][QUEEN],
    ord("R"): FAN_PIECES[BLACK][ROOK],
    ord("B"): FAN_PIECES[BLACK][BISHOP],
    ord("S"): FAN_PIECES[BLACK][BISHOP],
    ord("N"): FAN_PIECES[BLACK][KNIGHT],
    ord("P"): FAN_PIECES[BLACK][PAWN],
    ord("+"): "†",
    ord("#"): "‡"
}


def toFAN(board, move):
    """ Returns a Figurine Algebraic Notation string of a move """

    san = toSAN(board, move)
    return san.translate(san2WhiteFanDic)


################################################################################
# parseFAN                                                                     #
################################################################################

fan2SanDic = {}
for k, v in san2WhiteFanDic.items():
    fan2SanDic[ord(v)] = chr(k)
for k, v in san2BlackFanDic.items():
    fan2SanDic[ord(v)] = chr(k)


def parseFAN(board, fan):
    """ Parse a Figurine Algebraic Notation string """

    san = fan.translate(fan2SanDic)
    return parseSAN(board, san)

################################################################################
# toPolyglot                                                                   #
################################################################################


def toPolyglot(board, move):
    """ Returns a 16-bit Polyglot-format move
        board should be prior to the move
    """
    pg = move & 4095
    if FLAG(move) in PROMOTIONS:
        pg |= (PROMOTE_PIECE(FLAG(move)) - 1) << 12
    elif FLAG(move) == QUEEN_CASTLE:
        pg = (pg & 4032) | board.ini_rooks[board.color][0]
    elif FLAG(move) == KING_CASTLE:
        pg = (pg & 4032) | board.ini_rooks[board.color][1]

    return pg

################################################################################
# parsePolyglot                                                                #
################################################################################


def parsePolyglot(board, pg):
    """ Parse a 16-bit Polyglot-format move """

    tcord = TCORD(pg)
    fcord = FCORD(pg)
    flag = NORMAL_MOVE
    if pg >> 12:
        flag = FLAG_PIECE((pg >> 12) + 1)
    elif board.arBoard[fcord] == KING:
        if board.arBoard[tcord] == ROOK:
            color = board.color
            friends = board.friends[color]
            if bitPosArray[tcord] & friends:
                if board.ini_rooks[color][0] == tcord:
                    flag = QUEEN_CASTLE
                    if board.variant == NORMALCHESS:  # Want e1c1/e8c8
                        tcord += 2
                else:
                    flag = KING_CASTLE
                    if board.variant == NORMALCHESS:  # Want e1g1/e8g8
                        tcord -= 1
    elif board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY and \
            FILE(fcord) != FILE(tcord) and RANK(fcord) != RANK(tcord):
        flag = ENPASSANT

    return newMove(fcord, tcord, flag)
