import os
import tempfile
import unittest

from pychess.Savers import png
from pychess.System import conf
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel


class PngExportTests(unittest.TestCase):
    """Exporting a position must not leak the renderer it builds."""

    def test_export_writes_an_image_and_releases_the_view(self):
        gamemodel = GameModel(TimeModel(60, 0))
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        handle.close()
        self.addCleanup(os.unlink, handle.name)

        listeners_before = len(conf.idkeyfuncs)

        png.save(handle, gamemodel, position=0)

        self.assertGreater(os.path.getsize(handle.name), 0)
        # BoardView registers 18 config listeners in its constructor; they
        # used to stay registered forever, keeping the whole view alive.
        self.assertEqual(len(conf.idkeyfuncs), listeners_before)
