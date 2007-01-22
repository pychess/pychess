
################################################################################
# The purpose of this module, is to give a certain position a score. The       #
# greater the score, the better the position                                   #
################################################################################

from pychess.Utils.const import *
from ldata import *

def evaluateComplete (board, color):
    """ A detailed evaluation function, taking into account
        several positional factors """
    
    #if board.status == RUNNING:
        #analyzePawnStructure (board)
    s = evalMaterial (board) + \
        evalKingTropism (board)
            #evalPawnStructure (board, color) + \
            #evalBadBishops (board, color) + \
            #evalDevelopment (board, color) + \
            #evalCastling (board, color) + \
            #evalRookBonus (board, color)
    #elif board.status == DRAW:
    #    s = 0
    #elif board.status == WHITEWON:
    #    s = 9999
    #else: s = -9999
    
    return (color == WHITE and [s] or [-s])[0]

################################################################################
# evalMaterial                                                                 #
################################################################################

def evalMaterial (board):
    
    pieces = board.boards
    
    material = [0, 0]
    for piece in range(PAWN, KING):
        material[WHITE] += PIECE_VALUES[piece] * bitLength(pieces[WHITE][piece])
        material[BLACK] += PIECE_VALUES[piece] * bitLength(pieces[BLACK][piece])
    
    # If both sides are equal, no need to compute anything!
    if material[BLACK] == material[WHITE]:
        return 0
    
    matTotal = sum(material)
    
    # Who is leading the game, material-wise?
    if material[BLACK] > material[WHITE]:
        # Black leading
        blackPawns = bitLength(pieces[BLACK][PAWN])
        matDiff = material[BLACK] - material[WHITE]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * blackPawns ) \
                / ( 6400 * ( blackPawns + 1 ) )
        return -val
    else:
        # White leading
        whitePawns = bitLength(pieces[WHITE][PAWN])
        matDiff = material[WHITE] - material[BLACK]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * whitePawns ) \
                / ( 6400 * ( whitePawns + 1 ) )
        return val

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
    """ All other things being equal, having your Knights, Queens and Rooks close
        to the opponent's king is a good thing """
    
    score = 0
    whiteKing, blackKing = board.kings
    
    wpieces = board.boards[WHITE]
    
    for cord in iterBits(wpieces[PAWN]):
        score += pawnTropism[cord][blackKing]
    
    for cord in iterBits(wpieces[KNIGHT]):
        score += knightTropism[cord][blackKing]
    
    for cord in iterBits(wpieces[BISHOP]):
        score += bishopTropism[cord][blackKing]
    
    for cord in iterBits(wpieces[ROOK]):
        score += rookTropism[cord][blackKing]
    
    for cord in iterBits(wpieces[QUEEN]):
        score += queenTropism[cord][blackKing]
    
    bpieces = board.boards[BLACK]
    
    for cord in iterBits(bpieces[PAWN]):
        score -= pawnTropism[cord][whiteKing]
    
    for cord in iterBits(bpieces[KNIGHT]):
        score -= knightTropism[cord][whiteKing]
    
    for cord in iterBits(bpieces[BISHOP]):
        score -= bishopTropism[cord][whiteKing]
    
    for cord in iterBits(bpieces[ROOK]):
        score -= rookTropism[cord][whiteKing]
    
    for cord in iterBits(bpieces[QUEEN]):
        score -= queenTropism[cord][whiteKing]
    
    return score
