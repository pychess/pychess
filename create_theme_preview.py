from __future__ import print_function
import os

from os import listdir
from os.path import isdir, isfile, splitext

from gi.repository import Gtk
import cairo

from pychess.Utils.const import *
from pychess.Utils.Piece import Piece
from pychess.gfx import Pieces
from pychess.System.prefix import addDataPrefix, getUserDataPrefix


SQUARE = 39

PIECES = ((Piece(WHITE, KING), Piece(WHITE, QUEEN), Piece(WHITE, ROOK), None),
          (Piece(WHITE, KNIGHT), Piece(WHITE, BISHOP), None, Piece(BLACK, PAWN)),
          (Piece(WHITE, PAWN), None, Piece(BLACK, BISHOP), Piece(BLACK, KNIGHT)),
          (None, Piece(BLACK, ROOK), Piece(BLACK, QUEEN), Piece(BLACK, KING)))

themes = ['Pychess']

pieces = addDataPrefix("pieces")
themes += [d.capitalize() for d in listdir(pieces) if isdir(os.path.join(pieces,d)) and d != 'ttf']

ttf = addDataPrefix("pieces/ttf")
themes += ['ttf-' + splitext(d)[0].capitalize() for d in listdir(ttf) if splitext(d)[1] == '.ttf']
themes.sort()

for theme in themes:
    pngfile = "%s/%s.png" % (pieces, theme)
    print('Creating %s' % pngfile)
    
    Pieces.set_piece_theme(theme)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SQUARE*4, SQUARE*4)
    
    context = cairo.Context(surface)
    context.set_source_rgb(0.5, 0.5, 0.5)
    
    for x in range(4):
        for y in range(4):
            if (x+y) % 2 == 1:
                context.rectangle(x*SQUARE, y*SQUARE, SQUARE, SQUARE)
    context.fill()

    context.rectangle(0, 0, 4*SQUARE, 4*SQUARE)
    context.stroke()

    context.set_source_rgb(0, 0, 0)
    for y, row in enumerate(PIECES):
        for x, piece in enumerate(row):
            if piece is not None:
                Pieces.drawPiece(piece, context, x*SQUARE, (3-y)*SQUARE, SQUARE)

    surface.write_to_png(pngfile)
