
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
    
    s, phase = evalMaterial (board)
    s += evalKingTropism (board)
    s += evalKnights (board)
    s += evalBishops (board)
    s += evalTrappedBishops (board)
    s += evalRooks (board, phase)
    s += evalKing (board, phase)
    s += evalDev (board)
    s += evalPawnStructure (board, phase)
    
    s += randomval
    
    if balanced:
        opboard = LBoard(board)
        opboard.applyFen (board.asFen())
        opboard.setColor(1-board.color)
        s += evalKingTropism (opboard)
        s += evalPawnStructure (opboard, phase)
        s += evalBishops (opboard)
        s += evalTrappedBishops (opboard)
        s += evalRooks (opboard, phase)
    
    if color == WHITE:
        return s
    else: return -s

################################################################################
# evalMaterial                                                                 #
################################################################################

def evalMaterial (board):
    
    pieces = board.boards
    
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
    if material[BLACK] > material[WHITE]:
        # Black leading
        blackPawns = bitLength(pieces[BLACK][PAWN])
        matDiff = material[BLACK] - material[WHITE]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * blackPawns ) \
                / ( 6400 * ( blackPawns + 1 ) )
        return -val, phase
    else:
        # White leading
        whitePawns = bitLength(pieces[WHITE][PAWN])
        matDiff = material[WHITE] - material[BLACK]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * whitePawns ) \
                / ( 6400 * ( whitePawns + 1 ) )
        return val, phase

################################################################################
# evalKingTropism                                                              #
################################################################################

pawnTropism = [[0]*64 for i in range(64)]
bishopTropism = [[0]*64 for i in range(64)]
knightTropism = [[0]*64 for i in range(64)]
rookTropism = [[0]*64 for i in range(64)]
queenTropism = [[0]*64 for i in range(64)]

for pcord in range(64):
    for kcord in range(64):
        d = distance[pcord][kcord]
        pawnTropism[pcord][kcord] = pawnTScale[d]
        bishopTropism[pcord][kcord] = bishopTScale[d]
        knightTropism[pcord][kcord] = knightTScale[d]
        rookTropism[pcord][kcord] = rookTScale[d]
        queenTropism[pcord][kcord] = queenTScale[d]

def evalKingTropism (board):
    """ All other things being equal, having your Knights, Queens and Rooks
        close to the opponent's king is a good thing """
    
    opcolor = board.color
    opking = board.kings[opcolor]
    
    color = 1-opcolor
    pieces = board.boards[color]
    
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
    
    if color == WHITE:
        return score
    else: return -score

################################################################################
# evalPawnStructure                                                            #
################################################################################

pawntable = {}

def evalPawnStructure (board, phase):
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
    
    color = 1-board.color
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
        passed = 0
        weaked = 0
        nfile = [0]*8
        pScoreBoard = pawnScoreBoard[color]
        for cord in iterBits(pawns):
            score += pScoreBoard[cord] 
            
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
            
            if not i in range(64):
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
        
        # As the previous code worked color relative, and the following code is
        # absoulte, we have to turn it.
        if color == BLACK:
            score = -score
        
        # Save the score into the pawn hash table */ 
        pawntable[board.pawnhash] = (score, passed, weaked)
    
    ############################################################################
    #  This section of the pawn code cannot be saved into the pawn hash as     #
    #  they depend on the position of other pieces.  So they have to be        #
    #  calculated again.                                                       #
    ############################################################################
    
    if color == WHITE:
        wpawns = pawns
        wboards = boards
        wking = king
        bpawns = oppawns
        bboards = opboards
        bking = opking
    else:
        wpawns = oppawns
        wboards = opboards
        wking = opking
        bpawns = pawns
        bboards = boards
        bking = king
        
    # Pawn on f6/c6 with Queen against castled king is very strong
    
    if wboards[QUEEN] and (bitPosArray[C6] | bitPosArray[F6]) & wpawns:
        if wpawns & bitPosArray[F6] and bking > H6 and distance[bking][G7] == 1:
            score += 40
        if wpawns & bitPosArray[C6] and bking > H6 and distance[bking][B7] == 1:
            score += 40
    
    if bboards[QUEEN] and (bitPosArray[C3] | bitPosArray[F3]) & bpawns:
        if bpawns & bitPosArray[F3] and wking < A3 and distance[wking][G2] == 1:
            score -= 40
        if bpawns & bitPosArray[C3] and wking < A3 and distance[wking][B2] == 1:
            score -= 40
    
    # Connected passed pawns on 6th or 7th rank
    # Skipped. TODO.
    
    # Penalize Pawn on d2,e2/d7,e7 is blocked
    blocker = board.blocker
    if ((wpawns & d2e2[WHITE]) >> 8) & blocker:
        score -= 48
    if ((bpawns & d2e2[BLACK]) << 8) & blocker:
        score += 48
    
    # Enemy has no pieces & King is outcolor of passed pawn square
    # TODO

    # If both colors are castled on different colors, bonus for pawn storms
    if abs ((king>>7) - (opking&7)) >= 4 and phase < 6:
        n1 = opking & 7
        p = (isolaniMask[n1] | fileBits[n1]) & pawns
        
        s = 0
        for cord in iterBits(p):
            s += 10 * (5 - distance[cord][opking])
            
        if color == WHITE:
            score += s
        else: score -= s
    
    return score

