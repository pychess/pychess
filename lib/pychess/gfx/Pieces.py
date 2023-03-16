import sys

import gi

try:
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg
except Exception:
    print("Failed to import required gi module version")
    sys.exit(1)

from pychess.Utils.const import (
    BLACK,
    WHITE,
    KING,
    QUEEN,
    BISHOP,
    KNIGHT,
    ROOK,
    PAWN,
    reprSign,
    SITTUYINCHESS,
    HAWK,
    ELEPHANT,
    SCHESS,
)
from pychess.System import conf
from pychess.System.prefix import addDataPrefix


piece_ord = {KING: 0, QUEEN: 1, ROOK: 2, BISHOP: 3, KNIGHT: 4, PAWN: 5}
pnames = ("Pawn", "Knight", "Bishop", "Rook", "Queen", "King")

size = 800.0


def drawPiece(
    piece,
    context,
    x,
    y,
    psize,
    allwhite=False,
    allpawns=False,
    asean=False,
    variant=None,
):
    """Rendering pieces using .svg chess figurines"""

    color = WHITE if allwhite else piece.color
    sign = PAWN if allpawns else piece.sign
    if variant is not None and variant == SITTUYINCHESS:
        image = sittuyin_svg_pieces[color][sign]
        w, h = image.props.width, image.props.height
        offset_x = 0
        offset_y = 0
    elif asean:
        image = makruk_svg_pieces[color][sign]
        w, h = image.props.width, image.props.height
        offset_x = 0
        offset_y = 0
    elif all_in_one:
        image = svg_pieces
        w, h = image.props.width / 6, image.props.height / 2
        offset_x = piece_ord[sign] * psize
        offset_y = 0 if color == BLACK else psize
    else:
        if variant is not None and variant == SCHESS:
            image = schess_svg_pieces[color][sign]
        else:
            image = svg_pieces[color][sign]
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
        pieceid = "#{}{}".format("White" if color == 0 else "Black", pnames[sign - 1])
        image.render_cairo_sub(context, id=pieceid)
    else:
        image.render_cairo(context)

    context.pop_group_to_source()
    context.paint_with_alpha(piece.opacity)
    context.restore()


surfaceCache = {}

pieces = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, HAWK, ELEPHANT)


def get_svg_pieces(svgdir):
    """Load figurines from .svg files"""

    if all_in_one:
        rsvg_handles = Rsvg.Handle.new_from_file(
            addDataPrefix("pieces/{}/{}.svg".format(svgdir, svgdir))
        )
    else:
        rsvg_handles = [[None] * 9, [None] * 9]
        for c, color in ((WHITE, "white"), (BLACK, "black")):
            for p in pieces:
                if p in (HAWK, ELEPHANT) and svgdir != "merida":
                    continue
                rsvg_handles[c][p] = Rsvg.Handle.new_from_file(
                    addDataPrefix(
                        "pieces/{}/{}{}.svg".format(
                            svgdir, color[0], reprSign[p].lower()
                        )
                    )
                )
    return rsvg_handles


all_in_one = None
svg_pieces = None
makruk_svg_pieces = get_svg_pieces("makruk")
sittuyin_svg_pieces = get_svg_pieces("sittuyin")
schess_svg_pieces = get_svg_pieces("merida")
piece2char = None


def set_piece_theme(piece_set):
    global all_in_one
    global svg_pieces
    global piece2char

    piece_set = piece_set.lower()
    if piece_set in (
        "celtic",
        "eyes",
        "fantasy",
        "fantasy_alt",
        "freak",
        "prmi",
        "skulls",
        "spatial",
    ):
        all_in_one = True
    else:
        all_in_one = False

    try:
        svg_pieces = get_svg_pieces(piece_set)
    except Exception:
        print("Can't create piece set %s" % piece_set)
        all_in_one = False
        svg_pieces = get_svg_pieces("merida")


set_piece_theme(conf.get("pieceTheme"))
