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

    # Keep running the dialog until the user has canceled it or made an error
    # free operation
    while True:
    
        response = dialog.run()
    
        if response == gtk.RESPONSE_CANCEL:
            break

        uri = dialog.get_filename()
        
        if os.path.isfile(uri):
            d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"),
                        gtk.RESPONSE_ACCEPT)

            d.set_title(_("File exists"))
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>A file named '%s' already exists. Would you like to replace it?</b></big>") % file)
            d.format_secondary_text(_("The file already exists in '%s'. If you replace it, its content will be overwritten.") % folder)
            replaceRes = d.run()
            d.hide()

            if replaceRes == gtk.RESPONSE_CANCEL:
                continue

        try:
            surface.write_to_png(uri)
        except IOError, e:
            d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR)
            d.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
            d.set_title(_("Could not save the file"))
            d.set_markup(_("<big><b>PyChess was not able to export the position</b></big>"))
            d.format_secondary_text(_("The error was: %s") % ", ".join(str(a) for a in e.args))
            os.remove(uri)
            d.run()
            d.hide()
            continue

        break
        
    dialog.destroy()


class Diagram(BoardView):
    def draw_position(self, context):
        context.set_source_rgb(0.5, 0.5, 0.5)
        self.__drawBoard (context)

        pieces = self.model.getBoardAtPly(self.shown)
        context.set_source_rgb(0, 0, 0)
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
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
