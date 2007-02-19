def validateMove (board, move):
    pass

def validateBoard (board):
    """ Check the board to make sure that its valid.  Some things to check are
        a.  Both sides have max 1 king and max 8 pawns
        b.  Side not on the move must not be in check.
        c.  If en passant square is set, check it is possible.
        d.  Check if castling status are all correct. """
    
    int side, xside, sq;
    
    # You must place both a Black King and White King on the board
    if nbits (board.b[white][king]) != 1:
        return False
    if nbits (board.b[black][king]) != 1:
        return False
    
    # You can't place a pawn on the eight rank
    if board.b[white][pawn] & rankBits[7]:
        return False
    if board.b[black][pawn] & rankBits[0]:
        return False
    
    # You can't set up a position in which a side has more than eight pawns
    if nbits(board.b[white][pawn]) > 8:
        return False
    if nbits(board.b[black][pawn]) > 8:
        return False
    
    # You can't set up a position in which one side's King is in check and the
    # other side is to move (otherwise it's a position in which mate has
    # already been delivered)
    side = board.side;
    xside = 1^side;
    if SqAtakd (board.king[xside], side):
        return False
    
    if board.ep > -1:
        sq = board.ep + (xside == white ? 8 : -8);
        if not BitPosArray[sq] & board.b[xside][pawn]:
            return False
    
    if board.flag & WKINGCASTLE:
        if not(BitPosArray[E1] & board.b[white][king]):
            return False
        if not(BitPosArray[H1] & board.b[white][rook]):
            return False
    
    if board.flag & WQUEENCASTLE:
        if not(BitPosArray[E1] & board.b[white][king]):
            return False
        if not(BitPosArray[A1] & board.b[white][rook]):
            return False
    
    if board.flag & BKINGCASTLE:
        if not(BitPosArray[E8] & board.b[black][king]):
            return False
        if not(BitPosArray[H8] & board.b[black][rook]):
            return False
    
    if board.flag & BQUEENCASTLE:
        if not(BitPosArray[E8] & board.b[black][king]):
            return False
        if not(BitPosArray[A8] & board.b[black][rook]):
            return False
    
    return True
