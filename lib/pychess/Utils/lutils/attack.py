from __future__ import absolute_import

from .bitboard import bitPosArray, notBitPosArray, lastBit, firstBit, clearBit, lsb
from .ldata import moveArray, rays, directions, fromToRay, PIECE_VALUES, PAWN_VALUE
from pychess.Utils.const import ASEAN_VARIANTS, ASEAN_BBISHOP, ASEAN_WBISHOP, ASEAN_QUEEN, \
    BLACK, WHITE, PAWN, BPAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, ENPASSANT, ATOMICCHESS

#
# Caveat: Many functions in this module has very similar code. If you fix a
# bug, or write a perforance enchace, please update all functions. Apologies
# for the inconvenience
#


def isAttacked(board, cord, color, ischecked=False):
    """ To determine if cord is attacked by any pieces from color. """

    _moveArray = moveArray
    pboards = board.boards[color]

    # Knights
    if pboards[KNIGHT] & _moveArray[KNIGHT][cord]:
        return True

    rayto = fromToRay[cord]
    blocker = board.blocker

    # Bishops & Queens
    if board.variant in ASEAN_VARIANTS:
        bishopMoves = _moveArray[ASEAN_BBISHOP if color == WHITE else
                                 ASEAN_WBISHOP]
        if pboards[BISHOP] & bishopMoves[cord]:
            return True
        if pboards[QUEEN] & _moveArray[ASEAN_QUEEN][cord]:
            return True
    else:
        bitboard = (pboards[BISHOP] |
                    pboards[QUEEN]) & _moveArray[BISHOP][cord]
        if bitboard:
            others = ~bitboard & blocker
            # inlined iterBits()
            while bitboard:
                bit = bitboard & -bitboard
                ray = rayto[lsb[bit]]
                # If there is a path and no other piece stand in our way
                if ray and not ray & others:
                    return True
                bitboard -= bit

    # Rooks & Queens
    if board.variant in ASEAN_VARIANTS:
        bitboard = pboards[ROOK] & _moveArray[ROOK][cord]
    else:
        bitboard = (pboards[ROOK] | pboards[QUEEN]) & _moveArray[ROOK][cord]
    if bitboard:
        others = ~bitboard & blocker
        # inlined iterBits()
        while bitboard:
            bit = bitboard & -bitboard
            ray = rayto[lsb[bit]]
            # If there is a path and no other piece stand in our way
            if ray and not ray & others:
                return True
            bitboard -= bit

            # Pawns
            # Would a pawn of the opposite color, standing at out kings cord, be able
            # to attack any of our pawns?
    ptype = color == WHITE and BPAWN or PAWN
    if pboards[PAWN] & _moveArray[ptype][cord]:
        return True

    # King
    if pboards[KING] & _moveArray[KING][cord]:
        if board.variant == ATOMICCHESS and ischecked:
            return False
        else:
            return True

    return False


def getAttacks(board, cord, color):
    """ To create a bitboard of pieces of color, which attacks cord """

    _moveArray = moveArray
    pieces = board.boards[color]

    # Knights
    bits = pieces[KNIGHT] & _moveArray[KNIGHT][cord]

    # Kings
    bits |= pieces[KING] & _moveArray[KING][cord]

    # Pawns
    bits |= pieces[PAWN] & _moveArray[color == WHITE and BPAWN or PAWN][cord]

    rayto = fromToRay[cord]
    blocker = board.blocker

    # Bishops and Queens
    if board.variant in ASEAN_VARIANTS:
        bishopMoves = _moveArray[ASEAN_BBISHOP if color == WHITE else
                                 ASEAN_WBISHOP]
        bits |= pieces[BISHOP] & bishopMoves[cord]

        bits |= pieces[QUEEN] & _moveArray[ASEAN_QUEEN][cord]
    else:
        bitboard = (pieces[BISHOP] | pieces[QUEEN]) & _moveArray[BISHOP][cord]
        # inlined iterBits()
        while bitboard:
            bit = bitboard & -bitboard
            c = lsb[bit]
            ray = rayto[c]
            if ray and not clearBit(ray & blocker, c):
                bits |= bitPosArray[c]
            bitboard -= bit

    # Rooks and queens
    if board.variant in ASEAN_VARIANTS:
        bitboard = pieces[ROOK] & _moveArray[ROOK][cord]
    else:
        bitboard = (pieces[ROOK] | pieces[QUEEN]) & _moveArray[ROOK][cord]
    # inlined iterBits()
    while bitboard:
        bit = bitboard & -bitboard
        c = lsb[bit]
        ray = rayto[c]
        if ray and not clearBit(ray & blocker, c):
            bits |= bitPosArray[c]
        bitboard -= bit

    return bits


