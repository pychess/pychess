
"""
    This module differs from leval in that it is not optimized for speed.
    It checks differences between last and current board, and returns not
    scores, but strings describing the differences.
    Can be used for commenting on board changes.
"""

import leval
from pychess.Utils.const import *
from lmove import *
from lmovegen import *
from lsort import staticExchangeEvaluate
from ldata import *
from validator import validateMove

#
# Functions can be of types:
#   * Final: Will be shown alone: "mates", "draws"
#   * Moves (s): Will always be shown: "put into *"
#   * Prefix: Will always be shown: "castles", "promotes"
#   * Attack: Will always be shown: "threaten", "preassures", "defendes"
#   * Simple: (s) Max one will be shown: "develops", "activity"
#   * State: (s) Will always be shown: "new *"
#   * Tip: (s) Will sometimes be shown: "pawn storm", "cramped position"
#

def final_status (model, phase):
    if model.status == DRAW:
        yield _("draws")
    elif model.status in (WHITEWON,BLACKWON):
        yield _("mates")

def moves_check (model, phase):
    if model.boards[-1].board.isChecked():
        yield _("puts opponent in check")

def moves_safety (model, phase):
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    
    if board.arBoard[TCORD(model.moves[-1].move)] != KING:
        return
    
    color = oldboard.color
    opcolor = 1-color
    
    kc = board.kings[color]
    okc = oldboard.kings[color]
    s = ((6-phase)*leval.normalKing[kc] + phase*leval.endingKing[kc]) / 6
    os = ((6-phase)*leval.normalKing[okc] + phase*leval.endingKing[okc]) / 6
    
    if s > os:
        pawns = board.boards[color][PAWN]
        if bitLength(frontWall[color][kc] & pawns) == 3:
            yield _("improves king safety")
        else:
            yield _("slightly improves king safety")

def moves_rook (model, phase):
    move = model.moves[-1].move
    tcord = TCORD(move)
    board = model.boards[-1].board
    
    if board.arBoard[tcord] != ROOK:
        return
    
    color = 1-board.color
    opcolor = 1-color
    
    pawns = board.boards[color][PAWN] 
    oppawns = board.boards[opcolor][PAWN] 
    
    ffile = fileBits[FILE(FCORD(move))]
    tfile = fileBits[FILE(tcord)]
    
    if ffile & pawns and not tfile & pawns and bitLength(pawns) >= 3:
        if not tfile & oppawns:
            yield _("moves a rook to an open file")
        else: yield _("moves an rook to a half-open file")

def moves_fianchetto (model, phase):
    
    board = model.boards[-1].board
    tcord = TCORD(model.moves[-1].move)
    movingcolor = 1-board.color
    
    if movingcolor == WHITE:
        if board.castling & W_OO and tcord == G2:
            yield _("moves bishop into fianchetto: %s") % "g2"
        if board.castling & W_OOO and tcord == B2:
            yield _("moves bishop into fianchetto: %s") % "b2"
    else:
        if board.castling & B_OO and tcord == G7:
            yield _("moves bishop into fianchetto: %s") % "g7"
        if board.castling & B_OOO and tcord == B7:
            yield _("moves bishop into fianchetto: %s") % "b7"

def prefix_type (model, phase):
    flag = FLAG(model.moves[-1].move)
    
    if flag in PROMOTIONS:
        yield _("promotes a Pawn to a %s") % reprPiece[flag-3]
                    
    elif flag in (KING_CASTLE, QUEEN_CASTLE):
        yield _("castles")

