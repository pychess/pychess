"""
    This module differs from leval in that it is not optimized for speed.
    It checks differences between last and current board, and returns not
    scores, but strings describing the differences.
    Can be used for commenting on board changes.
"""

from .ldata import brank48, brank67, bitPosArray, left, right,\
    stonewall, distance, isolaniMask, fileBits, passedScores, passedPawnMask,\
    fromToRay, outpost, FILE, PIECE_VALUES,\
    ray45, ray135, ray90, ray00

from .bitboard import clearBit, lastBit, iterBits
from pychess.Utils.lutils.attack import staticExchangeEvaluate, getAttacks, \
    defends
from pychess.Utils.lutils.lmove import toSAN, TCORD, FCORD, FLAG, PROMOTE_PIECE
from pychess.Utils.const import BLACK, WHITEWON, BLACKWON, DRAW,\
    reprFile, reprCord, QUEEN_CASTLE, KING_CASTLE,\
    WHITE, KNIGHT, BISHOP, ROOK, PAWN, KING, QUEEN, EMPTY, PROMOTIONS,\
    FISCHERRANDOMCHESS,\
    H7, G6, A7, B6, H2, G3, A2, B3, B7, G7, B2, G2, B_OO, B_OOO, W_OO, W_OOO
from pychess.Utils.lutils.lmovegen import genCaptures, genAllMoves, newMove
from pychess.Utils.lutils.validator import validateMove
from pychess.Utils.repr import reprColor, reprPiece
from . import leval


def join(items):
    if len(items) == 1:
        return items[0]
    else:
        s = "%s %s %s" % (items[-2], _("and"), items[-1])
        if len(items) > 2:
            s = ", ".join(items[:-2] + [s])
        return s

# Functions can be of types:
#   * Final: Will be shown alone: "mates", "draws"
#   * Moves (s): Will always be shown: "put into *"
#   * Prefix: Will always be shown: "castles", "promotes"
#   * Attack: Will always be shown: "threaten", "preassures", "defendes"
#   * Simple: (s) Max one will be shown: "develops", "activity"
#   * State: (s) Will always be shown: "new *"
#   * Tip: (s) Will sometimes be shown: "pawn storm", "cramped position"


def final_status(model, ply, phase):
    if ply == model.ply:
        if model.status == DRAW:
            yield _("draws")
        elif model.status in (WHITEWON, BLACKWON):
            yield _("mates")


def offencive_moves_check(model, ply, phase):
    if model.getBoardAtPly(ply).board.isChecked():
        yield _("puts opponent in check")


