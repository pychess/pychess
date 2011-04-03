from pychess.Utils.Board import Board

class NormalChess:
    __desc__ = _("Classic chess rules\n" +
                 "http://en.wikipedia.org/wiki/Chess")
    name = _("Normal")
    cecp_name = "normal"
    board = Board
    need_initial_board = False
    standard_rules = True