def attack_type (model, phase):
    
    # We set bishop value down to knight value, as it is what most people expect
    bishopBackup = PIECE_VALUES[BISHOP]
    PIECE_VALUES[BISHOP] = PIECE_VALUES[KNIGHT]
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    
    if len(model.moves) > 1:
        oldmove = model.moves[-2].move
        oldboard3 = model.boards[-3].board
    else: oldmove = None
    move = model.moves[-1].move
    tcord = TCORD(move)
    
    if oldboard.arBoard[tcord] != EMPTY:
        if not (board.variant == FISCHERRANDOMCHESS and \
            FLAG(move) in (KING_CASTLE, QUEEN_CASTLE)): 
            if oldmove and oldboard3.arBoard[TCORD(oldmove)] != EMPTY and \
                    TCORD(oldmove) == tcord:
                yield _("takes back material")
            else:
                see = staticExchangeEvaluate(oldboard, move)
                if see == 0:
                    yield _("exchanges material")
                elif see > 0:
                    yield _("captures material")
                elif see < 0:
                    yield _("sacrifies material")
    
    # ------------------------------------------------------------------------ #
    # Test if we threats something, or at least puts more preassure on it      #
    # ------------------------------------------------------------------------ #
    
    # What do we attack now?
    board.setColor(1-board.color)
    for ncap in genCaptures(board):
        
        # getCaptures also generate promotions
        if FLAG(ncap) in PROMOTIONS:
            continue
        
        # We are only interested in the attacks of the piece we just moved
        if FCORD(ncap) != TCORD (move):
            continue
        
        # We don't thread the king. We check him! (in another function)
        if board.arBoard[TCORD(ncap)] == KING:
            continue
        
        # If we also was able to attack that cord last time, we don't care
        if validateMove(oldboard, newMove(FCORD(move), TCORD(ncap))):
            continue
        
        # We will always attack first with the lowest valued piece.
        # Where is it?
        lowest = None
        cord = None
        attacks = getAttacks (board, TCORD(ncap), board.color)
        for fcord in iterBits(attacks):
            v = PIECE_VALUES[board.arBoard[fcord]]
            if lowest == None or v < lowest:
                lowest = v
                cord = fcord
        assert cord != None, "How can there not be any attacks, when ncap exists? %s" % toString(attacks)
        easiestAttack = newMove(cord, TCORD(ncap))
        
        # Now test if we threats our enemy, or they are too strong
        see = staticExchangeEvaluate(board, easiestAttack)
        if see > 0:
            # If a new winning capture has been created
            yield _("threatens to win material %s") % toSAN(board,easiestAttack, True)
        elif bitLength(attacks) > 1:
            # Even though we might not yet be strong enough, we might still
            # have strengthened another friendly attack
            yield _("increases the pressure on %s") % reprCord[TCORD(ncap)]
    board.setColor(1-board.color)
    
    # ------------------------------------------------------------------------ #
    # Test if we defend a one of our pieces                                    #
    # ------------------------------------------------------------------------ #
    
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
        
        # If we were already defending the piece, we don't send a new message
        if defends(oldboard, FCORD(move), TCORD(ncap)):
            continue
        
        # If the attack was not strong, we ignore it
        oldboard.setColor(1-oldboard.color)
        see = staticExchangeEvaluate(oldboard, ncap)
        oldboard.setColor(1-oldboard.color)
        if see < 0: continue
        
        v = defends(board, TCORD(move), TCORD(ncap))
        
        # If the defend didn't help, it doesn't matter. Like defending a bishop,
        # threatened by a pawn, with a queen.
        # But on the other hand - it might still be a defend...
        # newsee = staticExchangeEvaluate(board, ncap)
        # if newsee <= see: continue
        
        if v:
            yield _("defends %s") % reprCord[TCORD(ncap)]
            
    PIECE_VALUES[BISHOP] = bishopBackup
    
def state_outpost (model, phase):
    
    if phase >= 6:
        # Doesn't make sense in endgame
        return
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    color = 1-board.color
    opcolor = 1-color
    
    wpawns = board.boards[WHITE][PAWN]
    oldwpawns = oldboard.boards[WHITE][PAWN]
    bpawns = board.boards[BLACK][PAWN]
    oldbpawns = oldboard.boards[BLACK][PAWN]
    
    wpieces = board.boards[WHITE][BISHOP] | board.boards[WHITE][KNIGHT]
    oldwpieces = oldboard.boards[WHITE][BISHOP] | oldboard.boards[WHITE][KNIGHT]
    bpieces = board.boards[BLACK][BISHOP] | board.boards[BLACK][KNIGHT]
    oldbpieces = oldboard.boards[BLACK][BISHOP] | oldboard.boards[BLACK][KNIGHT]
    
    for cord in iterBits(wpieces):
        sides = isolaniMask[FILE(cord)]
        front = passedPawnMask[WHITE][cord]
        if outpost[WHITE][cord] and not bpawns & sides & front and \
                (not oldwpieces & bitPosArray[cord] or \
                 oldbpawns & sides & front):
            yield 35, _("White has a new piece in outpost: %s") % reprCord[cord]
    
    for cord in iterBits(bpieces):
        sides = isolaniMask[FILE(cord)]
        front = passedPawnMask[BLACK][cord]
        if outpost[BLACK][cord] and not wpawns & sides & front and \
                (not oldbpieces & bitPosArray[cord] or \
                 oldwpawns & sides & front):
            yield 35, _("Black has a new piece in outpost: %s") % reprCord[cord]
    
