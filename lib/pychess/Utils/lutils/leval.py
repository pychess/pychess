
################################################################################
# The purpose of this module, is to give a certain position a score. The       #
# greater the score, the better the position                                   #
################################################################################

from pychess.Utils.const import *
from ldata import *
from LBoard import LBoard
from lsort import staticExchangeEvaluate
from lmove import newMove

#from random import randint
randomval = 0 #randint(8,12)/10.

def evaluateComplete (board, color, balanced=False):
    """ A detailed evaluation function, taking into account
        several positional factors """
    
    s, phase = evalMaterial (board, color)
    s += evalKingTropism (board, color, phase)
    s += evalKnights (board, color, phase)
    s += evalBishops (board, color, phase)
    s += evalTrappedBishops (board, color, phase)
    s += evalRooks (board, color, phase)
    s += evalKing (board, color, phase)
    s += evalDev (board, color, phase)
    s += evalPawnStructure (board, color, phase)
    s += evalDoubleQR7 (board, color, phase)
    
    s += randomval
    
    if balanced:
        s -= evalKingTropism (board, 1-color, phase)
        s -= evalKnights (board, 1-color, phase)
        s -= evalPawnStructure (board, 1-color, phase)
        s -= evalBishops (board, 1-color, phase)
        s -= evalTrappedBishops (board, 1-color, phase)
        s -= evalRooks (board, 1-color, phase)
    
    return s

################################################################################
# evalMaterial                                                                 #
################################################################################

def evalMaterial (board, color):
    
    pieces = board.boards
    opcolor = 1-color
    
    material = [0, 0]
    for piece in range(PAWN, KING):
        material[WHITE] += PIECE_VALUES[piece] * bitLength(pieces[WHITE][piece])
        material[BLACK] += PIECE_VALUES[piece] * bitLength(pieces[BLACK][piece])
    
    phase = 8 - (material[WHITE] + material[BLACK]) / 1150
    
    # If both sides are equal, we don't need to compute anything!
    if material[BLACK] == material[WHITE]:
        return 0, phase
    
    matTotal = sum(material)
    
    # Who is leading the game, material-wise?
    if material[color] > material[opcolor]:
        leading = color
    else: leading = opcolor
    
    pawns = bitLength(pieces[leading][PAWN])
    matDiff = material[leading] - material[1-leading]
    val = min(2400, matDiff) + \
          (matDiff * (12000-matTotal) * pawns) / (6400 * (pawns+1))
    
    if leading == color:
        return val, phase
    return -val, phase
    #if color == WHITE:
        #return val, phase
    #else: return -val, phase
    
################################################################################
# evalKingTropism                                                              #
################################################################################

pawnTropism = [[0]*64 for i in xrange(64)]
bishopTropism = [[0]*64 for i in xrange(64)]
knightTropism = [[0]*64 for i in xrange(64)]
rookTropism = [[0]*64 for i in xrange(64)]
queenTropism = [[0]*64 for i in xrange(64)]

for pcord in xrange(64):
    for kcord in xrange(pcord+1, 64):
        pawnTropism[pcord][kcord] = pawnTropism[kcord][pcord] = \
            (14 - taxicab[pcord][kcord])**2 * 10/169 # 0 - 10
        knightTropism[pcord][kcord] = knightTropism[kcord][pcord] = \
            (6-distance[KNIGHT][pcord][kcord])**2 * 2 # 0 - 50
        bishopTropism[pcord][kcord] = bishopTropism[kcord][pcord] = \
            (14 - distance[BISHOP][pcord][kcord] * sdistance[pcord][kcord])**2 * 30/169 # 0 - 30 
        rookTropism[pcord][kcord] = rookTropism[kcord][pcord] = \
            (14 - distance[ROOK][pcord][kcord] * sdistance[pcord][kcord])**2 * 40/169 # 0 - 40
        queenTropism[pcord][kcord] = queenTropism[kcord][pcord] = \
            (14 - distance[QUEEN][pcord][kcord] * sdistance[pcord][kcord])**2 * 50/169 # 0 - 50

