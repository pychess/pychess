
def evaluateComplete (board, color=WHITE):
    """ A detailed evaluation function, taking into account
        several positional factors """
    
    if board.status == RUNNING:
        #analyzePawnStructure (board)
        s = evalMaterial (board, color) + \
            evalKingTropism (board, color)
            #evalPawnStructure (board, color) + \
            #evalBadBishops (board, color) + \
            #evalDevelopment (board, color) + \
            #evalCastling (board, color) + \
            #evalRookBonus (board, color)
    elif board.status == DRAW:
        s = 0
    elif board.status == WHITEWON:
        s = 9999
    else: s = -9999
    
    return (color == WHITE and [s] or [-s])[0]

def evalMaterial (board, color):
    
    pieces = board.boards
    
    material = [0, 0]
    for piece in range(PAWN, KING):
        material[WHITE] += pieceValues[piece]*bitLength(pieces[WHITE][piece])
        material[BLACK] += pieceValues[piece]*bitLength(pieces[BLACK][piece])
    
    # If both sides are equal, no need to compute anything!
    if material[BLACK] == material[WHITE]:
        return 0
    
    matTotal = sum(material)
    
    # Who is leading the game, material-wise?
    if material[BLACK] > material[WHITE]:
        # Black leading
        blackPawns = bitLength(pieces[BLACK][PAWN]
        matDiff = materialValue[BLACK] - materialValue[WHITE]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * blackPawns ) \
                / ( 6400 * ( blackPawns + 1 ) )
        return -val
    else:
        # White leading
        whitePawns = bitLength(pieces[WHITE][PAWN]
        matDiff = materialValue[WHITE] - materialValue[BLACK]
        val =   min( 2400, matDiff ) + \
                ( matDiff * ( 12000 - matTotal ) * whitePawns ) \
                / ( 6400 * ( whitePawns + 1 ) )
        return val

pawnTScale = [40, 20, 10, 3, 1, 1, 0]
bishopTScale = [50, 25, 15, 5, 2, 2, 2]
knightTScale = [50, 70, 35, 10, 2, 1, 0]
rookTScale = [50, 40, 15, 5, 1, 1, 0]
queenTScale = [100, 60, 20, 5, 2, 0, 0]

pawnTropism = [[0]*64 for i in range(64)]
bishopTropism = [[0]*64 for i in range(64)]
knightTropism = [[0]*64 for i in range(64)]
rookTropism = [[0]*64 for i in range(64)]
queenTropism = [[0]*64 for i in range(64)]

for pcord in range(64):
    for kcord in range(64):
        px = pcord >> 3
        py = pcord & 7
        kx = kcord >> 3
        ky = kcord & 7
        pawnTropism[pcord][kcord] = pawnTScale[max(abs(px-kx), abs(py-ky))]
        bishopTropism[pcord][kcord] = bishopTScale[max(abs(px-kx), abs(py-ky))]
        knightTropism[pcord][kcord] = knightTScale[max(abs(px-kx), abs(py-ky))]
        rookTropism[pcord][kcord] = rookTScale[max(abs(px-kx), abs(py-ky))]
        queenTropism[pcord][kcord] = queenTScale[max(abs(px-kx), abs(py-ky))]

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
    
    bpieces = board.boards[WHITE]
    
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
    
