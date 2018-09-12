# -*- coding: UTF-8 -*-

import math

import cairo

from pychess.System import conf
from pychess.widgets.BoardView import BoardView, matrixAround

__label__ = _("Png image")
__ending__ = "png"
__append__ = False

SQUARE = 40


def save(file, model, position=None, flip=False):
    """Export the current position into a .png file"""

    show_cords = conf.get("showCords")
    boardview = BoardView(model)
    padding = int(SQUARE / 4) if show_cords else 0

    width = SQUARE * 8 + padding * 2
    height = SQUARE * 8 + padding * 2

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)

    boardview.shown = position
    boardview.square = 0 + padding, 0 + padding, SQUARE * 8, SQUARE

    if flip:
        boardview._rotation = math.pi
        boardview.matrix = cairo.Matrix.init_rotate(math.pi)

    boardview.matrix, boardview.invmatrix = matrixAround(boardview.matrix, width / 2., height / 2.)
    context.transform(boardview.matrix)

    boardview.drawBoard(context, None)
    boardview.drawPieces(context, None)

    if show_cords:
        boardview.drawCords(context, None)

    surface.write_to_png(file.name)
