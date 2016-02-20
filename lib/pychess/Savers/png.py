# -*- coding: UTF-8 -*-

import cairo

from pychess.gfx import Pieces
from pychess.widgets.BoardView import BoardView

__label__ = _("Png image")
__ending__ = "png"
__append__ = False

PADDING = 3
SQUARE = 40


def save(file, model, position=None):
    """Export the current position into a .png file"""

    d = Diagram(model)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SQUARE * 8, SQUARE * 8)
    context = cairo.Context(surface)

    d.shown = position
    d.draw_position(context)

    surface.write_to_png(file.name)


class Diagram(BoardView):
    def draw_position(self, context):
        context.set_source_rgb(0.5, 0.5, 0.5)
        self.__drawBoard(context)

        pieces = self.model.getBoardAtPly(self.shown)
        context.set_source_rgb(0, 0, 0)
        for y_loc, row in enumerate(pieces.data):
            for x_loc, piece in row.items():
                if piece is not None:
                    Pieces.drawPiece(piece, context, x_loc * SQUARE,
                                     (7 - y_loc) * SQUARE, SQUARE)

    def __drawBoard(self, context):
        for x_loc in range(8):
            for y_loc in range(8):
                if (x_loc + y_loc) % 2 == 1:
                    context.rectangle(x_loc * SQUARE, y_loc * SQUARE, SQUARE, SQUARE)
        context.fill()

        if not self.show_cords:
            context.rectangle(0, 0, 8 * SQUARE, 8 * SQUARE)
            context.stroke()
