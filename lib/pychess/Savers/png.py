# -*- coding: UTF-8 -*-

import cairo

from pychess.widgets.BoardView import BoardView

__label__ = _("Png image")
__ending__ = "png"
__append__ = False

SQUARE = 40


def save(file, model, position=None):
    """Export the current position into a .png file"""

    boardview = BoardView(model)
    padding = int(SQUARE / 4) if boardview.show_cords else 0

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 SQUARE * 8 + padding * 2, SQUARE * 8 + padding * 2)
    context = cairo.Context(surface)

    boardview.shown = position
    boardview.square = 0 + padding, 0 + padding, SQUARE * 8, SQUARE

    boardview.drawBoard(context, None)
    boardview.drawPieces(context, None)

    if boardview.show_cords:
        boardview.drawCords(context, None)

    surface.write_to_png(file.name)