################################################################################
# evalBateries                                                                 #
################################################################################

# TODO: This doesn't work at all
def evalBateries (board):
    """ Tests for QR, RR, QB and BB combos on the 7th rank. These are very
        strong and give quite a big bonus. """

    color = board.color
    opcolor = 1-board.color
    boards = board.boards[color]
    opboards = board.boards[opcolor]
    
    if color == WHITE:
        brank7 = rank[1]
        brank8 = rank[0]
    else:
        brank7 = rank[6]
        brank8 = rank[7]
    
    if bitLength ((boards[QUEEN] | boards[color][ROOK]) & brank7) > 1 and \
        (opboards[KING] & brank8) or (opboards[PAWN] & brank7):
        return 30
    
    return 0

#int DoubleQR7 (short side)
#   xside = 1^side;
#   if (nbits ((board.b[side][queen]|board.b[side][rook]) & brank7[side]) > 1
#      && ((board.b[xside][king] & brank8[side]) || 
#       (board.b[xside][pawn] & brank7[side])))
#
#      return (ROOKS7RANK);
#   else
#      return (0);
#}

normalKing = (
   24, 24, 24, 16, 16,  0, 32, 32,
   24, 20, 16, 12, 12, 16, 20, 24,
   16, 12,  8,  4,  4,  8, 12, 16,
   12,  8,  4,  0,  0,  4,  8, 12,
   12,  8,  4,  0,  0,  4,  8, 12,
   16, 12,  8,  4,  4,  8, 12, 16,
   24, 20, 16, 12, 12, 16, 20, 24,
   24, 24, 24, 16, 16,  0, 32, 32
)

endingKing = (
   0,  6, 12, 18, 18, 12,  6,  0,
   6, 12, 18, 24, 24, 18, 12,  6,
  12, 18, 24, 32, 32, 24, 18, 12,
  18, 24, 32, 48, 48, 32, 24, 18,
  18, 24, 32, 48, 48, 32, 24, 18,
  12, 18, 24, 32, 32, 24, 18, 12,
   6, 12, 18, 24, 24, 18, 12,  6,
   0,  6, 12, 18, 18, 12,  6,  0
)

def evalKing (board, phase):
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
        return endingKing[board.kings[WHITE]] - endingKing[board.kings[BLACK]]
    
    return 0
    
def evalKnights (board):
    outerring = ~lbox
    score = -15 * bitLength (board.boards[WHITE][KNIGHT] & outerring)
    score += 15 * bitLength (board.boards[BLACK][KNIGHT] & outerring)
    return score

def evalDev (board):
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
        
        # We don't encourage castling, but it certanly should always be possible
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
    
    return score

def evalBishops (board):
    
    opcolor = board.color
    
    color = 1-opcolor
    pawns = board.boards[color][PAWN]
    bishops = board.boards[color][BISHOP]
    
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
                  
        if color == WHITE:
            score -= s
        else: score += s
    
    # Avoid wasted moves
    
    if color == WHITE:
        if bishops & bitPosArray[B5] and arBoard[C6] == EMPTY and \
                oppawns & bitPosArray[B7] and oppawns & bitPosArray[C7]:
            score -= 15
        if bishops & bitPosArray[G5] and arBoard[F6] == EMPTY and \
                oppawns & bitPosArray[F7] and oppawns & bitPosArray[G7]:
            score -= 15
    
    else:
        if bishops & bitPosArray[B4] and arBoard[C3] == EMPTY and \
                oppawns & bitPosArray[B2] and oppawns & bitPosArray[C2]:
            score -= 15
        if bishops & bitPosArray[G4] and arBoard[F3] == EMPTY and \
                oppawns & bitPosArray[F2] and oppawns & bitPosArray[G2]:
            score -= 15
    
    return score

def evalTrappedBishops (board):
    """ Check for bishops trapped at A2/H2/A7/H7 """
    
    opcolor = board.color
    color = 1-opcolor
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
                score -= see
        if opbishops & bitPosArray[H2] and pawns & bitPosArray[G3]:
            see = staticExchangeEvaluate(board, newMove(H2,G3))
            if see < 0:
                score -= see
    
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

def evalRooks (board, phase):
    """ rooks on open/half-open files """

    opcolor = board.color
    color = 1-opcolor
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
    
    if color == BLACK:
        score = -score
    
    return score