def evalKingTropism (board, color, phase):
    """ All other things being equal, having your Knights, Queens and Rooks
        close to the opponent's king is a good thing """
    
    opcolor = 1-color
    pieces = board.boards[color]
    oppieces = board.boards[opcolor]
    
    if phase > 4 or not oppieces[QUEEN]:
        opking = board.kings[opcolor]
    else:
        opking = firstBit(oppieces[QUEEN])
    
    score = 0
    
    for cord in iterBits(pieces[PAWN]):
        score += pawnTropism[cord][opking]
    
    for cord in iterBits(pieces[KNIGHT]):
        score += knightTropism[cord][opking]
    
    for cord in iterBits(pieces[BISHOP]):
        score += bishopTropism[cord][opking]
    
    for cord in iterBits(pieces[ROOK]):
        score += rookTropism[cord][opking]
    
    for cord in iterBits(pieces[QUEEN]):
        score += queenTropism[cord][opking]
    
    return score

################################################################################
# evalPawnStructure                                                            #
################################################################################

pawntable = {}

def evalPawnStructure (board, color, phase):
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
    
    opcolor = 1-color
    opking = board.kings[opcolor]
    opboards = board.boards[opcolor]
    oppawns = opboards[PAWN]
    
    #ptable = PawnTab[color] + (PawnHashKey & PHashMask)
    #if ptable->phase == phase and ptable->pkey == KEY(PawnHashKey):
    if board.pawnhash in pawntable:
        score, passed, weaked = pawntable[board.pawnhash]
        
    else:
        score = 0
        passed = createBoard(0)
        weaked = createBoard(0)
        nfile = [0]*8
        pScoreBoard = pawnScoreBoard[color]
        for cord in iterBits(pawns):
            score += pScoreBoard[cord] * 2
            
            # Passed pawns
            if not oppawns & passedPawnMask[color][cord]:
                if (color == WHITE and not fromToRay[cord][cord|56] & pawns) or\
                   (color == BLACK and not fromToRay[cord][cord&7] & pawns):
                    passed |= bitPosArray[cord]
                    score += (passedScores[color][cord>>3] * phase) / 12
            
            # Backward pawns
            backward = False
            
            if color == WHITE:
                i = cord + 8
            else:
                i = cord - 8
            
            ptype = color == WHITE and PAWN or BPAWN
            opptype = color == BLACK and PAWN or BPAWN
            
            if not 0 <= i <= 63:
                print toString(pawns)
                print board
            if not (passedPawnMask[opcolor][i] & ~fileBits[cord&7] & pawns) and\
                    board.arBoard[i] != PAWN:
                n1 = bitLength (pawns & moveArray[opptype][i])
                n2 = bitLength (oppawns & moveArray[ptype][i])
                if n1 < n2:
                    backward = True

            if not backward and bitPosArray[cord] & brank7[opcolor]:
                i = i + (color == WHITE and 8 or -8)
                if not (passedPawnMask[opcolor][i] & ~fileBits[1] & pawns):
                    n1 = bitLength (pawns & moveArray[opptype][i])
                    n2 = bitLength (oppawns & moveArray[ptype][i])
                    if n1 < n2:
                        backward = True
            
            if backward:
                weaked |= bitPosArray[cord]
                score += -(8+phase) # Backward pawn penalty
            
            # Pawn base under attack
            if moveArray[ptype][cord] & oppawns and \
               moveArray[ptype][cord] & pawns:
                score += -18
     
            # Increment file count for isolani & doubled pawn evaluation
            nfile[cord&7] += 1
        
        for i in xrange(8):
            # Doubled pawns
            if nfile[i] > 1:
                score += -(8+phase)
            
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
        if bitLength(pawns) == 8:
            score -= 10
        
        # Detect stonewall formation in enemy
        if stonewall[opcolor] & oppawns == stonewall[opcolor]:
            score -= 10
        # Detect stonewall formation in our pawns
        if stonewall[color] & pawns == stonewall[color]:
            score += 10
        
        # Penalize Locked pawns
        n = bitLength((pawns >> 8) & oppawns & lbox)
        score -= n * 10
        # Opposite for opponent
        n = bitLength((oppawns << 8) & pawns & lbox)
        score += n * 10
        
        
        # Save the score into the pawn hash table */ 
        pawntable[board.pawnhash] = (score, passed, weaked)
    
    ############################################################################
    #  This section of the pawn code cannot be saved into the pawn hash as     #
    #  they depend on the position of other pieces.  So they have to be        #
    #  calculated again.                                                       #
    ############################################################################
        
    # Pawn on f6/c6 with Queen against castled king is very strong
    
    if boards[QUEEN] and opking > H6:
        if pawns & bitPosArray[F6] and distance[KING][opking][G7] <= 1:
            score += 40
        if pawns & bitPosArray[C6] and distance[KING][opking][B7] <= 1:
            score += 40
    
    if opboards[QUEEN] and king < A3:
        if oppawns & bitPosArray[F3] and distance[KING][king][G2] <= 1:
            score -= 20
        if oppawns & bitPosArray[C3] and distance[KING][king][B2] <= 1:
            score -= 20
        
    # Connected passed pawns on 6th or 7th rank
    t = passed & brank67[color]
    opMajorCount = sum(bitLength(opboards[p]) for p in xrange(KNIGHT, KING))
    if t and opMajorCount == 1:
        n1 = FILE(opking)
        n2 = RANK(opking)
        for f in xrange(7):
            if t & fileBits[f] and t & fileBits[f+1] and \
                    (n1 < f-1 or n1 > f+1 or (color == WHITE and n2 < 4) or \
                                             (color == BLACK and n2 > 3)):
                score += 50
        
    # Penalize Pawn on d2,e2/d7,e7 is blocked
    blocker = board.blocker
    if color == WHITE and ((pawns & d2e2[WHITE]) >> 8) & blocker:
        score -= 48
    elif color == BLACK and ((pawns & d2e2[BLACK]) << 8) & blocker:
        score -= 48
        
    # Enemy has no pieces & King is outcolor of passed pawn square
    if passed and not opMajorCount:
        for cord in iterBits(passed):
            if board.color == color:
                if not squarePawnMask[color][cord] & opboards[KING]:
                    score += 1100 * passedScores[color][RANK(cord)] / 550
            else:
                if not moveArray[KING][opking] & squarePawnMask[color][cord]:
                    score += 1100 * passedScores[color][RANK(cord)] / 550
        
    # If both colors are castled on different colors, bonus for pawn storms
    if abs(FILE(king)-FILE(opking)) >= 4 and phase < 6:
        n1 = FILE(opking)
        p = (isolaniMask[n1] | fileBits[n1]) & pawns
        score += sum(10 * (5 - distance[KING][c][opking]) for c in iterBits(p))
    
    return score

