
pieceValues = [0, 900, 500, 350, 300, 100]

from Utils.const import *

# these tables will be used for positional bonuses: #

from array import array
pos = {
    KNIGHT: {
        BLACK: array('b', [
            -20,-10,-10,-10,-10, -10,-10,-20,
            -10, 15, 25, 25, 25,  25, 15,-10,
            -10, 15, 25, 35, 35 , 35, 15,-10,
            -10, 10, 25, 20, 25,  25, 10,-10,
            -10, 0,  20, 20, 20,  20,  0,-10,
            -10, 0,  15, 15, 15,  15,  0,-10,
            -10, 0,   0,  3,  3,   0,  0,-10,
            -20,-35,-10,-10,-10, -10,-35,-20 ]),
        WHITE: array('b', [
            -20, -35,-10, -10, -10,-10, -35, -20,
            -10,   0,  0,   3,   3,  0,   0, -10,
            -10,   0, 15,  15,  15, 15,   0, -10,
            -10,   0, 20,  20,  20, 20,   0, -10,
            -10,  10, 25,  20,  25, 25,  10, -10,
            -10,  15, 25,  35,  35, 35,  15, -10,
            -10,  15, 25,  25,  25, 25,  15, -10,
            -20, -10,-10, -10, -10,-10, -10, -20 ]) },
    PAWN: {
        WHITE: array('b', [
             0,  0,   0, 0,  0,  0,  0,  0,
            25, 25, 35,  5,  5, 50, 45, 30,
             0,  0,  0,  7,  7,  5,  5,  0,
             0,  0,  0, 14, 14,  0,  0,  0,
             0,  0, 10, 20, 20, 10,  5,  5,
            12, 18, 18, 27, 27, 18, 18, 18,
            25, 30, 30, 35, 35, 35, 30, 25,
             0,  0,  0,  0,  0,  0,  0,  0 ]),
        BLACK: array('b', [
              0,  0,  0,  0,  0,  0,  0,  0,
             30, 30, 30, 35, 35, 35, 30, 25,
             12, 18, 18, 27, 27, 18, 18, 18,
              0,  0, 10, 20, 20, 10,  5,  5,
              0,  0,  0, 14, 14,  0,  0,  0,
              0,  0,  0,  7,  7,  5,  5,  0,
             25, 25, 35,  5,  5, 50, 45, 30,
              0,   0,  0,  0,  0,  0,  0, 0]) },
    KING: {
        WHITE: array('h', [
            -100,   15,   15,  -20,   10,    4,   15, -100,
            -250, -200, -150, -100, -100, -150, -200, -250,
            -350, -300, -300, -250, -250, -300, -300, -350,
            -400, -400, -400, -350, -350, -400, -400, -400,
            -450, -450, -450, -450, -450, -450, -450, -450,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500 ]),
        BLACK: array('h', [
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -450, -450, -450, -450, -450, -450, -450, -450,
            -400, -400, -400, -350, -350, -400, -400, -400,
            -350, -300, -300, -250, -250, -300, -300, -350,
            -250, -200, -150, -100, -100, -150, -200, -250,
            -100,   7,    15,    -20,   10,    4,   15, -100 ]) },
    QUEEN: {
        BLACK: array('b', [
              5,   5,   5,  10,  10,   5,   5,   5,
              0,   0,   3,   3,   3,   3,   3,   0,
            -30, -30, -30, -30, -30, -30, -30, -30,
            -60, -40, -40, -60, -60, -40, -40, -60,
            -40, -40, -40, -40, -40, -40, -40, -40,
            -15, -15, -15, -10, -10, -15, -15, -15,
              0,   0,   0,   7,  10,   5,   0,   0,
              0,   0,   0,   5,   0,   0,   0,   0 ]),
        WHITE: array('b', [
              0,   0,   0,   5,   0,   0,   0,   0,
              0,   0,   0,   7,  10,   5,   0,   0,
            -15, -15, -15, -10, -10, -15, -15, -15,
            -40, -40, -40, -40, -40, -40, -40, -40,
            -60, -40, -40, -60, -60, -40, -40, -60,
            -30, -30, -30, -30, -30, -30, -30, -30,
              0,   0,   3,   3,   3,   3,   3,   0,
              5,   5,   5,  10,  10,   5,   5,   5 ]) },
    ROOK: {
        WHITE: array('b', [
              2,   2,   2,   2,   2,   2,   2,   2,
              0,   0,   0,   7,  10,   0,   0,   0,
            -15, -15, -15, -10, -10, -15, -15, -15,
            -20, -20, -20, -20, -20, -20, -20, -20,
            -20, -20, -20, -30, -30, -20, -20, -20,
            -20, -20, -20, -20, -20, -20, -20, -20,
              0,  10,  15,  20,  20,  15,  10,   0,
             10,  15,  20,  25,  25,  20,  15,  10 ]),
        BLACK: array('b', [
             10 , 15,  20,  25,  25,  20,  15,  10,
              0 , 10,  15,  20,  20,  15,  10,   0,
            -20 ,-20, -20, -20, -20, -20, -20, -20,
            -20, -20, -20, -30, -30, -20, -20, -20,
            -20, -20, -20, -20, -20, -20, -20, -20,
            -15, -15, -15, -10, -10, -15, -15, -15,
              0,   0,   0,   7,  10,   0,   0,   0,
              2,   2,   2,   2,   2,   2,   2,   2 ]) },
    BISHOP: {
        WHITE: array('b', [
            -5, -5, -10, -5, -5, -10, -5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5, -5, -10, -5, -5, -10, -5, -5 ]),
        BLACK: array('b', [
            -5, -5, -10, -5, -5, -10, -5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5, -5, -10, -5, -5, -10, -5, -5 ]) }
}

