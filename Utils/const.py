WHITE, BLACK = range(2)

reprColor = ["White", "Black"]

RUNNING, DRAW, WHITEWON, BLACKWON = range(4)

reprResult = ["*", "1/2-1/2", "1-0", "0-1"]

DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, \
    WON_RESIGN, WON_CALLFLAG, WON_MATE = range(7)

KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = range(6)

reprSign = ["K", "Q", "R", "B", "N", "P"]
reprPiece = [_("King"), _("Queen"), _("Rook"), _("Bishop"), _("Knight"), _("Pawn")]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}

WHITE_OO, WHITE_OOO, BLACK_OO, \
    BLACK_OOO, WHITE_CASTLED, BLACK_CASTLED = map(lambda x: 2**x, range(6))
