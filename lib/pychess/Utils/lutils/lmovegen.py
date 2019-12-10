from .bitboard import bitPosArray, iterBits, clearBit, firstBit
from .attack import isAttacked, pinnedOnKing, getAttacks
from .ldata import fromToRay, moveArray, directions, fileBits, rankBits,\
    ray45, attack45, ray135, attack135, ray90, attack90, ray00, attack00, FILE, rays
from pychess.Utils.const import EMPTY, PAWN,\
    QUEEN, KNIGHT, BISHOP, ROOK, KING, WHITE, BLACK,\
    SITTUYINCHESS, FISCHERRANDOMCHESS, SUICIDECHESS, GIVEAWAYCHESS, CAMBODIANCHESS,\
    ATOMICCHESS, WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, CRAZYHOUSECHESS, ASEAN_VARIANTS,\
    HORDECHESS, PLACEMENTCHESS, BPAWN, sliders,\
    A8, A6, G6, F6, H1, C3, B2, B3, A3, D6, D8, E3, E1, E8, C7, F2, D1, E6, H3, D3, H2, G7, H6, H7,\
    ASEAN_QUEEN, ASEAN_BBISHOP, ASEAN_WBISHOP, NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT,\
    KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION, KING_PROMOTION, NULL_MOVE,\
    DROP_VARIANTS, DROP, B_OOO, B_OO, W_OOO, W_OO

# The format of a move is as follows - from left:
# 4 bits:  Descriping the type of the move
# 6 bits:  cord to move from
# 6 bits:  cord to move to

shiftedFromCords = []
for i in range(64):
    shiftedFromCords.append(i << 6)

shiftedFlags = []
for i in NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT, \
        KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION, KING_PROMOTION, NULL_MOVE, DROP:
    shiftedFlags.append(i << 12)


def newMove(fromcord, tocord, flag=NORMAL_MOVE):
    return shiftedFlags[flag] + shiftedFromCords[fromcord] + tocord

# Generate all moves


def genCastles(board):
    def generateOne(color, side, king_after, rook_after):
        if side == 0:
            castle = QUEEN_CASTLE
        else:
            castle = KING_CASTLE
        king = board.ini_kings[color]
        rook = board.ini_rooks[color][side]
        blocker = clearBit(clearBit(board.blocker, king), rook)
        stepover = fromToRay[king][king_after] | fromToRay[rook][rook_after]
        if not stepover & blocker:
            for cord in range(
                    min(king, king_after), max(king, king_after) + 1):
                if isAttacked(board, cord, 1 - color):
                    return
            if FILE(king) == 3 and board.variant in (WILDCASTLECHESS,
                                                     WILDCASTLESHUFFLECHESS):
                castle = QUEEN_CASTLE if castle == KING_CASTLE else KING_CASTLE
            if board.variant == FISCHERRANDOMCHESS:
                return newMove(king, rook, castle)
            else:
                return newMove(king, king_after, castle)

    king = board.ini_kings[board.color]
    wildcastle = FILE(king) == 3 and board.variant in (WILDCASTLECHESS,
                                                       WILDCASTLESHUFFLECHESS)
    if board.color == WHITE:
        if board.castling & W_OO:
            side = 0 if wildcastle else 1
            move = generateOne(WHITE, side, board.fin_kings[WHITE][side],
                               board.fin_rooks[WHITE][side])
            if move:
                yield move

        if board.castling & W_OOO:
            side = 1 if wildcastle else 0
            move = generateOne(WHITE, side, board.fin_kings[WHITE][side],
                               board.fin_rooks[WHITE][side])
            if move:
                yield move
    else:
        if board.castling & B_OO:
            side = 0 if wildcastle else 1
            move = generateOne(BLACK, side, board.fin_kings[BLACK][side],
                               board.fin_rooks[BLACK][side])
            if move:
                yield move

        if board.castling & B_OOO:
            side = 1 if wildcastle else 0
            move = generateOne(BLACK, side, board.fin_kings[BLACK][side],
                               board.fin_rooks[BLACK][side])
            if move:
                yield move