endking = array('b', [
    -5, -3, -1,  0,  0, -1, -3, -5,
    -3, 10, 10, 10, 10, 10, 10, -3,
    -1, 10, 25, 25, 25, 25, 10, -1,
     0, 10, 25, 30, 30, 25, 10,  0,
     0, 10, 25, 30, 30, 25, 10,  0,
    -1, 10, 25, 25, 25, 25, 10, -1,
    -3, 10, 10, 10, 10, 10, 10, -3,
    -5, -3, -1,  0,  0, -1, -3, -5
])

hashmap = {}

def evaluateComplete (board, color=WHITE):
    """ A detailed evaluation function, taking into account
        several positional factors """

    if board in hashmap:
        s = hashmap[board]
    else:
        if board.status == RUNNING:
            analyzePawnStructure (board)
            s = evalMaterial (board) + \
                evalPawnStructure (board) + \
                evalBadBishops (board) + \
                evalDevelopment (board) + \
                evalRookBonus (board) + \
                evalKingTropism (board)
        elif board.status == DRAW:
            s = 0
        elif board.status == WHITEWON:
            s = 9999
        else: s = -9999
        hashmap[board] = s

    return (color == WHITE and [s] or [-s])[0]

def evalMaterial (board):
    
    materialValue = [0, 0]
    numPawns = [0, 0]
    for row in board.data:
        for piece in row:
            if not piece: continue
            materialValue[piece.color] += pieceValues[piece.sign]
            if piece.sign == PAWN:
                numPawns[piece.color] += 1

    # If both sides are equal, no need to compute anything!
    if materialValue[BLACK] == materialValue[WHITE]:
        return 0

    matTotal = materialValue[BLACK] + materialValue[WHITE]

    # Who is leading the game, material-wise?
    if materialValue[BLACK] > materialValue[WHITE]:
        # Black leading
        matDiff = materialValue[BLACK] - materialValue[WHITE]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * numPawns[BLACK] ) \
                / ( 6400 * ( numPawns[BLACK] + 1 ) )
        return -val
    else:
        # White leading
        matDiff = materialValue[WHITE] - materialValue[BLACK]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * numPawns[WHITE] ) \
                / ( 6400 * ( numPawns[WHITE] + 1 ) )
        return val

