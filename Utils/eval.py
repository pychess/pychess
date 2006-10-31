
pieceValues = {'p':100, 'n':300, 'b':350, 'r':500, 'q':900, 'k':2000}
SIDE_WHITE, SIDE_BLACK = range(2)

# these tables will be used for positional bonuses: #

from array import array
pos = {
    "n": {
        "black": array('b', [
            -20,-10,-10,-10,-10, -10,-10,-20,
            -10, 15, 25, 25, 25,  25, 15,-10,
            -10, 15, 25, 35, 35 , 35, 15,-10,
            -10, 10, 25, 20, 25,  25, 10,-10,
            -10, 0,  20, 20, 20,  20,  0,-10,
            -10, 0,  15, 15, 15,  15,  0,-10,
            -10, 0,   0,  3,  3,   0,  0,-10,
            -20,-35,-10,-10,-10, -10,-35,-20 ]),
        "white": array('b', [
            -20, -35,-10, -10, -10,-10, -35, -20,
            -10,   0,  0,   3,   3,  0,   0, -10,
            -10,   0, 15,  15,  15, 15,   0, -10,
            -10,   0, 20,  20,  20, 20,   0, -10,
            -10,  10, 25,  20,  25, 25,  10, -10,
            -10,  15, 25,  35,  35, 35,  15, -10,
            -10,  15, 25,  25,  25, 25,  15, -10,
            -20, -10,-10, -10, -10,-10, -10, -20 ]) },
    "p": {
        "white": array('b', [
             0,  0,   0, 0,  0,  0,  0,  0,
            25, 25, 35,  5,  5, 50, 45, 30,
             0,  0,  0,  7,  7,  5,  5,  0,
             0,  0,  0, 14, 14,  0,  0,  0,
             0,  0, 10, 20, 20, 10,  5,  5,
            12, 18, 18, 27, 27, 18, 18, 18,
            25, 30, 30, 35, 35, 35, 30, 25,
             0,  0,  0,  0,  0,  0,  0,  0 ]),
        "black": array('b', [
              0,  0,  0,  0,  0,  0,  0,  0,
             30, 30, 30, 35, 35, 35, 30, 25,
             12, 18, 18, 27, 27, 18, 18, 18,
              0,  0, 10, 20, 20, 10,  5,  5,
              0,  0,  0, 14, 14,  0,  0,  0,
              0,  0,  0,  7,  7,  5,  5,  0,
             25, 25, 35,  5,  5, 50, 45, 30,
              0,   0,  0,  0,  0,  0,  0, 0]) },
    "k": {
        "white": array('h', [
            -100,   15,   15,  -20,   10,    4,   15, -100,
            -250, -200, -150, -100, -100, -150, -200, -250,
            -350, -300, -300, -250, -250, -300, -300, -350,
            -400, -400, -400, -350, -350, -400, -400, -400,
            -450, -450, -450, -450, -450, -450, -450, -450,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500 ]),
        "black": array('h', [
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -500, -500, -500, -500, -500, -500, -500, -500,
            -450, -450, -450, -450, -450, -450, -450, -450,
            -400, -400, -400, -350, -350, -400, -400, -400,
            -350, -300, -300, -250, -250, -300, -300, -350,
            -250, -200, -150, -100, -100, -150, -200, -250,
            -100,   7,    15,    -20,   10,    4,   15, -100 ]) },
    "q": {
        "black": array('b', [
              5,   5,   5,  10,  10,   5,   5,   5,
              0,   0,   3,   3,   3,   3,   3,   0,
            -30, -30, -30, -30, -30, -30, -30, -30,
            -60, -40, -40, -60, -60, -40, -40, -60,
            -40, -40, -40, -40, -40, -40, -40, -40,
            -15, -15, -15, -10, -10, -15, -15, -15,
              0,   0,   0,   7,  10,   5,   0,   0,
              0,   0,   0,   5,   0,   0,   0,   0 ]),
        "white": array('b', [
              0,   0,   0,   5,   0,   0,   0,   0,
              0,   0,   0,   7,  10,   5,   0,   0,
            -15, -15, -15, -10, -10, -15, -15, -15,
            -40, -40, -40, -40, -40, -40, -40, -40,
            -60, -40, -40, -60, -60, -40, -40, -60,
            -30, -30, -30, -30, -30, -30, -30, -30,
              0,   0,   3,   3,   3,   3,   3,   0,
              5,   5,   5,  10,  10,   5,   5,   5 ]) },
    "r": {
        "white": array('b', [
              2,   2,   2,   2,   2,   2,   2,   2,
              0,   0,   0,   7,  10,   0,   0,   0,
            -15, -15, -15, -10, -10, -15, -15, -15,
            -20, -20, -20, -20, -20, -20, -20, -20,
            -20, -20, -20, -30, -30, -20, -20, -20,
            -20, -20, -20, -20, -20, -20, -20, -20,
              0,  10,  15,  20,  20,  15,  10,   0,
             10,  15,  20,  25,  25,  20,  15,  10 ]),
        "black": array('b', [
             10 , 15,  20,  25,  25,  20,  15,  10,
              0 , 10,  15,  20,  20,  15,  10,   0,
            -20 ,-20, -20, -20, -20, -20, -20, -20,
            -20, -20, -20, -30, -30, -20, -20, -20,
            -20, -20, -20, -20, -20, -20, -20, -20,
            -15, -15, -15, -10, -10, -15, -15, -15,
              0,   0,   0,   7,  10,   0,   0,   0,
              2,   2,   2,   2,   2,   2,   2,   2 ]) },
    "b": {
        "white": array('b', [
            -5, -5, -10, -5, -5, -10, -5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  3,  15, 10, 10,  15,  3, -5,
            -5,  5,   6, 15, 15,   6,  5, -5,
            -5, 10,   5, 10, 10,   5, 10, -5,
            -5, -5, -10, -5, -5, -10, -5, -5 ]),
        "black": array('b', [
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

def evaluateQuickie (history, color="white"):
    """ Only based on material """
    s = evalMaterial (history)
    return (color == "white" and [s] or [-s])[0]

from Savers import epd
from cStringIO import StringIO
hashmap = {}

from Utils.validator import FINE, DRAW, WHITEWON, BLACKWON

def evaluateComplete (history, color="white"):
    """ A detailed evaluation function, taking into account
        several positional factors """

    board = history[-1]
    if board in hashmap:
        s = hashmap[board]
    else:
        if history.status == FINE:
            analyzePawnStructure (history)
            s = evalMaterial (history) + \
                evalPawnStructure (history) + \
                evalBadBishops (history) + \
                evalDevelopment (history) + \
                evalRookBonus (history) + \
                evalKingTropism (history)
        elif history.status == DRAW:
            s = 0
        elif history.status == WHITEWON:
            s = 9999
        else: s = -9999
        hashmap[board] = s

    return (color == "white" and [s] or [-s])[0]

def evalMaterial (history):
    
    materialValue = {"white":0, "black":0}
    numPawns = {"white":0, "black":0}
    for row in history[-1].data:
        for piece in row:
            if not piece: continue
            materialValue[piece.color] += pieceValues[piece.sign]
            if piece.sign == 'p':
                numPawns[piece.color] += 1

    # If both sides are equal, no need to compute anything!
    if materialValue["black"] == materialValue["white"]:
        return 0

    matTotal = materialValue["black"] + materialValue["white"]

    # Who is leading the game, material-wise?
    if materialValue["black"] > materialValue["white"]:
        # Black leading
        matDiff = materialValue["black"] - materialValue["white"]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * numPawns["black"] ) \
                / ( 6400 * ( numPawns["black"] + 1 ) )
        return -val
    else:
        # White leading
        matDiff = materialValue["white"] - materialValue["black"]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * numPawns["white"] ) \
                / ( 6400 * ( numPawns["white"] + 1 ) )
        return val

from validator import _findKing
def evalKingTropism (history):
    """ All other things being equal, having your Knights, Queens and Rooks close
        to the opponent's king is a good thing """
    
    # Sjeng uses a [64][64] array for KingTropism.
    # This way the calcualtions will only have to be made once.
    # Sjeng also uses max instead of min..
    
    score = 0
    
    try:
        wky, wkx = _findKing(history[-1], "white").cords
        bky, bkx = _findKing(history[-1], "black").cords
    except:
        return 0
        
    for py, row in enumerate(history[-1].data):
        for px, piece in enumerate(row):
            if piece and piece.color == "white":
                if piece.sign == 'r':
                    score -= min(abs( bky - py ), abs( bkx - px )) *2
                elif piece.sign == 'n':
                    score -= abs( bky - py ) + abs( bkx - px ) -5
                elif piece.sign == 'q':
                    score -= min(abs( bky - py ), abs( bkx - px ))

            elif piece and piece.color == "black":
                if piece.sign == 'r':
                    score += min(abs( wky - py ), abs( wkx - px )) *2
                elif piece.sign == 'n':
                    score += abs( wky - py ) + abs( wkx - px ) -5
                elif piece.sign == 'q':
                    score += min(abs( wky - py ), abs( wkx - px ))
    
    return score

def evalRookBonus (history):
    """ Rooks are more effective on the seventh rank and on open files """
    
    score = 0
    
    for y, row in enumerate(history[-1].data):
        for x, piece in enumerate(row):
            if not piece or not piece.sign == 'r': continue
            
            # This kinda sucks ?!
            if piece.color == "white" and y == 0:
                score += 22
            elif piece.color == "black" and y == 7:
                score -= 22

            # Is this rook on a semi- or completely open file?
            noblack = blackPawnFileBins[x] == 0 and 1 or 0
            nowhite = whitePawnFileBins[x] == 0 and 1 or 0
            if piece.color == "white":
                if nowhite:
                    score += (noblack+nowhite)*8
                else: score += noblack*6
            else:
                if noblack:
                    score -= (noblack+nowhite)*8
                else: score -= noblack*6
    
    return score

from Utils import History
def evalDevelopment (history):
    """ Mostly useful in the opening, this term encourages the machine to move
        its bishops and knights into play, to control the center with its queen's
        and king's pawns, and to castle if the opponent has many major pieces on
        the board """
    
    board = history[-1]
    score = 0
    
    # Test endgame
    if pieceCount <= 6 and sum(whitePawnFileBins) + sum(whitePawnFileBins) <= 8:
        for y, row in enumerate(board.data):
            for x, piece in enumerate(row):
                if piece and piece.sign == 'k':
                    if piece.color == "white":
                        score += endking[y*8+x]
                    else: score -= endking[y*8+x]
        return score
        
    for y, row in enumerate(board.data):
        for x, piece in enumerate(row):
            if not piece: continue
            s = pos[piece.sign][piece.color][y*8+x]
            if piece.color == "white":
                score += s
            else: score -= s
    
    for color, mod in (("white",1),("black",-1)):
        
        mainrow = board.data[int(3.5-3.5*mod)]
        
        # We don't wanna care about castling before opponent's got its queen out
        dobreak = False
        for piece in mainrow:
            if piece and piece.sign == 'q' and piece.color == color:
                dobreak = True
                continue
        if dobreak: continue
        
        castled = (color == "white" and [History.WHITE_CASTLED] or [History.BLACK_CASTLED])[0]
        kside = (color == "white" and [History.WHITE_OO] or [History.BLACK_OO])[0]
        qside = (color == "white" and [History.WHITE_OOO] or [History.BLACK_OOO])[0]
        
        # Being castled deserves a bonus
        if history.castling & castled:
            score += 15*mod
            for x, p in enumerate(mainrow):
                if p and p.sign == 'k' and p.color == color:
                    bin = color == "white" and whitePawnFileBins or blackPawnFileBins
                    if not bin[x]:
                        score -= 10*mod
                    break
            continue
        
        # Biggest penalty if you can't castle at all
        if not history.castling & (qside|kside):
            score -= 60*mod
        # Penalty if you can only castle kingside
        elif not history.castling & qside:
            score -= 30*mod
        # Bigger penalty if you can only castle queenside
        elif not history.castling & kside:
            score -= 45*mod
    
    return score


def evalBadBishops (history):
    """ Bishops may be limited in their movement
        if there are too many pawns on squares of their color """
        
    score = 0
    
    for y, row in enumerate(history[-1].data):
        for x, piece in enumerate(row):
            if not piece or not piece.sign == 'b': continue
            mod = piece.color == "white" and 1 or -1
            
            # What is the bishop's square color?
            lightsq = x % 2 + y % 2 == 1
            
            if lightsq:
                score -= pawnColorBins[0]*7 * mod
            else:
                score -= pawnColorBins[1]*7 * mod

    return score


def evalPawnStructure (history) :
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

def analyzePawnStructure (history):
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
    
    data = history[-1].data
    for y, row in enumerate(data[1:-1][::-1]):
        for x, piece in enumerate(row):
            if piece and piece.sign == 'p':
                if piece.color == "white":
                    whitePawnFileBins[x] += 1
                else: blackPawnFileBins[x] += 1

                # Is this pawn on a white or a black square?
                if y % 2 == x % 2:
                    pawnColorBins[ 0 ] += 1
                else: pawnColorBins[ 1 ] += 1

                # Look for a "pawn ram", i.e., a situation where a black pawn
                # is located in the square immediately ahead of this one.
                ahead = data[y+1][x]
                if ahead and ahead.sign == 'p' and ahead.color == piece.color:
                    if piece.color == "white":
                        pawnRams += 1
                    else: pawnRams -= 1
            elif piece:
                pieceCount += 1
            
