from pychess.Utils.Board import Board


class NormalChess:
    name = _("Normal")
    variant_name = "normal"
    board = Board
    need_initial_board = False
    standard_rules = True

