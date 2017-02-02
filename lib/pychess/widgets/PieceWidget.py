from gi.repository import Gtk, GObject

from pychess.Utils.const import ASEAN_VARIANTS, NORMALCHESS
from pychess.gfx import Pieces


class PieceWidget(Gtk.DrawingArea):
    def __init__(self, piece, variant=NORMALCHESS):
        GObject.GObject.__init__(self)
        self.connect("draw", self.expose)
        self.piece = piece
        self.asean = variant in ASEAN_VARIANTS

    def setPiece(self, piece):
        self.piece = piece

    def getPiece(self):
        return self.piece

    def expose(self, widget, ctx):
        context = widget.get_window().cairo_create()
        rect = self.get_allocation()
        s_min = min(rect.width, rect.height)
        x_loc = (rect.width - s_min) / 2.0
        y_loc = (rect.height - s_min) / 2.0
        Pieces.drawPiece(self.piece, context, x_loc, y_loc, s_min, asean=self.asean)