from validator import _findKing
def evalKingTropism (board):
    """ All other things being equal, having your Knights, Queens and Rooks close
        to the opponent's king is a good thing """
    
    # Sjeng uses a [64][64] array for KingTropism.
    # This way the calcualtions will only have to be made once.
    # Sjeng also uses max instead of min..
    
    score = 0
    
    try:
        wky, wkx = _findKing(board, WHITE).cords
        bky, bkx = _findKing(board, BLACK).cords
    except:
        return 0
        
    for py, row in enumerate(board.data):
        for px, piece in enumerate(row):
            if piece and piece.color == WHITE:
                if piece.sign == ROOK:
                    score -= min(abs( bky - py ), abs( bkx - px )) *2
                elif piece.sign == KNIGHT:
                    score -= abs( bky - py ) + abs( bkx - px ) -5
                elif piece.sign == QUEEN:
                    score -= min(abs( bky - py ), abs( bkx - px ))

            elif piece and piece.color == BLACK:
                if piece.sign == ROOK:
                    score += min(abs( wky - py ), abs( wkx - px )) *2
                elif piece.sign == KNIGHT:
                    score += abs( wky - py ) + abs( wkx - px ) -5
                elif piece.sign == QUEEN:
                    score += min(abs( wky - py ), abs( wkx - px ))
    
    return score

def evalRookBonus (board):
    """ Rooks are more effective on the seventh rank and on open files """
    
    score = 0
    
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if not piece or not piece.sign == ROOK: continue
            
            # We should try to keep the rooks at the back lines
            if y in (0,7):
            	score += piece.color == WHITE and 12 or -12

            # Is this rook on a semi- or completely open file?
            noblack = blackPawnFileBins[x] == 0 and 1 or 0
            nowhite = whitePawnFileBins[x] == 0 and 1 or 0
            if piece.color == WHITE:
                if noblack:
                    score += (noblack+nowhite)*6
                else: score += nowhite*8
            else:
                if nowhite:
                    score -= (noblack+nowhite)*6
                else: score -= nowhite*8
    
    return score

def evalDevelopment (board):
    """ Mostly useful in the opening, this term encourages the machine to move
        its bishops and knights into play, to control the center with its queen's
        and king's pawns, and to castle if the opponent has many major pieces on
        the board """
    
    score = 0
    
    # Test endgame
    if pieceCount <= 6 and sum(whitePawnFileBins) + sum(whitePawnFileBins) <= 8:
        for y, row in enumerate(board.data):
            for x, piece in enumerate(row):
                if piece and piece.sign == KING:
                    if piece.color == WHITE:
                        score += endking[y*8+x]
                    else: score -= endking[y*8+x]
        return score
        
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if not piece: continue
            s = pos[piece.sign][piece.color][y*8+x]
            if piece.color == WHITE:
                score += s
            else: score -= s
    
    for color, mod in ((WHITE,1),(BLACK,-1)):
        
        mainrow = board.data[int(3.5-3.5*mod)]
        
        # It is good to have a pawn in the king column
        for x, p in enumerate(mainrow):
            if p and p.sign == KING and p.color == color:
                bin = color == WHITE and whitePawnFileBins or blackPawnFileBins
                if not bin[x]:
                    score -= 10*mod
                break
        
        # We don't wanna care about castling before opponent's got its queen out
        dobreak = False
        for piece in mainrow:
            if piece and piece.sign == QUEEN and piece.color == color:
                dobreak = True
                continue
        if dobreak: continue
        
        castled = color == BLACK and BLACK_CASTLED or WHITE_CASTLED
        kside = color == BLACK and BLACK_OO or WHITE_OO
        qside = color == BLACK and BLACK_OOO or WHITE_OOO
        
        # Being castled deserves a bonus
        if board.castling & castled:
            score += 15*mod
            continue
        
        # Biggest penalty if you can't castle at all
        if not board.castling & (qside|kside):
            score -= 60*mod
        # Penalty if you can only castle kingside
        elif not board.castling & qside:
            score -= 30*mod
        # Bigger penalty if you can only castle queenside
        elif not board.castling & kside:
            score -= 45*mod
    
    return score


