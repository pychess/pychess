import gtk
import cairo

from pychess.gfx.Pieces import drawPiece

class PieceWidget (gtk.DrawingArea):
    def __init__(self, piece):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.piece = piece
    
    def setPiece(self, piece):
        self.piece = piece
    
    def getPiece(self):
        return self.piece
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        rect = self.get_allocation()
        s = min(rect.width, rect.height)
        x = (rect.width-s) / 2.0
        y = (rect.height-s) / 2.0
        drawPiece(self.piece, context, x, y, s)
