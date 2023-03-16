""" Wildcastle shuffle Chess """

import random

from pychess.Utils.const import WILDCASTLESHUFFLECHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board


class WildcastleShuffleBoard(Board):
    variant = WILDCASTLESHUFFLECHESS
    __desc__ = _(
        "xboard wildcastle http://home.hccnet.nl/h.g.muller/engine-intf.html#8\n"
        + "FICS wild/1: http://www.freechess.org/Help/HelpFiles/wild.html\n"
        + "* In this variant both sides have the same set of pieces as in normal chess.\n"
        + "* The white king starts on d1 or e1 and the black king starts on d8 or e8,\n"
        + "* and the rooks are in their usual positions.\n"
        + "* Bishops are always on opposite colors.\n"
        + "* Subject to these constraints the position of the \
                 pieces on their first ranks is random.\n"
        + "* Castling is done similarly to normal chess:\n"
        + "* o-o-o indicates long castling and o-o short castling."
    )
    name = _("Wildcastle shuffle")
    cecp_name = "wildcastle"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        def get_shuffle():
            positions = [2, 3, 4, 5, 6, 7]
            back_rank = ["r"] + ([""] * 6) + ["r"]

            king = random.choice((4, 5))
            back_rank[king - 1] = "k"
            positions.remove(king)

            bishop = random.choice(positions)
            back_rank[bishop - 1] = "b"
            positions.remove(bishop)
            color = bishop % 2

            bishop = random.choice([i for i in positions if i % 2 != color])
            back_rank[bishop - 1] = "b"
            positions.remove(bishop)

            queen = random.choice(positions)
            back_rank[queen - 1] = "q"
            positions.remove(queen)

            knight = random.choice(positions)
            back_rank[knight - 1] = "n"
            positions.remove(knight)

            knight = random.choice(positions)
            back_rank[knight - 1] = "n"
            positions.remove(knight)

            return "".join(back_rank)

        fen = (
            get_shuffle()
            + "/pppppppp/8/8/8/8/PPPPPPPP/"
            + get_shuffle().upper()
            + " w KQkq - 0 1"
        )

        return fen