def pinnedOnKing(board, cord, color):
    # Determine if the piece on cord is pinned against its colors king.
    # In chess, a pin is a situation in which a piece is forced to stay put
    # because moving it would expose a more valuable piece behind it to
    # capture.
    # Caveat: pinnedOnKing should only be called by genCheckEvasions().

    kingCord = board.kings[color]

    dir = directions[kingCord][cord]
    if dir == -1:
        return False

    opcolor = 1 - color
    blocker = board.blocker

    #  Path from piece to king is blocked, so no pin
    if clearBit(fromToRay[kingCord][cord], cord) & blocker:
        return False

    b = (rays[kingCord][dir] ^ fromToRay[kingCord][cord]) & blocker
    if not b:
        return False

    cord1 = cord > kingCord and firstBit(b) or lastBit(b)

    #  If diagonal
    if board.variant in ASEAN_VARIANTS:
        pass
    else:
        if dir <= 3 and bitPosArray[cord1] & \
                (board.boards[opcolor][QUEEN] | board.boards[opcolor][BISHOP]):
            return True

#  Rank / file
    if board.variant in ASEAN_VARIANTS:
        if dir >= 4 and bitPosArray[cord1] & \
                board.boards[opcolor][ROOK]:
            return True
    else:
        if dir >= 4 and bitPosArray[cord1] & \
                (board.boards[opcolor][QUEEN] | board.boards[opcolor][ROOK]):
            return True

    return False


def staticExchangeEvaluate(board, moveOrTcord, color=None):
    """ The GnuChess Static Exchange Evaluator (or SEE for short).
    First determine the target square.  Create a bitboard of all squares
    attacking the target square for both sides.  Using these 2 bitboards,
    we take turn making captures from smallest piece to largest piece.
    When a sliding piece makes a capture, we check behind it to see if
    another attacker piece has been exposed.  If so, add this to the bitboard
    as well.  When performing the "captures", we stop if one side is ahead
    and doesn't need to capture, a form of pseudo-minimaxing. """

    #
    # Notice: If you use the tcord version, the color is the color attacked, and
    #         the color to witch the score is relative.
    #

    swaplist = [0]

    if color is None:
        move = moveOrTcord
        flag = move >> 12
        fcord = (move >> 6) & 63
        tcord = move & 63

        color = board.friends[BLACK] & bitPosArray[fcord] and BLACK or WHITE
        opcolor = 1 - color
        boards = board.boards[color]
        opboards = board.boards[opcolor]

        ours = getAttacks(board, tcord, color)
        ours = clearBit(ours, fcord)
        theirs = getAttacks(board, tcord, opcolor)

        if xray[board.arBoard[fcord]]:
            ours, theirs = addXrayPiece(board, tcord, fcord, color, ours,
                                        theirs)

        from pychess.Variants import variants
        PROMOTIONS = variants[board.variant].PROMOTIONS
        if flag in PROMOTIONS:
            swaplist = [PIECE_VALUES[flag - 3] - PAWN_VALUE]
            lastval = -PIECE_VALUES[flag - 3]
        else:
            if flag == ENPASSANT:
                swaplist = [PAWN_VALUE]
            else:
                swaplist = [PIECE_VALUES[board.arBoard[tcord]]]
            lastval = -PIECE_VALUES[board.arBoard[fcord]]

    else:
        tcord = moveOrTcord
        opcolor = 1 - color
        boards = board.boards[color]
        opboards = board.boards[opcolor]

        ours = getAttacks(board, tcord, color)
        theirs = getAttacks(board, tcord, opcolor)

        lastval = -PIECE_VALUES[board.arBoard[tcord]]

    while theirs:
        for piece in range(PAWN, KING + 1):
            r = theirs & opboards[piece]
            if r:
                cord = firstBit(r)
                theirs = clearBit(theirs, cord)
                if xray[piece]:
                    ours, theirs = addXrayPiece(board, tcord, cord, color,
                                                ours, theirs)
                swaplist.append(swaplist[-1] + lastval)
                lastval = PIECE_VALUES[piece]
                break

        if not ours:
            break

        for piece in range(PAWN, KING + 1):
            r = ours & boards[piece]
            if r:
                cord = firstBit(r)
                ours = clearBit(ours, cord)
                if xray[piece]:
                    ours, theirs = addXrayPiece(board, tcord, cord, color,
                                                ours, theirs)
                swaplist.append(swaplist[-1] + lastval)
                lastval = -PIECE_VALUES[piece]
                break

    #  At this stage, we have the swap scores in a list.  We just need to
    #  mini-max the scores from the bottom up to the top of the list.

    for n in range(len(swaplist) - 1, 0, -1):
        if n & 1:
            if swaplist[n] <= swaplist[n - 1]:
                swaplist[n - 1] = swaplist[n]
        else:
            if swaplist[n] >= swaplist[n - 1]:
                swaplist[n - 1] = swaplist[n]

    return swaplist[0]


