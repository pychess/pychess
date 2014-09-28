from gi.repository import Gtk
from gi.repository import GObject
import cairo

from pychess.gfx import Pieces

class PieceWidget (Gtk.DrawingArea):
    def __init__(self, piece):
        GObject.GObject.__init__(self)        
        self.connect("draw", self.expose)
        self.piece = piece
    
    def setPiece(self, piece):
        self.piece = piece
    
    def getPiece(self):
        return self.piece

    def expose(self, widget, ctx):
        context = widget.get_window().cairo_create()
        rect = self.get_allocation()
        s = min(rect.width, rect.height)
        x = (rect.width-s) / 2.0
        y = (rect.height-s) / 2.0
        Pieces.drawPiece(self.piece, context, x, y, s)