def genPieceMoves(board, piece, tcord):
    """"
    Used by parseSAN only to accelerate it a bit
    """
    moves = set()
    friends = board.friends[board.color]
    notfriends = ~friends
    if piece == KNIGHT:
        knights = board.boards[board.color][KNIGHT]
        knightMoves = moveArray[KNIGHT]
        for fcord in iterBits(knights):
            if tcord in iterBits(knightMoves[fcord] & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves

    if piece == BISHOP:
        bishops = board.boards[board.color][BISHOP]
        if board.variant in ASEAN_VARIANTS:
            bishopMoves = moveArray[ASEAN_WBISHOP if board.color == WHITE else
                                    ASEAN_BBISHOP]
            for fcord in iterBits(bishops):
                if tcord in iterBits(bishopMoves[fcord] & notfriends):
                    moves.add(newMove(fcord, tcord))
            return moves
        else:
            blocker = board.blocker
            for fcord in iterBits(bishops):
                try:
                    attackBoard = attack45[fcord][ray45[fcord] & blocker] | \
                        attack135[fcord][ray135[fcord] & blocker]
                except KeyError:
                    attackBoard = 0
                if tcord in iterBits(attackBoard & notfriends):
                    moves.add(newMove(fcord, tcord))
            return moves

    if piece == ROOK:
        blocker = board.blocker
        rooks = board.boards[board.color][ROOK]
        for fcord in iterBits(rooks):
            try:
                attackBoard = attack00[fcord][ray00[fcord] & blocker] | \
                    attack90[fcord][ray90[fcord] & blocker]
            except KeyError:
                attackBoard = 0
            if tcord in iterBits(attackBoard & notfriends):
                moves.add(newMove(fcord, tcord))
        return moves

    if piece == QUEEN:
        queens = board.boards[board.color][QUEEN]
        if board.variant in ASEAN_VARIANTS:
            queenMoves = moveArray[ASEAN_QUEEN]
            for fcord in iterBits(queens):
                if tcord in iterBits(queenMoves[fcord] & notfriends):
                    moves.add(newMove(fcord, tcord))
            # Cambodian extra first move
            if board.variant == CAMBODIANCHESS:
                if board.is_first_move[QUEEN][board.color]:
                    if board.color == WHITE:
                        if not board.arBoard[E3]:
                            moves.add(newMove(E1, E3))
                    else:
                        if not board.arBoard[D6]:
                            moves.add(newMove(D8, D6))
            return moves
        else:
            blocker = board.blocker
            for fcord in iterBits(queens):
                try:
                    attackBoard = attack45[fcord][ray45[fcord] & blocker] | \
                        attack135[fcord][ray135[fcord] & blocker]
                except KeyError:
                    attackBoard = 0
                if tcord in iterBits(attackBoard & notfriends):
                    moves.add(newMove(fcord, tcord))

                try:
                    attackBoard = attack00[fcord][ray00[fcord] & blocker] | \
                        attack90[fcord][ray90[fcord] & blocker]
                except KeyError:
                    attackBoard = 0
                if tcord in iterBits(attackBoard & notfriends):
                    moves.add(newMove(fcord, tcord))
            return moves

    if (board.variant == SUICIDECHESS or board.variant == GIVEAWAYCHESS) and piece == KING:
        kings = board.boards[board.color][KING]
        if kings:
            kingMoves = moveArray[KING]
            for fcord in iterBits(kings):
                for tc in iterBits(kingMoves[fcord] & notfriends):
                    if tc == tcord:
                        moves.add(newMove(fcord, tcord))
            return moves

    return moves


def gen_sittuyin_promotions(board):
    from pychess.Variants import variants
    blocker = board.blocker
    notblocker = ~blocker

    pawns = board.boards[board.color][PAWN]

    queenMoves = moveArray[ASEAN_QUEEN]

    def willDirectAttack(board, move, cord):
        board_clone = board.clone()
        board_clone.applyMove(move)
        return board.friends[1 - board.color] & moveArray[ASEAN_QUEEN][cord]

    promotion_zone = variants[SITTUYINCHESS].PROMOTION_ZONE[board.color]
    for cord in iterBits(pawns):
        if board.pieceCount[board.color][PAWN] == 1 or cord in promotion_zone:
            # in place promotions
            move = newMove(cord, cord, QUEEN_PROMOTION)
            if not board.willGiveCheck(move) and not willDirectAttack(board, move, cord):
                yield move

            # queen move promotion
            for c in iterBits(queenMoves[cord] & notblocker):
                move = newMove(cord, c, QUEEN_PROMOTION)
                if not board.willGiveCheck(move) and not willDirectAttack(board, move, c):
                    yield move


def genAllMoves(board, drops=True):
    from pychess.Variants import variants
    if drops and board.variant in DROP_VARIANTS:
        for move in genDrops(board):
            yield move

    # In sittuyin you have to place your pieces before any real move
    if board.variant == SITTUYINCHESS or board.variant == PLACEMENTCHESS:
        if board.plyCount < 16:
            return

    blocker = board.blocker
    notblocker = ~blocker
    enpassant = board.enpassant

    friends = board.friends[board.color]
    notfriends = ~friends
    enemies = board.friends[1 - board.color]

    pawns = board.boards[board.color][PAWN]
    knights = board.boards[board.color][KNIGHT]
    bishops = board.boards[board.color][BISHOP]
    rooks = board.boards[board.color][ROOK]
    queens = board.boards[board.color][QUEEN]
    kings = board.boards[board.color][KING]

    PROMOTIONS = variants[board.variant].PROMOTIONS
    # In sittuyin only one queen allowed to exist any time per side
    if board.variant == SITTUYINCHESS and queens:
        PROMOTIONS = (NORMAL_MOVE, )

    # Knights
    knightMoves = moveArray[KNIGHT]
    for cord in iterBits(knights):
        for c in iterBits(knightMoves[cord] & notfriends):
            yield newMove(cord, c)

    # King
    if kings:
        kingMoves = moveArray[KING]
        # cord = firstBit(kings)
        for cord in iterBits(kings):
            for c in iterBits(kingMoves[cord] & notfriends):
                if board.variant == ATOMICCHESS:
                    if not board.arBoard[c]:
                        yield newMove(cord, c)
                else:
                    yield newMove(cord, c)

    if board.variant in ASEAN_VARIANTS:
        # Rooks
        for cord in iterBits(rooks):
            try:
                attackBoard = attack00[cord][ray00[cord] & blocker] | \
                    attack90[cord][ray90[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & notfriends):
                yield newMove(cord, c)

        # Queens
        queenMoves = moveArray[ASEAN_QUEEN]
        for cord in iterBits(queens):
            for c in iterBits(queenMoves[cord] & notfriends):
                yield newMove(cord, c)

        # Bishops
        bishopMoves = moveArray[ASEAN_WBISHOP if board.color == WHITE else
                                ASEAN_BBISHOP]
        for cord in iterBits(bishops):
            for c in iterBits(bishopMoves[cord] & notfriends):
                yield newMove(cord, c)

    else:
        # Rooks and Queens
        for cord in iterBits(rooks | queens):
            try:
                attackBoard = attack00[cord][ray00[cord] & blocker] | \
                    attack90[cord][ray90[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & notfriends):
                yield newMove(cord, c)

    # Bishops and Queens
        for cord in iterBits(bishops | queens):
            try:
                attackBoard = attack45[cord][ray45[cord] & blocker] | \
                    attack135[cord][ray135[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & notfriends):
                yield newMove(cord, c)

    # White pawns
    pawnEnemies = enemies | (enpassant is not None and bitPosArray[enpassant] or 0)
    if board.color == WHITE:

        # One step

        if board.variant == SITTUYINCHESS:
            promotion_zone = []
        else:
            promotion_zone = variants[board.variant].PROMOTION_ZONE[WHITE]
        movedpawns = (pawns >>
                      8) & notblocker  # Move all pawns one step forward
        for cord in iterBits(movedpawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord - 8, cord, p)
            else:
                yield newMove(cord - 8, cord)

        # Two steps

        seccondrow = pawns & rankBits[1]  # Get seccond row pawns
        movedpawns = (seccondrow >>
                      8) & notblocker  # Move two steps forward, while
        movedpawns = (movedpawns >>
                      8) & notblocker  # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            yield newMove(cord - 16, cord)

        # In horde white pawns on first rank may move two squares also
        if board.variant == HORDECHESS:
            firstrow = pawns & rankBits[0]  # Get first row pawns
            movedpawns = (firstrow >>
                          8) & notblocker  # Move two steps forward, while
            movedpawns = (movedpawns >>
                          8) & notblocker  # ensuring middle cord is clear
            for cord in iterBits(movedpawns):
                yield newMove(cord - 16, cord)

        # Capture left

        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord - 7, cord, p)
            elif cord == enpassant:
                yield newMove(cord - 7, cord, ENPASSANT)
            else:
                yield newMove(cord - 7, cord)

        # Capture right

        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord - 9, cord, p)
            elif cord == enpassant:
                yield newMove(cord - 9, cord, ENPASSANT)
            else:
                yield newMove(cord - 9, cord)

    # Black pawns
    else:

        # One step

        if board.variant == SITTUYINCHESS:
            promotion_zone = []
        else:
            promotion_zone = variants[board.variant].PROMOTION_ZONE[BLACK]
        movedpawns = (pawns << 8) & notblocker
        movedpawns &= 0xffffffffffffffff  # contrain to 64 bits
        for cord in iterBits(movedpawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord + 8, cord, p)
            else:
                yield newMove(cord + 8, cord)

        # Two steps

        seccondrow = pawns & rankBits[6]  # Get seventh row pawns
        # Move two steps forward, while ensuring middle cord is clear
        movedpawns = seccondrow << 8 & notblocker
        movedpawns = movedpawns << 8 & notblocker
        for cord in iterBits(movedpawns):
            yield newMove(cord + 16, cord)

        # Capture left

        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord + 7, cord, p)
            elif cord == enpassant:
                yield newMove(cord + 7, cord, ENPASSANT)
            else:
                yield newMove(cord + 7, cord)

        # Capture right

        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord + 9, cord, p)
            elif cord == enpassant:
                yield newMove(cord + 9, cord, ENPASSANT)
            else:
                yield newMove(cord + 9, cord)

    # Sittuyin promotions
    if board.variant == SITTUYINCHESS and pawns and not queens:
        for move in gen_sittuyin_promotions(board):
            yield move

    # Cambodian extra first moves for king and queen
    if board.variant == CAMBODIANCHESS:
        if board.arBoard[board.ini_kings[board.color]] == KING and \
                board.is_first_move[KING][board.color]:
            if board.color == WHITE:
                if not board.arBoard[B2]:
                    yield newMove(D1, B2)
                if not board.arBoard[F2]:
                    yield newMove(D1, F2)
            else:
                if not board.arBoard[C7]:
                    yield newMove(E8, C7)
                if not board.arBoard[G7]:
                    yield newMove(E8, G7)
        if board.arBoard[board.ini_queens[board.color]] == QUEEN and \
                board.is_first_move[QUEEN][board.color]:
            if board.color == WHITE:
                if not board.arBoard[E3]:
                    yield newMove(E1, E3)
            else:
                if not board.arBoard[D6]:
                    yield newMove(D8, D6)

    # Castling
    if kings:
        for move in genCastles(board):
            yield move

