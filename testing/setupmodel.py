import unittest

from pychess.Utils.SetupModel import SetupModel
from pychess.Utils.const import SCHESS, SETUPCHESS


class SetupModelTestCase(unittest.TestCase):
    def test_display_variant_does_not_change_editor_variant(self):
        model = SetupModel(display_variant=SCHESS)

        self.assertEqual(model.variant.variant, SETUPCHESS)
        self.assertEqual(model.display_variant, SCHESS)