def evalBadBishops (board):
    """ Bishops may be limited in their movement
        if there are too many pawns on squares of their color """
        
    score = 0
    
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if not piece or not piece.sign == BISHOP: continue
            mod = piece.color == WHITE and 1 or -1
            
            # What is the bishop's square color?
            lightsq = x % 2 + y % 2 == 1
            
            if lightsq:
                score -= pawnColorBins[0]*7 * mod
            else:
                score -= pawnColorBins[1]*7 * mod

    return score


def evalPawnStructure (board) :
    """ Given the pawn formations, penalize or bonify the position according to
        the features it contains """
    
    score = 0
    
    for x in range (8):
        # First, look for doubled pawns
        # In chess, two or more pawns on the same file usually hinder each other,
        # so we assign a penalty
        
        if whitePawnFileBins[x] > 1:
            score -= 10
        if blackPawnFileBins[x] > 1:
            score += 10
        
        # Now, look for an isolated pawn, i.e., one which has no neighbor pawns
        # capable of protecting it from attack at some point in the future
        
        if x == 0 and whitePawnFileBins[x] > 0 and whitePawnFileBins[1] == 0:
            score -= 15
        elif x == 7 and whitePawnFileBins[x] > 0 and whitePawnFileBins[6] == 0:
            score -= 15
        elif whitePawnFileBins[x] > 0 and whitePawnFileBins[x-1] == 0 and \
                whitePawnFileBins[x+1] == 0:
            score -= 15
    
        if x == 0 and blackPawnFileBins[x] > 0 and blackPawnFileBins[1] == 0:
            score += 15
        elif x == 7 and blackPawnFileBins[x] > 0 and blackPawnFileBins[6] == 0:
            score += 15
        elif blackPawnFileBins[x] > 0 and blackPawnFileBins[x-1] == 0 and \
                blackPawnFileBins[x+1] == 0:
            score += 15

        # Penalize pawn rams, because they restrict movement
        score -= 8 * pawnRams

    return score

whitePawnFileBins = [0]*8
pawnColorBins = [0]*2
pawnRams = 0
blackPawnFileBins = [0]*8

def analyzePawnStructure (board):
    """ Look at pawn positions to be able to detect features such as doubled,
        isolated or passed pawns """
    
    global whitePawnFileBins, blackPawnFileBins, pawnColorBins, pawnRams
    whitePawnFileBins = [0]*8
    blackPawnFileBins = [0]*8
    pawnColorBins[0] = 0
    pawnColorBins[1] = 0
    # Whiterams-Blackrams
    pawnRams = 0 
    
    global pieceCount
    pieceCount = 0
    
    data = board.data
    for y, row in enumerate(data[1:-1][::-1]):
        for x, piece in enumerate(row):
            if piece and piece.sign == PAWN:
                if piece.color == WHITE:
                    whitePawnFileBins[x] += 1
                else: blackPawnFileBins[x] += 1

                # Is this pawn on a white or a black square?
                if y % 2 == x % 2:
                    pawnColorBins[ 0 ] += 1
                else: pawnColorBins[ 1 ] += 1

                # Look for a "pawn ram", i.e., a situation where a black pawn
                # is located in the square immediately ahead of this one.
                ahead = data[y+1][x]
                if ahead and ahead.sign == PAWN and ahead.color == piece.color:
                    if piece.color == WHITE:
                        pawnRams += 1
                    else: pawnRams -= 1
            elif piece:
                pieceCount += 1
            