################################################################################
#   Generate capturing moves                                                   #
################################################################################


def genCaptures(board):
    from pychess.Variants import variants

    blocker = board.blocker
    enpassant = board.enpassant

    enemies = board.friends[1 - board.color]

    pawns = board.boards[board.color][PAWN]
    knights = board.boards[board.color][KNIGHT]
    bishops = board.boards[board.color][BISHOP]
    rooks = board.boards[board.color][ROOK]
    queens = board.boards[board.color][QUEEN]
    kings = board.boards[board.color][KING]

    PROMOTIONS = variants[board.variant].PROMOTIONS
    # In sittuyin promotion can't give capture
    if board.variant == SITTUYINCHESS:
        PROMOTIONS = (NORMAL_MOVE, )

    # Knights
    knightMoves = moveArray[KNIGHT]
    for cord in iterBits(knights):
        for c in iterBits(knightMoves[cord] & enemies):
            yield newMove(cord, c)

    # King
    if kings:
        kingMoves = moveArray[KING]
        # cord = firstBit(kings)
        for cord in iterBits(kings):
            for c in iterBits(kingMoves[cord] & enemies):
                if board.variant != ATOMICCHESS:
                    yield newMove(cord, c)

    # Rooks and Queens
    if board.variant in ASEAN_VARIANTS:
        for cord in iterBits(rooks):
            try:
                attackBoard = attack00[cord][ray00[cord] & blocker] | \
                    attack90[cord][ray90[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & enemies):
                yield newMove(cord, c)
    else:
        for cord in iterBits(rooks | queens):
            try:
                attackBoard = attack00[cord][ray00[cord] & blocker] | \
                    attack90[cord][ray90[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & enemies):
                yield newMove(cord, c)

    # Bishops and Queens
    if board.variant in ASEAN_VARIANTS:
        bishopMoves = moveArray[ASEAN_WBISHOP if board.color == WHITE else
                                ASEAN_BBISHOP]
        for cord in iterBits(bishops):
            for c in iterBits(bishopMoves[cord] & enemies):
                yield newMove(cord, c)
        queenMoves = moveArray[ASEAN_QUEEN]
        for cord in iterBits(queens):
            for c in iterBits(queenMoves[cord] & enemies):
                yield newMove(cord, c)
    else:
        for cord in iterBits(bishops | queens):
            try:
                attackBoard = attack45[cord][ray45[cord] & blocker] | \
                    attack135[cord][ray135[cord] & blocker]
            except KeyError:
                attackBoard = 0
            for c in iterBits(attackBoard & enemies):
                yield newMove(cord, c)

    # White pawns
    pawnEnemies = enemies | (enpassant is not None and bitPosArray[enpassant] or 0)

    if board.color == WHITE:
        promotion_zone = variants[board.variant].PROMOTION_ZONE[WHITE]

        # Promotes

        # Capture left

        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord - 7, cord, p)
            elif cord == enpassant:
                yield newMove(cord - 7, cord, ENPASSANT)
            else:
                yield newMove(cord - 7, cord)

        # Capture right

        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord - 9, cord, p)
            elif cord == enpassant:
                yield newMove(cord - 9, cord, ENPASSANT)
            else:
                yield newMove(cord - 9, cord)

    # Black pawns
    else:
        promotion_zone = variants[board.variant].PROMOTION_ZONE[BLACK]

        # One step

        # Capture left

        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord + 7, cord, p)
            elif cord == enpassant:
                yield newMove(cord + 7, cord, ENPASSANT)
            else:
                yield newMove(cord + 7, cord)

        # Capture right

        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord in promotion_zone:
                for p in PROMOTIONS:
                    yield newMove(cord + 9, cord, p)
            elif cord == enpassant:
                yield newMove(cord + 9, cord, ENPASSANT)
            else:
                yield newMove(cord + 9, cord)

