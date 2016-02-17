from __future__ import absolute_import

# The purpose of this module, is to give a certain position a score.
# The greater the score, the better the position

from pychess.Utils.const import WHITE, BLACK, LOSERSCHESS, SUICIDECHESS,\
    ASEAN_VARIANTS, ATOMICCHESS, CRAZYHOUSECHESS,\
    BPAWN, BISHOP, KNIGHT, QUEEN, KING, PAWN, ROOK, \
    CAS_FLAGS, H7, B6, A7, H2, G3, A2, B3, G6, D1, G8, B8, G1, B1
from .bitboard import iterBits, firstBit, lsb
from .ldata import fileBits, bitPosArray, PIECE_VALUES, FILE, RANK,\
    WHITE_SQUARES, BLACK_SQUARES, ASEAN_PIECE_VALUES, ATOMIC_PIECE_VALUES, CRAZY_PIECE_VALUES,\
    kwingpawns1, kwingpawns2, qwingpawns1, qwingpawns2, frontWall, endingKing,\
    brank7, brank8, distance, isolaniMask, d2e2, passedScores, squarePawnMask,\
    moveArray, brank67, lbox, stonewall, isolani_normal, isolani_weaker,\
    passedPawnMask, fromToRay, pawnScoreBoard, sdistance, taxicab
from .lsort import staticExchangeEvaluate
from .lmovegen import newMove
from ctypes import create_string_buffer, memset
from struct import Struct

# from random import randint
randomval = 0  # randint(8,12)/10.


def evaluateComplete(board, color):
    """ A detailed evaluation function, taking into account
        several positional factors """

    s, phase = evalMaterial(board, color)
    if board.variant in (LOSERSCHESS, SUICIDECHESS):
        return s
    s += evalBishops(board, color, phase) - evalBishops(board, 1 - color,
                                                        phase)
    s += evalRooks(board, color, phase) - evalRooks(board, 1 - color, phase)
    s += evalDoubleQR7(board, color, phase) - evalDoubleQR7(board, 1 - color,
                                                            phase)
    s += evalKing(board, color, phase) - evalKing(board, 1 - color, phase)
    s += evalKingTropism(board, color, phase) - evalKingTropism(board, 1 -
                                                                color, phase)
    if board.variant in ASEAN_VARIANTS:
        return s
    s += evalDev(board, color, phase) - evalDev(board, 1 - color, phase)
    if board.variant == ATOMICCHESS:
        return s
    pawnScore, passed, weaked = cacheablePawnInfo(board, phase)
    s += pawnScore if color == WHITE else -pawnScore
    s += evalPawnStructure(board, color, phase, passed,
                           weaked) - evalPawnStructure(board, 1 - color, phase,
                                                       passed, weaked)

    s += evalTrappedBishops(board, color)
    s += randomval

    return s

################################################################################
# evalMaterial                                                                 #
################################################################################


