import urllib
import re

from pychess.Utils.lutils.lmove import newMove, FILE, RANK
from pychess.Utils.const import *
from pychess.Utils.lutils.bitboard import bitLength
from pychess.System.Log import log

URL = "http://www.k4it.de/egtb/fetch.php?action=egtb&fen="
expression = re.compile("(\d+)-(\d+)-?(\d+)?: (Win in \d+|Draw|Lose in \d+)")
PROMOTION_FLAGS = {
    8: QUEEN_PROMOTION,
    9: ROOK_PROMOTION,
    10: BISHOP_PROMOTION,
    11: KNIGHT_PROMOTION
}

table = {}

def probeEndGameTable (board):
    
    fen = board.asFen().split()[0] + " w - - 0 1"
    if (fen,board.color) in table:
        return table[(fen,board.color)]
    
    # k4it has all 6-men tables except 5 vs. 1
    whites = bitLength(board.friends[WHITE])
    blacks = bitLength(board.friends[BLACK])
    if whites >= 5 or blacks >= 5 or whites+blacks >= 7:
        return []
    
    # Request the page
    f = urllib.urlopen(URL + fen)
    data = f.read()
    
    # Parse
    for color, move_data in enumerate(data.split("\nNEXTCOLOR\n")):
        moves = []
        for fcord, tcord, promotion, result in expression.findall(move_data):
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
        
        if moves:
            table[(fen,board.color)] = moves
        else:
            log.warn("Unable to get egtb data for position: %s.\nData was: %s" %
                     (board.asFen(), repr(data)))
    
    return table[(fen,board.color)]

if __name__ == "__main__":
    from pychess.Utils.lutils.LBoard import LBoard
    board = LBoard(NORMALCHESS)
    board.applyFen("8/k2P4/8/8/8/8/8/4K2R w - - 0 1")
    moves = probeEndGameTable(board)
    print moves
    assert len(moves) == 18