################################################################################
#   Generate escapes from check                                                #
################################################################################


def genCheckEvasions(board):
    from pychess.Variants import variants
    color = board.color
    opcolor = 1 - color

    kcord = board.kings[color]
    kings = board.boards[color][KING]
    pawns = board.boards[color][PAWN]
    queens = board.boards[board.color][QUEEN]
    checkers = getAttacks(board, kcord, opcolor)

    arBoard = board.arBoard
    if bin(checkers).count("1") == 1:

        PROMOTIONS = variants[board.variant].PROMOTIONS
        # In sittuyin promotion move not allowed to capture opponent pieces
        if board.variant == SITTUYINCHESS and board.boards[board.color][QUEEN]:
            PROMOTIONS = (NORMAL_MOVE, )
        promotion_zone = variants[board.variant].PROMOTION_ZONE[color]

        # Captures of checking pieces (except by king, which we will test later)
        chkcord = firstBit(checkers)
        b = getAttacks(board, chkcord, color) & ~kings
        for cord in iterBits(b):
            if not pinnedOnKing(board, cord, color):
                if arBoard[cord] == PAWN and chkcord in promotion_zone and board.variant != SITTUYINCHESS:
                    for p in PROMOTIONS:
                        yield newMove(cord, chkcord, p)
                else:
                    yield newMove(cord, chkcord)

        # Maybe enpassant can help
        if board.enpassant:
            ep = board.enpassant
            if ep + (color == WHITE and -8 or 8) == chkcord:
                bits = moveArray[color == WHITE and BPAWN or PAWN][ep] & pawns
                for cord in iterBits(bits):
                    if not pinnedOnKing(board, cord, color):
                        yield newMove(cord, ep, ENPASSANT)

        # Lets block/capture the checking piece
        if sliders[arBoard[chkcord]]:
            bits = clearBit(fromToRay[kcord][chkcord], chkcord)

            for cord in iterBits(bits):
                b = getAttacks(board, cord, color)
                b &= ~(kings | pawns)

                # Add in pawn advances
                if color == WHITE and cord > H2:
                    if bitPosArray[cord - 8] & pawns:
                        b |= bitPosArray[cord - 8]
                    if cord >> 3 == 3 and arBoard[cord - 8] == EMPTY and \
                            bitPosArray[cord - 16] & pawns:
                        b |= bitPosArray[cord - 16]

                elif color == BLACK and cord < H7:
                    if bitPosArray[cord + 8] & pawns:
                        b |= bitPosArray[cord + 8]
                    if cord >> 3 == 4 and arBoard[cord + 8] == EMPTY and \
                            bitPosArray[cord + 16] & pawns:
                        b |= bitPosArray[cord + 16]

                for fcord in iterBits(b):
                    # If the piece is blocking another attack, we cannot move it
                    if pinnedOnKing(board, fcord, color):
                        continue
                    if arBoard[fcord] == PAWN and cord in promotion_zone:
                        for p in PROMOTIONS:
                            yield newMove(fcord, cord, p)
                    else:
                        yield newMove(fcord, cord)

                if board.variant == CRAZYHOUSECHESS:
                    holding = board.holding[color]
                    for piece in holding:
                        if holding[piece] > 0:
                            if piece == PAWN:
                                if cord >= 56 or cord <= 7:
                                    continue
                            yield newMove(piece, cord, DROP)

                if board.variant == SITTUYINCHESS and pawns and not queens:
                    from .lmove import TCORD
                    for move in gen_sittuyin_promotions(board):
                        if TCORD(move) == cord:
                            yield move

    # If more than one checkers, move king to get out of check
    if checkers:
        escapes = moveArray[KING][kcord] & ~board.friends[color]
    else:
        escapes = 0

    for chkcord in iterBits(checkers):
        dir = directions[chkcord][kcord]
        if sliders[arBoard[chkcord]]:
            escapes &= ~rays[chkcord][dir]

    for cord in iterBits(escapes):
        if not isAttacked(board, cord, opcolor):
            yield newMove(kcord, cord)


