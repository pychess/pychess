import re

from pychess.compat import urlopen
from pychess.Utils.lutils.lmovegen import newMove
from pychess.Utils.lutils.lmove import FILE, RANK
from pychess.Utils.const import WHITE, DRAW, NORMAL_MOVE, ENPASSANT, \
    EMPTY, PAWN, BLACKWON, WHITEWON, \
    QUEEN_PROMOTION, ROOK_PROMOTION, BISHOP_PROMOTION, KNIGHT_PROMOTION

from pychess.Utils.repr import reprColor
from pychess.System.Log import log
from pychess.System import conf

URL = "http://www.k4it.de/egtb/fetch.php?action=egtb&fen="
expression = re.compile("(\d+)-(\d+)-?(\d+)?: (Win in \d+|Draw|Lose in \d+)")
PROMOTION_FLAGS = {
    2: QUEEN_PROMOTION,
    3: ROOK_PROMOTION,
    4: BISHOP_PROMOTION,
    5: KNIGHT_PROMOTION,
    8: QUEEN_PROMOTION,
    9: ROOK_PROMOTION,
    10: BISHOP_PROMOTION,
    11: KNIGHT_PROMOTION
}


class EgtbK4kit:
    def __init__(self):
        self.table = {}

    def supports(self, size):
        return sum(size) < 7

    def scoreAllMoves(self, board, probeSoft=False):
        global URL, expression, PROMOTION_FLAGS
        fen = board.asFen().split()[0] + " w - - 0 1"
        if (fen, board.color) in self.table:
            return self.table[(fen, board.color)]

        if probeSoft or not conf.get("online_egtb_check", True):
            return []

        # Request the page
        url = (URL + fen).replace(" ", "%20")
        try:
            f = urlopen(url)
        except IOError as e:
            log.warning(
                "Unable to read endgame tablebase from the Internet: %s" %
                repr(e))
            return []
        data = f.read()

        # Parse
        for color, move_data in enumerate(data.split(b"\nNEXTCOLOR\n")):
            try:
                moves = []
                for fcord, tcord, promotion, result in expression.findall(
                        move_data.decode()):
                    fcord = int(fcord)
                    tcord = int(tcord)

                    if promotion:
                        flag = PROMOTION_FLAGS[int(promotion)]
                    elif RANK(fcord) != RANK(tcord) and FILE(fcord) != FILE(tcord) and \
                            board.arBoard[fcord] == PAWN and board.arBoard[tcord] == EMPTY:
                        flag = ENPASSANT
                    else:
                        flag = NORMAL_MOVE

                    move = newMove(fcord, tcord, flag)

                    if result == "Draw":
                        state = DRAW
                        steps = 0
                    else:
                        s, steps = result.split(" in ")
                        steps = int(steps)

                    if result.startswith("Win"):
                        if color == WHITE:
                            state = WHITEWON
                        else:
                            state = BLACKWON
                    elif result.startswith("Lose"):
                        if color == WHITE:
                            state = BLACKWON
                        else:
                            state = WHITEWON

                    moves.append((move, state, steps))

                if moves:
                    self.table[(fen, color)] = moves
                elif color == board.color and board.opIsChecked():
                    log.warning("Asked endgametable for a won position: %s" %
                                fen)
                elif color == board.color:
                    log.warning(
                        "Couldn't get %s data for position %s.\nData was: %s" %
                        (reprColor[color], fen, repr(data)))
            except (KeyError, ValueError):
                log.warning(
                    "Couldn't parse %s data for position %s.\nData was: %s" % (
                        reprColor[color], fen, repr(data)))
                self.table[(fen, color)] = []  # Don't try again.

        if (fen, board.color) in self.table:
            return self.table[(fen, board.color)]
        return []

    def scoreGame(self, board, omitDepth, probeSoft):
        scores = self.scoreAllMoves(board, probeSoft)
        if scores:
            return scores[0][1], scores[0][2]
        return None, None


if __name__ == "__main__":
    from pychess.Utils.lutils.LBoard import LBoard
    from pychess.Utils.lutils.lmove import listToSan
    board = LBoard(NORMALCHESS)

    board.applyFen("8/k2P4/8/8/8/8/8/4K2R w - - 0 1")
    moves = probeEndGameTable(board)
    assert len(moves) == 18, listToSan(board, (move[0] for move in moves))

    board.applyFen("8/p7/6kp/3K4/6PP/8/8/8 b - - 0 1")
    moves = probeEndGameTable(board)
    assert len(moves) == 7, listToSan(board, (move[0] for move in moves))

    board.applyFen("8/p6k/2K5/7R/6PP/8/8/8 b - - 0 66")
    moves = probeEndGameTable(board)
    assert len(moves) == 3, listToSan(board, (move[0] for move in moves))