################################################################################
# evalBateries                                                                 #
################################################################################

def evalDoubleQR7 (board, color, phase):
    """ Tests for QR, RR, QB and BB combos on the 7th rank. These are dangerous
        to kings, and good at killing pawns """

    opcolor = 1-board.color
    boards = board.boards[color]
    opboards = board.boards[opcolor]
    
    if bitLength((boards[QUEEN] | boards[ROOK]) & brank7[color]) >= 2 and \
        (opboards[KING] & brank8[color] or opboards[PAWN] & brank7[color]):
        return 30
    
    return 0

def evalKing (board, color, phase):
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
    
    # If we are in endgame
    if phase >= 6:
        return endingKing[board.kings[color]] - endingKing[board.kings[1-color]]
    
    return 0
    
def evalKnights (board, color, phase):
    outerring = ~lbox
    score = -15 * bitLength (board.boards[color][KNIGHT] & outerring)
    return score-score/phase

def evalDev (board, color, phase):
    """
    Calculate the development score for side (for opening only).
    Penalize the following.
    .  Uncastled and cannot castled
    .  Early queen move.
    -  bad wing pawns
    """
    
    # If we are castled or beyond the 20th move, no more evalDev
    
    if len(board.history) >= 38:
        return 0
    
    score = 0
    
    if not board.hasCastled[WHITE]:
    
        wboards = board.boards[WHITE]
        pawns = wboards[PAWN]
        
        # We don't encourage castling, but it should always be possible
        if not board.castling & W_OOO:
            score -= 40
        if not board.castling & W_OO:
            score -= 50
        
        # Should keep queen home
        cord = firstBit(wboards[QUEEN])
        if cord != D1: score -= 30
        
        qpawns = max(qwwingpawns1 & pawns, qwwingpawns2 & pawns) 
        kpawns = max(kwwingpawns1 & pawns, kwwingpawns2 & pawns) 
        
        if qpawns != 2 and kpawns != 2:
            # Structure destroyed in both sides
            score -= 35
        else:
            # Discourage any wing pawn moves
            score += (qpawns+kpawns) *6
    
    if not board.hasCastled[BLACK]:
        
        bboards = board.boards[BLACK]
        pawns = bboards[PAWN]
        
        if not board.castling & B_OOO:
            score += 40
        if not board.castling & B_OO:
            score += 50
        
        cord = firstBit(bboards[QUEEN])
        if cord != D8: score += 30
        
        qpawns = max(qbwingpawns1 & pawns, qbwingpawns2 & pawns) 
        kpawns = max(kbwingpawns1 & pawns, kbwingpawns2 & pawns) 
        
        if qpawns != 2 and kpawns != 2:
            # Structure destroyed in both sides
            score += 35
        else:
            # Discourage any wing pawn moves
            score -= (qpawns+kpawns) *6
    
    if color == BLACK:
        score = -score
    
    return score