def state_pawn (model, phase):
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    color = 1-board.color
    opcolor = 1-color
    
    move = model.moves[-1].move
    
    pawns = board.boards[color][PAWN]
    oppawns = board.boards[opcolor][PAWN]
    oldpawns = oldboard.boards[color][PAWN]
    oldoppawns = oldboard.boards[opcolor][PAWN]
    
    # Passed pawns
    for cord in iterBits(pawns):
        if not oppawns & passedPawnMask[color][cord]:
            if color == WHITE:
                frontCords = fromToRay[cord][cord|56]
            else: frontCords = fromToRay[cord][cord&7]
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
            
            score = (passedScores[color][cord>>3] * phase)
            yield score, _("%s has a new passed pawn on %s") % \
                    (reprColor[color], reprCord[cord])
    
    # Double pawns
    for file in range(8):
        bits = fileBits[file]
        
        count = bitLength(pawns & bits)
        oldcount = bitLength(oldpawns & bits)
        opcount = bitLength(oppawns & bits)
        oldopcount = bitLength(oldoppawns & bits)
        
        # Double pawns
        if count > oldcount >= 1:
            if not opcount:
                yield (8+phase)*2, \
                    _("%s has a new double pawn in the half-open %s file") % \
                            (reprColor[color], reprFile[file])
            else:
                yield 8+phase, _("%s has a new double pawn in the %s file") % \
                        (reprColor[color], reprFile[file])
                        
        elif count > 1 and opcount == 0 and oldopcount > 0:
            yield (8+phase)*2, \
                _("%s has an double pawn in the half-open %s file") % \
                            (reprColor[color], reprFile[file])
        
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
            yield 20, _("%s has a new isolated pawn in the %s file") % \
                            (reprColor[WHITE], reprFile[file])
        
        if bpawns & bits and not bpawns & isolaniMask[file] and \
                (not oldbpawns & bits or oldbpawns & isolaniMask[file]):
            yield 20, _("%s has a new isolated pawn in the %s file") % \
                            (reprColor[BLACK], reprFile[file])
    
    # Stone wall
    if stonewall[color] & pawns == stonewall[color] and \
       stonewall[color] & oldpawns != stonewall[color]:
        yield 10, _("%s moves pawns into stonewall formation") % reprColor[color]

def state_destroysCastling (model, phase):
    """ Does the move destroy the castling ability of the opponent """
    
    # If the move is a castling, nobody will every care if the castling
    # possibilities has changed
    if FLAG(model.moves[-1].move) in (QUEEN_CASTLE, KING_CASTLE):
        return
    
    oldcastling = model.boards[-2].board.castling
    castling = model.boards[-1].board.castling
    
    if oldcastling & W_OOO and not castling & W_OOO:
        yield 400/phase, _("White can no longer castle in queenside")
    if oldcastling & W_OO and not castling & W_OO:
        yield 500/phase, _("White can no longer castle in kingside")
        
    if oldcastling & B_OOO and not castling & B_OOO:
        yield 400/phase, _("Black can no longer castle in queenside")
    if oldcastling & B_OO and not castling & B_OO:
        yield 500/phase, _("Black can no longer castle in kingside")

def state_trappedBishops (model, phase):
    """ Check for bishops trapped at A2/H2/A7/H7 """
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    
    opcolor = board.color
    color = 1-opcolor
    
    move = model.moves[-1].move
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
    
    s = leval.evalTrappedBishops (board, opcolor, phase)
    olds = leval.evalTrappedBishops (oldboard, opcolor, phase)
    
    # We have got more points -> We have trapped a bishop
    if s > olds:
        yield 300/phase, _("%s has a new trapped bishop on %s") % \
                            (reprColor[opcolor], reprCord[cord])

