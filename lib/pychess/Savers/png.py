# -*- coding: UTF-8 -*-

import os

import gtk
import cairo
import rsvg

from pychess.Utils.const import *
from pychess.gfx import Pieces
from pychess.widgets.BoardView import BoardView
from pychess.widgets import gamewidget
from pychess.System.prefix import addDataPrefix


__label__ = _("Png image")
__ending__ = "png"
__append__ = False

PADDING = 3
SQUARE = 40


def save(file, model, position=None):
    """Export the current position into a .png file"""

    d = Diagram(model)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SQUARE*8, SQUARE*8)
    context = cairo.Context(surface)

    d.shown = position
    d.draw_position(context)

    surface.write_to_png(file.name)


class Diagram(BoardView):
    def draw_position(self, context):
        context.set_source_rgb(0.5, 0.5, 0.5)
        self.__drawBoard (context)

        pieces = self.model.getBoardAtPly(self.shown)
        context.set_source_rgb(0, 0, 0)
        for y, row in enumerate(pieces.data):
            for x, piece in row.items():
                if piece is not None:
                    Pieces.drawPiece(piece, context, x*SQUARE, (7-y)*SQUARE, SQUARE)

    def __drawBoard(self, context):
        for x in xrange(8):
            for y in xrange(8):
                if (x+y) % 2 == 1:
                    context.rectangle(x*SQUARE, y*SQUARE, SQUARE, SQUARE)
        context.fill()

        if not self.showCords:
            context.rectangle(0, 0, 8*SQUARE, 8*SQUARE)
            context.stroke()
