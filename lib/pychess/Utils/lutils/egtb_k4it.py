import urllib
import re

from pychess.Utils.lutils.lmove import newMove, FILE, RANK
from pychess.Utils.const import *
from pychess.Utils.lutils.bitboard import bitLength

URL = "http://www.k4it.de/egtb/fetch.php?"
expression = re.compile("(\d+)-(\d+)-?(\d+)?: (Win in \d+|Draw|Lose in \d+)")
PROMOTION_FLAGS = {
    8: QUEEN_PROMOTION,
    9: ROOK_PROMOTION,
    10: BISHOP_PROMOTION,
    11: KNIGHT_PROMOTION
}

def probeEndGameTable (board):
    
    # k4it has all 6-men tables except 5 vs. 1
    whites = bitLength(board.friends[WHITE])
    blacks = bitLength(board.friends[BLACK])
    if whites >= 5 or blacks >= 5 or whites+blacks >= 7:
        return []
    
    # Request the page
    data = {
        "action": "egtb",
        "fen": board.asFen()
    }
    f = urllib.urlopen(URL + urllib.urlencode(data))
    data = f.read()
    
    # The response has not only the moves of our requested color, but the
    # the opponents moves as well. We don't use these.
    color_data, opcolor_data = data.split("NEXTCOLOR")
    
    # Parse
    moves = []
    for fcord, tcord, promotion, result in expression.findall(color_data):
        fcord = int(fcord)
        tcord = int(tcord)
        
        if promotion:
            flag = PROMOTION_FLAGS[int(promotion)]
        elif RANK(fcord) != RANK(tcord) and FILE(fcord) != FILE(tcord) and \
                board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY:
            flag = ENPASSANT
        else: flag = NORMAL_MOVE
        
        move = newMove(fcord, tcord, flag)
        
        if result == "Draw":
            state = DRAW
            steps = 0
        else:
            s, steps = result.split(" in ")
            steps = int(steps)
        
        if result.startswith("Win"):
            if board.color == WHITE:
                state = (WHITEWON, int(steps))
            else: state = (BLACKWON, int(steps))
        elif result.startswith("Lose"):
            if board.color == WHITE:
                state = (BLACKWON, int(steps))
            else: state = (WHITEWON, int(steps))
        
        moves.append( (move,state,steps) )
    
    assert moves, repr(data)
    return moves

if __name__ == "__main__":
    from pychess.Utils.lutils.LBoard import LBoard
    board = LBoard(NORMALCHESS)
    board.applyFen("8/k2P4/8/8/8/8/8/4K2R w - - 0 1")
    moves = probeEndGameTable(board)
    print moves
    assert len(moves) == 18