def genDrops(board):
    color = board.color
    arBoard = board.arBoard
    holding = board.holding[color]
    for piece in holding:
        if holding[piece] > 0:
            for cord, elem in enumerate(arBoard):
                if elem == EMPTY:
                    # forbidden drop moves
                    if board.variant == SITTUYINCHESS:
                        if color == WHITE:
                            if cord in (A3, B3, C3, D3) or cord > H3:
                                continue
                            if piece == ROOK and cord > H1:
                                continue
                        else:
                            if cord in (E6, F6, G6, H6) or cord < A6:
                                continue
                            if piece == ROOK and cord < A8:
                                continue

                    elif board.variant == PLACEMENTCHESS:
                        # drop pieces enabled on base line only
                        if color == WHITE:
                            if cord > H1:
                                continue
                        else:
                            if cord < A8:
                                continue

                        # bishops must be on opposite colour squares
                        base_line = arBoard[0:8] if color == WHITE else arBoard[56:64]
                        occupied_colors = [0, 0]
                        occupied_colors[cord % 2] += 1
                        for i, baseline_piece in enumerate(base_line):
                            if baseline_piece != EMPTY:
                                occupied_colors[i % 2] += 1

                        if holding[BISHOP] == 2 and piece != BISHOP:
                            # occupying all same colored fields before any bishop dropped is no-no
                            if occupied_colors[WHITE] == 4 or occupied_colors[BLACK] == 4:
                                continue
                        elif holding[BISHOP] == 1:
                            for i, baseline_piece in enumerate(base_line):
                                if baseline_piece == BISHOP:
                                    first_bishop_cord = i
                                    break
                            # occupying all possible place of opp colored bishop is no-no
                            if piece != BISHOP and occupied_colors[1 - first_bishop_cord % 2] == 4:
                                continue
                            # same colored bishop is no-no
                            elif piece == BISHOP and first_bishop_cord % 2 == cord % 2:
                                continue

                    if piece == PAWN:
                        if cord >= 56 or cord <= 7:
                            continue

                    yield newMove(piece, cord, DROP)
