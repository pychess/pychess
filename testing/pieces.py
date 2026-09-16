import unittest
from unittest.mock import patch

from pychess.Utils.Piece import Piece
from pychess.Utils.const import HAWK, KNIGHT, SCHESS, WHITE
from pychess.gfx import Pieces


class _Props:
    width = 100
    height = 100


class _Image:
    props = _Props()

    def __init__(self):
        self.rendered = False
        self.rendered_sub = False

    def render_cairo(self, context):
        self.rendered = True

    def render_cairo_sub(self, context, id=None):
        self.rendered_sub = True


class _Context:
    def save(self):
        pass

    def rectangle(self, *args):
        pass

    def clip(self):
        pass

    def translate(self, *args):
        pass

    def scale(self, *args):
        pass

    def push_group(self):
        pass

    def pop_group_to_source(self):
        pass

    def paint_with_alpha(self, *args):
        pass

    def restore(self):
        pass


def _piece_sets(sign, image):
    pieces = [[None] * 9, [None] * 9]
    pieces[WHITE][sign] = image
    return pieces


class PieceRenderingTestCase(unittest.TestCase):
    def test_schess_uses_fixed_set_for_standard_pieces(self):
        selected_image = _Image()
        schess_image = _Image()

        with (
            patch.object(Pieces, "all_in_one", False),
            patch.object(Pieces, "svg_pieces", _piece_sets(KNIGHT, selected_image)),
            patch.object(
                Pieces, "schess_svg_pieces", _piece_sets(KNIGHT, schess_image)
            ),
        ):
            Pieces.drawPiece(
                Piece(WHITE, KNIGHT),
                _Context(),
                0,
                0,
                32,
                variant=SCHESS,
            )

        self.assertTrue(schess_image.rendered)
        self.assertFalse(selected_image.rendered)

    def test_schess_ignores_all_in_one_theme(self):
        selected_image = _Image()
        schess_image = _Image()

        with (
            patch.object(Pieces, "all_in_one", True),
            patch.object(Pieces, "svg_pieces", selected_image),
            patch.object(Pieces, "schess_svg_pieces", _piece_sets(HAWK, schess_image)),
        ):
            Pieces.drawPiece(
                Piece(WHITE, HAWK),
                _Context(),
                0,
                0,
                32,
                variant=SCHESS,
            )

        self.assertTrue(schess_image.rendered)
        self.assertFalse(selected_image.rendered_sub)