def simple_tropism (model, phase):
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    color = oldboard.color

    move = model.moves[-1].move
    fcord = FCORD(move)
    tcord = TCORD(move)
    arBoard = board.arBoard
    
    if arBoard[tcord] != PAWN:
        score = leval.evalKingTropism(board, color, phase)
        oldscore = leval.evalKingTropism(oldboard, color, phase)
    else:
        if color == WHITE:
            rank23 = brank67[BLACK]
        else: rank23 = brank67[WHITE]
        if bitPosArray[fcord] & rank23:
            yield 2, _("develops a %s: %s") % (reprPiece[PAWN], reprCord[tcord])
        else: yield 1, _("brings a pawn closer to the backrow: %s") % \
                                                                 reprCord[tcord]
        return
        
    king = board.kings[color]
    opking = board.kings[1-color]
    
    if score > oldscore:
        if phase >= 5 or distance[arBoard[tcord]][fcord][opking] < \
                distance[arBoard[tcord]][fcord][king]:
            yield score-oldscore, _("brings a %s closer to enemy king: %s") % \
                    (reprPiece[arBoard[tcord]], reprCord[tcord])
        else:
            yield (score-oldscore)*2, _("develops a %s: %s") % \
                    (reprPiece[arBoard[tcord]], reprCord[tcord])

def simple_activity (model, phase):
    
    board = model.boards[-1].board
    oldboard = model.boards[-2].board
    color = 1-board.color
    move = model.moves[-1].move
    fcord = FCORD(move)
    tcord = TCORD(move)
    
    board.setColor(1-board.color)
    moves = len([m for m in genAllMoves(board) if FCORD(m) == tcord])
    board.setColor(1-board.color)
    oldmoves = len([m for m in genAllMoves(oldboard) if FCORD(m) == fcord])
    
    if moves > oldmoves:
        yield (moves-oldmoves)/2, _("places a %s more active: %s") % \
                (reprPiece[board.arBoard[tcord]], reprCord[tcord])

def tip_pawnStorm (model, phase):
    """ If players are castled in different directions we should storm in
        opponent side """
    
    if phase >= 6:
        # We don't use this in endgame
        return
    
    board = model.boards[-1].board
    
    #if not board.hasCastled[WHITE] or not board.hasCastled[BLACK]:
    #    # Only applies after castling for both sides
    #    return
    
    wking = board.boards[WHITE][KING]
    bking = board.boards[BLACK][KING]
    wleft = bitLength(board.boards[WHITE][PAWN] & left)
    wright = bitLength(board.boards[WHITE][PAWN] & right)
    bleft = bitLength(board.boards[BLACK][PAWN] & left)
    bright = bitLength(board.boards[BLACK][PAWN] & right)
    
    if wking & left and bking & right:
        if wright > bright:
            yield (wright+3-bright)*10, _("White should do pawn storm in right")
        elif bleft > wleft:
            yield (bright+3-wright)*10, _("Black should do pawn storm in left")
    if wking & right and bking & left:
        if wleft > bleft:
            yield (wleft+3-bleft)*10, _("White should do pawn storm in left")
        if bright > wright:
            yield (bleft+3-wleft)*10, _("Black should do pawn storm in right")

def tip_mobility (model, phase):
    
    board = model.boards[-1].board
    colorBackup = board.color
    
    # People need a chance to get developed
    #if model.ply < 16:
    #    return
    
    board.setColor(WHITE)
    wmoves = len([move for move in genAllMoves(board) if \
                        KNIGHT <= board.arBoard[FCORD(move)] <= QUEEN and \
                        bitPosArray[TCORD(move)] & brank48[WHITE] and \
                        staticExchangeEvaluate(board, move) >= 0])
    
    board.setColor(BLACK)
    bmoves = len([move for move in genAllMoves(board) if \
                        KNIGHT <= board.arBoard[FCORD(move)] <= QUEEN and \
                        bitPosArray[TCORD(move)] & brank48[BLACK] and \
                        staticExchangeEvaluate(board, move) >= 0])
    
    board.setColor(colorBackup)
    
    #print wmoves, bmoves, phase
    
    #wb = board.boards[WHITE]
    #print float(wmoves)/bitLength(wb[KNIGHT]|wb[BISHOP]|wb[ROOK]|wb[QUEEN])
    #bb = board.boards[WHITE]
    #print float(bmoves)/bitLength(bb[KNIGHT]|bb[BISHOP]|bb[ROOK]|bb[QUEEN])
    
    if wmoves-phase >= (bmoves+1)*7:
        yield wmoves-bmoves, _("Black has a rather cramped position")
    elif wmoves-phase >= (bmoves+1)*3:
        yield wmoves-bmoves, _("Black has a slightly cramped position")
    elif bmoves-phase >= (wmoves+1)*7:
        yield wmoves-bmoves, _("White has a rather cramped position")
    elif bmoves-phase >= (wmoves+1)*3:
        yield wmoves-bmoves, _("White has a slightly cramped position")