def defencive_moves_safety(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board

    if board.arBoard[TCORD(model.getMoveAtPly(ply - 1).move)] != KING:
        return

    color = oldboard.color
    opcolor = 1 - color

    delta_eval_king = leval.evalKing(board, color, phase) - \
        leval.evalKing(oldboard, color, phase)

    # PyChess points tropism to queen for phase <= 3. Thus we set a high phase
    delta_eval_tropism = leval.evalKingTropism(board, opcolor, 10) - \
        leval.evalKingTropism(oldboard, opcolor, 10)

    # Notice, that tropism was negative
    delta_score = delta_eval_king - delta_eval_tropism / 2

    if delta_score > 35:
        yield _("improves king safety")
    elif delta_score > 15:
        yield _("slightly improves king safety")


def offencive_moves_rook(model, ply, phase):
    move = model.getMoveAtPly(ply - 1).move
    tcord = TCORD(move)
    board = model.getBoardAtPly(ply).board
    color = 1 - board.color
    opcolor = 1 - color

    # We also detect rook-to-open castlings
    if board.arBoard[tcord] == KING:
        if FLAG(move) == QUEEN_CASTLE:
            tcord = tcord + 1
        elif FLAG(move) == KING_CASTLE:
            tcord = tcord - 1

    if board.arBoard[tcord] != ROOK:
        return

    color = 1 - board.color
    opcolor = 1 - color

    pawns = board.boards[color][PAWN]
    oppawns = board.boards[opcolor][PAWN]

    ffile = fileBits[FILE(FCORD(move))]
    tfile = fileBits[FILE(tcord)]

    if ffile & pawns and not tfile & pawns and bin(pawns).count("1") >= 3:
        if not tfile & oppawns:
            yield _("moves a rook to an open file")
        else:
            yield _("moves an rook to a half-open file")


def offencive_moves_fianchetto(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    tcord = TCORD(model.getMoveAtPly(ply - 1).move)
    movingcolor = 1 - board.color

    if movingcolor == WHITE:
        if board.castling & W_OO and tcord == G2:
            yield _("moves bishop into fianchetto: %s") % "g2"
        elif board.castling & W_OOO and tcord == B2:
            yield _("moves bishop into fianchetto: %s") % "b2"
    else:
        if board.castling & B_OO and tcord == G7:
            yield _("moves bishop into fianchetto: %s") % "g7"
        elif board.castling & B_OOO and tcord == B7:
            yield _("moves bishop into fianchetto: %s") % "b7"


def prefix_type(model, ply, phase):
    flag = FLAG(model.getMoveAtPly(ply - 1).move)

    if flag in PROMOTIONS:
        yield _("promotes a Pawn to a %s") % reprPiece[PROMOTE_PIECE(flag)]

    elif flag in (KING_CASTLE, QUEEN_CASTLE):
        yield _("castles")


def attack_type(model, ply, phase):

    # We set bishop value down to knight value, as it is what most people expect
    bishopBackup = PIECE_VALUES[BISHOP]
    PIECE_VALUES[BISHOP] = PIECE_VALUES[KNIGHT]

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board

    if ply - model.lowply >= 2:
        oldmove = model.getMoveAtPly(ply - 2).move
        oldboard3 = model.getBoardAtPly(ply - 2).board
    else:
        oldmove = None
    move = model.getMoveAtPly(ply - 1).move
    tcord = TCORD(move)

    if oldboard.arBoard[tcord] != EMPTY:
        if not (board.variant == FISCHERRANDOMCHESS and
                FLAG(move) in (KING_CASTLE, QUEEN_CASTLE)):
            if oldmove and oldboard3.arBoard[TCORD(oldmove)] != EMPTY and \
                    TCORD(oldmove) == tcord:
                yield _("takes back material")
            else:
                see = staticExchangeEvaluate(oldboard, move)
                if see < 0:
                    yield _("sacrifices material")
                elif see == 0:
                    yield _("exchanges material")
                elif see > 0:
                    yield _("captures material")
    else:
        see = staticExchangeEvaluate(oldboard, move)
        if see < 0:
            yield _("sacrifices material")

    PIECE_VALUES[BISHOP] = bishopBackup


def defencive_moves_tactic(model, ply, phase):

    # ------------------------------------------------------------------------ #
    # Test if we threat something, or at least put more pressure on it         #
    # ------------------------------------------------------------------------ #

    # We set bishop value down to knight value, as it is what most people expect
    bishopBackup = PIECE_VALUES[BISHOP]
    PIECE_VALUES[BISHOP] = PIECE_VALUES[KNIGHT]

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board
    move = model.getMoveAtPly(ply - 1).move
    fcord = FCORD(move)
    tcord = TCORD(move)

    found_threatens = []
    found_increases = []

    # What do we attack now?
    board.setColor(1 - board.color)
    for ncap in genCaptures(board):

        # getCaptures also generate promotions
        if FLAG(ncap) in PROMOTIONS:
            continue

        # We are only interested in the attacks of the piece we just moved
        if FCORD(ncap) != TCORD(move):
            continue

        # We don't want to move back
        if TCORD(ncap) == FCORD(move):
            continue

        # We don't thread the king. We check him! (in another function)
        if board.arBoard[TCORD(ncap)] == KING:
            continue

        # If we also was able to attack that cord last time, we don't care
        if validateMove(oldboard, newMove(FCORD(move), TCORD(ncap))):
            continue

        # Test if we threats our enemy, at least more than before
        see0 = staticExchangeEvaluate(oldboard, TCORD(ncap),
                                      1 - oldboard.color)
        see1 = staticExchangeEvaluate(board, TCORD(ncap), 1 - oldboard.color)
        if see1 > see0:

            # If a new winning capture has been created
            if see1 > 0:
                # Find the easiest attack
                attacks = getAttacks(board, TCORD(ncap), board.color)
                v, cord = min((PIECE_VALUES[board.arBoard[fc]], fc)
                              for fc in iterBits(attacks))
                easiestAttack = newMove(cord, TCORD(ncap))
                found_threatens.append(toSAN(board, easiestAttack, True))

            # Even though we might not yet be strong enough, we might still
            # have strengthened another friendly attack
            else:
                found_increases.append(reprCord[TCORD(ncap)])

    board.setColor(1 - board.color)

    # -------------------------------------------------------------------- #
    # Test if we defend a one of our pieces                                #
    # -------------------------------------------------------------------- #

    found_defends = []

    # Test which pieces were under attack
    used = []
    for ncap in genCaptures(board):

        # getCaptures also generate promotions
        if FLAG(ncap) in PROMOTIONS:
            continue

        # We don't want to know about the same cord more than once
        if TCORD(ncap) in used:
            continue
        used.append(TCORD(ncap))

        # If the attack was poining on the piece we just moved, we ignore it
        if TCORD(ncap) == FCORD(move) or TCORD(ncap) == TCORD(move):
            continue

        # If we were already defending the piece, we don't send a new
        # message
        if defends(oldboard, FCORD(move), TCORD(ncap)):
            continue

        # If the attack was not strong, we ignore it
        see = staticExchangeEvaluate(oldboard, ncap)
        if see < 0:
            continue

        v = defends(board, TCORD(move), TCORD(ncap))

        # If the defend didn't help, it doesn't matter. Like defending a
        # bishop, threatened by a pawn, with a queen.
        # But on the other hand - it might still be a defend...
        # newsee = staticExchangeEvaluate(board, ncap)
        # if newsee <= see: continue

        if v:
            found_defends.append(reprCord[TCORD(ncap)])

    # ------------------------------------------------------------------------ #
    # Test if we are rescuing an otherwise exposed piece                       #
    # ------------------------------------------------------------------------ #

    # Rescuing is only an option, if our own move wasn't an attack
    if oldboard.arBoard[tcord] == EMPTY:
        see0 = staticExchangeEvaluate(oldboard, fcord, oldboard.color)
        see1 = staticExchangeEvaluate(board, tcord, oldboard.color)
        if see1 > see0 and see1 > 0:
            yield _("rescues a %s") % reprPiece[board.arBoard[tcord]].lower()

    if found_threatens:
        yield _("threatens to win material by %s") % join(found_threatens)
    if found_increases:
        yield _("increases the pressure on %s") % join(found_increases)
    if found_defends:
        yield _("defends %s") % join(found_defends)

    PIECE_VALUES[BISHOP] = bishopBackup


def offencive_moves_pin(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    move = model.getMoveAtPly(ply - 1).move
    fcord = FCORD(move)
    tcord = TCORD(move)
    piece = board.arBoard[tcord]

    ray = 0
    if piece in (BISHOP, QUEEN):
        ray |= (ray45[tcord] | ray135[tcord]) & ~(ray45[fcord] | ray135[fcord])
    if piece in (ROOK, QUEEN):
        ray |= (ray00[tcord] | ray90[tcord]) & ~(ray00[fcord] | ray90[fcord])

    if ray:
        for c in iterBits(ray & board.friends[board.color]):
            # We don't pin on pieces that are less worth than us
            if not PIECE_VALUES[piece] < PIECE_VALUES[board.arBoard[c]]:
                continue
            # There should be zero friendly pieces in between
            ray = fromToRay[tcord][c]
            if ray & board.friends[1 - board.color]:
                continue
            # There should be exactly one opponent piece in between
            op = clearBit(ray & board.friends[board.color], c)
            if bin(op).count("1") != 1:
                continue
            # The king can't be pinned
            pinned = lastBit(op)
            oppiece = board.arBoard[pinned]
            if oppiece == KING:
                continue
            # Yield
            yield _(
                "pins an enemy %(oppiece)s on the %(piece)s at %(cord)s") % {
                    'oppiece': reprPiece[oppiece].lower(),
                    'piece': reprPiece[board.arBoard[c]].lower(),
                    'cord': reprCord[c]}


def state_outpost(model, ply, phase):

    if phase >= 6:
        # Doesn't make sense in endgame
        return

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board

    wpawns = board.boards[WHITE][PAWN]
    oldwpawns = oldboard.boards[WHITE][PAWN]
    bpawns = board.boards[BLACK][PAWN]
    oldbpawns = oldboard.boards[BLACK][PAWN]

    wpieces = board.boards[WHITE][BISHOP] | board.boards[WHITE][KNIGHT]
    oldwpieces = oldboard.boards[WHITE][BISHOP] | oldboard.boards[WHITE][
        KNIGHT]
    bpieces = board.boards[BLACK][BISHOP] | board.boards[BLACK][KNIGHT]
    oldbpieces = oldboard.boards[BLACK][BISHOP] | oldboard.boards[BLACK][
        KNIGHT]

    for cord in iterBits(wpieces):
        sides = isolaniMask[FILE(cord)]
        front = passedPawnMask[WHITE][cord]
        if outpost[WHITE][cord] and not bpawns & sides & front and \
                (not oldwpieces & bitPosArray[cord] or
                 oldbpawns & sides & front):
            yield 35, _("White has a new piece in outpost: %s") % reprCord[
                cord]

    for cord in iterBits(bpieces):
        sides = isolaniMask[FILE(cord)]
        front = passedPawnMask[BLACK][cord]
        if outpost[BLACK][cord] and not wpawns & sides & front and \
                (not oldbpieces & bitPosArray[cord] or
                 oldwpawns & sides & front):
            yield 35, _("Black has a new piece in outpost: %s") % reprCord[
                cord]


def state_pawn(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board
    color = 1 - board.color
    opcolor = 1 - color

    move = model.getMoveAtPly(ply - 1).move

    pawns = board.boards[color][PAWN]
    oppawns = board.boards[opcolor][PAWN]
    oldpawns = oldboard.boards[color][PAWN]
    oldoppawns = oldboard.boards[opcolor][PAWN]

    # Passed pawns
    for cord in iterBits(pawns):
        if not oppawns & passedPawnMask[color][cord]:
            if color == WHITE:
                frontCords = fromToRay[cord][cord | 56]
            else:
                frontCords = fromToRay[cord][cord & 7]
            if frontCords & pawns:
                continue

            # Was this a passed pawn before?
            if oldpawns & bitPosArray[cord] and \
                    not oldoppawns & passedPawnMask[color][cord] and \
                    not frontCords & oldpawns:
                continue

            # Is this just a passed pawn that has been moved?
            if TCORD(move) == cord:
                frontCords |= bitPosArray[cord]
                if not frontCords & oldpawns and \
                        not oldoppawns & passedPawnMask[color][FCORD(move)]:
                    continue

            score = (passedScores[color][cord >> 3] * phase)
            yield score, _("%(color)s has a new passed pawn on %(cord)s") % {
                'color': reprColor[color],
                'cord': reprCord[cord]
            }

    # Double pawns
    found_doubles = []
    found_halfopen_doubles = []
    found_white_isolates = []
    found_black_isolates = []
    for file in range(8):
        bits = fileBits[file]

        count = bin(pawns & bits).count("1")
        oldcount = bin(oldpawns & bits).count("1")
        opcount = bin(oppawns & bits).count("1")
        oldopcount = bin(oldoppawns & bits).count("1")

        # Single pawn -> double pawns
        if count > oldcount >= 1:
            if not opcount:
                found_halfopen_doubles.append(reprFile[file])
            else:
                found_doubles.append(reprFile[file])

        # Closed file double pawn -> half-open file double pawn
        elif count > 1 and opcount == 0 and oldopcount > 0:
            found_halfopen_doubles.append(reprFile[file])

        # Isolated pawns
        if color == WHITE:
            wpawns = pawns
            oldwpawns = oldpawns
            bpawns = oppawns
            oldbpawns = oldoppawns
        else:
            bpawns = pawns
            oldbpawns = oldpawns
            wpawns = oppawns
            oldwpawns = oldoppawns

        if wpawns & bits and not wpawns & isolaniMask[file] and \
                (not oldwpawns & bits or oldwpawns & isolaniMask[file]):
            found_white_isolates.append(reprFile[file])

        if bpawns & bits and not bpawns & isolaniMask[file] and \
                (not oldbpawns & bits or oldbpawns & isolaniMask[file]):
            found_black_isolates.append(reprFile[file])

    # We need to take care of 'worstcases' like: "got new double pawns in the a
    # file, in the half-open b, c and d files and in the open e and f files"

    doubles_count = len(found_doubles) + len(found_halfopen_doubles)
    if doubles_count > 0:

        parts = []
        for type_, list_ in (("", found_doubles),
                             (_("half-open") + " ", found_halfopen_doubles)):
            if len(list_) == 1:
                parts.append(_("in the %(x)s%(y)s file") % {'x': type_,
                                                            'y': list_[0]})
            elif len(list_) >= 2:
                parts.append(_("in the %(x)s%(y)s files") % {'x': type_,
                                                             'y': join(list_)})

        if doubles_count == 1:
            s = _("%(color)s got a double pawn %(place)s")
        else:
            s = _("%(color)s got new double pawns %(place)s")

        yield (8 + phase) * 2 * doubles_count, s % {'color': reprColor[color],
                                                    'place': join(parts)}

    for (color_, list_) in ((WHITE, found_white_isolates),
                            (BLACK, found_black_isolates)):
        if list_:
            yield 20 * len(list_), ngettext(
                "%(color)s got an isolated pawn in the %(x)s file",
                "%(color)s got isolated pawns in the %(x)s files",
                len(list_)) % {'color': reprColor[color_],
                               'x': join(list_)}

    # Stone wall
    if stonewall[color] & pawns == stonewall[color] and \
       stonewall[color] & oldpawns != stonewall[color]:
        yield 10, _("%s moves pawns into stonewall formation") % reprColor[
            color]


def state_destroysCastling(model, ply, phase):
    """ Does the move destroy the castling ability of the opponent """

    # If the move is a castling, nobody will every care if the castling
    # possibilities has changed
    if FLAG(model.getMoveAtPly(ply - 1).move) in (QUEEN_CASTLE, KING_CASTLE):
        return

    oldcastling = model.getBoardAtPly(ply - 1).board.castling
    castling = model.getBoardAtPly(ply).board.castling

    if oldcastling & W_OOO and not castling & W_OOO:
        if oldcastling & W_OO and not castling & W_OO:
            yield 900 / phase, _("%s can no longer castle") % reprColor[WHITE]
        else:
            yield 400 / phase, _(
                "%s can no longer castle in queenside") % reprColor[WHITE]
    elif oldcastling & W_OO and not castling & W_OO:
        yield 500 / phase, _(
            "%s can no longer castle in kingside") % reprColor[WHITE]

    if oldcastling & B_OOO and not castling & B_OOO:
        if oldcastling & B_OO and not castling & B_OO:
            yield 900 / phase, _("%s can no longer castle") % reprColor[BLACK]
        else:
            yield 400 / phase, _(
                "%s can no longer castle in queenside") % reprColor[BLACK]
    elif oldcastling & B_OO and not castling & B_OO:
        yield 500 / phase, _(
            "%s can no longer castle in kingside") % reprColor[BLACK]


def state_trappedBishops(model, ply, phase):
    """ Check for bishops trapped at A2/H2/A7/H7 """

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board

    opcolor = board.color

    move = model.getMoveAtPly(ply - 1).move
    tcord = TCORD(move)

    # Only a pawn is able to trap a bishop
    if board.arBoard[tcord] != PAWN:
        return

    if tcord == B3:
        cord = A2
    elif tcord == G3:
        cord = H2
    elif tcord == B6:
        cord = A7
    elif tcord == G6:
        cord = H7
    else:
        return

    s = leval.evalTrappedBishops(board, opcolor)
    olds = leval.evalTrappedBishops(oldboard, opcolor)

    # We have got more points -> We have trapped a bishop
    if s > olds:
        yield 300 / phase, _(
            "%(opcolor)s has a new trapped bishop on %(cord)s") % {
                'opcolor': reprColor[opcolor],
                'cord': reprCord[cord]}


def simple_tropism(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board
    color = oldboard.color

    move = model.getMoveAtPly(ply - 1).move
    fcord = FCORD(move)
    tcord = TCORD(move)
    arBoard = board.arBoard

    if arBoard[tcord] != PAWN:
        score = leval.evalKingTropism(board, color, phase)
        oldscore = leval.evalKingTropism(oldboard, color, phase)
    else:
        if color == WHITE:
            rank23 = brank67[BLACK]
        else:
            rank23 = brank67[WHITE]
        if bitPosArray[fcord] & rank23:
            yield 2, _("develops a pawn: %s") % reprCord[tcord]
        else:
            yield 1, _("brings a pawn closer to the backrow: %s") % reprCord[tcord]
        return

    king = board.kings[color]
    opking = board.kings[1 - color]

    if score > oldscore:
        # in FISCHERRANDOMCHESS unusual casting case the tcord is
        # the involved rook's position, not the king's destination!
        flag = move >> 12
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            piece = KING
        else:
            piece = arBoard[tcord]
        if phase >= 5 or distance[piece][fcord][opking] < \
                distance[piece][fcord][king]:
            yield score - oldscore, _(
                "brings a %(piece)s closer to enemy king: %(cord)s") % {
                    'piece': reprPiece[piece],
                    'cord': reprCord[tcord]}
        else:
            yield (
                score - oldscore) * 2, _("develops a %(piece)s: %(cord)s") % {
                    'piece': reprPiece[piece].lower(),
                    'cord': reprCord[tcord]}


def simple_activity(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    oldboard = model.getBoardAtPly(ply - 1).board
    move = model.getMoveAtPly(ply - 1).move
    fcord = FCORD(move)
    tcord = TCORD(move)

    board.setColor(1 - board.color)
    moves = len([m for m in genAllMoves(board) if FCORD(m) == tcord])
    board.setColor(1 - board.color)
    oldmoves = len([m for m in genAllMoves(oldboard) if FCORD(m) == fcord])

    if moves > oldmoves:
        yield (moves -
               oldmoves) / 2, _("places a %(piece)s more active: %(cord)s") % {
                   'piece': reprPiece[board.arBoard[tcord]].lower(),
                   'cord': reprCord[tcord]}


def tip_pawnStorm(model, ply, phase):
    """ If players are castled in different directions we should storm in
        opponent side """

    if phase >= 6:
        # We don't use this in endgame
        return

    board = model.getBoardAtPly(ply).board

    # if not board.hasCastled[WHITE] or not board.hasCastled[BLACK]:
    #    # Only applies after castling for both sides
    #    return

    wking = board.boards[WHITE][KING]
    bking = board.boards[BLACK][KING]
    wleft = bin(board.boards[WHITE][PAWN] & left).count("1")
    wright = bin(board.boards[WHITE][PAWN] & right).count("1")
    bleft = bin(board.boards[BLACK][PAWN] & left).count("1")
    bright = bin(board.boards[BLACK][PAWN] & right).count("1")

    if wking & left and bking & right:
        if wright > bright:
            yield (wright + 3 -
                   bright) * 10, _("White should do pawn storm in right")
        elif bleft > wleft:
            yield (bright + 3 -
                   wright) * 10, _("Black should do pawn storm in left")
    if wking & right and bking & left:
        if wleft > bleft:
            yield (wleft + 3 -
                   bleft) * 10, _("White should do pawn storm in left")
        if bright > wright:
            yield (bleft + 3 -
                   wleft) * 10, _("Black should do pawn storm in right")


def tip_mobility(model, ply, phase):

    board = model.getBoardAtPly(ply).board
    colorBackup = board.color

    # People need a chance to get developed
    # if model.ply < 16:
    #    return

    board.setColor(WHITE)
    wmoves = len([move for move in genAllMoves(board) if
                  KNIGHT <= board.arBoard[FCORD(move)] <= QUEEN and
                  bitPosArray[TCORD(move)] & brank48[WHITE] and
                  staticExchangeEvaluate(board, move) >= 0])

    board.setColor(BLACK)
    bmoves = len([move for move in genAllMoves(board) if
                  KNIGHT <= board.arBoard[FCORD(move)] <= QUEEN and
                  bitPosArray[TCORD(move)] & brank48[BLACK] and
                  staticExchangeEvaluate(board, move) >= 0])

    board.setColor(colorBackup)

    if wmoves - phase >= (bmoves + 1) * 7:
        yield wmoves - bmoves, _("Black has a rather cramped position")
    elif wmoves - phase >= (bmoves + 1) * 3:
        yield wmoves - bmoves, _("Black has a slightly cramped position")
    elif bmoves - phase >= (wmoves + 1) * 7:
        yield wmoves - bmoves, _("White has a rather cramped position")
    elif bmoves - phase >= (wmoves + 1) * 3:
        yield wmoves - bmoves, _("White has a slightly cramped position")