xray = (False, True, False, True, True, True, False)


def addXrayPiece(board, tcord, fcord, color, ours, theirs):
    """ This is used by swapOff.
    The purpose of this routine is to find a piece which attack through
    another piece (e.g. two rooks, Q+B, B+P, etc.) Color is the side attacking
    the square where the swapping is to be done. """

    dir = directions[tcord][fcord]
    a = rays[fcord][dir] & board.blocker
    if not a:
        return ours, theirs

    if tcord < fcord:
        ncord = firstBit(a)
    else:
        ncord = lastBit(a)

    piece = board.arBoard[ncord]
    if board.variant in ASEAN_VARIANTS:
        cond = piece == ROOK and dir > 3
    else:
        cond = piece == QUEEN or (
            piece == ROOK and dir > 3) or (
            piece == BISHOP and dir < 4)
    if cond:
        bit = bitPosArray[ncord]
        if bit & board.friends[color]:
            ours |= bit
        else:
            theirs |= bit

    return ours, theirs


def defends(board, fcord, tcord):
    """ Could fcord attack tcord if the piece on tcord wasn't on the team of
        fcord?
        Doesn't test check. """

    # Work on a board copy, as we are going to change some stuff
    board = board.clone()

    if board.friends[WHITE] & bitPosArray[fcord]:
        color = WHITE
    else:
        color = BLACK
    opcolor = 1 - color

    boards = board.boards[color]
    opboards = board.boards[opcolor]

    # To see if we now defend the piece, we have to "give" it to the other team
    piece = board.arBoard[tcord]

    # backup = boards[piece]
    # opbackup = opboards[piece]

    boards[piece] &= notBitPosArray[tcord]
    opboards[piece] |= bitPosArray[tcord]
    board.friends[color] &= notBitPosArray[tcord]
    board.friends[opcolor] |= bitPosArray[tcord]

    # Can we "attack" the piece now?
    backupColor = board.color
    board.setColor(color)
    from .lmovegen import newMove
    from .validator import validateMove
    islegal = validateMove(board, newMove(fcord, tcord))
    board.setColor(backupColor)

    # We don't need to set the board back, as we work on a copy
    # boards[piece] = backup
    # opboards[piece] = opbackup
    # board.friends[color] |= bitPosArray[tcord]
    # board.friends[opcolor] &= notBitPosArray[tcord]

    return islegal