def evalBishops (board, color, phase):
    
    opcolor = 1-color
    pawns = board.boards[color][PAWN]
    bishops = board.boards[color][BISHOP]
    opbishops = board.boards[opcolor][BISHOP]
    oppawns = board.boards[opcolor][PAWN]
    
    arBoard = board.arBoard
    score = 0
    
    # Avoid having too many pawns on you bishops color
    
    if bitLength (bishops) == 1:
        if bishops & WHITE_SQUARES:
            s =   bitLength(pawns & WHITE_SQUARES) \
                + bitLength(oppawns & WHITE_SQUARES)/2
                
        else: s =   bitLength(pawns & BLACK_SQUARES) \
                  + bitLength(oppawns & BLACK_SQUARES)/2
                  
        score -= s
    
    # In later games, try to get your pices away from opponent bishop colos
    
    if phase > 6 and bitLength (opbishops) == 1:
        if opbishops & WHITE_SQUARES:
            s = bitLength(board.friends[color] & WHITE_SQUARES)
        else: s = bitLength(board.friends[color] & BLACK_SQUARES)
                  
        score -= s
    
    # Avoid wasted moves
    
    if color == WHITE:
        if bishops & bitPosArray[B5] and arBoard[C6] == EMPTY and \
                oppawns & bitPosArray[B7] and oppawns & bitPosArray[C7]:
            score -= 25
        if bishops & bitPosArray[G5] and arBoard[F6] == EMPTY and \
                oppawns & bitPosArray[F7] and oppawns & bitPosArray[G7]:
            score -= 25
    
    else:
        if bishops & bitPosArray[B4] and arBoard[C3] == EMPTY and \
                oppawns & bitPosArray[B2] and oppawns & bitPosArray[C2]:
            score -= 25
        if bishops & bitPosArray[G4] and arBoard[F3] == EMPTY and \
                oppawns & bitPosArray[F2] and oppawns & bitPosArray[G2]:
            score -= 25
    
    return score

def evalTrappedBishops (board, color, phase):
    """ Check for bishops trapped at A2/H2/A7/H7 """
    
    opcolor = 1-color
    opbishops = board.boards[opcolor][BISHOP]
    pawns = board.boards[color][PAWN]
    score = 0
    
    # Don't waste time
    if not opbishops:
        return 0
    
    if color == WHITE:
        if opbishops & bitPosArray[A2] and pawns & bitPosArray[B3]:
            see = staticExchangeEvaluate(board, newMove(A2,B3))
            if see < 0:
                score += see
        if opbishops & bitPosArray[H2] and pawns & bitPosArray[G3]:
            see = staticExchangeEvaluate(board, newMove(H2,G3))
            if see < 0:
                score += see
    
    else:
        if opbishops & bitPosArray[A7] and pawns & bitPosArray[B6]:
            see = staticExchangeEvaluate(board, newMove(A7,B6))
            if see < 0:
                score += see
        if opbishops & bitPosArray[H7] and pawns & bitPosArray[G6]:
            see = staticExchangeEvaluate(board, newMove(H7,G6))
            if see < 0:
                score += see

    
    return score

def evalRooks (board, color, phase):
    """ rooks on open/half-open files """

    opcolor = 1-color
    boards = board.boards[color]
    rooks = boards[ROOK]
    
    if not rooks:
        return 0
    
    opboards = board.boards[opcolor]
    opking = board.kings[opcolor]
    
    score = 0
    
    for cord in iterBits(rooks):
        file = cord & 7
        if phase < 7:
            if not boards[PAWN] & fileBits[file]:
                if file == 5 and opking & 7 >= 4:
                    score += 40
                score += 5
                if not boards[PAWN] & fileBits[file]:
                    score += 6
    
    return score
