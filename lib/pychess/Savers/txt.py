# -*- coding: utf-8 -*-

from pychess.System import conf
from pychess.Utils.const import FAN_PIECES, BLACK, WHITE

__label__ = _("Text Diagram")
__ending__ = "txt"
__append__ = True


def save(file, model, position=None, flip=False):
    """Export the current position into a .txt file using unicode chars"""

    data = model.boards[position].data[:]

    show_cords = conf.get("showCords")
    cords_side = "12345678" if flip else "87654321"
    cords_bottom = "hgfedcba" if flip else "abcdefgh"

    board = ""
    for j, row in enumerate(data if flip else reversed(data)):
        for i in range(8):
            piece = row.get(i)
            if piece is not None:
                if piece.color == BLACK:
                    piece_fan = FAN_PIECES[BLACK][piece.piece]
                else:
                    piece_fan = FAN_PIECES[WHITE][piece.piece]
                board += piece_fan
            else:
                board += "."
        if show_cords:
            board += cords_side[j]
        board += "\n"

    if show_cords:
        board += cords_bottom + "\n"

    print(board, file=file)

    file.close()
