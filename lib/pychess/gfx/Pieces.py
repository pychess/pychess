from gi.repository import Rsvg

from pychess.Utils.const import BLACK, WHITE, KING, QUEEN, BISHOP, KNIGHT, ROOK, PAWN, \
    reprSign
from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.System.cairoextras import create_cairo_font_face_for_file


piece_ord = {KING: 0, QUEEN: 1, ROOK: 2, BISHOP: 3, KNIGHT: 4, PAWN: 5}
pnames = ('Pawn', 'Knight', 'Bishop', 'Rook', 'Queen', 'King')

size = 800.0

makruk_svg_pieces = None


def drawPiece3(piece, context, x, y, psize, allwhite=False, asean=False):
    """Rendering pieces using .svg chess figurines"""

    color = WHITE if allwhite else piece.color
    if asean:
        global makruk_svg_pieces
        if makruk_svg_pieces is None:
            makruk_svg_pieces = get_svg_pieces("makruk")
        image = makruk_svg_pieces[color][piece.sign]
        w, h = image.props.width, image.props.height
        offset_x = 0
        offset_y = 0
    elif all_in_one:
        image = svg_pieces
        w, h = image.props.width / 6, image.props.height / 2
        offset_x = piece_ord[piece.sign] * psize
        offset_y = 0 if color == BLACK else psize
    else:
        image = svg_pieces[color][piece.sign]
        w, h = image.props.width, image.props.height
        offset_x = 0
        offset_y = 0

    context.save()

    context.rectangle(x, y, psize, psize)
    context.clip()
    context.translate(x - offset_x, y - offset_y)
    context.scale(1.0 * psize / w, 1.0 * psize / h)

    context.push_group()

    if asean:
        image.render_cairo(context)
    elif all_in_one:
        pieceid = '#%s%s' % ('White' if color == 0 else 'Black',
                             pnames[piece.sign - 1])
        image.render_cairo_sub(context, id=pieceid)
    else:
        image.render_cairo(context)

    context.pop_group_to_source()
    context.paint_with_alpha(piece.opacity)
    context.restore()


def drawPiece4(piece, context, x, y, psize, allwhite=False, asean=False):
    """Rendering pieces using .ttf chessfont figurines"""

    if asean:
        drawPiece3(piece, context, x, y, psize, allwhite=allwhite, asean=True)
        return

    color = WHITE if allwhite else piece.color

    context.set_font_face(chess_font_face)
    context.set_font_size(psize)
    context.move_to(x, y + psize)

    context.text_path(piece2char[color][piece.sign])
    close_path = False
    for cmd, points in context.copy_path():
        if cmd == 0:
            context.move_to(*points)
            if close_path:
                context.set_source_rgb(1, 1, 1)
                context.fill_preserve()
                context.set_source_rgb(0, 0, 0)
                close_path = False
        elif cmd == 1:
            context.line_to(*points)
        elif cmd == 2:
            context.curve_to(*points)
        else:
            close_path = True
    context.fill()


surfaceCache = {}

pieces = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING)


def get_svg_pieces(svgdir):
    """Load figurines from .svg files"""

    if all_in_one:
        rsvg_handles = Rsvg.Handle.new_from_file(addDataPrefix(
            "pieces/%s/%s.svg" % (svgdir, svgdir)))
    else:
        rsvg_handles = [[None] * 7, [None] * 7]
        for c, color in ((WHITE, 'white'), (BLACK, 'black')):
            for p in pieces:
                rsvg_handles[c][p] = Rsvg.Handle.new_from_file(addDataPrefix(
                    "pieces/%s/%s%s.svg" % (svgdir, color[0], reprSign[
                        p].lower())))
    return rsvg_handles


def get_chess_font_face(name):
    """Set chess font and char mapping for a chess .ttf"""
    name = name[4:]
    if name in ('alpha', 'berlin', 'cheq'):
        char_map = ('phbrqk', 'ojntwl')
    else:
        char_map = ('pnbrqk', 'omvtwl')

    piece_chars = [[None] * 7, [None] * 7]
    for color in (WHITE, BLACK):
        for piece, char in zip(pieces, char_map[color]):
            piece_chars[color][piece] = char

    face = create_cairo_font_face_for_file(addDataPrefix("pieces/ttf/%s.ttf" %
                                                         name))
    return face, piece_chars


all_in_one = None
drawPiece = None
svg_pieces = None
chess_font_face = None
piece2char = None


def set_piece_theme(piece_set):
    global all_in_one
    global drawPiece
    global svg_pieces
    global chess_font_face
    global piece2char

    piece_set = piece_set.lower()
    if piece_set == 'pychess':
        from pychess.gfx.pychess_pieces import drawPiece2
        drawPiece = drawPiece2
    elif piece_set.startswith("ttf-"):
        drawPiece = drawPiece4
        try:
            chess_font_face, piece2char = get_chess_font_face(piece_set)
        except Exception:
            from pychess.gfx.pychess_pieces import drawPiece2
            drawPiece = drawPiece2
    elif piece_set in ('celtic', 'eyes', 'fantasy', 'fantasy_alt', 'freak',
                       'prmi', 'skulls', 'spatial'):
        all_in_one = True
        drawPiece = drawPiece3
        svg_pieces = get_svg_pieces(piece_set)
    else:
        all_in_one = False
        drawPiece = drawPiece3
        try:
            svg_pieces = get_svg_pieces(piece_set)
        except Exception:
            from pychess.gfx.pychess_pieces import drawPiece2
            drawPiece = drawPiece2


set_piece_theme(conf.get("pieceTheme"))
