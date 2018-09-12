# -*- coding: utf-8 -*-

from pychess.Utils.const import FAN_PIECES, BLACK, WHITE

__label__ = _("Text Diagram")
__ending__ = "txt"
__append__ = True


def save(file, model, position=None, flip=False):
    """Export the current position into a .txt file using unicode chars"""

    data = model.boards[position].data[:]

    board = ""
    for row in data if flip else reversed(data):
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
        board += "\n"

    print(board, file=file)

    file.close()
