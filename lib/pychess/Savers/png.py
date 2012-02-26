# -*- coding: UTF-8 -*-

import os

import gtk
import cairo
import rsvg

from pychess.Utils.const import *
from pychess.gfx.Pieces import drawPiece
from pychess.widgets.BoardView import BoardView
from pychess.widgets import gamewidget
from pychess.System.prefix import addDataPrefix


PADDING = 3
SQUARE = 40


def export(widget, game):
    """Export the current position into a .png file"""

    d = Diagram(game)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SQUARE*8, SQUARE*8)
    context = cairo.Context(surface)

    d.shown = widget.board.view.shown
    d.draw_position(context)

    dialog = gtk.FileChooserDialog(_("Export position"), None, gtk.FILE_CHOOSER_ACTION_SAVE,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
    dialog.set_current_folder(os.environ["HOME"])

    dialog.set_current_name("%s %s %s.png" %
                            (game.players[0], _("vs."), game.players[1]))

    filter = gtk.FileFilter()
    filter.set_name(_("All files"))
    filter.add_pattern("*")
    dialog.add_filter(filter)

    filter = gtk.FileFilter()
    filter.set_name(_("Images"))
    filter.add_mime_type("image/png")
    filter.add_pattern("*.png")
    dialog.add_filter(filter)
    
    response = dialog.run()
    
    # TODO: error handling
    if response == gtk.RESPONSE_ACCEPT:
        print dialog.get_filename(), 'selected'
        surface.write_to_png(dialog.get_filename())
    elif response == gtk.RESPONSE_CANCEL:
        print 'Closed, no files selected'
    
    dialog.destroy()


class Diagram(BoardView):
    def draw_position(self, context):
        context.set_source_rgba(0.5, 0.5, 0.5)
        self.__drawBoard (context)

        pieces = self.model.getBoardAtPly(self.shown)
        context.set_source_rgba(0, 0, 0)
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if piece is not None:
                    drawPiece(piece, context, x*SQUARE, (7-y)*SQUARE, SQUARE)

    def __drawBoard(self, context):
        for x in xrange(8):
            for y in xrange(8):
                if (x+y) % 2 == 1:
                    context.rectangle(x*SQUARE, y*SQUARE, SQUARE, SQUARE)
        context.fill()