def evalMaterial(board, color):
    pieceCount = board.pieceCount
    opcolor = 1 - color
    material = [0, 0]
    if board.variant == CRAZYHOUSECHESS:
        for piece in range(PAWN, KING):
            material[WHITE] += CRAZY_PIECE_VALUES[piece] * pieceCount[WHITE][
                piece]
            material[BLACK] += CRAZY_PIECE_VALUES[piece] * pieceCount[BLACK][
                piece]
            material[WHITE] += CRAZY_PIECE_VALUES[piece] * board.holding[
                WHITE][piece]
            material[BLACK] += CRAZY_PIECE_VALUES[piece] * board.holding[
                BLACK][piece]
    elif board.variant == LOSERSCHESS:
        for piece in range(PAWN, KING):
            material[WHITE] += pieceCount[WHITE][piece]
            material[BLACK] += pieceCount[BLACK][piece]
    elif board.variant == SUICIDECHESS:
        for piece in range(PAWN, KING + 1):
            material[WHITE] += pieceCount[WHITE][piece]
            material[BLACK] += pieceCount[BLACK][piece]
    elif board.variant == ATOMICCHESS:
        for piece in range(PAWN, KING + 1):
            material[WHITE] += ATOMIC_PIECE_VALUES[piece] * pieceCount[WHITE][
                piece]
            material[BLACK] += ATOMIC_PIECE_VALUES[piece] * pieceCount[BLACK][
                piece]
    elif board.variant in ASEAN_VARIANTS:
        for piece in range(PAWN, KING + 1):
            material[WHITE] += ASEAN_PIECE_VALUES[piece] * pieceCount[WHITE][
                piece]
            material[BLACK] += ASEAN_PIECE_VALUES[piece] * pieceCount[BLACK][
                piece]
    else:
        for piece in range(PAWN, KING):
            material[WHITE] += PIECE_VALUES[piece] * pieceCount[WHITE][piece]
            material[BLACK] += PIECE_VALUES[piece] * pieceCount[BLACK][piece]

    phase = max(1, 8 - (material[WHITE] + material[BLACK]) // 1150)

    # If both sides are equal, we don't need to compute anything!
    if material[BLACK] == material[WHITE]:
        return 0, phase

    matTotal = sum(material)

    # Who is leading the game, material-wise?
    if material[color] > material[opcolor]:
        leading = color
    else:
        leading = opcolor

    if board.variant in (LOSERSCHESS, SUICIDECHESS):
        val = material[leading] - material[1 - leading]
        if leading == 1 - color:
            return val, phase
        return -val, phase

    pawns = pieceCount[leading][PAWN]
    matDiff = material[leading] - material[1 - leading]
    val = min(2400, matDiff) + (matDiff * (12000 - matTotal) * pawns) // (6400 * (pawns + 1))

    if leading == color:
        return val, phase
    return -val, phase

    ################################################################################
    # evalKingTropism                                                              #
    ################################################################################


pawnTropism = [[0] * 64 for i in range(64)]
bishopTropism = [[0] * 64 for i in range(64)]
knightTropism = [[0] * 64 for i in range(64)]
rookTropism = [[0] * 64 for i in range(64)]
queenTropism = [[0] * 64 for i in range(64)]

for pcord in range(64):
    for kcord in range(pcord + 1, 64):
        pawnTropism[pcord][kcord] = pawnTropism[kcord][pcord] = \
            (14 - taxicab[pcord][kcord])**2 * 10 / 169
        knightTropism[pcord][kcord] = knightTropism[kcord][pcord] = \
            (6 - distance[KNIGHT][pcord][kcord])**2 * 2
        bishopTropism[pcord][kcord] = bishopTropism[kcord][pcord] = \
            (14 - distance[BISHOP][pcord][kcord] * sdistance[pcord][kcord])**2 * 30 // 169
        rookTropism[pcord][kcord] = rookTropism[kcord][pcord] = \
            (14 - distance[ROOK][pcord][kcord] * sdistance[pcord][kcord])**2 * 40 // 169
        queenTropism[pcord][kcord] = queenTropism[kcord][pcord] = \
            (14 - distance[QUEEN][pcord][kcord] * sdistance[pcord][kcord])**2 * 50 // 169

tropisms = {
    PAWN: pawnTropism,
    KNIGHT: knightTropism,
    BISHOP: bishopTropism,
    ROOK: rookTropism,
    QUEEN: queenTropism
}


def evalKingTropism(board, color, phase):
    """ All other things being equal, having your Knights, Queens and Rooks
        close to the opponent's king is a good thing """
    _tropisms = tropisms
    _lsb = lsb
    opcolor = 1 - color
    pieces = board.boards[color]

    opking = board.kings[opcolor]

    score = 0
    for piece in range(KNIGHT, KING):
        #    for piece in range(PAWN, KING):
        bitboard = pieces[piece]
        tropism = _tropisms[piece]
        # inlined iterBits()
        while bitboard:
            bit = bitboard & -bitboard
            score += tropism[_lsb[bit]][opking]
            bitboard -= bit
    return score

################################################################################
# evalPawnStructure                                                            #
################################################################################

# For pawn hash, don't use buckets. Store:
# key         high 16 bits of pawn hash key
# score       score from white's point of view
# passed      bitboard of passed pawns
# weaked      bitboard of weak pawns
pawnEntryType = Struct('=H h Q Q')
PAWN_HASH_SIZE = 16384
PAWN_PHASE_KEY = (0x343d, 0x055d, 0x3d3c, 0x1a1c, 0x28aa, 0x19ee, 0x1538,
                  0x2a99)
pawntable = create_string_buffer(PAWN_HASH_SIZE * pawnEntryType.size)


def clearPawnTable():
    memset(pawntable, 0, PAWN_HASH_SIZE * pawnEntryType.size)


def probePawns(board, phase):
    index = (board.pawnhash % PAWN_HASH_SIZE) ^ PAWN_PHASE_KEY[phase - 1]
    key, score, passed, weaked = pawnEntryType.unpack_from(pawntable, index *
                                                           pawnEntryType.size)
    if key == (board.pawnhash >> 14) & 0xffff:
        return score, passed, weaked
    return None


def recordPawns(board, phase, score, passed, weaked):
    index = (board.pawnhash % PAWN_HASH_SIZE) ^ PAWN_PHASE_KEY[phase - 1]
    key = (board.pawnhash >> 14) & 0xffff
    pawnEntryType.pack_into(pawntable, index * pawnEntryType.size, key, score,
                            passed, weaked)


def cacheablePawnInfo(board, phase):
    entry = probePawns(board, phase)
    if entry:
        return entry

    score = 0
    passed = 0
    weaked = 0

    for color in WHITE, BLACK:
        opcolor = 1 - color
        pawns = board.boards[color][PAWN]
        oppawns = board.boards[opcolor][PAWN]

        nfile = [0] * 8
        pScoreBoard = pawnScoreBoard[color]
        for cord in iterBits(pawns):
            score += pScoreBoard[cord] * 2

            # Passed pawns
            if not oppawns & passedPawnMask[color][cord]:
                if (color == WHITE and not fromToRay[cord][cord | 56] & pawns) or\
                   (color == BLACK and not fromToRay[cord][cord & 7] & pawns):
                    passed |= bitPosArray[cord]
                    score += (passedScores[color][cord >> 3] * phase) // 12

            # Backward pawns
            backward = False

            if color == WHITE:
                i = cord + 8
            else:
                i = cord - 8

            ptype = color == WHITE and PAWN or BPAWN
            opptype = color == BLACK and PAWN or BPAWN

            if not (passedPawnMask[opcolor][i] & ~fileBits[cord & 7] & pawns) and\
                    board.arBoard[i] != PAWN:
                n1 = bin(pawns & moveArray[opptype][i]).count("1")
                n2 = bin(oppawns & moveArray[ptype][i]).count("1")
                if n1 < n2:
                    backward = True

            if not backward and bitPosArray[cord] & brank7[opcolor]:
                i = i + (color == WHITE and 8 or -8)
                if not (passedPawnMask[opcolor][i] & ~fileBits[1] & pawns):
                    n1 = bin(pawns & moveArray[opptype][i]).count("1")
                    n2 = bin(oppawns & moveArray[ptype][i]).count("1")
                    if n1 < n2:
                        backward = True

                if not backward and bitPosArray[cord] & brank7[opcolor]:
                    i = i + (color == WHITE and 8 or -8)
                    if not (passedPawnMask[opcolor][i] & ~fileBits[1] & pawns):
                        n1 = bin(pawns & moveArray[opptype][i]).count("1")
                        n2 = bin(oppawns & moveArray[ptype][i]).count("1")
                        if n1 < n2:
                            backward = True

            if backward:
                weaked |= bitPosArray[cord]
                score += -(8 + phase)  # Backward pawn penalty

            # Pawn base under attack
            if moveArray[ptype][cord] & oppawns and \
               moveArray[ptype][cord] & pawns:
                score += -18

    # Increment file count for isolani & doubled pawn evaluation
            nfile[cord & 7] += 1

        for i in range(8):
            # Doubled pawns
            if nfile[i] > 1:
                score += -(8 + phase)

            # Isolated pawns
            if nfile[i] and not pawns & isolaniMask[i]:
                if not fileBits[i] & oppawns:
                    # Isolated on a half-open file
                    score += isolani_weaker[i] * nfile[i]
                else:
                    # Normal isolated pawn
                    score += isolani_normal[i] * nfile[i]
                weaked |= pawns & fileBits[i]

        # Penalize having eight pawns
        if board.pieceCount[color][PAWN] == 8:
            score -= 10

        # Detect stonewall formation in our pawns
        if stonewall[color] & pawns == stonewall[color]:
            score += 10

        # Penalize Locked pawns
        n = bin((pawns >> 8) & oppawns & lbox).count("1")
        score -= n * 10

        # Switch point of view when switching colors
        score = -score

    recordPawns(board, phase, score, passed, weaked)
    return score, passed, weaked


def evalPawnStructure(board, color, phase, passed, weaked):
    """
    Pawn evaluation is based on the following factors:
    1.  Pawn square tables.
    2.  Passed pawns.
    3.  Backward pawns.
    4.  Pawn base under attack.
    5.  Doubled pawns
    6.  Isolated pawns
    7.  Connected passed pawns on 6/7th rank.
    8.  Unmoved & blocked d, e pawn
    9.  Passed pawn which cannot be caught.
    10. Pawn storms.
    Notice: The function has better precicion for current player
    """

    boards = board.boards[color]

    if not boards[PAWN]:
        return 0

    king = board.kings[color]
    pawns = boards[PAWN]

    opcolor = 1 - color
    opking = board.kings[opcolor]
    opboards = board.boards[opcolor]

    score = 0
    passed &= pawns
    weaked &= pawns

    # This section of the pawn code cannot be saved into the pawn hash as
    # they depend on the position of other pieces.  So they have to be
    # calculated again.
    if passed:
        # Connected passed pawns on 6th or 7th rank
        t = passed & brank67[color]
        opMajorCount = 0
        for p in range(KNIGHT, KING):
            opMajorCount += board.pieceCount[opcolor][p]
        if t and opMajorCount == 1:
            n1 = FILE(opking)
            n2 = RANK(opking)
            for f in range(7):
                if t & fileBits[f] and t & fileBits[f + 1] and \
                        (n1 < f - 1 or n1 > f + 1 or (color == WHITE and n2 < 4) or
                            (color == BLACK and n2 > 3)):
                    score += 50

            # Enemy has no pieces & King is outcolor of passed pawn square
        if not opMajorCount:
            for cord in iterBits(passed):
                if board.color == color:
                    if not squarePawnMask[color][cord] & opboards[KING]:
                        score += passedScores[color][RANK(cord)]
                else:
                    if not moveArray[KING][opking] & squarePawnMask[color][
                            cord]:
                        score += passedScores[color][RANK(cord)]

        # Estimate if any majors are able to hunt us down
        for pawn in iterBits(passed):
            found_hunter = False
            if color == WHITE:
                prom_cord = 7 << 3 | FILE(pawn)
            else:
                prom_cord = FILE(pawn)
            distance_to_promotion = distance[PAWN][pawn][prom_cord]
            for piece in range(KNIGHT, KING + 1):
                for cord in iterBits(opboards[piece]):
                    hunter_distance = distance[piece][cord][prom_cord]
                    if hunter_distance <= distance_to_promotion:
                        found_hunter = True
                        break
                if found_hunter:
                    break
            if not found_hunter:
                score += passedScores[color][RANK(pawn)] // 5

    # Penalize Pawn on d2,e2/d7,e7 is blocked
    blocker = board.blocker
    if color == WHITE and ((pawns & d2e2[WHITE]) >> 8) & blocker:
        score -= 48
    elif color == BLACK and ((pawns & d2e2[BLACK]) << 8) & blocker:
        score -= 48

    # If both colors are castled on different colors, bonus for pawn storms
    if abs(FILE(king) - FILE(opking)) >= 4 and phase < 6:
        n1 = FILE(opking)
        p = (isolaniMask[n1] | fileBits[n1]) & pawns
        score += sum(10 * (5 - distance[KING][c][opking]) for c in iterBits(p))

    return score


# evalBateries
def evalDoubleQR7(board, color, phase):
    """ Tests for QR, RR, QB and BB combos on the 7th rank. These are dangerous
        to kings, and good at killing pawns """

    opcolor = 1 - board.color
    boards = board.boards[color]
    opboards = board.boards[opcolor]

    if bin((boards[QUEEN] | boards[ROOK]) & brank7[color]).count("1") >= 2 and \
            (opboards[KING] & brank8[color] or opboards[PAWN] & brank7[color]):
            return 30

    return 0


def evalKing(board, color, phase):
    # Should avoid situations like those:
    # r - - - n K - -
    # which makes forks more easy
    # and
    # R - - - K - - -
    # and
    # - - - - - - - -
    # - - - K - - - -
    # - - - - - - - -
    # - - - - - - - -
    # - - - - - - B -
    # which might turn bad

    # Also being check should be avoided, like
    # - q - - - K - r
    # and
    # - - - - - n - -
    # - - - K - - - R

    king = board.kings[color]

    # If we are in endgame, we want our king in the center, and theirs far away
    if phase >= 6:
        return endingKing[king]

    # else if castled, prefer having some pawns in front
    elif FILE(king) not in (3, 4) and RANK(king) in (0, 8):
        if color == WHITE:
            if FILE(king) < 3:
                wall1 = frontWall[color][B1]
            else:
                wall1 = frontWall[color][G1]
            wall2 = wall1 >> 8
        else:
            if FILE(king) < 3:
                wall1 = frontWall[color][B8]
            else:
                wall1 = frontWall[color][G8]
            wall2 = wall1 << 8

        pawns = board.boards[color][PAWN]
        total_in_front = bin(wall1 | wall2 & pawns).count("1")
        numbermod = (0, 3, 6, 9, 7, 5, 3)[total_in_front]

        s = bin(wall1 & pawns).count("1") * 2 + bin(wall2 & pawns).count("1")
        return (s * numbermod * 5) // 6

    return 0


def evalDev(board, color, phase):
    """
    Calculate the development score for side (for opening only).
    Penalize the following.
    .  Uncastled and cannot castled
    .  Early queen move.
    -  bad wing pawns
    """

    # If we are castled or beyond the 20th move, no more evalDev

    if board.plyCount >= 38:
        return 0

    score = 0

    if not board.hasCastled[color]:

        boards = board.boards[color]
        pawns = boards[PAWN]

        # We don't encourage castling, but it should always be possible
        if not board.castling & CAS_FLAGS[color][0]:
            score -= 40
        if not board.castling & CAS_FLAGS[color][1]:
            score -= 50

        # Should keep queen home
        cord = firstBit(boards[QUEEN])
        if cord != D1 + 56 * color:
            score -= 30

        qpawns = max(qwingpawns1[color] & pawns, qwingpawns2[color] & pawns)
        kpawns = max(kwingpawns1[color] & pawns, kwingpawns2[color] & pawns)

        if qpawns != 2 and kpawns != 2:
            # Structure destroyed in both sides
            score -= 35
        else:
            # Discourage any wing pawn moves
            score += (qpawns + kpawns) * 6

    return score


def evalBishops(board, color, phase):

    opcolor = 1 - color
    bishops = board.boards[color][BISHOP]
    if not bishops:
        return 0

    pawns = board.boards[color][PAWN]
    oppawns = board.boards[opcolor][PAWN]

    score = 0

    # Avoid having too many pawns on you bishop's color.
    # In late game phase, add a bonus for enemy pieces on your bishop's color.

    if board.pieceCount[color][BISHOP] == 1:
        squareMask = WHITE_SQUARES if (bishops &
                                       WHITE_SQUARES) else BLACK_SQUARES
        score = - bin(pawns & squareMask).count("1") \
                - bin(oppawns & squareMask).count("1") // 2
        if phase > 6:
            score += bin(board.friends[1 - color] & squareMask).count("1")

    return score


def evalTrappedBishops(board, color):
    """ Check for bishops trapped at A2/H2/A7/H7 """

    _bitPosArray = bitPosArray
    wbishops = board.boards[WHITE][BISHOP]
    bbishops = board.boards[BLACK][BISHOP]
    wpawns = board.boards[WHITE][PAWN]
    bpawns = board.boards[BLACK][PAWN]
    score = 0

    if bbishops:
        if bbishops & _bitPosArray[A2] and wpawns & _bitPosArray[B3]:
            see = staticExchangeEvaluate(board, newMove(A2, B3))
            if see < 0:
                score -= see
        if bbishops & _bitPosArray[H2] and wpawns & _bitPosArray[G3]:
            see = staticExchangeEvaluate(board, newMove(H2, G3))
            if see < 0:
                score -= see

    if wbishops:
        if wbishops & _bitPosArray[A7] and bpawns & _bitPosArray[B6]:
            see = staticExchangeEvaluate(board, newMove(A7, B6))
            if see < 0:
                score += see
        if wbishops & _bitPosArray[H7] and bpawns & _bitPosArray[G6]:
            see = staticExchangeEvaluate(board, newMove(H7, G6))
            if see < 0:
                score += see

    return score if color == WHITE else -score


def evalRooks(board, color, phase):
    """ rooks on open/half-open files """

    opcolor = 1 - color
    boards = board.boards[color]
    rooks = boards[ROOK]

    if not rooks:
        return 0

    opking = board.kings[opcolor]
    score = 0

    if phase < 7:
        for cord in iterBits(rooks):
            file = cord & 7
            if not boards[PAWN] & fileBits[file]:
                if file == 5 and opking & 7 >= 4:
                    score += 40
                score += 5
                if not boards[PAWN] & fileBits[file]:
                    score += 6

    return score
