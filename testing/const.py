import unittest

from pychess.Utils.const import (
    ASEANCHESS,
    AIWOKCHESS,
    ASEAN_BOARD_VARIANTS,
    CAMBODIANCHESS,
    MAKRUKCHESS,
    MAKRUK_PIECE_VARIANTS,
    SITTUYINCHESS,
)


class AseanDisplayConstantsTestCase(unittest.TestCase):
    def test_asean_uses_western_board_and_non_makruk_pieces(self):
        self.assertNotIn(ASEANCHESS, ASEAN_BOARD_VARIANTS)
        self.assertNotIn(ASEANCHESS, MAKRUK_PIECE_VARIANTS)

    def test_other_asean_variants_keep_existing_special_styles(self):
        self.assertEqual(
            ASEAN_BOARD_VARIANTS,
            (MAKRUKCHESS, CAMBODIANCHESS, AIWOKCHESS, SITTUYINCHESS),
        )
        self.assertEqual(
            MAKRUK_PIECE_VARIANTS, (MAKRUKCHESS, CAMBODIANCHESS, AIWOKCHESS)
        )
