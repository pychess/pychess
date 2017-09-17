""" Suicide Variation"""

from pychess.Utils.const import SUICIDECHESS, VARIANTS_OTHER_NONSTANDARD, KING_PROMOTION, \
    QUEEN_PROMOTION, ROOK_PROMOTION, BISHOP_PROMOTION, KNIGHT_PROMOTION
from pychess.Utils.Board import Board

SUICIDESTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"


class SuicideBoard(Board):
    """:Description: This is the FICS version of Losing chess used on FICS as suicide chess.
        You must capture if you can, and the object is to lose all your pieces or to have no moves left.
        But in Suicide, the king is just like any other piece.
        It can move into check and be captured, and you can even promote pawns to kings.
    """
    variant = SUICIDECHESS
    __desc__ = _(
        "FICS suicide: http://www.freechess.org/Help/HelpFiles/suicide_chess.html")
    name = _("Suicide")
    cecp_name = "suicide"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    PROMOTIONS = (KING_PROMOTION, QUEEN_PROMOTION, ROOK_PROMOTION,
                  BISHOP_PROMOTION, KNIGHT_PROMOTION)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=SUICIDESTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


def pieceCount(board, color):
    return bin(board.friends[color]).count("1")


if __name__ == '__main__':
    from pychess.Utils.Move import Move
    from pychess.Utils.lutils.lmove import parseAN
    from pychess.Utils.lutils.lmovegen import genCaptures

    FEN = "rnbqk1nr/pppp1pPp/4p3/8/8/8/PPPbPPP1/RNBQKBNR b - - 7 4"
    game = SuicideBoard(SUICIDESTART)

    game = game.move(Move(parseAN(game.board, "h2h4")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "e7e6")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "h4h5")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "f8b4")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "h5h6")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "b4d2")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "h6g7")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))

    game = game.move(Move(parseAN(game.board, "d2e1")))
    print(game.board.__repr__())
    for move in genCaptures(game.board):
        print(Move(move))
